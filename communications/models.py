from django.conf import settings
from django.db import models

from buildings.models import Building, TimeStampedModel


class Announcement(TimeStampedModel):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="announcements",
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Notification(TimeStampedModel):
    class Type(models.TextChoices):
        EXPENSE = "expense", "هزینه"
        PAYMENT = "payment", "پرداخت"
        MAINTENANCE = "maintenance", "تعمیرات"
        ANNOUNCEMENT = "announcement", "اطلاعیه"
        MESSAGE = "message", "پیام"
        SYSTEM = "system", "سیستم"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=255)
    body = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"