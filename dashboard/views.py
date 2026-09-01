from functools import wraps
import base64
import json
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.utils import ProgrammingError
from django.db.models import Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from biometrics.snapshots import SnapshotError, process_webcam_snapshot
from accounts.models import User
from .models import CampusToken, GuestTokenRequest, TokenAudit
from .token_utils import pdf_pass, qr_data_url, qr_png, signed_payload, token_from_signed_payload
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
        'active_token_qr': qr_data_url(active_token) if active_token else '',
        'latest_token': latest_token,
        'latest_token_qr': qr_data_url(latest_token) if latest_token else '',
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

def _admin_students(request):
    students = User.objects.filter(role=User.Role.STUDENT)
    return students if request.user.is_superuser else students.filter(branch=request.user.branch)

@require_GET
@role_required(User.Role.ADMIN)
def token_management(request):
    now = timezone.now()
    scope = Q(user__in=_admin_students(request))
    if request.user.is_superuser:
        scope |= Q(guest_request__isnull=False)
    tokens = CampusToken.objects.filter(scope).select_related('user', 'user__branch', 'guest_request').order_by('-created_at')
    live_tokens = tokens.filter(revoked_at__isnull=True, used_at__isnull=True, expires_at__gt=now)
    expired_tokens = tokens.exclude(pk__in=live_tokens.values('pk'))
    return render(request, 'dashboard/tokens.html', {'live_tokens': live_tokens, 'expired_tokens': expired_tokens, 'live_count': live_tokens.count(), 'expired_count': expired_tokens.count(), 'now': now})

@require_GET
@role_required(User.Role.ADMIN)
def token_history(request, user_id):
    user = get_object_or_404(_admin_students(request), pk=user_id)
    return render(request, 'dashboard/token_history.html', {'student': user, 'tokens': user.campus_tokens.order_by('-created_at'), 'now': timezone.now()})

@require_POST
@role_required(User.Role.ADMIN)
def cancel_token(request, token_id):
    with transaction.atomic():
        scope = Q(user__in=_admin_students(request))
        if request.user.is_superuser:
            scope |= Q(guest_request__isnull=False)
        token = get_object_or_404(CampusToken.objects.select_for_update().select_related('guest_request'), scope, public_id=token_id)
        if token.revoked_at is None and token.expires_at > timezone.now() and token.used_at is None:
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at'])
            if token.guest_request_id:
                token.guest_request.status = GuestTokenRequest.Status.CANCELLED
                token.guest_request.approved_by = request.user
                token.guest_request.approved_at = timezone.now()
                token.guest_request.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
            return JsonResponse({'status': 'cancelled'})
    return JsonResponse({'error': 'Only a live, unused token can be cancelled.'}, status=409)

@role_required(User.Role.SECURITY)
def security_dashboard(request):
    return render(request, 'dashboard/security.html', {'guest_requests': GuestTokenRequest.objects.filter(status=GuestTokenRequest.Status.PENDING).order_by('-created_at')})


def _guest_staff_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.SECURITY and not request.user.is_superuser:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


def _token_viewer_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role not in (User.Role.STUDENT, User.Role.SECURITY) and not request.user.is_superuser:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


@require_GET
@_guest_staff_required
def guest_requests(request):
    requests = GuestTokenRequest.objects.select_related('approved_by').prefetch_related(
        Prefetch('token', to_attr='guest_token')
    ).order_by('-created_at')
    for guest in requests:
        if guest.status == GuestTokenRequest.Status.APPROVED and guest.guest_token:
            guest.token_qr = qr_data_url(guest.guest_token)
        else:
            guest.token_qr = ''
    return render(request, 'dashboard/guest_requests.html', {'guest_requests': requests, 'pending_count': requests.filter(status=GuestTokenRequest.Status.PENDING).count()})


@require_GET
@_guest_staff_required
def guest_request_detail(request, request_id):
    guest = get_object_or_404(
        GuestTokenRequest.objects.select_related('approved_by').prefetch_related(
            Prefetch('token', to_attr='guest_token')
        ),
        pk=request_id,
    )
    # Detect guest live photo MIME type to build a correct data URL
    photo = ''
    if guest.live_photo:
        try:
            from io import BytesIO
            from PIL import Image
            image_format = Image.open(BytesIO(guest.live_photo)).format.lower()
            mime_type = {'jpg': 'jpeg'}.get(image_format, image_format)
            photo = f'data:image/{mime_type};base64,' + base64.b64encode(guest.live_photo).decode()
        except Exception:
            photo = 'data:image/jpeg;base64,' + base64.b64encode(guest.live_photo).decode()
    guest_token_qr = ''
    if guest.guest_token:
        guest_token_qr = qr_data_url(guest.guest_token)
    return render(request, 'dashboard/guest_request_detail.html', {
        'guest_request': guest,
        'guest_photo': photo,
        'guest_token_qr': guest_token_qr,
    })


