from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core.exceptions import ValidationError
from .models import Branch, EmailOTP, User

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

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if request.user.is_superuser:
            return fieldsets
        return tuple(
            (name, {**options, 'fields': tuple(field for field in options['fields'] if field != 'profile_photo')})
            for name, options in fieldsets
        )

admin.site.register(EmailOTP)
