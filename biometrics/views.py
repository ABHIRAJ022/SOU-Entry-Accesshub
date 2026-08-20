import json
import secrets
from datetime import timedelta
from django.utils import timezone

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .crypto import decrypt_vector, encrypt_vector
from .models import FaceProfile
from .vision import VisionError, analyze_frame, average_vectors, compare_vector, decode_webcam_frame, has_liveness_variation

MIN_FRAMES = 5
MAX_FRAMES = 10


def _error(message, status=400):
    return JsonResponse({'verified': False, 'error': message}, status=status)


def _payload(request):
    if int(request.META.get('CONTENT_LENGTH') or 0) > settings.BIOMETRIC_MAX_REQUEST_BYTES:
        raise VisionError('The capture payload is too large.')
    if not request.content_type.startswith('application/json'):
        raise VisionError('Biometric requests must use application/json.')
    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisionError('The biometric request is not valid JSON.') from exc
    if not isinstance(payload, dict):
        raise VisionError('The biometric request must be a JSON object.')
    return payload


def _frames(request, payload):
    if payload.get('capture_mode') != 'webcam':
        raise VisionError('Only live webcam capture is accepted.')
    if payload.get('capture_id') != request.session.get('biometric_capture_id'):
        raise VisionError('This capture session expired. Reload the camera page.')
    frames = payload.get('frames')
    if not isinstance(frames, list) or not MIN_FRAMES <= len(frames) <= MAX_FRAMES:
        raise VisionError(f'Send between {MIN_FRAMES} and {MAX_FRAMES} sequential webcam frames.')
    analyses = []
    previous_timestamp = 0
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or frame.get('sequence') != index:
            raise VisionError('Webcam frames must have contiguous sequence numbers.')
        timestamp = int(frame.get('timestamp_ms') or 0)
        if timestamp <= previous_timestamp:
            raise VisionError('Webcam frame timestamps must be increasing.')
        previous_timestamp = timestamp
        analyses.append(analyze_frame(decode_webcam_frame(frame.get('data'))))
    return analyses


def _require_secure_camera(request):
    if not request.is_secure():
        raise VisionError('Camera enrollment and verification require HTTPS.')
    if not request.user.is_authenticated and not request.session.get('pending_biometric_email'):
        raise VisionError('Authentication is required.', 401)
    if request.user.is_authenticated:
        if not request.user.can_login:
            raise VisionError('Your account must be verified and approved before biometric access.', 403)


def _pending_user(request):
    from accounts.models import User
    email = request.session.get('pending_biometric_email')
    return User.objects.filter(email=email, is_email_verified=True).first() if email else None


def _capture_owner(request):
    return request.user if request.user.is_authenticated else _pending_user(request)


def has_recent_live_verification(request, email=None):
    verified_email = request.session.get('live_face_verified_email')
    timestamp = request.session.get('live_face_verified_at', 0)
    return bool(verified_email and (email is None or verified_email == email) and timezone.now().timestamp() - float(timestamp) <= settings.BIOMETRIC_VERIFICATION_MAX_AGE_SECONDS)


@require_GET
@ensure_csrf_cookie
def enrollment_page(request):
    owner = _capture_owner(request)
    if not owner:
        return render(request, 'biometrics/enroll.html', {'error': 'Sign in or complete email verification before enrolling your live face.'}, status=403)
    request.session['biometric_capture_id'] = secrets.token_urlsafe(24)
    return render(request, 'biometrics/enroll.html', {'capture_id': request.session['biometric_capture_id'], 'mode': 'enroll'})


@require_GET
@login_required
@ensure_csrf_cookie
def verification_page(request):
    request.session['biometric_capture_id'] = secrets.token_urlsafe(24)
    return render(request, 'biometrics/enroll.html', {'capture_id': request.session['biometric_capture_id'], 'mode': 'verify'})


@require_POST
@csrf_protect
def enroll(request):
    try:
        _require_secure_camera(request)
        owner = _capture_owner(request)
        if not owner:
            raise VisionError('Authentication or verified registration is required.', 401)
        payload = _payload(request)
        analyses = _frames(request, payload)
        if not has_liveness_variation(analyses):
            return _error('Liveness check failed. Blink or slowly move your head during capture.')
        vector = average_vectors([analysis[0] for analysis in analyses])
        profile, _ = FaceProfile.objects.update_or_create(user=owner, defaults={'encrypted_vector': encrypt_vector(vector), 'samples_count': len(analyses)})
        request.session.pop('biometric_capture_id', None)
        if not request.user.is_authenticated:
            request.session['registration_face_complete'] = owner.email
            request.session.pop('pending_biometric_email', None)
        return JsonResponse({'enrolled': True, 'registration_complete': not request.user.is_authenticated, 'samples': profile.samples_count, 'message': 'Biometric enrollment completed securely.'})
    except VisionError as exc:
        message = str(exc)
        return _error(message, 401 if 'Authentication' in message else (403 if 'HTTPS' in message or 'approved' in message else 400))


@require_POST
@csrf_protect
@login_required
def verify(request):
    try:
        _require_secure_camera(request)
        profile = FaceProfile.objects.filter(user=request.user).first()
        if not profile:
            return _error('No biometric profile is enrolled.', 404)
        payload = _payload(request)
        analyses = _frames(request, payload)
        if not has_liveness_variation(analyses):
            return _error('Liveness check failed. Blink or slowly move your head during capture.')
        stored = decrypt_vector(profile.encrypted_vector)
        distances = [compare_vector(analysis[0], stored) for analysis in analyses]
        distance, confidence = min(distances, key=lambda item: item[0])
        verified = confidence >= settings.BIOMETRIC_MATCH_THRESHOLD
        request.session.pop('biometric_capture_id', None)
        if verified:
            request.session['live_face_verified_email'] = request.user.email
            request.session['live_face_verified_at'] = timezone.now().timestamp()
        return JsonResponse({'verified': verified, 'confidence': round(confidence, 4), 'distance': round(distance, 4), 'error': None if verified else 'Face did not match the enrolled profile.'})
    except VisionError as exc:
        message = str(exc)
        return _error(message, 401 if 'Authentication' in message else (403 if 'HTTPS' in message or 'approved' in message else 400))


@require_POST
@csrf_protect
def login_verify(request):
    try:
        _require_secure_camera(request)
        from accounts.models import User
        payload = _payload(request)
        email = str(payload.get('email', '')).strip().lower()
        user = User.objects.filter(email=email, is_active=True).first()
        profile = FaceProfile.objects.filter(user=user).first() if user else None
        if not user or not profile:
            raise VisionError('Live face verification could not be completed.')
        analyses = _frames(request, payload)
        if not has_liveness_variation(analyses):
            return _error('Liveness check failed. Blink or slowly move your head during capture.')
        stored = decrypt_vector(profile.encrypted_vector)
        distance, confidence = min((compare_vector(analysis[0], stored) for analysis in analyses), key=lambda item: item[0])
        if confidence < settings.BIOMETRIC_MATCH_THRESHOLD:
            return _error('Live face did not match this account.')
        request.session['live_face_verified_email'] = user.email
        request.session['live_face_verified_at'] = timezone.now().timestamp()
        return JsonResponse({'verified': True, 'confidence': round(confidence, 4)})
    except VisionError as exc:
        return _error(str(exc), 403 if 'HTTPS' in str(exc) else 400)
