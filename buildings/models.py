import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Building(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "در انتظار تأیید"
        ACTIVE = "ACTIVE", "فعال"
        SUSPENDED = "SUSPENDED", "معلق"
        REJECTED = "REJECTED", "رد شده"

    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_buildings",
    )
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    floors_count = models.PositiveIntegerField(default=0)
    apartments_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def sync_is_active(self):
        self.is_active = self.status == self.Status.ACTIVE

    def save(self, *args, **kwargs):
        self.sync_is_active()
        super().save(*args, **kwargs)

    def current_subscription(self):
        from subscriptions.models import Subscription

        return (
            self.subscriptions.exclude(
                status__in=[
                    Subscription.Status.CANCELLED,
                    Subscription.Status.REJECTED,
                ]
            )
            .order_by("-created_at")
            .first()
        )


class Membership(TimeStampedModel):
    class Role(models.TextChoices):
        MANAGER = "manager", "مدیر"
        RESIDENT = "resident", "ساکن"

    class Status(models.TextChoices):
        ACTIVE = "active", "فعال"
        INACTIVE = "inactive", "غیرفعال"
        PENDING = "pending", "در انتظار"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RESIDENT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        unique_together = ("user", "building")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.building} ({self.role})"


class Unit(TimeStampedModel):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="units")
    number = models.CharField(max_length=50)
    floor = models.IntegerField(default=0)
    area_sqm = models.PositiveIntegerField(help_text="متراژ به متر مربع")
    resident_count = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("building", "number")
        ordering = ["floor", "number"]

    def __str__(self) -> str:
        return f"{self.building.name} - واحد {self.number}"


class UnitOccupancy(TimeStampedModel):
    class Relationship(models.TextChoices):
        OWNER = "owner", "مالک"
        TENANT = "tenant", "مستأجر"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="occupancies")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="occupancies",
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=Relationship.choices,
        default=Relationship.TENANT,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    occupants_count = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["unit", "is_current"]),
            models.Index(fields=["user", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.unit}"
def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


class ResidentInvitation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "?? ??????"
        ACCEPTED = "ACCEPTED", "???????????"
        EXPIRED = "EXPIRED", "?????"
        REVOKED = "REVOKED", "????????"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="invitations")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_invitations",
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    relationship_type = models.CharField(
        max_length=20,
        choices=UnitOccupancy.Relationship.choices,
        default=UnitOccupancy.Relationship.TENANT,
    )
    start_date = models.DateField()
    occupants_count = models.PositiveIntegerField(default=1)
    token = models.CharField(max_length=64, unique=True, default=generate_invitation_token, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["building", "status"]),
            models.Index(fields=["token", "status"]),
        ]

    def __str__(self) -> str:
        return f"Invite {self.phone or self.email} -> {self.unit}"

    def is_usable(self) -> bool:
        if self.status != self.Status.PENDING:
            return False
        if self.expires_at <= timezone.now():
            return False
        return True

    def mark_expired_if_needed(self) -> bool:
        if self.status == self.Status.PENDING and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status", "updated_at"])
            return True
        return False
