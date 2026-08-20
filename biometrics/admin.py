from django.contrib import admin
from .models import IdentityVerification


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_method', 'snapshot_size', 'verified_at', 'expires_at')
    readonly_fields = ('audit_snapshot', 'snapshot_size', 'verified_at', 'expires_at')
    search_fields = ('user__email', 'user__full_name')
