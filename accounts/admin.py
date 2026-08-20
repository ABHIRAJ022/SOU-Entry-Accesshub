from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Branch, EmailOTP, User

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'assigned_admin', 'is_active')
    search_fields = ('name', 'code')

@admin.register(User)
class AccountUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'full_name', 'role', 'branch', 'is_email_verified', 'is_approved_by_admin', 'is_approved_by_super_admin', 'is_active')
    ordering = ('email',)
    fieldsets = ((None, {'fields': ('email', 'password')}), ('Profile', {'fields': ('full_name', 'enrollment_number', 'phone_number', 'role', 'branch')}), ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'is_approved_by_admin', 'is_approved_by_super_admin', 'groups', 'user_permissions')}))
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'full_name', 'password1', 'password2')}),)

admin.site.register(EmailOTP)
