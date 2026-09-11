from django.urls import path
from . import location_api

urlpatterns = [
    path('me/', location_api.me, name='location_me'),
    path('update/', location_api.update, name='location_update'),
    path('start/', location_api.start, name='location_start'),
    path('stop/', location_api.stop, name='location_stop'),
    path('history/', location_api.history, name='location_history'),
    path('users/', location_api.users, name='location_users'),
    path('scans/', location_api.scans, name='location_scans'),
]
