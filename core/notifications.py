from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import User
from .models import EventNotification


ROLE_RECIPIENTS = {
    'user': lambda event_user: [event_user] if event_user else [],
    'security': lambda event_user: list(User.objects.filter(role=User.Role.SECURITY, is_active=True)),
    'admins': lambda event_user: list(User.objects.filter(role=User.Role.ADMIN, is_active=True)),
}


def emit_event(event, *, user=None, payload=None, roles=('admins',)):
    recipients = []
    for role in roles:
        if role == 'user' and user:
            recipients.append(user)
        else:
            recipients.extend(ROLE_RECIPIENTS.get(role, lambda _: [])(user))
    unique = {recipient.pk: recipient for recipient in recipients if recipient and recipient.email}
    emails = list(unique.values())
    notification = EventNotification.objects.create(
        event=event,
        recipients=[recipient.email for recipient in emails],
        payload=payload or {},
    )
    if emails:
        send_mail(
            f'SOU Entry AccessHub: {event.replace("_", " ").title()}',
            str(payload or {}),
            settings.DEFAULT_FROM_EMAIL,
            [recipient.email for recipient in emails],
            fail_silently=True,
        )
        notification.sent_at = timezone.now()
        notification.save(update_fields=['sent_at'])
    return notification
