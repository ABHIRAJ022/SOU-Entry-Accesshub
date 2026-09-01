import logging
import os

logger = logging.getLogger(__name__)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def ensure_database_migrations():
    try:
        import django
        from django.core.management import call_command
        django.setup()
        call_command('migrate', interactive=False, verbosity=0, run_syncdb=True)
    except Exception:
        logger.exception('Automatic database migration failed during startup.')
        raise


ensure_database_migrations()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Vercel's Python runtime accepts a module-level WSGI callable.
app = application
