import hashlib
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from accounts.models import User


class CampusToken(models.Model):
    DAILY_LIMIT = 3

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name='campus_tokens')
    guest_request = models.OneToOneField('GuestTokenRequest', null=True, blank=True, on_delete=models.CASCADE, related_name='token')
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    generation = models.PositiveIntegerField(default=1)
    revoked_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='validated_tokens')

    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(user__isnull=False, guest_request__isnull=True) | models.Q(user__isnull=True, guest_request__isnull=False)), name='token_has_exactly_one_owner')]

    @classmethod
    def issue(cls, user, duration_minutes=60):
        user = User.objects.get(pk=user.pk)
        raw_token = secrets.token_urlsafe(32)
        latest = cls.objects.filter(user=user).order_by('-generation').first()
        generation = (latest.generation + 1) if latest else 1
        now = timezone.now()
        if cls.objects.filter(user=user, created_at__date=timezone.localdate()).count() >= cls.DAILY_LIMIT:
            raise ValueError('You can generate a maximum of 3 tokens per day.')
        cls.objects.filter(user=user, revoked_at__isnull=True, expires_at__lte=now).update(revoked_at=now)
        if cls.objects.filter(user=user, revoked_at__isnull=True, expires_at__gt=now).exists():
            raise ValueError('An active token already exists for this student.')
        token = cls.objects.create(user=user, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=now + timedelta(minutes=duration_minutes), duration_minutes=duration_minutes, generation=generation)
        return token, raw_token

    @classmethod
    def issue_for_guest(cls, guest_request):
        raw_token = secrets.token_urlsafe(32)
        now = timezone.now()
        token = cls.objects.create(
            guest_request=guest_request,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=guest_request.duration_minutes),
            duration_minutes=guest_request.duration_minutes,
            generation=1,
        )
        return token, raw_token

    @property
    def is_active(self):
        return self.revoked_at is None and timezone.now() < self.expires_at

    @property
    def holder_name(self):
        return self.user.full_name if self.user_id else self.guest_request.name

    @property
    def holder_email(self):
        return self.user.email if self.user_id else self.guest_request.email

    def mark_expired(self):
        if self.revoked_at is None and timezone.now() >= self.expires_at:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])


class GuestTokenRequest(models.Model):
    class Gender(models.TextChoices):
        FEMALE = 'FEMALE', 'Female'
        MALE = 'MALE', 'Male'
        NON_BINARY = 'NON_BINARY', 'Non-binary'
        PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', 'Prefer not to say'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        MAIN_ADMIN_REQUIRED = 'MAIN_ADMIN_REQUIRED', 'Main admin approval required'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    name = models.CharField(max_length=120)
    gender = models.CharField(max_length=20, choices=Gender.choices)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=32)
    purpose = models.CharField(max_length=500)
    live_photo = models.BinaryField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_guest_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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


class TokenScan(models.Model):
    """Record each scan of a token by a security staff member.

    Rules enforced by code and constraints:
    - A security user may scan a given token at most once (unique constraint).
    - The application will allow up to 3 distinct scans per token in total.
    """
    token = models.ForeignKey(CampusToken, on_delete=models.CASCADE, related_name='scans')
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='token_scans')
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('token', 'scanned_by'), name='unique_token_scan_per_user'),
        ]
        ordering = ['-scanned_at']
