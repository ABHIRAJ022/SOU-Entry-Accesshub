import hashlib
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class CampusToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campus_tokens')
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    generation = models.PositiveIntegerField(default=1)
    revoked_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='validated_tokens')

    @classmethod
    def issue(cls, user, duration_minutes=60):
        raw_token = secrets.token_urlsafe(32)
        latest = cls.objects.filter(user=user).order_by('-generation').first()
        generation = (latest.generation + 1) if latest else 1
        now = timezone.now()
        cls.objects.filter(user=user, revoked_at__isnull=True, expires_at__lte=now).update(revoked_at=now)
        if cls.objects.filter(user=user, revoked_at__isnull=True, expires_at__gt=now).exists():
            raise ValueError('An active token already exists for this student.')
        token = cls.objects.create(user=user, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=now + timedelta(minutes=duration_minutes), duration_minutes=duration_minutes, generation=generation)
        return token, raw_token

    @property
    def is_active(self):
        return self.revoked_at is None and timezone.now() < self.expires_at

    def mark_expired(self):
        if self.revoked_at is None and timezone.now() >= self.expires_at:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])


class TokenAudit(models.Model):
    token = models.OneToOneField(CampusToken, on_delete=models.CASCADE, related_name='audit')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='token_audits')
    snapshot = models.BinaryField()
    snapshot_size = models.PositiveIntegerField()
    verification_method = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)


class CampusLocation(models.Model):
    class Category(models.TextChoices):
        LIBRARY = 'LIBRARY', 'Library'
        SECURITY_GATE = 'SECURITY_GATE', 'Security Gate'
        ADMIN_BLOCK = 'ADMIN_BLOCK', 'Admin Block'
        HOSTEL = 'HOSTEL', 'Hostel'
        CANTEEN = 'CANTEEN', 'Canteen'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        SPORTS_COMPLEX = 'SPORTS_COMPLEX', 'Sports Complex'
        MEDICAL_CENTER = 'MEDICAL_CENTER', 'Medical Center'
        LAB = 'LAB', 'Lab'
        AUDITORIUM = 'AUDITORIUM', 'Auditorium'

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Category.choices)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    description = models.TextField(blank=True)
    building_code = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='campus_locations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'


class TokenNotification(models.Model):
    token = models.ForeignKey(CampusToken, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=16)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('token', 'kind'), name='unique_token_notification')]
