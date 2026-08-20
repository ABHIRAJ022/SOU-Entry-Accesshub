import time
import psutil
from django.contrib.staticfiles import finders
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.shortcuts import render

@require_GET
@never_cache
def health_check(request):
    started = time.perf_counter(); database = 'ok'
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except Exception:
        database = 'error'
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse({'status': 'operational' if database == 'ok' else 'degraded', 'database': database, 'latency_ms': latency_ms, 'memory': {'percent': psutil.virtual_memory().percent, 'available_mb': round(psutil.virtual_memory().available / 1048576)}})

def csrf_failure(request, reason=''):
    return render(request, 'csrf_failure.html', {'reason': reason}, status=403)

def static_asset(request, path):
    asset_path = finders.find(path)
    if not asset_path:
        raise Http404
    return FileResponse(open(asset_path, 'rb'))
