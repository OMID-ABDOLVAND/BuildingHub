from calendar import monthrange
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from buildings.models import Building
from communications.models import Notification
from core.models import AuditLog
from core.utils import notify_user
from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionHistory,
    SubscriptionPayment,
    SubscriptionPlan,
    SubscriptionPlanPricing,
)


def add_subscription_history(subscription, event_type, *, actor=None, message="", metadata=None):
    return SubscriptionHistory.objects.create(
        subscription=subscription,
        event_type=event_type,
        actor=actor,
        message=message,
        metadata=metadata or {},
    )


def has_history_event(subscription, event_type) -> bool:
    return SubscriptionHistory.objects.filter(
        subscription=subscription,
        event_type=event_type,
    ).exists()


def _add_months(dt, months: int):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def compute_period_end(starts_at, duration: str):
    if duration == Subscription.Duration.YEARLY:
        return _add_months(starts_at, 12)
    return _add_months(starts_at, 1)


def resolve_plan_for_apartments(apartment_count: int) -> SubscriptionPlan:
    plan = (
        SubscriptionPlan.objects.filter(
            is_active=True,
            min_apartments__lte=apartment_count,
            max_apartments__gte=apartment_count,
        )
        .order_by("display_order", "min_apartments")
        .first()
    )
    if not plan:
        raise ValidationError(
            {"plan": f"پلنی برای ظرفیت {apartment_count} واحد یافت نشد."}
        )
    return plan


def get_pricing(plan: SubscriptionPlan, duration: str) -> SubscriptionPlanPricing:
    pricing = plan.pricings.filter(duration=duration, is_active=True).first()
    if not pricing:
        raise ValidationError({"duration": "قیمت‌گذاری برای این مدت فعال نیست."})
    return pricing


@transaction.atomic
def create_subscription_for_building(
    *,
    building: Building,
    duration: str,
    plan: SubscriptionPlan | None = None,
    created_by=None,
    discount_toman: int = 0,
    is_free: bool = False,
) -> Subscription:
    apartment_count = building.apartments_count or building.units.count() or 1
    if plan is None:
        plan = resolve_plan_for_apartments(apartment_count)
    if not plan.matches_apartment_count(apartment_count):
        raise ValidationError(
            {
                "plan": (
                    f"پلن «{plan.name}» برای ظرفیت {apartment_count} واحد مناسب نیست "
                    f"({plan.min_apartments}–{plan.max_apartments})."
                )
            }
        )
    pricing = get_pricing(plan, duration)
    price = 0 if is_free else int(pricing.price_toman)
    discount = min(max(int(discount_toman), 0), price)
    final_price = 0 if is_free else price - discount

    subscription = Subscription.objects.create(
        building=building,
        plan=plan,
        plan_name_snapshot=plan.name,
        duration=duration,
        status=Subscription.Status.PENDING_PAYMENT,
        apartment_capacity_snapshot=apartment_count,
        price_snapshot_toman=price,
        discount_toman=discount,
        final_price_toman=final_price,
        is_free=is_free,
        created_by=created_by,
    )
    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.CREATED,
        actor=created_by,
        message="اشتراک ایجاد شد.",
        metadata={"duration": duration, "final_price": final_price},
    )
    return subscription


@transaction.atomic
def activate_subscription(subscription: Subscription, *, actor=None, request=None):
    now = timezone.now()
    settings = PlatformSettings.get_solo()
    # Extend from current expiry when still covered; otherwise start now.
    if subscription.expires_at and subscription.expires_at > now:
        period_start = subscription.expires_at
    else:
        period_start = now
    expires_at = compute_period_end(period_start, subscription.duration)

    subscription.status = Subscription.Status.ACTIVE
    subscription.starts_at = subscription.starts_at or now
    subscription.expires_at = expires_at
    subscription.grace_ends_at = None
    subscription.activated_at = now
    subscription.save(
        update_fields=[
            "status",
            "starts_at",
            "expires_at",
            "grace_ends_at",
            "activated_at",
            "updated_at",
        ]
    )

    building = subscription.building
    building.status = Building.Status.ACTIVE
    building.save(update_fields=["status", "is_active", "updated_at"])

    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.ACTIVATED,
        actor=actor,
        message="اشتراک فعال شد.",
        metadata={
            "starts_at": str(subscription.starts_at),
            "expires_at": str(subscription.expires_at),
            "grace_period_days": settings.grace_period_days,
        },
    )
    if request is not None:
        AuditLog.objects.create(
            user=actor,
            building=building,
            action="subscription.activate",
            entity_type="Subscription",
            entity_id=str(subscription.id),
            changes={"expires_at": str(expires_at)},
            ip_address=None,
        )
    notify_user(
        user=building.manager,
        title="اشتراک فعال شد",
        body=f"اشتراک ساختمان «{building.name}» فعال شد و تا {timezone.localtime(expires_at):%Y-%m-%d} معتبر است.",
        type=Notification.Type.SUBSCRIPTION,
        building=building,
        link="/app/subscription",
    )
    return subscription


