import time
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.shortcuts import render

_HEALTH_CACHE_TTL = 15
_health_cache = {'expires_at': 0.0, 'status': 'degraded'}

@require_GET
@never_cache
def health_check(request):
    now = time.monotonic()
    if now < _health_cache['expires_at']:
        return JsonResponse({'status': _health_cache['status']})
    database = 'ok'
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except Exception:
        database = 'error'
    status = 'operational' if database == 'ok' else 'degraded'
    _health_cache.update({'expires_at': now + _HEALTH_CACHE_TTL, 'status': status})
    return JsonResponse({'status': status})

def csrf_failure(request, reason=''):
    return render(request, 'csrf_failure.html', {'reason': reason}, status=403)

def static_asset(request, path):
    asset_path = finders.find(path)
    if not asset_path:
        raise Http404
    return FileResponse(open(asset_path, 'rb'))
