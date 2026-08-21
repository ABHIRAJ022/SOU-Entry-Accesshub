import os
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

if os.getenv('VERCEL') == '1' and os.getenv('DATABASE_URL'):
	try:
		call_command('migrate', interactive=False, verbosity=0)
	except Exception:
		logging.getLogger(__name__).exception('Database migrations failed during Vercel startup.')

# Vercel's Python runtime accepts a module-level WSGI callable.
app = application