@transaction.atomic
def approve_subscription_payment(payment: SubscriptionPayment, *, actor, request=None):
    payment = SubscriptionPayment.objects.select_for_update().select_related(
        "subscription", "subscription__building"
    ).get(pk=payment.pk)

    if payment.status == SubscriptionPayment.Status.APPROVED:
        raise ValidationError("این پرداخت قبلاً تأیید شده است.")
    if payment.status == SubscriptionPayment.Status.REJECTED:
        raise ValidationError("پرداخت ردشده قابل تأیید نیست؛ پرداخت جدید ثبت کنید.")
    if payment.status not in {
        SubscriptionPayment.Status.SUBMITTED,
        SubscriptionPayment.Status.UNDER_REVIEW,
    }:
        raise ValidationError("وضعیت پرداخت برای تأیید مناسب نیست.")

    now = timezone.now()
    payment.status = SubscriptionPayment.Status.APPROVED
    payment.reviewed_by = actor
    payment.reviewed_at = now
    payment.approved_at = now
    payment.rejection_reason = ""
    payment.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "approved_at",
            "rejection_reason",
            "updated_at",
        ]
    )

    subscription = payment.subscription
    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.APPROVED,
        actor=actor,
        message="پرداخت اشتراک تأیید شد.",
        metadata={"payment_id": payment.id},
    )
    activate_subscription(subscription, actor=actor, request=request)

    if request is not None:
        from core.utils import audit

        audit(
            request,
            action="subscription_payment.approve",
            entity_type="SubscriptionPayment",
            entity_id=payment.id,
            building=subscription.building,
            changes={"amount": payment.amount_toman},
        )
    return payment


@transaction.atomic
def reject_subscription_payment(payment: SubscriptionPayment, *, actor, reason: str, request=None):
    if not reason:
        raise ValidationError({"rejection_reason": "دلیل رد الزامی است."})
    payment = SubscriptionPayment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == SubscriptionPayment.Status.APPROVED:
        raise ValidationError("پرداخت تأییدشده قابل رد نیست.")
    if payment.status == SubscriptionPayment.Status.REJECTED:
        raise ValidationError("این پرداخت قبلاً رد شده است.")

    now = timezone.now()
    payment.status = SubscriptionPayment.Status.REJECTED
    payment.rejection_reason = reason
    payment.reviewed_by = actor
    payment.reviewed_at = now
    payment.save(
        update_fields=["status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at"]
    )

    subscription = payment.subscription
    subscription.status = Subscription.Status.REJECTED
    subscription.save(update_fields=["status", "updated_at"])

    building = subscription.building
    building.status = Building.Status.PENDING
    building.save(update_fields=["status", "is_active", "updated_at"])

    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.REJECTED,
        actor=actor,
        message=reason,
        metadata={"payment_id": payment.id},
    )
    notify_user(
        user=building.manager,
        title="پرداخت اشتراک رد شد",
        body=f"پرداخت اشتراک ساختمان «{building.name}» رد شد: {reason}",
        type=Notification.Type.SUBSCRIPTION,
        building=building,
        link="/app/onboarding/payment",
    )
    if request is not None:
        from core.utils import audit

        audit(
            request,
            action="subscription_payment.reject",
            entity_type="SubscriptionPayment",
            entity_id=payment.id,
            building=building,
            changes={"reason": reason},
        )
    return payment


@transaction.atomic
def grant_free_subscription(*, building: Building, duration: str, plan=None, actor=None, notes=""):
    subscription = create_subscription_for_building(
        building=building,
        duration=duration,
        plan=plan,
        created_by=actor,
        is_free=True,
    )
    subscription.notes = notes
    subscription.save(update_fields=["notes", "updated_at"])
    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.FREE_GRANTED,
        actor=actor,
        message=notes or "اشتراک رایگان اعطا شد.",
    )
    return activate_subscription(subscription, actor=actor)


@transaction.atomic
def extend_subscription(subscription: Subscription, *, days: int, actor=None):
    if days <= 0:
        raise ValidationError({"days": "تعداد روز باید مثبت باشد."})
    base = subscription.expires_at or timezone.now()
    subscription.expires_at = base + timedelta(days=days)
    if subscription.status in {
        Subscription.Status.EXPIRED,
        Subscription.Status.GRACE_PERIOD,
    }:
        subscription.status = Subscription.Status.ACTIVE
        subscription.grace_ends_at = None
        building = subscription.building
        building.status = Building.Status.ACTIVE
        building.save(update_fields=["status", "is_active", "updated_at"])
    subscription.save(update_fields=["expires_at", "status", "grace_ends_at", "updated_at"])
    add_subscription_history(
        subscription,
        SubscriptionHistory.EventType.EXTENDED,
        actor=actor,
        message=f"تمدید دستی {days} روز",
        metadata={"days": days, "expires_at": str(subscription.expires_at)},
    )
    return subscription


