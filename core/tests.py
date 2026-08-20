from django.test import TestCase, override_settings
from django.urls import reverse
from django.urls import resolve
from urllib.parse import parse_qs, urlparse
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


@override_settings(SITE_URL='https://campus.example.com')
class SeoTests(TestCase):
    def test_robots_and_sitemap_are_valid(self):
        robots = self.client.get(reverse('robots_txt'))
        self.assertEqual(robots.status_code, 200)
        self.assertIn('Disallow: /dashboard/', robots.content.decode())
        self.assertIn('https://campus.example.com/sitemap.xml', robots.content.decode())
        sitemap = self.client.get(reverse('sitemap_xml'))
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn('https://campus.example.com', sitemap.content.decode())

    def test_auth_pages_are_not_indexable(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="robots" content="noindex, nofollow"')
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'name="description"')

    def test_google_login_route_resolves(self):
        match = resolve('/accounts/google/login/')
        self.assertEqual(match.url_name, 'google_login')
        callback = resolve('/accounts/google/login/callback/')
        self.assertEqual(callback.url_name, 'google_callback')

    def test_google_redirect_uses_forwarded_codespaces_host(self):
        app = SocialApp.objects.create(provider='google', name='Test Google', client_id='test-client', secret='test-secret')
        app.sites.add(Site.objects.get_current())
        response = self.client.post(
            '/accounts/google/login/',
            HTTP_HOST='localhost:8000',
            HTTP_X_FORWARDED_HOST='fantastic-space-guacamole-4qw7rx99754xfq6x4-8000.app.github.dev',
            HTTP_X_FORWARDED_PROTO='https',
        )
        redirect_uri = parse_qs(urlparse(response['Location']).query)['redirect_uri'][0]
        self.assertEqual(redirect_uri, 'https://fantastic-space-guacamole-4qw7rx99754xfq6x4-8000.app.github.dev/accounts/google/login/callback/')
