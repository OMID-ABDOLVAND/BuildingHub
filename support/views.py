from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from communications.models import Notification
from core.permissions import (
    is_manager_of,
    is_platform_super_admin,
    is_support_operator,
    managed_building_ids,
)
from core.utils import audit, notify_user, safe_upload_name, validate_upload
from support.models import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketMessage,
    SupportTicketStatusHistory,
)
from support.serializers import (
    SupportMessageCreateSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
    SupportTicketUpdateSerializer,
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["ticket_number", "subject", "description"]
    filterset_fields = ["status", "category", "priority", "building"]
    ordering_fields = ["created_at", "priority", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = SupportTicket.objects.select_related(
            "building", "created_by", "assigned_to"
        ).prefetch_related("messages", "attachments", "status_history")
        if is_support_operator(user) or is_platform_super_admin(user):
            return qs
        return qs.filter(created_by=user) | qs.filter(building_id__in=managed_building_ids(user))

    def get_serializer_class(self):
        if self.action == "create":
            return SupportTicketCreateSerializer
        if self.action in ("update", "partial_update"):
            return SupportTicketUpdateSerializer
        return SupportTicketSerializer

    def perform_create(self, serializer):
        building = serializer.validated_data.get("building")
        if building and not is_manager_of(self.request.user, building.id):
            if not is_platform_super_admin(self.request.user):
                raise PermissionDenied("فقط مدیر ساختمان می‌تواند تیکت مرتبط ایجاد کند.")
        ticket = serializer.save(created_by=self.request.user)
        SupportTicketStatusHistory.objects.create(
            ticket=ticket,
            from_status="",
            to_status=ticket.status,
            changed_by=self.request.user,
            note="ایجاد تیکت",
        )
        SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=self.request.user,
            body=ticket.description,
            is_internal=False,
        )
        attachment = self.request.FILES.get("attachment") or self.request.FILES.get("file")
        if attachment:
            validate_upload(attachment)
            att = SupportTicketAttachment(
                ticket=ticket,
                uploaded_by=self.request.user,
                original_name=attachment.name,
            )
            att.file.save(safe_upload_name(attachment.name), attachment, save=True)
        audit(
            self.request,
            action="support.create",
            entity_type="SupportTicket",
            entity_id=ticket.id,
            building=building,
            changes={"ticket_number": ticket.ticket_number},
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        ticket = serializer.instance
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if not (is_support_operator(self.request.user) or is_platform_super_admin(self.request.user)):
            raise PermissionDenied("فقط پشتیبانی می‌تواند وضعیت را تغییر دهد.")
        ticket = self.get_object()
        old_status = ticket.status
        ticket = serializer.save()
        if "status" in serializer.validated_data and serializer.validated_data["status"] != old_status:
            SupportTicketStatusHistory.objects.create(
                ticket=ticket,
                from_status=old_status,
                to_status=ticket.status,
                changed_by=self.request.user,
            )
            if ticket.status == SupportTicket.Status.CLOSED:
                ticket.closed_at = timezone.now()
                ticket.save(update_fields=["closed_at", "updated_at"])
            notify_user(
                user=ticket.created_by,
                title="به‌روزرسانی تیکت پشتیبانی",
                body=f"وضعیت تیکت {ticket.ticket_number} به {ticket.get_status_display()} تغییر کرد.",
                type=Notification.Type.SUPPORT,
                building=ticket.building,
                link=f"/app/support/{ticket.id}",
            )

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = SupportMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_staff = is_support_operator(request.user) or is_platform_super_admin(request.user)
        if not is_staff and ticket.created_by_id != request.user.id:
            if not (ticket.building_id and is_manager_of(request.user, ticket.building_id)):
                raise PermissionDenied("دسترسی غیرمجاز.")
        is_internal = bool(serializer.validated_data.get("is_internal")) and is_staff
        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=serializer.validated_data["body"],
            is_internal=is_internal,
        )
        attachment = request.FILES.get("attachment") or request.FILES.get("file")
        if attachment:
            validate_upload(attachment)
            att = SupportTicketAttachment(
                ticket=ticket,
                message=message,
                uploaded_by=request.user,
                original_name=attachment.name,
            )
            att.file.save(safe_upload_name(attachment.name), attachment, save=True)

        if is_staff and not is_internal:
            if ticket.status != SupportTicket.Status.ANSWERED:
                old = ticket.status
                ticket.status = SupportTicket.Status.ANSWERED
                ticket.save(update_fields=["status", "updated_at"])
                SupportTicketStatusHistory.objects.create(
                    ticket=ticket,
                    from_status=old,
                    to_status=ticket.status,
                    changed_by=request.user,
                    note="پاسخ پشتیبانی",
                )
            notify_user(
                user=ticket.created_by,
                title="پاسخ جدید به تیکت",
                body=f"پاسخ جدیدی برای تیکت {ticket.ticket_number} ثبت شد.",
                type=Notification.Type.SUPPORT,
                building=ticket.building,
                link=f"/app/support/{ticket.id}",
            )
        elif not is_staff:
            if ticket.status == SupportTicket.Status.ANSWERED:
                old = ticket.status
                ticket.status = SupportTicket.Status.WAITING_FOR_CUSTOMER
                # actually customer replied - set IN_PROGRESS or WAITING is wrong
                ticket.status = SupportTicket.Status.IN_PROGRESS
                ticket.save(update_fields=["status", "updated_at"])
                SupportTicketStatusHistory.objects.create(
                    ticket=ticket,
                    from_status=old,
                    to_status=ticket.status,
                    changed_by=request.user,
                    note="پاسخ مشتری",
                )

        ticket.refresh_from_db()
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        ticket = self.get_object()
        is_staff = is_support_operator(request.user) or is_platform_super_admin(request.user)
        is_owner = ticket.created_by_id == request.user.id or (
            ticket.building_id and is_manager_of(request.user, ticket.building_id)
        )
        if not (is_staff or is_owner):
            raise PermissionDenied("دسترسی غیرمجاز.")
        old = ticket.status
        ticket.status = SupportTicket.Status.CLOSED
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=["status", "closed_at", "updated_at"])
        SupportTicketStatusHistory.objects.create(
            ticket=ticket,
            from_status=old,
            to_status=ticket.status,
            changed_by=request.user,
            note="بستن تیکت",
        )
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status != SupportTicket.Status.CLOSED:
            raise ValidationError("فقط تیکت بسته‌شده قابل بازگشایی است.")
        is_staff = is_support_operator(request.user) or is_platform_super_admin(request.user)
        is_owner = ticket.created_by_id == request.user.id
        if not (is_staff or is_owner):
            raise PermissionDenied("دسترسی غیرمجاز.")
        old = ticket.status
        ticket.status = SupportTicket.Status.OPEN
        ticket.closed_at = None
        ticket.save(update_fields=["status", "closed_at", "updated_at"])
        SupportTicketStatusHistory.objects.create(
            ticket=ticket,
            from_status=old,
            to_status=ticket.status,
            changed_by=request.user,
            note="بازگشایی تیکت",
        )
        return Response(SupportTicketSerializer(ticket).data)