def process_subscription_lifecycle(*, now=None) -> dict:
    """ACTIVE→GRACE_PERIOD→EXPIRED and expiration notifications (idempotent)."""
    now = now or timezone.now()
    settings = PlatformSettings.get_solo()
    grace_days = settings.grace_period_days or 7
    stats = {
        "grace_started": 0,
        "expired": 0,
        "notify_7d": 0,
        "notify_3d": 0,
        "notify_0d": 0,
        "notify_grace": 0,
        "notify_grace_end": 0,
    }

    active_subs = Subscription.objects.filter(status=Subscription.Status.ACTIVE).select_related(
        "building", "building__manager"
    )
    for sub in active_subs:
        if not sub.expires_at:
            continue
        days_left = (timezone.localdate(sub.expires_at) - timezone.localdate(now)).days

        if days_left == 7 and not has_history_event(sub, SubscriptionHistory.EventType.NOTIFY_7D):
            notify_user(
                user=sub.building.manager,
                title="۷ روز تا پایان اشتراک",
                body=f"اشتراک ساختمان «{sub.building.name}» تا ۷ روز دیگر منقضی می‌شود.",
                type=Notification.Type.SUBSCRIPTION,
                building=sub.building,
                link="/app/subscription",
            )
            add_subscription_history(sub, SubscriptionHistory.EventType.NOTIFY_7D, message="اعلان ۷ روز")
            stats["notify_7d"] += 1

        if days_left == 3 and not has_history_event(sub, SubscriptionHistory.EventType.NOTIFY_3D):
            notify_user(
                user=sub.building.manager,
                title="۳ روز تا پایان اشتراک",
                body=f"اشتراک ساختمان «{sub.building.name}» تا ۳ روز دیگر منقضی می‌شود.",
                type=Notification.Type.SUBSCRIPTION,
                building=sub.building,
                link="/app/subscription",
            )
            add_subscription_history(sub, SubscriptionHistory.EventType.NOTIFY_3D, message="اعلان ۳ روز")
            stats["notify_3d"] += 1

        if sub.expires_at <= now:
            sub.status = Subscription.Status.GRACE_PERIOD
            sub.grace_ends_at = now + timedelta(days=grace_days)
            sub.save(update_fields=["status", "grace_ends_at", "updated_at"])
            add_subscription_history(
                sub,
                SubscriptionHistory.EventType.GRACE_STARTED,
                message="ورود به دوره ارفاق",
                metadata={"grace_ends_at": str(sub.grace_ends_at)},
            )
            if not has_history_event(sub, SubscriptionHistory.EventType.NOTIFY_0D):
                notify_user(
                    user=sub.building.manager,
                    title="اشتراک منقضی شد — دوره ارفاق",
                    body=(
                        f"اشتراک «{sub.building.name}» منقضی شد. "
                        f"تا {grace_days} روز می‌توانید تمدید کنید؛ عملیات مدیریتی محدود است."
                    ),
                    type=Notification.Type.SUBSCRIPTION,
                    building=sub.building,
                    link="/app/subscription",
                )
                add_subscription_history(sub, SubscriptionHistory.EventType.NOTIFY_0D, message="اعلان انقضا")
                stats["notify_0d"] += 1
            if not has_history_event(sub, SubscriptionHistory.EventType.NOTIFY_GRACE):
                add_subscription_history(sub, SubscriptionHistory.EventType.NOTIFY_GRACE, message="اعلان ارفاق")
                stats["notify_grace"] += 1
            stats["grace_started"] += 1

    grace_subs = Subscription.objects.filter(status=Subscription.Status.GRACE_PERIOD).select_related(
        "building", "building__manager"
    )
    for sub in grace_subs:
        if sub.grace_ends_at and sub.grace_ends_at <= now:
            sub.status = Subscription.Status.EXPIRED
            sub.save(update_fields=["status", "updated_at"])
            add_subscription_history(sub, SubscriptionHistory.EventType.EXPIRED, message="پایان دوره ارفاق")
            if not has_history_event(sub, SubscriptionHistory.EventType.NOTIFY_GRACE_END):
                notify_user(
                    user=sub.building.manager,
                    title="دوره ارفاق به پایان رسید",
                    body=(
                        f"اشتراک «{sub.building.name}» منقضی است. "
                        "فقط تمدید و پشتیبانی در دسترس است."
                    ),
                    type=Notification.Type.SUBSCRIPTION,
                    building=sub.building,
                    link="/app/subscription",
                )
                add_subscription_history(
                    sub, SubscriptionHistory.EventType.NOTIFY_GRACE_END, message="اعلان پایان ارفاق"
                )
                stats["notify_grace_end"] += 1
            stats["expired"] += 1

    return stats
