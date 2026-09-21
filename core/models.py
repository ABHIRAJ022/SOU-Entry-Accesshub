from django.conf import settings
from django.db import models


def default_report_formats():
    return ['csv', 'xlsx', 'pdf']


class AuditLog(models.Model):
    class Event(models.TextChoices):
        AUTHENTICATION = 'AUTHENTICATION', 'Authentication'
        TOKEN_CREATED = 'TOKEN_CREATED', 'Token created'
        ADMIN_DECISION = 'ADMIN_DECISION', 'Admin decision'
        FACE_VERIFICATION = 'FACE_VERIFICATION', 'Face verification'
        SECURITY_EVENT = 'SECURITY_EVENT', 'Security event'

    event = models.CharField(max_length=24, choices=Event.choices)
    action = models.CharField(max_length=64)
    status = models.CharField(max_length=16)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    path = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('AuditLog records are immutable.')
        super().save(*args, **kwargs)


class SystemHealthEvent(models.Model):
    component = models.CharField(max_length=40)
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    recovered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=('component', '-opened_at'))]


class AccessReportSchedule(models.Model):
    class Period(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    period = models.CharField(max_length=10, choices=Period.choices, unique=True)
    recipients = models.JSONField(default=list)
    formats = models.JSONField(default=default_report_formats)
    enabled = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)


class AccessReport(models.Model):
    period = models.CharField(max_length=10)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    metrics = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)


class EventNotification(models.Model):
    event = models.CharField(max_length=64)
    recipients = models.JSONField(default=list)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)