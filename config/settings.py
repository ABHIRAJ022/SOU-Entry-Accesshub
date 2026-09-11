import os
from pathlib import Path
from urllib.parse import quote_plus, unquote_plus, urlsplit, urlunsplit
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-this-secret-key')
IS_VERCEL = os.getenv('VERCEL') == '1'
IS_NETLIFY = os.getenv('NETLIFY') == 'true'
DEBUG = env_bool('DJANGO_DEBUG', not IS_VERCEL)
if not DEBUG and (SECRET_KEY == 'dev-only-change-this-secret-key' or not os.getenv('JWT_SECRET')):
    raise RuntimeError('DJANGO_SECRET_KEY and JWT_SECRET must be configured in production.')
JWT_SECRET = os.getenv('JWT_SECRET', SECRET_KEY)
ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]
ALLOWED_HOSTS = [f'.{host[2:]}' if host.startswith('*.') else host for host in ALLOWED_HOSTS]
if not DEBUG and not os.getenv('DJANGO_ALLOWED_HOSTS'):
    raise RuntimeError('DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG=False.')
codespace_name = os.getenv('CODESPACE_NAME')
codespace_domain = os.getenv('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')
if codespace_name:
    codespace_host = f'{codespace_name}-8000.{codespace_domain}'
    if codespace_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(codespace_host)
SITE_URL = os.getenv('DJANGO_SITE_URL', 'http://localhost:8000').rstrip('/')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SEO_SITE_NAME = 'Your Campus Token'
SEO_DEFAULT_DESCRIPTION = 'Your Campus Token provides secure, role-based campus entry and token management for students, administrators, and security staff.'
GOOGLE_SITE_VERIFICATION = os.getenv('GOOGLE_SITE_VERIFICATION', '').strip()
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'http://localhost:8000,https://localhost:8000,http://127.0.0.1:8000,https://127.0.0.1:8000',
).split(',') if origin.strip()]
if codespace_name:
    codespace_origin = f'https://{codespace_host}'
    if codespace_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(codespace_origin)
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

INSTALLED_APPS = [
    'config.apps.MongoAdminConfig', 'config.apps.MongoAuthConfig', 'config.apps.MongoContentTypesConfig',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'config.apps.MongoSitesConfig', 'allauth', 'config.apps.MongoAccountConfig', 'config.apps.MongoSocialAccountConfig',
    'allauth.socialaccount.providers.google', 'rest_framework', 'csp',
    'corsheaders', 'cloudinary_storage', 'accounts', 'core', 'dashboard', 'biometrics',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware', 'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware', 'core.middleware.AuditLoggingMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'core.context_processors.seo',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
MONGODB_URI = os.getenv('MONGODB_URI', '').strip()
if not MONGODB_URI:
    raise RuntimeError('MONGODB_URI must be configured for every environment.')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'your_campus_token').strip()
if not MONGODB_DB_NAME:
    raise RuntimeError('MONGODB_DB_NAME must not be empty.')

parsed_mongodb_uri = urlsplit(MONGODB_URI)
if '@' in parsed_mongodb_uri.netloc:
    userinfo, host = parsed_mongodb_uri.netloc.rsplit('@', 1)
    username, separator, password = userinfo.partition(':')
    encoded_userinfo = quote_plus(unquote_plus(username))
    if separator:
        encoded_userinfo += f':{quote_plus(unquote_plus(password))}'
    MONGODB_URI = urlunsplit(parsed_mongodb_uri._replace(netloc=f'{encoded_userinfo}@{host}'))
    parsed_mongodb_uri = urlsplit(MONGODB_URI)
if not parsed_mongodb_uri.path or parsed_mongodb_uri.path == '/':
    MONGODB_URI = urlunsplit(parsed_mongodb_uri._replace(path=f'/{MONGODB_DB_NAME}'))

import django_mongodb_backend
from .django_compat import apply_python314_template_compatibility

