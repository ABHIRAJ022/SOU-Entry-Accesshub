from django.contrib import admin

from .models import CampusLocation, CampusToken, TokenAudit, TokenNotification


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'building_code', 'latitude', 'longitude', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'building_code')


@admin.register(CampusToken)
class CampusTokenAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'user', 'expires_at', 'revoked_at', 'used_at')
    readonly_fields = ('token_hash', 'public_id', 'created_at')


@admin.register(TokenAudit)
class TokenAuditAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'verification_method', 'created_at')
    readonly_fields = ('snapshot', 'created_at')


@admin.register(TokenNotification)
class TokenNotificationAdmin(admin.ModelAdmin):
    list_display = ('token', 'kind', 'sent_at')