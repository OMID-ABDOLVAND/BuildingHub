from django.contrib import admin

from support.models import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketMessage,
    SupportTicketStatusHistory,
)


class MessageInline(admin.TabularInline):
    model = SupportTicketMessage
    extra = 0


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "subject", "category", "priority", "status", "created_at")
    list_filter = ("status", "category", "priority")
    inlines = [MessageInline]


@admin.register(SupportTicketMessage)
class SupportTicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "sender", "is_internal", "created_at")


@admin.register(SupportTicketAttachment)
class SupportTicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "original_name", "created_at")


@admin.register(SupportTicketStatusHistory)
class SupportTicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "from_status", "to_status", "created_at")
