from django.conf import settings
from django.db import models


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