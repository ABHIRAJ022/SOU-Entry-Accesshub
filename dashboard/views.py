from functools import wraps
import base64
import json
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from biometrics.snapshots import SnapshotError, process_webcam_snapshot
from accounts.models import User
from .models import CampusToken, TokenAudit
from .token_utils import pdf_pass, qr_png, signed_payload, token_from_signed_payload
from .models import CampusLocation
from .notifications import send_account_approved, send_token_created, send_token_expiry_notice

TOKEN_DURATIONS = {30, 60, 120, 180, 240, 300, 360, 420, 480}

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles: return JsonResponse({'error': 'Forbidden'}, status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

@role_required(User.Role.ADMIN, User.Role.SECURITY, User.Role.STUDENT)
def home(request):
    if request.user.role == User.Role.ADMIN: return admin_dashboard(request)
    if request.user.role == User.Role.SECURITY: return security_dashboard(request)
    now = timezone.now()
    request.user.campus_tokens.filter(revoked_at__isnull=True, expires_at__lte=now).update(revoked_at=now)
    tokens = request.user.campus_tokens.order_by('-created_at')
    active_token = tokens.filter(revoked_at__isnull=True, expires_at__gt=now).first()
    latest_token = tokens.first()
    return render(request, 'dashboard/student.html', {
        'student': request.user,
        'email_verified': request.user.is_email_verified,
        'approval_status': 'approved' if request.user.is_approved_by_admin else ('rejected' if not request.user.is_active else 'pending'),
        'active_token': active_token,
        'active_token_qr': 'data:image/png;base64,' + base64.b64encode(qr_png(active_token)).decode() if active_token else '',
        'latest_token': latest_token,
        'latest_token_qr': 'data:image/png;base64,' + base64.b64encode(qr_png(latest_token)).decode() if latest_token else '',
        'token_history': tokens[:20],
    })

@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    students = User.objects.filter(role=User.Role.STUDENT)
    if not request.user.is_superuser:
        students = students.filter(branch=request.user.branch)
    staff_approvals = User.objects.none()
    if request.user.is_superuser:
        staff_approvals = User.objects.filter(role__in=(User.Role.ADMIN, User.Role.SECURITY), is_superuser=False)
    return render(request, 'dashboard/admin.html', {
        'students': students,
        'staff_approvals': staff_approvals,
        'is_super_admin': request.user.is_superuser,
        'branch': request.user.branch,
        'total_students': students.count(),
        'pending': students.filter(is_approved_by_admin=False, is_active=True, is_email_verified=True).count(),
        'active_staff': User.objects.filter(role=User.Role.SECURITY, is_active=True, is_approved_by_super_admin=True).count(),
    })

@role_required(User.Role.SECURITY)
def security_dashboard(request): return render(request, 'dashboard/security.html')

@require_POST
@role_required(User.Role.ADMIN)
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id); action = request.POST.get('action')
    if action not in {'approve', 'reject', 'revoke'}: return JsonResponse({'error': 'Invalid action'}, status=400)
    if user.role == User.Role.STUDENT:
        if not request.user.is_superuser and (request.user.role != User.Role.ADMIN or request.user.branch_id != user.branch_id):
            return JsonResponse({'error': 'You can only manage students in your assigned branch.'}, status=403)
        user.is_approved_by_admin = action == 'approve'
        user.is_active = action == 'approve'
        user.save(update_fields=['is_approved_by_admin', 'is_active'])
        if action == 'approve':
            send_account_approved(user)
        return JsonResponse({'status': 'approved' if action == 'approve' else ('revoked' if action == 'revoke' else 'rejected')})
    if user.role in {User.Role.ADMIN, User.Role.SECURITY} and request.user.is_superuser:
        user.is_approved_by_super_admin = action == 'approve'
        user.is_active = action == 'approve'
        user.save(update_fields=['is_approved_by_super_admin', 'is_active'])
        if action == 'approve':
            send_account_approved(user)
        return JsonResponse({'status': 'approved' if action == 'approve' else ('revoked' if action == 'revoke' else 'rejected')})
    return JsonResponse({'error': 'Only the main super administrator can manage staff accounts.'}, status=403)

@require_GET
@role_required(User.Role.SECURITY)
def student_lookup(request):
    query = request.GET.get('q', '').strip()[:32]
    users = User.objects.filter(role=User.Role.STUDENT).filter(Q(enrollment_number__icontains=query) | Q(full_name__icontains=query))[:10] if query else []
    return JsonResponse({'results': [{'name': user.full_name, 'enrollment_number': user.enrollment_number, 'email_verified': user.is_email_verified, 'approved': user.is_approved_by_admin, 'active': user.is_active} for user in users]})

