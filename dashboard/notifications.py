import logging
from smtplib import SMTPException
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.utils import timezone
from .models import TokenNotification
from .token_utils import pdf_pass

logger = logging.getLogger(__name__)


def send_account_approved(user):
    _send('account-approved', 'Your Smart Campus account was approved', f'Hello {user.full_name}, your Smart Campus account is now approved.', user.email)


def send_token_created(token):
    recipient = token.holder_email
    if not recipient:
        return
    try:
        message = EmailMessage(
            'Your Smart Campus token was created',
            f'Your campus token {token.public_id} expires at {token.expires_at.isoformat()}. The PDF pass is attached.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
        )
        message.attach(f'campus-pass-{token.public_id}.pdf', pdf_pass(token), 'application/pdf')
        message.send(fail_silently=False)
    except (OSError, SMTPException):
        logger.exception('Token PDF email failed for %s', token.public_id)


def send_token_expiry_notice(token, kind):
    if TokenNotification.objects.filter(token=token, kind=kind).exists():
        return
    messages = {
        '2m': 'Your campus token is expiring in 2 minutes. If you want to stay on campus, regenerate the token.',
    }
    try:
        message = messages.get(kind, f'Your campus token {token.public_id} expires soon at {token.expires_at.isoformat()}.')
        send_mail('Your campus token expires in 2 minutes' if kind == '2m' else 'Smart Campus token expiry reminder', message, settings.DEFAULT_FROM_EMAIL, [token.user.email], fail_silently=False)
        TokenNotification.objects.get_or_create(token=token, kind=kind)
    except (OSError, SMTPException):
        logger.exception('Token expiry email failed for %s', token.public_id)


def _send(kind, subject, body, recipient):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
    except (OSError, SMTPException):
        logger.exception('Notification email failed: %s', kind)