@require_POST
@_guest_staff_required
def approve_guest_request(request, request_id):
    with transaction.atomic():
        guest = get_object_or_404(GuestTokenRequest.objects.select_for_update(), pk=request_id)
        if guest.status in {GuestTokenRequest.Status.REJECTED, GuestTokenRequest.Status.CANCELLED}:
            return JsonResponse({'error': 'This guest request is no longer active.'}, status=409)
        if guest.status == GuestTokenRequest.Status.APPROVED:
            return JsonResponse({'status': 'already-approved'})
        if guest.status == GuestTokenRequest.Status.MAIN_ADMIN_REQUIRED and not request.user.is_superuser:
            return JsonResponse({'error': 'A main administrator must approve a replacement token.'}, status=403)
        token, raw_token = CampusToken.issue_for_guest(guest)
        guest.status = GuestTokenRequest.Status.APPROVED
        guest.approved_by = request.user
        guest.approved_at = timezone.now()
        guest.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    messages.success(request, f'Temporary token created for {guest.name}: {raw_token}')
    send_token_created(token)
    return redirect('dashboard:guest_request_detail', request_id=guest.pk)


@require_POST
@_guest_staff_required
def reject_guest_request(request, request_id):
    with transaction.atomic():
        guest = get_object_or_404(GuestTokenRequest.objects.select_for_update(), pk=request_id)
        if guest.status == GuestTokenRequest.Status.PENDING:
            guest.status = GuestTokenRequest.Status.REJECTED
            guest.approved_by = request.user
            guest.approved_at = timezone.now()
            guest.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    return redirect('dashboard:guest_requests')

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
    if int(request.META.get('CONTENT_LENGTH') or 0) > 450000:
        return JsonResponse({'error': 'The token request is too large.'}, status=413)
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
@_token_viewer_required
def token_status(request, token_id):
    tokens = CampusToken.objects.filter(public_id=token_id)
    if request.user.role == User.Role.STUDENT:
        tokens = tokens.filter(user=request.user)
    else:
        tokens = tokens.filter(guest_request__isnull=False)
    token = tokens.first()
    if not token:
        return JsonResponse({'error': 'Token not found.'}, status=404)
    token.mark_expired()
    remaining = (token.expires_at - timezone.now()).total_seconds()
    for lower_bound, upper_bound, kind in ((300, 600, '10m'), (120, 300, '5m'), (60, 120, '2m'), (0, 60, '1m')):
        if lower_bound < remaining <= upper_bound:
            send_token_expiry_notice(token, kind)
            break
    return JsonResponse({'status': 'ACTIVE' if token.is_active else 'EXPIRED', 'expires_at': token.expires_at.isoformat(), 'server_now': timezone.now().isoformat()})


@require_GET
@_token_viewer_required
def token_pdf(request, token_id):
    tokens = CampusToken.objects.filter(public_id=token_id)
    if request.user.role == User.Role.STUDENT:
        tokens = tokens.filter(user=request.user)
    else:
        tokens = tokens.filter(guest_request__isnull=False)
    token = tokens.select_related('user__branch', 'guest_request', 'audit').first()
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
    locations = CampusLocation.objects.all() if request.user.is_superuser else CampusLocation.objects.filter(created_by__branch_id=request.user.branch_id)
    location = get_object_or_404(locations, pk=location_id)
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
    locations = CampusLocation.objects.all() if request.user.is_superuser else CampusLocation.objects.filter(created_by__branch_id=request.user.branch_id)
    location = get_object_or_404(locations, pk=location_id)
    location.is_active = False
    location.save(update_fields=['is_active', 'updated_at'])
    return JsonResponse({'deleted': True})


