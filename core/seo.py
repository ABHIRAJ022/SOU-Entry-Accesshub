from django.conf import settings
from django.http import HttpResponse
from django.utils.html import escape


def robots_txt(request):
    sitemap = f'{settings.SITE_URL}/sitemap.xml'
    content = '\n'.join(('User-agent: *', 'Disallow: /admin/', 'Disallow: /accounts/', 'Disallow: /dashboard/', 'Disallow: /api/', f'Sitemap: {sitemap}', ''))
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    locations = (settings.SITE_URL,)
    body = ''.join(f'<url><loc>{escape(location)}</loc></url>' for location in locations)
    content = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return HttpResponse(content, content_type='application/xml; charset=utf-8')
