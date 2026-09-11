import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User
from .location_service import is_inside_campus, rate_limit, record_location
from .models import LocationHistory, TokenScan, UserLocation


MAX_BODY = 16 * 1024


def _role_allowed(request, *roles):
    return request.user.is_superuser or request.user.role in roles


def _location_json(location):
    return {
        'latitude': float(location.latitude), 'longitude': float(location.longitude),
        'accuracy': location.accuracy, 'recorded_at': location.recorded_at.isoformat(),
    }


@login_required
@require_GET
def me(request):
    location = UserLocation.objects.filter(user=request.user).first()
    return JsonResponse({
        'sharing_enabled': request.user.location_sharing_enabled,
        'online': bool(location and location.recorded_at >= timezone.now() - timedelta(
            seconds=getattr(settings, 'LOCATION_ONLINE_THRESHOLD_SECONDS', 120)
        )),
        'location': _location_json(location) if location else None,
    })


@login_required
@require_POST
def update(request):
    if request.META.get('CONTENT_LENGTH') and int(request.META['CONTENT_LENGTH']) > MAX_BODY:
        return JsonResponse({'error': 'Request is too large.'}, status=413)
    if not request.user.location_sharing_enabled:
        return JsonResponse({'error': 'Location sharing is not enabled.'}, status=403)
    if not rate_limit(f'update:{request.user.pk}'):
        return JsonResponse({'error': 'Too many location updates. Try again shortly.'}, status=429)
    try:
        payload = json.loads(request.body or '{}')
        location = record_location(
            request.user, payload['latitude'], payload['longitude'],
            payload.get('accuracy'), payload.get('recorded_at'),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return JsonResponse({'error': str(exc) or 'Invalid location data.'}, status=400)
    return JsonResponse({'location': _location_json(location), 'inside_campus': is_inside_campus(location.latitude, location.longitude)})


@login_required
@require_POST
def start(request):
    request.user.location_sharing_enabled = True
    request.user.save(update_fields=['location_sharing_enabled'])
    return JsonResponse({'sharing_enabled': True})


@login_required
@require_POST
def stop(request):
    request.user.location_sharing_enabled = False
    request.user.save(update_fields=['location_sharing_enabled'])
    return JsonResponse({'sharing_enabled': False})


@login_required
@require_GET
def history(request):
    target = request.user
    target_id = request.GET.get('user_id')
    if target_id:
        if not _role_allowed(request, User.Role.ADMIN, User.Role.SECURITY):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        target = get_object_or_404(User, pk=target_id)
    if target != request.user and not target.location_sharing_enabled:
        return JsonResponse({'history': []})
    try:
        limit = min(max(int(request.GET.get('limit', 100)), 1), 500)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'limit must be a number.'}, status=400)
    rows = LocationHistory.objects.filter(user=target).order_by('-recorded_at')[:limit]
    return JsonResponse({'history': [_location_json(row) for row in rows]})


@login_required
@require_GET
def users(request):
    if not _role_allowed(request, User.Role.ADMIN, User.Role.SECURITY):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    threshold = timezone.now() - timedelta(seconds=getattr(settings, 'LOCATION_ONLINE_THRESHOLD_SECONDS', 120))
    rows = UserLocation.objects.filter(user__location_sharing_enabled=True).select_related('user')
    return JsonResponse({'users': [{
        'id': str(row.user_id), 'name': row.user.full_name, 'role': row.user.role,
        'online': row.recorded_at >= threshold, **_location_json(row),
    } for row in rows]})


@login_required
@require_GET
def scans(request):
    if not _role_allowed(request, User.Role.ADMIN, User.Role.SECURITY):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    scans = TokenScan.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related('scanned_by').order_by('-scanned_at')[:200]
    return JsonResponse({'scans': [{
        'id': str(scan.pk), 'latitude': float(scan.latitude), 'longitude': float(scan.longitude),
        'accuracy': scan.accuracy, 'scanned_at': scan.scanned_at.isoformat(),
        'scanned_by': scan.scanned_by.full_name,
    } for scan in scans]})
