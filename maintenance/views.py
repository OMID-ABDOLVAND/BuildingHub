from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from communications.models import Notification
from core.permissions import (
    assert_building_write_allowed,
    can_access_unit,
    is_manager_of,
    is_platform_super_admin,
    managed_building_ids,
    user_unit_ids,
)
from core.utils import audit, notify_user, safe_upload_name, validate_upload
from maintenance.models import MaintenanceRequest, RequestMessage
from maintenance.serializers import (
    MaintenanceRequestSerializer,
    MaintenanceStatusSerializer,
    RequestMessageSerializer,
)


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ["building", "unit", "status", "priority", "category"]
    search_fields = ["title", "tracking_code", "description"]
    ordering_fields = ["created_at", "priority", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceRequest.objects.select_related(
            "building", "unit", "created_by"
        ).prefetch_related("messages", "messages__sender")
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        return qs.filter(
            Q(building_id__in=manager_ids) | Q(unit_id__in=user_unit_ids(user))
        ).distinct()

    def perform_create(self, serializer):
        unit = serializer.validated_data["unit"]
        building = serializer.validated_data.get("building") or unit.building
        if building.id != unit.building_id:
            raise ValidationError("واحد متعلق به این ساختمان نیست.")
        if not can_access_unit(self.request.user, unit) and not is_manager_of(
            self.request.user, building.id
        ):
            raise PermissionDenied("دسترسی غیرمجاز.")
        image = self.request.FILES.get("image")
        if image:
            validate_upload(image)
            image.name = safe_upload_name(image.name)
        req = serializer.save(
            created_by=self.request.user,
            building=building,
            image=image if image else serializer.validated_data.get("image"),
        )
        audit(
            self.request,
            action="maintenance.create",
            entity_type="MaintenanceRequest",
            entity_id=req.id,
            building=building,
            changes={"tracking_code": req.tracking_code},
        )
        from buildings.models import Membership

        for m in Membership.objects.filter(
            building=building,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
        ):
            notify_user(
                user=m.user,
                title="درخواست تعمیر جدید",
                body=f"{req.title} ({req.tracking_code})",
                type=Notification.Type.MAINTENANCE,
                building=building,
                link=f"/maintenance/{req.id}",
            )

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        req = self.get_object()
        if not is_manager_of(request.user, req.building_id):
            raise PermissionDenied("فقط مدیر می‌تواند وضعیت را تغییر دهد.")
        if not is_platform_super_admin(request.user):
            assert_building_write_allowed(req.building)
        serializer = MaintenanceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        new_status = data["status"]
        if new_status == MaintenanceRequest.Status.REJECTED and not data.get("rejection_reason"):
            raise ValidationError({"rejection_reason": "دلیل رد الزامی است."})
        req.status = new_status
        if "resolution_notes" in data:
            req.resolution_notes = data["resolution_notes"]
        if "rejection_reason" in data:
            req.rejection_reason = data["rejection_reason"]
        if "action_taken" in data:
            req.action_taken = data["action_taken"]
        req.save()
        audit(
            request,
            action="maintenance.status",
            entity_type="MaintenanceRequest",
            entity_id=req.id,
            building=req.building,
            changes={"status": new_status},
        )
        notify_user(
            user=req.created_by,
            title="وضعیت درخواست تغییر کرد",
            body=f"{req.tracking_code}: {req.get_status_display()}",
            type=Notification.Type.MAINTENANCE,
            building=req.building,
            link=f"/maintenance/{req.id}",
        )
        return Response(MaintenanceRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def add_message(self, request, pk=None):
        req = self.get_object()
        if not (
            is_manager_of(request.user, req.building_id)
            or req.unit_id in user_unit_ids(request.user)
            or req.created_by_id == request.user.id
        ):
            raise PermissionDenied("دسترسی غیرمجاز.")
        body = request.data.get("body", "").strip()
        if not body:
            raise ValidationError({"body": "متن پیام الزامی است."})
        is_internal = bool(request.data.get("is_internal")) and is_manager_of(
            request.user, req.building_id
        )
        msg = RequestMessage.objects.create(
            request=req,
            sender=request.user,
            body=body,
            is_internal=is_internal,
        )
        if not is_internal:
            target = req.created_by if request.user != req.created_by else None
            if is_manager_of(request.user, req.building_id):
                notify_user(
                    user=req.created_by,
                    title="پیام جدید در درخواست",
                    body=body[:120],
                    type=Notification.Type.MESSAGE,
                    building=req.building,
                    link=f"/maintenance/{req.id}",
                )
            else:
                from buildings.models import Membership

                for m in Membership.objects.filter(
                    building=req.building,
                    role=Membership.Role.MANAGER,
                    status=Membership.Status.ACTIVE,
                ):
                    notify_user(
                        user=m.user,
                        title="پیام ساکن در درخواست",
                        body=body[:120],
                        type=Notification.Type.MESSAGE,
                        building=req.building,
                        link=f"/maintenance/{req.id}",
                    )
        return Response(RequestMessageSerializer(msg).data, status=status.HTTP_201_CREATED)