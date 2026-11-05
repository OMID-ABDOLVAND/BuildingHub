from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Building(TimeStampedModel):
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
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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