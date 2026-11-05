import secrets
import string

from django.conf import settings
from django.db import models

from buildings.models import Building, TimeStampedModel, Unit


def generate_tracking_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "BH-" + "".join(secrets.choice(alphabet) for _ in range(8))


class MaintenanceRequest(TimeStampedModel):
    class Category(models.TextChoices):
        PLUMBING = "plumbing", "لوله‌کشی"
        ELECTRICAL = "electrical", "برق"
        ELEVATOR = "elevator", "آسانسور"
        STRUCTURAL = "structural", "سازه‌ای"
        CLEANING = "cleaning", "نظافت"
        OTHER = "other", "سایر"

    class Priority(models.TextChoices):
        LOW = "low", "کم"
        MEDIUM = "medium", "متوسط"
        HIGH = "high", "زیاد"
        URGENT = "urgent", "فوری"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "ثبت‌شده"
        UNDER_REVIEW = "under_review", "در حال بررسی"
        NEEDS_INFORMATION = "needs_information", "نیازمند اطلاعات بیشتر"
        IN_PROGRESS = "in_progress", "در حال اقدام"
        RESOLVED = "resolved", "حل‌شده"
        REJECTED = "rejected", "ردشده"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="maintenance_requests")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="maintenance_requests")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)
    tracking_code = models.CharField(max_length=20, unique=True, default=generate_tracking_code)
    image = models.FileField(upload_to="maintenance/", blank=True, null=True)
    resolution_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.tracking_code} - {self.title}"


class RequestMessage(TimeStampedModel):
    request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="request_messages",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message on {self.request.tracking_code}"