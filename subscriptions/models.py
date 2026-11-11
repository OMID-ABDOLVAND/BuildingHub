from django.conf import settings
from django.db import models

from buildings.models import Building, TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    min_apartments = models.PositiveIntegerField(default=1)
    max_apartments = models.PositiveIntegerField(default=10)
    monthly_features = models.JSONField(default=list, blank=True)
    yearly_features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "min_apartments", "id"]

    def __str__(self) -> str:
        return self.name

    def matches_apartment_count(self, count: int) -> bool:
        return self.min_apartments <= count <= self.max_apartments


class SubscriptionPlanPricing(TimeStampedModel):
    class Duration(models.TextChoices):
        MONTHLY = "MONTHLY", "ماهانه"
        YEARLY = "YEARLY", "سالانه"

    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="pricings")
    duration = models.CharField(max_length=20, choices=Duration.choices)
    price_toman = models.BigIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("plan", "duration")
        ordering = ["plan_id", "duration"]

    def __str__(self) -> str:
        return f"{self.plan.name} / {self.duration}: {self.price_toman}"


class PlatformSettings(TimeStampedModel):
    """Singleton platform configuration (pk=1)."""

    grace_period_days = models.PositiveIntegerField(default=7)
    destination_card_number = models.CharField(max_length=32, blank=True)
    cardholder_name = models.CharField(max_length=120, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    payment_instructions = models.TextField(blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "Platform settings"

    def __str__(self) -> str:
        return "PlatformSettings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Subscription(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "در انتظار پرداخت"
        PENDING_APPROVAL = "PENDING_APPROVAL", "در انتظار تأیید"
        ACTIVE = "ACTIVE", "فعال"
        GRACE_PERIOD = "GRACE_PERIOD", "دوره ارفاق"
        EXPIRED = "EXPIRED", "منقضی"
        SUSPENDED = "SUSPENDED", "معلق"
        REJECTED = "REJECTED", "رد شده"
        CANCELLED = "CANCELLED", "لغو شده"

    class Duration(models.TextChoices):
        MONTHLY = "MONTHLY", "ماهانه"
        YEARLY = "YEARLY", "سالانه"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    plan_name_snapshot = models.CharField(max_length=120, blank=True)
    duration = models.CharField(max_length=20, choices=Duration.choices)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    apartment_capacity_snapshot = models.PositiveIntegerField(default=0)
    price_snapshot_toman = models.BigIntegerField(default=0)
    discount_toman = models.BigIntegerField(default=0)
    final_price_toman = models.BigIntegerField(default=0)
    is_free = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    grace_ends_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_subscriptions",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["building", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.building_id} {self.plan_name_snapshot} ({self.status})"

    @property
    def payable_amount(self) -> int:
        return max(int(self.final_price_toman), 0)


class SubscriptionPayment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "در انتظار پرداخت"
        SUBMITTED = "SUBMITTED", "ارسال‌شده"
        UNDER_REVIEW = "UNDER_REVIEW", "در حال بررسی"
        APPROVED = "APPROVED", "تأیید شده"
        REJECTED = "REJECTED", "رد شده"

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount_toman = models.BigIntegerField()
    payer_name = models.CharField(max_length=120, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_payments",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_subscription_payments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SubPay#{self.id} {self.status}"


class SubscriptionPaymentReceipt(TimeStampedModel):
    payment = models.OneToOneField(
        SubscriptionPayment,
        on_delete=models.CASCADE,
        related_name="receipt",
    )
    file = models.FileField(upload_to="subscription_receipts/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Receipt for SubPay#{self.payment_id}"


class SubscriptionHistory(TimeStampedModel):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "ایجاد"
        PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED", "ثبت پرداخت"
        APPROVED = "APPROVED", "تأیید"
        REJECTED = "REJECTED", "رد"
        ACTIVATED = "ACTIVATED", "فعال‌سازی"
        RENEWED = "RENEWED", "تمدید"
        GRACE_STARTED = "GRACE_STARTED", "شروع ارفاق"
        EXPIRED = "EXPIRED", "انقضا"
        SUSPENDED = "SUSPENDED", "تعلیق"
        REACTIVATED = "REACTIVATED", "فعال‌سازی مجدد"
        EXTENDED = "EXTENDED", "تمدید دستی"
        FREE_GRANTED = "FREE_GRANTED", "اشتراک رایگان"
        NOTIFY_7D = "NOTIFY_7D", "اعلان ۷ روز"
        NOTIFY_3D = "NOTIFY_3D", "اعلان ۳ روز"
        NOTIFY_0D = "NOTIFY_0D", "اعلان روز انقضا"
        NOTIFY_GRACE = "NOTIFY_GRACE", "اعلان ارفاق"
        NOTIFY_GRACE_END = "NOTIFY_GRACE_END", "اعلان پایان ارفاق"
        CANCELLED = "CANCELLED", "لغو"
        NOTE = "NOTE", "یادداشت"

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="history",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_history_events",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["subscription", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.subscription_id}:{self.event_type}"
