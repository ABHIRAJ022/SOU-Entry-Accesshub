from django.contrib import admin
from django.urls import include, path
from allauth.urls import build_provider_urlpatterns
from accounts import views as account_views
from core.views import health_check, static_asset
from core.seo import robots_txt, sitemap_xml
from dashboard import views as dashboard_views

urlpatterns = [
    path('static/<path:path>', static_asset, name='static_asset'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include(build_provider_urlpatterns())),
    path('api/health/', health_check, name='health'),
    path('admin-tools/', include('core.urls')),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('', account_views.home, name='home'),
    path('dashboard/', include('dashboard.urls')),
    path('api/', include('biometrics.urls')),
    path('api/locations/', include('dashboard.location_urls')),
    path('api/tokens/validate/', dashboard_views.validate_token, name='validate_token'),
]
