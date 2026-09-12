import base64
import binascii
import json
import secrets
from datetime import timedelta
from io import BytesIO
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit
from PIL import Image, UnidentifiedImageError

from accounts.models import EmailOTP
from .models import IdentityVerification
from .snapshots import SnapshotError, process_webcam_snapshot

MAX_SNAPSHOT_BYTES = 200 * 1024


class IdentityError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _error(message, status=400):
    return JsonResponse({'verified': False, 'error': message}, status=status)


def _payload(request):
    if int(request.META.get('CONTENT_LENGTH') or 0) > settings.IDENTITY_MAX_REQUEST_BYTES:
        raise IdentityError('The verification payload is too large.')
    if request.content_type != 'application/json':
        raise IdentityError('Identity verification must use application/json.')
    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityError('The verification request is not valid JSON.') from exc
    if not isinstance(payload, dict):
        raise IdentityError('The verification request must be a JSON object.')
    return payload


def _snapshot(payload, request):
    if payload.get('capture_mode') != 'webcam':
        raise IdentityError('Only live webcam capture is accepted.')
    if payload.get('capture_id') != request.session.get('identity_capture_id'):
        raise IdentityError('This camera session expired. Reload the verification page.')
    try:
        captured_at = float(payload.get('captured_at'))
    except (TypeError, ValueError) as exc:
        raise IdentityError('A live capture timestamp is required.') from exc
    now = timezone.now().timestamp()
    if captured_at > now + 5 or now - captured_at > 120:
        raise IdentityError('The webcam snapshot is stale. Capture a new image.')
    data = payload.get('image')
    if not isinstance(data, str) or not data.startswith('data:image/jpeg;base64,'):
        raise IdentityError('Only a JPEG snapshot from the live webcam is accepted.')
    try:
        return process_webcam_snapshot(payload)
    except SnapshotError as exc:
        raise IdentityError(str(exc)) from exc


def _valid_user(request):
    if not request.user.is_authenticated:
        raise IdentityError('Authentication is required.', 401)
    if not request.user.can_login:
        raise IdentityError('Your account must be verified and approved before identity verification.', 403)
    if not request.is_secure():
        raise IdentityError('Camera verification requires HTTPS.', 403)
    return request.user


def _verification_code(user):
    code = f'{secrets.randbelow(10000):04d}'
    user.otps.filter(used_at__isnull=True).update(used_at=timezone.now())
    EmailOTP.objects.create(user=user, code_hash=make_password(code))
    send_mail('Your SOU Entry AccessHub identity verification code', f'Hello {user.full_name},\n\nYour identity verification code for SOU Entry AccessHub is:\n\n{code}\n\nThis code expires in 10 minutes and can be used only for the current verification attempt. Do not share it. If you did not request identity verification, contact your campus administrator.', settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def has_recent_identity_verification(request):
    verification_id = request.session.get('identity_verification_id')
    timestamp = float(request.session.get('identity_verified_at', 0) or 0)
    if not verification_id or timezone.now().timestamp() - timestamp > settings.IDENTITY_VERIFICATION_MAX_AGE_SECONDS:
        return False
    verification = IdentityVerification.objects.filter(pk=verification_id, user=request.user).first()
    return bool(verification and verification.is_valid)


has_recent_live_verification = has_recent_identity_verification


@require_GET
@login_required
@ensure_csrf_cookie
def verification_page(request):
    request.session['identity_capture_id'] = secrets.token_urlsafe(24)
    return render(request, 'biometrics/enroll.html', {'capture_id': request.session['identity_capture_id']})


@require_POST
@csrf_protect
@login_required
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def request_emergency_otp(request):
    try:
        user = _valid_user(request)
        _verification_code(user)
        return JsonResponse({'sent': True, 'message': 'A four-digit emergency code was sent to your registered email.'})
    except IdentityError as exc:
        return _error(str(exc), exc.status)
    except (OSError, SMTPException):
        return _error('The emergency code could not be sent. Try again later.', 503)


@require_POST
@csrf_protect
@login_required
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def verify_identity(request):
    try:
        user = _valid_user(request)
        payload = _payload(request)
        snapshot = _snapshot(payload, request)
        otp_code = str(payload.get('otp') or '').strip()
        verified = False
        if len(otp_code) == 4 and otp_code.isdigit():
            otp = user.otps.filter(used_at__isnull=True).order_by('-created_at').first()
            verified = bool(otp and otp.is_valid() and check_password(otp_code, otp.code_hash))
            if verified:
                otp.used_at = timezone.now()
                otp.save(update_fields=['used_at'])
            elif otp:
                otp.attempts = min(otp.attempts + 1, 255)
                otp.save(update_fields=['attempts'])
        else:
            return _error('Enter the four-digit emergency code sent to your email or request one.')
        if not verified:
            return _error('Identity verification failed. Check your emergency code.')
        verification = IdentityVerification.objects.create(user=user, audit_snapshot=snapshot, snapshot_size=len(snapshot), verification_method='webcam', expires_at=timezone.now() + timedelta(seconds=settings.IDENTITY_VERIFICATION_MAX_AGE_SECONDS))
        request.session['identity_verified'] = True
        request.session['identity_verification_id'] = str(verification.pk)
        request.session['identity_verified_at'] = timezone.now().timestamp()
        request.session.pop('identity_capture_id', None)
        return JsonResponse({'verified': True, 'expires_in': settings.IDENTITY_VERIFICATION_MAX_AGE_SECONDS})
    except IdentityError as exc:
        return _error(str(exc), exc.status)
