from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("اطلاعات تکمیلی", {"fields": ("phone", "national_id", "avatar")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "is_staff")