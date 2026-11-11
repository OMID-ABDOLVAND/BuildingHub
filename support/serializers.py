from rest_framework import serializers

from support.models import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketMessage,
    SupportTicketStatusHistory,
)


class SupportTicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicketAttachment
        fields = ["id", "file", "original_name", "message", "created_at"]
        read_only_fields = fields


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    attachments = SupportTicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicketMessage
        fields = [
            "id",
            "body",
            "is_internal",
            "sender",
            "sender_name",
            "attachments",
            "created_at",
        ]
        read_only_fields = ["sender", "created_at"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class SupportTicketStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by",
            "changed_by_name",
            "note",
            "created_at",
        ]

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None
        return obj.changed_by.get_full_name() or obj.changed_by.username


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportTicketMessageSerializer(many=True, read_only=True)
    status_history = SupportTicketStatusHistorySerializer(many=True, read_only=True)
    attachments = SupportTicketAttachmentSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    building_name = serializers.CharField(source="building.name", read_only=True, default=None)
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "building",
            "building_name",
            "created_by",
            "created_by_name",
            "assigned_to",
            "assigned_to_name",
            "subject",
            "category",
            "priority",
            "status",
            "description",
            "closed_at",
            "messages",
            "status_history",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "ticket_number",
            "created_by",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return None
        return obj.assigned_to.get_full_name() or obj.assigned_to.username


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["building", "subject", "category", "priority", "description"]


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["status", "priority", "assigned_to"]


class SupportMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    is_internal = serializers.BooleanField(required=False, default=False)