@require_POST
@role_required(User.Role.STUDENT)
def issue_token(request):
    if not request.user.can_login:
        return JsonResponse({'error': 'Your account must be verified and approved before requesting a token.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
        duration = int(payload.get('duration_minutes', 30))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Choose a valid token duration.'}, status=400)
    if duration not in TOKEN_DURATIONS:
        return JsonResponse({'error': 'Token duration must be 30 minutes or between 1 and 8 hours.'}, status=400)
    try:
        snapshot = process_webcam_snapshot(payload)
    except SnapshotError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    with transaction.atomic():
        try:
            token, raw_token = CampusToken.issue(request.user, duration)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=409)
        TokenAudit.objects.create(token=token, user=request.user, snapshot=snapshot, snapshot_size=len(snapshot), verification_method='webcam')
    send_token_created(token)
    return JsonResponse({'token': raw_token, 'token_id': str(token.public_id), 'generation': token.generation, 'expires_at': token.expires_at.isoformat(), 'server_now': timezone.now().isoformat(), 'qr_payload': signed_payload(token), 'qr_data_url': 'data:image/png;base64,' + base64.b64encode(qr_png(token)).decode(), 'pdf_url': reverse('dashboard:token_pdf', args=[token.public_id]), 'status_url': reverse('dashboard:token_status', args=[token.public_id])})

@require_POST
@role_required(User.Role.STUDENT)
def regenerate_token(request):
    return issue_token(request)


@require_GET
@role_required(User.Role.STUDENT)
def token_status(request, token_id):
    token = CampusToken.objects.filter(public_id=token_id, user=request.user).first()
    if not token:
        return JsonResponse({'error': 'Token not found.'}, status=404)
    token.mark_expired()
    remaining = (token.expires_at - timezone.now()).total_seconds()
    for seconds, kind in ((600, '10m'), (300, '5m'), (60, '1m')):
        if 0 < remaining <= seconds:
            send_token_expiry_notice(token, kind)
            break
    return JsonResponse({'status': 'ACTIVE' if token.is_active else 'EXPIRED', 'expires_at': token.expires_at.isoformat(), 'server_now': timezone.now().isoformat()})


@require_GET
@role_required(User.Role.STUDENT)
def token_pdf(request, token_id):
    token = CampusToken.objects.filter(public_id=token_id, user=request.user).select_related('user__branch', 'audit').first()
    if not token:
        return JsonResponse({'error': 'Token not found.'}, status=404)
    token.mark_expired()
    response = HttpResponse(pdf_pass(token), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="campus-pass-{token.public_id}.pdf"'
    return response


def _location_data(location):
    return {'id': location.id, 'name': location.name, 'category': location.category, 'category_label': location.get_category_display(), 'latitude': float(location.latitude), 'longitude': float(location.longitude), 'description': location.description, 'building_code': location.building_code, 'is_active': location.is_active}


def _coordinates(payload):
    try:
        latitude = Decimal(str(payload['latitude']))
        longitude = Decimal(str(payload['longitude']))
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('Latitude and longitude must be valid numbers.') from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError('Latitude must be between -90 and 90 and longitude between -180 and 180.')
    return latitude, longitude


@require_GET
@role_required(User.Role.ADMIN, User.Role.SECURITY, User.Role.STUDENT)
def campus_map(request):
    return render(request, 'dashboard/campus_map.html', {'is_location_admin': request.user.role == User.Role.ADMIN, 'categories': CampusLocation.Category.choices})


@require_GET
@role_required(User.Role.ADMIN, User.Role.SECURITY, User.Role.STUDENT)
def locations_api(request):
    return JsonResponse({'locations': [_location_data(location) for location in CampusLocation.objects.filter(is_active=True).order_by('name')]})


@require_POST
@role_required(User.Role.ADMIN)
def create_location(request):
    try:
        payload = json.loads(request.body)
        latitude, longitude = _coordinates(payload)
        category = payload['category']
        if category not in CampusLocation.Category.values:
            raise ValueError('Invalid campus location category.')
        location = CampusLocation.objects.create(name=str(payload['name']).strip()[:120], category=category, latitude=latitude, longitude=longitude, description=str(payload.get('description', ''))[:2000], building_code=str(payload.get('building_code', ''))[:32], created_by=request.user)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return JsonResponse({'error': str(exc) or 'Invalid location data.'}, status=400)
    return JsonResponse(_location_data(location), status=201)


@require_POST
@role_required(User.Role.ADMIN)
def update_location(request, location_id):
    location = get_object_or_404(CampusLocation, pk=location_id)
    try:
        payload = json.loads(request.body)
        latitude, longitude = _coordinates(payload)
        if payload.get('category') not in CampusLocation.Category.values:
            raise ValueError('Invalid campus location category.')
        location.name = str(payload['name']).strip()[:120]
        location.category = payload['category']
        location.latitude = latitude
        location.longitude = longitude
        location.description = str(payload.get('description', ''))[:2000]
        location.building_code = str(payload.get('building_code', ''))[:32]
        location.is_active = bool(payload.get('is_active', True))
        location.save()
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return JsonResponse({'error': str(exc) or 'Invalid location data.'}, status=400)
    return JsonResponse(_location_data(location))


@require_POST
@role_required(User.Role.ADMIN)
def delete_location(request, location_id):
    location = get_object_or_404(CampusLocation, pk=location_id)
    location.is_active = False
    location.save(update_fields=['is_active', 'updated_at'])
    return JsonResponse({'deleted': True})


@require_POST
@role_required(User.Role.SECURITY)
def validate_token(request):
    try:
        payload = json.loads(request.body)
        token = token_from_signed_payload(payload.get('qr_payload', ''))
    except (json.JSONDecodeError, TypeError):
        token = None
    if not token or not token.user.is_active or not token.user.can_login:
        return JsonResponse({'valid': False, 'error': 'Invalid token signature or student approval.'}, status=400)
    if token.used_at or token.revoked_at or timezone.now() >= token.expires_at:
        token.mark_expired()
        return JsonResponse({'valid': False, 'error': 'Token is expired, revoked, or already used.'}, status=409)
    token.used_at = timezone.now()
    token.used_by = request.user
    token.save(update_fields=['used_at', 'used_by'])
    return JsonResponse({'valid': True, 'student': token.user.full_name, 'enrollment_number': token.user.enrollment_number, 'expires_at': token.expires_at.isoformat()})
