import os
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from communications.models import Notification
from core.models import AuditLog


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(request, *, action, entity_type, entity_id="", building=None, changes=None):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        building=building,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        changes=changes or {},
        ip_address=get_client_ip(request),
    )


def notify_user(*, user, title, body, type=Notification.Type.SYSTEM, building=None, link=""):
    return Notification.objects.create(
        user=user,
        building=building,
        type=type,
        title=title,
        body=body,
        link=link,
    )


def notify_building_members(*, building, title, body, type=Notification.Type.SYSTEM, link="", exclude_user=None):
    from buildings.models import Membership

    memberships = Membership.objects.filter(
        building=building,
        status=Membership.Status.ACTIVE,
    ).select_related("user")
    created = []
    for m in memberships:
        if exclude_user and m.user_id == exclude_user.id:
            continue
        created.append(
            Notification(
                user=m.user,
                building=building,
                type=type,
                title=title,
                body=body,
                link=link,
            )
        )
    Notification.objects.bulk_create(created)
    return len(created)


def validate_upload(uploaded_file):
    if not uploaded_file:
        raise ValidationError("فایل الزامی است.")
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError("حجم فایل نباید بیشتر از ۵ مگابایت باشد.")
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("فرمت فایل مجاز نیست. فقط jpg، png، webp و pdf پذیرفته می‌شود.")
    return ext


def safe_upload_name(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def to_jalali(dt):
    if not dt:
        return None
    try:
        import jdatetime

        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        if hasattr(dt, "hour"):
            j = jdatetime.datetime.fromgregorian(datetime=dt)
            return j.strftime("%Y/%m/%d %H:%M")
        j = jdatetime.date.fromgregorian(date=dt)
        return j.strftime("%Y/%m/%d")
    except Exception:
        return str(dt)