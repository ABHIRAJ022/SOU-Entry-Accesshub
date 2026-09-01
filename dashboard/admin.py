from django.contrib import admin, messages
from django.contrib.messages.api import MessageFailure
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import DatabaseError, OperationalError, ProgrammingError

from .models import CampusLocation, CampusToken, GuestTokenRequest, TokenAudit, TokenNotification, TokenScan


def _token_scan_table_available():
    try:
        return 'dashboard_tokenscan' in connection.introspection.table_names()
    except Exception:
        return False


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'building_code', 'latitude', 'longitude', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'building_code')


class TokenScanInline(admin.TabularInline):
    model = TokenScan
    fields = ('scanned_by', 'scanned_at')
    readonly_fields = ('scanned_by', 'scanned_at')
    extra = 0
    can_delete = False

@admin.register(CampusToken)
class CampusTokenAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'user', 'guest_request', 'expires_at', 'revoked_at', 'used_at')
    readonly_fields = ('token_hash', 'public_id', 'created_at')

    def get_inlines(self, request, obj=None):
        if not _token_scan_table_available():
            return []
        return (TokenScanInline,)

    def get_deleted_objects(self, objs, request):
        if not _token_scan_table_available():
            model_count = {self.model._meta.label: len(objs)}
            return [], model_count, set(), set()
        try:
            return super().get_deleted_objects(objs, request)
        except (DatabaseError, ProgrammingError, OperationalError):
            model_count = {self.model._meta.label: len(objs)}
            return [], model_count, set(), set()

    def delete_queryset(self, request, queryset):
        if not _token_scan_table_available():
            try:
                if hasattr(request, '_messages'):
                    messages.error(request, 'Campus token deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass
            return
        try:
            super().delete_queryset(request, queryset)
        except (DatabaseError, ProgrammingError, OperationalError):
            try:
                if hasattr(request, '_messages'):
                    messages.error(request, 'Campus token deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass


@admin.register(TokenAudit)
class TokenAuditAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'verification_method', 'created_at')
    readonly_fields = ('snapshot', 'created_at')


@admin.register(TokenNotification)
class TokenNotificationAdmin(admin.ModelAdmin):
    list_display = ('token', 'kind', 'sent_at')


if _token_scan_table_available():
    @admin.register(TokenScan)
    class TokenScanAdmin(admin.ModelAdmin):
        list_display = ('token', 'scanned_by', 'scanned_at')
        list_filter = ('scanned_at', 'scanned_by')
        search_fields = ('token__public_id', 'scanned_by__email', 'scanned_by__full_name')
        readonly_fields = ('scanned_at',)


@admin.register(GuestTokenRequest)
class GuestTokenRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'purpose', 'status', 'approved_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'email', 'mobile', 'purpose')
    readonly_fields = ('created_at', 'updated_at', 'approved_at')

    def get_deleted_objects(self, objs, request):
        if not _token_scan_table_available():
            model_count = {self.model._meta.label: len(objs)}
            return [], model_count, set(), set()
        try:
            return super().get_deleted_objects(objs, request)
        except (DatabaseError, ProgrammingError, OperationalError):
            model_count = {self.model._meta.label: len(objs)}
            return [], model_count, set(), set()

    def delete_queryset(self, request, queryset):
        if not _token_scan_table_available():
            try:
                if hasattr(request, '_messages'):
                    messages.error(request, 'Guest token request deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass
            return
        try:
            super().delete_queryset(request, queryset)
        except (DatabaseError, ProgrammingError, OperationalError):
            try:
                if hasattr(request, '_messages'):
                    messages.error(request, 'Guest token request deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass