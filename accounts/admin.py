from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import EmailOTP, User

@admin.register(User)
class AccountUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'full_name', 'role', 'is_email_verified', 'is_approved_by_admin', 'is_active')
    ordering = ('email',)
    fieldsets = ((None, {'fields': ('email', 'password')}), ('Profile', {'fields': ('full_name', 'enrollment_number', 'phone_number', 'role')}), ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'is_approved_by_admin', 'groups', 'user_permissions')}))
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'full_name', 'password1', 'password2')}),)

admin.site.register(EmailOTP)
