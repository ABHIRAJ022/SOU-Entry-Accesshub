from django.contrib import admin
from .models import FaceProfile


@admin.register(FaceProfile)
class FaceProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'samples_count', 'vector_version', 'updated_at')
    readonly_fields = ('encrypted_vector', 'enrolled_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name')
