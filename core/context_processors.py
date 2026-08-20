from urllib.parse import urlsplit, urlunsplit

from django.conf import settings


def seo(request):
    path = request.path
    private_prefixes = ('/accounts/', '/dashboard/', '/admin/', '/api/')
    descriptions = {
        '/accounts/login/': 'Securely sign in to Smart Campus using your approved campus account.',
        '/accounts/register/': 'Create a Smart Campus account for student, administrator, or security staff access.',
        '/accounts/verify-otp/': 'Verify your Smart Campus email address with a secure one-time code.',
    }
    canonical_path = urlsplit(request.get_full_path())._replace(query='', fragment='').geturl()
    return {
        'seo': {
            'site_name': settings.SEO_SITE_NAME,
            'description': descriptions.get(path, settings.SEO_DEFAULT_DESCRIPTION),
            'canonical': f'{settings.SITE_URL}{urlunsplit(('', '', canonical_path, '', ''))}',
            'robots': 'noindex, nofollow' if path.startswith(private_prefixes) or path != '/' else 'index, follow',
        },
    }