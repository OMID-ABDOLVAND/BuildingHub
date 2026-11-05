from rest_framework import serializers

from maintenance.models import MaintenanceRequest, RequestMessage


class RequestMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)

    class Meta:
        model = RequestMessage
        fields = [
            "id",
            "request",
            "sender",
            "sender_name",
            "body",
            "is_internal",
            "created_at",
        ]
        read_only_fields = ["sender", "created_at"]


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    unit_number = serializers.CharField(source="unit.number", read_only=True)
    messages = RequestMessageSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            "id",
            "building",
            "unit",
            "unit_number",
            "created_by",
            "created_by_name",
            "title",
            "category",
            "description",
            "priority",
            "status",
            "tracking_code",
            "image",
            "resolution_notes",
            "rejection_reason",
            "action_taken",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "tracking_code",
            "status",
            "resolution_notes",
            "rejection_reason",
            "action_taken",
            "created_at",
            "updated_at",
        ]


class MaintenanceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=MaintenanceRequest.Status.choices)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    action_taken = serializers.CharField(required=False, allow_blank=True)