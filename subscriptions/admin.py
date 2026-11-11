from django.contrib import admin

from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionHistory,
    SubscriptionPayment,
    SubscriptionPaymentReceipt,
    SubscriptionPlan,
    SubscriptionPlanPricing,
)


class PricingInline(admin.TabularInline):
    model = SubscriptionPlanPricing
    extra = 0


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "min_apartments", "max_apartments", "is_active", "display_order")
    inlines = [PricingInline]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "building",
        "plan_name_snapshot",
        "duration",
        "status",
        "final_price_toman",
        "expires_at",
    )
    list_filter = ("status", "duration")


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "subscription", "amount_toman", "status", "created_at")
    list_filter = ("status",)


@admin.register(SubscriptionPaymentReceipt)
class SubscriptionPaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "original_name", "created_at")


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ("subscription", "event_type", "created_at")
    list_filter = ("event_type",)


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ("pk", "grace_period_days", "bank_name", "cardholder_name")
