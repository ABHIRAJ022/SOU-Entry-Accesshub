from django.contrib import admin
from .models import AccessReport, AccessReportSchedule, AuditLog, EventNotification, SystemHealthEvent


@admin.register(SystemHealthEvent)
class SystemHealthEventAdmin(admin.ModelAdmin):
    list_display = ('component', 'status', 'opened_at', 'recovered_at')
    list_filter = ('component', 'status')
    readonly_fields = tuple(field.name for field in SystemHealthEvent._meta.fields)


@admin.register(AccessReportSchedule)
class AccessReportScheduleAdmin(admin.ModelAdmin):
    list_display = ('period', 'enabled', 'last_sent_at')
    list_filter = ('period', 'enabled')


@admin.register(AccessReport)
class AccessReportAdmin(admin.ModelAdmin):
    list_display = ('period', 'starts_at', 'ends_at', 'generated_at')
    readonly_fields = tuple(field.name for field in AccessReport._meta.fields)


@admin.register(EventNotification)
class EventNotificationAdmin(admin.ModelAdmin):
    list_display = ('event', 'created_at', 'sent_at')
    readonly_fields = tuple(field.name for field in EventNotification._meta.fields)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event', 'action', 'status', 'user', 'ip_address', 'path')
    list_filter = ('event', 'status', 'created_at')
    search_fields = ('user__email', 'ip_address', 'path', 'action')
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False