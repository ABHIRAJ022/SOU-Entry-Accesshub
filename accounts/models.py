from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import UserManager

class Branch(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    assigned_admin = models.OneToOneField('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_branch')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.assigned_admin_id:
            User.objects.filter(pk=self.assigned_admin_id, role=User.Role.ADMIN).exclude(branch_id=self.id).update(branch_id=self.id)

    def __str__(self):
        return f'{self.name} ({self.code})'

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'; STUDENT = 'STUDENT', 'Student'; SECURITY = 'SECURITY', 'Security Staff'
    email = models.EmailField(unique=True); enrollment_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=120); phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.SET_NULL, related_name='members')
    is_email_verified = models.BooleanField(default=False); is_approved_by_admin = models.BooleanField(default=False); is_approved_by_super_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now); is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    objects = UserManager()
    USERNAME_FIELD = 'email'; REQUIRED_FIELDS = ['full_name']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def can_login(self):
        if not self.is_email_verified:
            return False
        if self.role == self.Role.STUDENT:
            return bool(self.branch_id and self.is_approved_by_admin)
        return self.is_approved_by_super_admin

class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code_hash = models.CharField(max_length=128); created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0); used_at = models.DateTimeField(null=True, blank=True)
    def is_valid(self): return self.used_at is None and timezone.now() <= self.created_at + timedelta(minutes=10) and self.attempts < 5
