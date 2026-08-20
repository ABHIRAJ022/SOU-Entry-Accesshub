from django.conf import settings
from django.db import models


class FaceProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='face_profile')
    encrypted_vector = models.TextField()
    vector_version = models.PositiveSmallIntegerField(default=1)
    samples_count = models.PositiveSmallIntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Face profile for {self.user.email}'