DATABASES = {'default': django_mongodb_backend.parse_uri(MONGODB_URI)}
# MongoDB has no transaction support, so Django's serialized test-database
# template is incompatible with the backend. Each test still flushes data.
DATABASES['default']['TEST'] = {'SERIALIZE': False}
apply_python314_template_compatibility()
MIGRATION_MODULES = {
    'admin': 'mongo_migrations.admin',
    'auth': 'mongo_migrations.auth',
    'contenttypes': 'mongo_migrations.contenttypes',
    'sessions': 'mongo_migrations.sessions',
    'sites': 'mongo_migrations.sites',
    'account': 'mongo_migrations.account',
    'socialaccount': 'mongo_migrations.socialaccount',
    'accounts': 'mongo_migrations.accounts',
    'core': 'mongo_migrations.core',
    'dashboard': 'mongo_migrations.dashboard',
    'biometrics': 'mongo_migrations.biometrics',
}

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend', 'allauth.account.auth_backends.AuthenticationBackend']
from bson import ObjectId

SITE_ID = ObjectId('000000000000000000000001')
SILENCED_SYSTEM_CHECKS = ['sites.E101']
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher', 'django.contrib.auth.hashers.PBKDF2PasswordHasher']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'; TIME_ZONE = 'Asia/Kolkata'; USE_I18N = True; USE_TZ = True
STATIC_URL = '/static/'; STATICFILES_DIRS = [BASE_DIR / 'static']; STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'} if os.getenv('CLOUDINARY_URL') else {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG or IS_VERCEL else 'core.static_storage.NonStrictCompressedManifestStaticFilesStorage'},
}
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
DEFAULT_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'

EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost'); EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', ''); EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False); DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@example.com')
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
    if (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
    else 'django.core.mail.backends.console.EmailBackend',
)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '15'))
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False}},
}

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0; SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG; SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG; CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True; CSRF_COOKIE_HTTPONLY = True; SESSION_COOKIE_SAMESITE = 'Lax'; CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'campus_csrftoken_v2'
# Keep authenticated sessions active until the user explicitly signs out.
# Django requires a finite cookie age, so use a long-lived value instead of
# the previous 30-minute idle timeout.
SESSION_COOKIE_AGE = 315360000
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SECURE_CONTENT_TYPE_NOSNIFF = True; X_FRAME_OPTIONS = 'DENY'; SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
CONTENT_SECURITY_POLICY = {'DIRECTIVES': {
    'default-src': ("'self'",), 'script-src': ("'self'", 'https://cdn.jsdelivr.net'),
    'style-src': ("'self'", 'https://cdn.jsdelivr.net'), 'font-src': ("'self'", 'https://cdn.jsdelivr.net'),
    'img-src': ("'self'", 'data:', 'https://res.cloudinary.com', 'https://*.tile.openstreetmap.org'),
    'connect-src': ("'self'", 'https://router.project-osrm.org'),
}}
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    if not os.getenv('CLOUDINARY_URL'):
        raise RuntimeError('CLOUDINARY_URL must be set in production.')
    if not os.getenv('MONGODB_URI'):
        raise RuntimeError('MONGODB_URI must be set in production.')
    CLOUDINARY_STORAGE = {'SECURE': True}

RATELIMIT_ENABLE = True
REST_FRAMEWORK = {'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'], 'DEFAULT_THROTTLE_RATES': {'anon': '60/minute', 'user': '120/minute'}}
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
SOCIALACCOUNT_PROVIDERS = {'google': {
    'SCOPE': ['profile', 'email'],
    'AUTH_PARAMS': {'access_type': 'online'},
}}
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': '',
    }
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CampusSocialAccountAdapter'
ACCOUNT_LOGIN_METHODS = {'email'}; ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']; ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
IDENTITY_MAX_REQUEST_BYTES = int(os.getenv('IDENTITY_MAX_REQUEST_BYTES', '400000'))
IDENTITY_VERIFICATION_MAX_AGE_SECONDS = int(os.getenv('IDENTITY_VERIFICATION_MAX_AGE_SECONDS', '300'))
