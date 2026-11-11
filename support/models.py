import uuid

from django.conf import settings
from django.db import models

from buildings.models import Building, TimeStampedModel


def generate_ticket_number() -> str:
    return f"TKT-{uuid.uuid4().hex[:10].upper()}"


class SupportTicket(TimeStampedModel):
    class Category(models.TextChoices):
        TECHNICAL = "TECHNICAL", "فنی"
        SUBSCRIPTION = "SUBSCRIPTION", "اشتراک"
        PAYMENT = "PAYMENT", "پرداخت"
        ACCOUNT = "ACCOUNT_ACCESS", "دسترسی حساب"
        BUG = "BUG_REPORT", "گزارش باگ"
        FEATURE = "FEATURE_REQUEST", "درخواست ویژگی"
        OTHER = "OTHER", "سایر"

    class Priority(models.TextChoices):
        LOW = "LOW", "کم"
        NORMAL = "NORMAL", "عادی"
        HIGH = "HIGH", "بالا"
        URGENT = "URGENT", "فوری"

    class Status(models.TextChoices):
        OPEN = "OPEN", "باز"
        IN_PROGRESS = "IN_PROGRESS", "در حال انجام"
        WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER", "منتظر مشتری"
        ANSWERED = "ANSWERED", "پاسخ داده‌شده"
        CLOSED = "CLOSED", "بسته"

    ticket_number = models.CharField(max_length=32, unique=True, default=generate_ticket_number)
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="support_tickets",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="support_tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
    )
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True)
    description = models.TextField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["created_by", "status"]),
        ]

    def __str__(self) -> str:
        return self.ticket_number


class SupportTicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="support_messages",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Msg#{self.id} on {self.ticket.ticket_number}"


class SupportTicketAttachment(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="attachments")
    message = models.ForeignKey(
        SupportTicketMessage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_attachments",
    )
    file = models.FileField(upload_to="support_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return self.original_name or f"Attachment#{self.id}"


class SupportTicketStatusHistory(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_status_changes",
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Support ticket status histories"

    def __str__(self) -> str:
        return f"{self.ticket.ticket_number}: {self.from_status}→{self.to_status}"
