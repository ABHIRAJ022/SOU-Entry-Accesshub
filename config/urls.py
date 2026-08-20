from django.contrib import admin
from django.urls import include, path
from allauth.urls import build_provider_urlpatterns
from accounts import views as account_views
from core.views import health_check
from core.seo import robots_txt, sitemap_xml

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include(build_provider_urlpatterns())),
    path('api/health/', health_check, name='health'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('', account_views.home, name='home'),
    path('dashboard/', include('dashboard.urls')),
    path('api/face/', include('biometrics.urls')),
]
