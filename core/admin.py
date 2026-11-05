from django.contrib import admin

from core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "user", "building", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action")