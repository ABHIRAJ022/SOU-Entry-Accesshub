import logging
from smtplib import SMTPException
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils import timezone
from email.mime.image import MIMEImage
from .models import TokenNotification
from .token_utils import accesshub_logo_bytes, institution_logo_bytes, pdf_pass

logger = logging.getLogger(__name__)


def _ist(value):
    return timezone.localtime(value).strftime('%d %b %Y, %I:%M %p IST')


def send_account_approved(user):
    subject = 'Your SOU Entry AccessHub account is approved'
    body = (
        f"Hello {user.full_name},\n\n"
        f"Account approved for role: {user.get_role_display()}.\n\n"
        "You can now sign in: /accounts/login/\n\n"
        "If you are a student, complete identity verification before generating a campus entry pass.\n\n"
        "If you did not expect this approval, contact your campus administrator."
    )
    _send('account-approved', subject, body, user.email)


def send_token_created(token):
    recipient = token.holder_email
    if not recipient:
        return
    try:
        subject = 'Your SOU Entry AccessHub pass is ready'
        body = (
            f"Hello {token.holder_name or token.user.full_name},\n\n"
            f"Token ID: {token.public_id}\n"
            f"Expires: {_ist(token.expires_at)}\n"
            f"Validity: {token.duration_minutes} minutes\n\n"
            "The signed PDF pass is attached to this email. Present the QR at campus entry and do not share this pass.\n\n"
            "If any profile information is incorrect, contact campus administration."
        )
        html_body = (
            f'<p>Hello {token.holder_name or token.user.full_name},</p>'
            '<p><img src="cid:sou-logo" alt="Silver Oak University logo" '
            'style="max-width:420px;height:auto;">'
            '<img src="cid:accesshub-logo" alt="SOU Entry AccessHub logo" '
            'style="max-width:120px;height:auto;margin-left:16px;"></p>'
            f'<p>Token ID: {token.public_id}<br>'
            f'Expires: {_ist(token.expires_at)}<br>'
            f'Validity: {token.duration_minutes} minutes</p>'
            '<p>The signed PDF pass is attached to this email. Present the QR at campus entry and do not share this pass.</p>'
            '<p>If any profile information is incorrect, contact campus administration.</p>'
        )
        message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
        message.attach(f'campus-pass-{token.public_id}.pdf', pdf_pass(token), 'application/pdf')
        logo = MIMEImage(institution_logo_bytes(), _subtype='png')
        logo.add_header('Content-ID', '<sou-logo>')
        logo.add_header('Content-Disposition', 'inline', filename='silver-oak-university-logo.png')
        message.attach(logo)
        accesshub_logo = MIMEImage(accesshub_logo_bytes(), _subtype='png')
        accesshub_logo.add_header('Content-ID', '<accesshub-logo>')
        accesshub_logo.add_header('Content-Disposition', 'inline', filename='logo.png')
        message.attach(accesshub_logo)
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
    except (OSError, SMTPException):
        logger.exception('Token PDF email failed for %s', token.public_id)


def send_token_expiry_notice(token, kind):
    if TokenNotification.objects.filter(token=token, kind=kind).exists():
        return
    messages = {
            '2m': (
                f"Hello {token.holder_name or token.user.full_name},\n\n"
                f"Token ID: {token.public_id}\n"
                f"Expires: {_ist(token.expires_at)}\n"
                f"Validity: {token.duration_minutes} minutes\n\n"
                "Open your dashboard to generate a new pass if needed: /dashboard/\n\n"
                "If you did not create this pass, contact your campus administrator."
            ),
    }
    try:
        default_message = (
            f"Hello {token.holder_name or token.user.full_name},\n\n"
            f"Token ID: {token.public_id}\n"
            f"Expires: {_ist(token.expires_at)}\n\n"
            "Open your dashboard to generate a new pass if needed: /dashboard/\n\n"
            "If you did not create this pass, contact your campus administrator."
        )
        message = messages.get(kind, default_message)
        send_mail('Your SOU Entry AccessHub pass expires soon', message, settings.DEFAULT_FROM_EMAIL, [token.user.email], fail_silently=False)
        TokenNotification.objects.get_or_create(token=token, kind=kind)
    except (OSError, SMTPException):
        logger.exception('Token expiry email failed for %s', token.public_id)


def _send(kind, subject, body, recipient):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
    except (OSError, SMTPException):
        logger.exception('Notification email failed: %s', kind)