from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class PlatformRole(models.TextChoices):
        NONE = "", "بدون نقش پلتفرم"
        SUPER_ADMIN = "SUPER_ADMIN", "سوپرادمین"
        SUPPORT_OPERATOR = "SUPPORT_OPERATOR", "اپراتور پشتیبانی"

    phone = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    platform_role = models.CharField(
        max_length=30,
        choices=PlatformRole.choices,
        blank=True,
        default=PlatformRole.NONE,
        db_index=True,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_platform_super_admin(self) -> bool:
        return self.is_superuser or self.platform_role == self.PlatformRole.SUPER_ADMIN

    @property
    def is_support_operator(self) -> bool:
        return self.platform_role == self.PlatformRole.SUPPORT_OPERATOR or self.is_platform_super_admin
