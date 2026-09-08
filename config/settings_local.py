from .settings import *
import os
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEBUG = True
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
	'http://localhost:8000', 'https://localhost:8000',
	'http://127.0.0.1:8000', 'https://127.0.0.1:8000',
	'http://localhost:8001', 'https://localhost:8001',
	'http://127.0.0.1:8001', 'https://127.0.0.1:8001',
]
# If running inside GitHub Codespaces / forwarded app domain, add the forwarding origin so CSRF checks pass
codespace_name = os.getenv('CODESPACE_NAME')
codespace_domain = os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')
if codespace_name:
    codespace_host = f'{codespace_name}-8000.{codespace_domain}'
    codespace_origin = f'https://{codespace_host}'
    if codespace_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(codespace_origin)

MONGODB_URI = os.getenv('MONGODB_URI', '').strip()
if not MONGODB_URI:
    raise RuntimeError('MONGODB_URI must be configured for local development.')
STORAGES = {
	**STORAGES,
	'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
