from rest_framework import serializers

from communications.models import Announcement, Notification


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "building",
            "title",
            "body",
            "created_by",
            "created_by_name",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "published_at", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "building",
            "type",
            "title",
            "body",
            "link",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields