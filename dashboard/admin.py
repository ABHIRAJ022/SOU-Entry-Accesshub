from django.contrib import admin

from .models import CampusLocation, CampusToken, GuestTokenRequest, TokenAudit, TokenNotification


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'building_code', 'latitude', 'longitude', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'building_code')


@admin.register(CampusToken)
class CampusTokenAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'user', 'guest_request', 'expires_at', 'revoked_at', 'used_at')
    readonly_fields = ('token_hash', 'public_id', 'created_at')


@admin.register(TokenAudit)
class TokenAuditAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'verification_method', 'created_at')
    readonly_fields = ('snapshot', 'created_at')


@admin.register(TokenNotification)
class TokenNotificationAdmin(admin.ModelAdmin):
    list_display = ('token', 'kind', 'sent_at')


@admin.register(GuestTokenRequest)
class GuestTokenRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'purpose', 'status', 'approved_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'mobile', 'purpose')
    readonly_fields = ('created_at', 'updated_at', 'approved_at')