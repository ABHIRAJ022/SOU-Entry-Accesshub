from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import get_connection


class Command(BaseCommand):
    help = 'Validate email configuration and optionally test the SMTP connection.'

    def add_arguments(self, parser):
        parser.add_argument('--connect', action='store_true', help='Open and close the configured email connection.')

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f'Email backend: {backend}')
        self.stdout.write(f'Email host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'Email user configured: {bool(settings.EMAIL_HOST_USER)}')
        if 'console.EmailBackend' in backend:
            self.stdout.write(self.style.WARNING('Development mode: OTP messages are printed in the server terminal, not delivered to an inbox.'))
            return
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError('EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required for SMTP delivery.')
        if options['connect']:
            try:
                connection = get_connection(fail_silently=False)
                connection.open()
                connection.close()
            except Exception as exc:
                raise CommandError(f'SMTP connection failed: {exc}') from exc
            self.stdout.write(self.style.SUCCESS('SMTP connection succeeded.'))
