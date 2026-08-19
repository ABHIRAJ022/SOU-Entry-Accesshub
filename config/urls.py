from django.contrib import admin
from django.urls import include, path
from accounts import views as account_views
from core.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/google/', include('allauth.socialaccount.urls')),
    path('api/health/', health_check, name='health'),
    path('', account_views.home, name='home'),
    path('dashboard/', include('dashboard.urls')),
]
