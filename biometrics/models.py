from django.conf import settings
from django.db import models


class IdentityVerification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='identity_verifications')
    audit_snapshot = models.BinaryField()
    snapshot_size = models.PositiveIntegerField()
    verification_method = models.CharField(max_length=12)
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f'Identity verification for {self.user.email}'

    @property
    def is_valid(self):
        from django.utils import timezone
        return timezone.now() < self.expires_at
