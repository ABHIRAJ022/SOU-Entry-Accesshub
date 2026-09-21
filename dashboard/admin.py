from django.contrib import admin, messages
from django.contrib.messages.api import MessageFailure
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import DatabaseError, OperationalError, ProgrammingError
from django import forms

from .models import CampusLocation, CampusToken, GuestTokenRequest, LocationCategory, SecurityDevice, TokenAudit, TokenNotification, TokenScan


class SecurityDeviceAdminForm(forms.ModelForm):
    credential = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False), help_text='Set or rotate the device credential. It is stored hashed.')

    class Meta:
        model = SecurityDevice
        exclude = ('credential_hash',)


@admin.register(SecurityDevice)
class SecurityDeviceAdmin(admin.ModelAdmin):
    form = SecurityDeviceAdminForm
    list_display = ('device_id', 'name', 'gate', 'campus_location', 'status', 'last_seen')
    list_filter = ('status', 'campus_location')
    search_fields = ('device_id', 'name', 'gate')
    filter_horizontal = ('assigned_security_staff',)

    def save_model(self, request, obj, form, change):
        credential = form.cleaned_data.get('credential')
        if credential:
            obj.set_credential(credential)
        super().save_model(request, obj, form, change)


def _token_scan_table_available():
    return True


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'building_code', 'latitude', 'longitude', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'building_code')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['category'] = forms.ChoiceField(
            choices=_location_category_choices(),
            label='Category',
            required=True,
        )
        return form


def _location_category_choices():
    built_in = list(CampusLocation.Category.choices)
    custom = LocationCategory.objects.exclude(code__in=dict(built_in)).values_list('code', 'name')
    return built_in + list(custom)


@admin.register(LocationCategory)
class LocationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at',)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class TokenScanInline(admin.TabularInline):
    model = TokenScan
    fields = ('scanned_by', 'location', 'scanned_at')
    readonly_fields = ('scanned_by', 'location', 'scanned_at')
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