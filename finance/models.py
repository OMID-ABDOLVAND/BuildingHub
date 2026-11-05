from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from buildings.models import Building, TimeStampedModel, Unit


class Expense(TimeStampedModel):
    class Category(models.TextChoices):
        ELEVATOR = "elevator", "آسانسور"
        WATER = "water", "آب"
        ELECTRICITY = "electricity", "برق"
        GAS = "gas", "گاز"
        CLEANING = "cleaning", "نظافت"
        REPAIR = "repair", "تعمیرات"
        SECURITY = "security", "نگهبانی"
        OTHER = "other", "سایر"

    class AllocationMethod(models.TextChoices):
        EQUAL = "equal", "مساوی"
        RESIDENT = "resident", "بر اساس نفرات"
        AREA = "area", "بر اساس متراژ"
        CUSTOM = "custom", "سفارشی"

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        FINALIZED = "finalized", "نهایی‌شده"
        CANCELLED = "cancelled", "باطل‌شده"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    amount = models.BigIntegerField(help_text="مبلغ کل به تومان")
    expense_date = models.DateField()
    due_date = models.DateField()
    invoice_image = models.FileField(upload_to="invoices/", blank=True, null=True)
    allocation_method = models.CharField(
        max_length=20,
        choices=AllocationMethod.choices,
        default=AllocationMethod.EQUAL,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_expenses",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finalized_expenses",
    )
    included_units = models.ManyToManyField(Unit, related_name="expenses", blank=True)
    maintenance_request = models.ForeignKey(
        "maintenance.MaintenanceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_expenses",
    )

    class Meta:
        ordering = ["-expense_date", "-id"]

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "مبلغ باید بزرگ‌تر از صفر باشد."})

    def __str__(self) -> str:
        return f"{self.title} ({self.amount})"


class ExpenseAllocation(TimeStampedModel):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "پرداخت‌نشده"
        PARTIALLY_PAID = "partially_paid", "پرداخت ناقص"
        PAID = "paid", "تسویه‌شده"
        OVERDUE = "overdue", "معوق"

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="allocations")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="allocations")
    amount = models.BigIntegerField(help_text="سهم واحد به تومان")
    snapshot_resident_count = models.PositiveIntegerField(default=0)
    snapshot_area_sqm = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)

    class Meta:
        unique_together = ("expense", "unit")
        ordering = ["unit__number"]

    @property
    def approved_paid(self) -> int:
        return (
            self.payments.filter(status=Payment.Status.APPROVED).aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )

    @property
    def remaining(self) -> int:
        return max(self.amount - self.approved_paid, 0)

    def refresh_status(self, save: bool = True):
        paid = self.approved_paid
        if paid <= 0:
            new_status = self.Status.UNPAID
        elif paid >= self.amount:
            new_status = self.Status.PAID
        else:
            new_status = self.Status.PARTIALLY_PAID

        if (
            new_status != self.Status.PAID
            and self.expense.due_date
            and self.remaining > 0
        ):
            from django.utils import timezone

            if self.expense.due_date < timezone.localdate():
                new_status = self.Status.OVERDUE

        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])

    def __str__(self) -> str:
        return f"{self.unit} -> {self.amount}"


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        APPROVED = "approved", "تأییدشده"
        REJECTED = "rejected", "ردشده"

    allocation = models.ForeignKey(
        ExpenseAllocation,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.BigIntegerField(help_text="مبلغ پرداختی به تومان")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_payments",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_payments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payment {self.id} ({self.amount}) - {self.status}"


class PaymentReceipt(TimeStampedModel):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    file = models.FileField(upload_to="receipts/")
    original_name = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Receipt for payment {self.payment_id}"