import logging
from smtplib import SMTPException
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import TokenNotification

logger = logging.getLogger(__name__)


def send_account_approved(user):
    _send('account-approved', 'Your Smart Campus account was approved', f'Hello {user.full_name}, your Smart Campus account is now approved.', user.email)


def send_token_created(token):
    _send('token-created', 'Your Smart Campus token was created', f'Your campus token {token.public_id} expires at {token.expires_at.isoformat()}.', token.user.email)


def send_token_expiry_notice(token, kind):
    if TokenNotification.objects.filter(token=token, kind=kind).exists():
        return
    try:
        send_mail('Smart Campus token expiry reminder', f'Your campus token {token.public_id} expires soon at {token.expires_at.isoformat()}.', settings.DEFAULT_FROM_EMAIL, [token.user.email], fail_silently=False)
        TokenNotification.objects.get_or_create(token=token, kind=kind)
    except (OSError, SMTPException):
        logger.exception('Token expiry email failed for %s', token.public_id)


def _send(kind, subject, body, recipient):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
    except (OSError, SMTPException):
        logger.exception('Notification email failed: %s', kind)