@require_POST
@role_required(User.Role.SECURITY)
def validate_token(request):
    try:
        try:
            payload = json.loads(request.body)
            qr_payload = payload.get('qr_payload', '')
            
            if not qr_payload:
                return JsonResponse({'valid': False, 'error': 'No QR payload provided.'}, status=400)
            
            token = token_from_signed_payload(qr_payload)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            return JsonResponse({'valid': False, 'error': f'Invalid QR code format: {str(e)}'}, status=400)
        
        # Check if token exists and is valid
        guest_approved = token and token.guest_request_id and token.guest_request.status == GuestTokenRequest.Status.APPROVED
        student_approved = token and token.user_id and token.user.is_active and token.user.can_login
        
        if not token:
            return JsonResponse({'valid': False, 'error': 'Token not found. Invalid QR code.'}, status=400)
        
        if not (guest_approved or student_approved):
            if token.user_id and not token.user.is_active:
                return JsonResponse({'valid': False, 'error': 'Student account is inactive.'}, status=400)
            if token.user_id and not token.user.can_login:
                return JsonResponse({'valid': False, 'error': 'Student account is not verified or approved.'}, status=400)
            if token.guest_request_id:
                status = token.guest_request.status
                return JsonResponse({'valid': False, 'error': f'Guest request status: {status}. Not approved.'}, status=400)
            return JsonResponse({'valid': False, 'error': 'Invalid token or student not approved.'}, status=400)
        
        # Validate token state
        with transaction.atomic():
            # Lock the token without select_related to avoid outer join issue with FOR UPDATE
            # (PostgreSQL doesn't allow FOR UPDATE on nullable outer joins)
            token = CampusToken.objects.select_for_update().filter(pk=token.pk).first()
            
            if not token:
                return JsonResponse({'valid': False, 'error': 'Token no longer exists.'}, status=409)
            
            if token.revoked_at:
                return JsonResponse({'valid': False, 'error': 'Token has been revoked.'}, status=409)
            
            if timezone.now() >= token.expires_at:
                token.mark_expired()
                return JsonResponse({'valid': False, 'error': 'Token has expired.'}, status=409)
            
            # Allow up to 3 distinct scans per token. Prevent the same security user from scanning the same token more than once.
            tokenscan_missing = False
            TokenScan = None
            try:
                from .models import TokenScan as _TokenScan
            except Exception as e:
                # Import errors or missing table will be handled below when trying DB ops
                _TokenScan = None
            TokenScan = _TokenScan

            if TokenScan is not None:
                try:
                    scan_count = TokenScan.objects.filter(token=token).count()
                except ProgrammingError as pe:
                    # TokenScan table exists in models but not in DB (migrations not applied). Log and continue with a degraded mode.
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error('TokenScan table missing when validating token: %s', pe)
                    # Rollback the DB connection to clear the aborted transaction state so
                    # subsequent DB operations (like token.save) don't fail with
                    # "current transaction is aborted".
                    try:
                        from django.db import connection
                        connection.rollback()
                    except Exception:
                        logger.exception('Failed to rollback DB connection after TokenScan ProgrammingError')
                    tokenscan_missing = True
                    scan_count = 0
            else:
                # TokenScan model not importable (unexpected), operate in degraded mode
                tokenscan_missing = True
                scan_count = 0

            if not tokenscan_missing and scan_count >= 3:
                # Token has reached maximum allowed scans
                return JsonResponse({'valid': False, 'error': 'Token has already been used.'}, status=409)

            if not tokenscan_missing:
                # Prevent same security staff scanning the same token multiple times
                if TokenScan.objects.filter(token=token, scanned_by=request.user).exists():
                    return JsonResponse({'valid': False, 'error': 'You have already scanned this token.'}, status=409)

                # Record this scan
                try:
                    TokenScan.objects.create(token=token, scanned_by=request.user)
                except ProgrammingError as pe:
                    # Race or missing table; log and continue without recording
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error('Failed to record TokenScan (missing table or DB error): %s', pe)
                    # Rollback the DB connection to clear an aborted transaction state.
                    try:
                        from django.db import connection
                        connection.rollback()
                    except Exception:
                        logger.exception('Failed to rollback DB connection after TokenScan create ProgrammingError')
                    tokenscan_missing = True

            # On the first scan, keep used_at/used_by for backward compatibility and auditing
            if not token.used_at:
                token.used_at = timezone.now()
                token.used_by = request.user
                token.save(update_fields=['used_at', 'used_by'])
        
        # Prepare response data
        is_guest = bool(token.guest_request_id)
        holder = token.guest_request if is_guest else token.user
        profile_photo = holder.live_photo if is_guest else holder.profile_photo

        # Build a correct data URL for the photo by detecting its format (PNG/JPEG/etc.)
        photo_data_url = ''
        if profile_photo:
            try:
                from io import BytesIO
                from PIL import Image
                image_format = Image.open(BytesIO(profile_photo)).format.lower()
                mime_type = {'jpg': 'jpeg'}.get(image_format, image_format)
                photo_data_url = f'data:image/{mime_type};base64,' + base64.b64encode(profile_photo).decode()
            except Exception:
                # Fallback to JPEG data URL (was previously used)
                photo_data_url = 'data:image/jpeg;base64,' + base64.b64encode(profile_photo).decode()

        return JsonResponse({
            'valid': True,
            'token_id': str(token.public_id),
            'holder_type': 'Guest' if is_guest else 'Student',
            'student': token.holder_name,
            'full_name': token.holder_name,
            'email': token.holder_email,
            'mobile': holder.mobile if is_guest else holder.phone_number,
            'phone_number': holder.mobile if is_guest else holder.phone_number,
            'enrollment_number': '' if is_guest else holder.enrollment_number,
            'gender': holder.get_gender_display() if is_guest else '',
            'branch': '' if is_guest or not holder.branch_id else holder.branch.name,
            'purpose': token.guest_request.purpose if is_guest else 'Student access',
            'duration_minutes': token.duration_minutes,
            'created_at': token.created_at.isoformat(),
            'expires_at': token.expires_at.isoformat(),
            'profile_photo': photo_data_url,
            'pdf_url': reverse('dashboard:token_pdf', args=[token.public_id]),
            'scan_recorded': (not tokenscan_missing),
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception('Error in validate_token endpoint')
        return JsonResponse({'valid': False, 'error': f'Server error: {str(e)}'}, status=500)
