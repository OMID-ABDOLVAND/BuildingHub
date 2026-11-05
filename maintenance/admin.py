from django.contrib import admin

from maintenance.models import MaintenanceRequest, RequestMessage


class MessageInline(admin.TabularInline):
    model = RequestMessage
    extra = 0


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ("tracking_code", "title", "building", "status", "priority", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("tracking_code", "title")
    inlines = [MessageInline]