import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class CampusToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campus_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    generation = models.PositiveIntegerField(default=1)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, user):
        raw_token = secrets.token_urlsafe(32)
        latest = cls.objects.filter(user=user).order_by('-generation').first()
        generation = (latest.generation + 1) if latest else 1
        token = cls.objects.create(user=user, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=timezone.now() + timedelta(hours=1), generation=generation)
        if latest:
            latest.revoked_at = timezone.now()
            latest.save(update_fields=['revoked_at'])
        return token, raw_token

    @property
    def is_active(self):
        return self.revoked_at is None and timezone.now() < self.expires_at
