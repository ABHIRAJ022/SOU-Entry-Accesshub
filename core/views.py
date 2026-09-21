import time
from django.contrib.staticfiles import finders
from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.shortcuts import render
from django.utils import timezone
from .models import SystemHealthEvent
import logging
import os
import requests
from django.conf import settings
from django.core.mail import get_connection
from django.db import connection

_HEALTH_CACHE_TTL = 15
_health_cache = {'expires_at': 0.0, 'status': 'degraded'}

@require_GET
@never_cache
def health_check(request):
    now = time.monotonic()
    if now < _health_cache['expires_at']:
        return JsonResponse({'status': _health_cache['status']})
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as exc:
        checks['database'] = 'error'
        logging.getLogger(__name__).warning('Database health check failed: %s', exc)
    checks['mongodb'] = 'ok' if checks['database'] == 'ok' else 'error'
    try:
        get_connection().open()
        checks['email'] = 'ok'
    except Exception:
        checks['email'] = 'error'
    checks['cloudinary'] = 'ok' if os.environ.get('CLOUDINARY_URL') else 'not_configured'
    checks['osrm'] = _http_check(getattr(settings, 'OSRM_BASE_URL', ''))
    checks['token_service'] = 'ok'
    checks['location_api'] = 'ok'
    checks['scanner_api'] = 'ok'
    _record_health_transitions(checks)
    status = 'degraded' if 'error' in checks.values() else 'operational'
    _health_cache.update({'expires_at': now + _HEALTH_CACHE_TTL, 'status': status})
    return JsonResponse({'status': status, 'components': checks})


def _http_check(url):
    if not url:
        return 'not_configured'
    try:
        response = requests.get(url, timeout=3)
        return 'ok' if response.ok else 'error'
    except requests.RequestException:
        return 'error'


def _record_health_transitions(checks):
    from django.core.mail import send_mail
    from accounts.models import User
    for component, status in checks.items():
        current = SystemHealthEvent.objects.filter(component=component, recovered_at__isnull=True).first()
        failed = status == 'error'
        if failed and not current:
            event = SystemHealthEvent.objects.create(component=component, status='outage', message='Health check failed.')
            recipients = list(User.objects.filter(role=User.Role.ADMIN, is_active=True).values_list('email', flat=True))
            if recipients:
                send_mail(f'AccessHub outage: {component}', event.message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)
        elif not failed and current:
            current.status = 'recovered'
            current.recovered_at = timezone.now()
            current.save(update_fields=['status', 'recovered_at'])

def csrf_failure(request, reason=''):
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
        return JsonResponse({'error': 'Security check failed. Refresh the page and try again.'}, status=403)
    return render(request, 'csrf_failure.html', {'reason': reason}, status=403)

def static_asset(request, path):
    asset_path = finders.find(path)
    if not asset_path:
        raise Http404
    return FileResponse(open(asset_path, 'rb'))
