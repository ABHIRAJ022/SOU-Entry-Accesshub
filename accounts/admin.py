from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.messages.api import MessageFailure
from django import forms
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection
from django.db.utils import DatabaseError, OperationalError, ProgrammingError
from .models import Branch, EmailOTP, User


def _token_scan_table_available():
    return True

class AccountUserAdminForm(forms.ModelForm):
    profile_photo = forms.ImageField(required=False, label='Profile photo')

    class Meta:
        model = User
        exclude = ('profile_photo',)

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo and photo.size > 2 * 1024 * 1024:
            raise ValidationError('Profile photos must be 2 MB or smaller.')
        return photo

    def save(self, commit=True):
        user = super().save(commit=False)
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            user.profile_photo = photo.read()
        if commit:
            user.save()
            self.save_m2m()
        return user

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'assigned_admin', 'is_active')
    search_fields = ('name', 'code')

@admin.register(User)
class AccountUserAdmin(UserAdmin):
    model = User
    form = AccountUserAdminForm
    list_display = ('email', 'full_name', 'role', 'branch', 'is_email_verified', 'is_approved_by_admin', 'is_approved_by_super_admin', 'is_active')
    ordering = ('email',)
    fieldsets = ((None, {'fields': ('email', 'password')}), ('Profile', {'fields': ('full_name', 'enrollment_number', 'phone_number', 'profile_photo', 'role', 'branch')}), ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'is_approved_by_admin', 'is_approved_by_super_admin', 'groups', 'user_permissions')}))
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'full_name', 'password1', 'password2')}),)

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
                    messages.error(request, 'User deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass
            return
        try:
            super().delete_queryset(request, queryset)
        except (DatabaseError, ProgrammingError, OperationalError):
            try:
                if hasattr(request, '_messages'):
                    messages.error(request, 'User deletion could not continue because the TokenScan database table is missing. Run the migrations and try again.')
            except (AttributeError, ImproperlyConfigured, MessageFailure):
                pass

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets
        return tuple(
            (name, {**options, 'fields': tuple(field for field in options['fields'] if field != 'profile_photo')})
            for name, options in fieldsets
        )

admin.site.register(EmailOTP)
