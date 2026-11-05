from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from communications.models import Announcement, Notification
from communications.serializers import AnnouncementSerializer, NotificationSerializer
from core.permissions import is_manager_of, managed_building_ids, resident_building_ids
from core.utils import audit, notify_building_members


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    filterset_fields = ["building", "is_published"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "published_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.select_related("building", "created_by")
        if user.is_superuser:
            return qs
        ids = managed_building_ids(user) | resident_building_ids(user)
        manager_ids = managed_building_ids(user)
        return qs.filter(building_id__in=ids).filter(
            Q(building_id__in=manager_ids) | Q(is_published=True)
        ).distinct()

    def perform_create(self, serializer):
        building = serializer.validated_data["building"]
        if not is_manager_of(self.request.user, building.id):
            raise PermissionDenied("فقط مدیر می‌تواند اطلاعیه منتشر کند.")
        ann = serializer.save(
            created_by=self.request.user,
            published_at=timezone.now() if serializer.validated_data.get("is_published", True) else None,
        )
        audit(
            self.request,
            action="announcement.publish",
            entity_type="Announcement",
            entity_id=ann.id,
            building=building,
            changes={"title": ann.title},
        )
        if ann.is_published:
            notify_building_members(
                building=building,
                title="اطلاعیه جدید",
                body=ann.title,
                type=Notification.Type.ANNOUNCEMENT,
                link="/announcements",
                exclude_user=self.request.user,
            )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["is_read", "type", "building"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = timezone.now()
            notif.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"updated": updated})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"count": count})