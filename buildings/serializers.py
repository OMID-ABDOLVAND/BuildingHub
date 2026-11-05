from django.contrib.auth import get_user_model
from rest_framework import serializers

from buildings.models import Building, Membership, Unit, UnitOccupancy

User = get_user_model()


class BuildingSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source="manager.get_full_name", read_only=True)
    units_count = serializers.IntegerField(source="units.count", read_only=True)

    class Meta:
        model = Building
        fields = [
            "id",
            "name",
            "address",
            "description",
            "manager",
            "manager_name",
            "contact_phone",
            "contact_email",
            "is_active",
            "units_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["manager", "created_at", "updated_at"]


class UnitSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source="building.name", read_only=True)

    class Meta:
        model = Unit
        fields = [
            "id",
            "building",
            "building_name",
            "number",
            "floor",
            "area_sqm",
            "resident_count",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class MembershipSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    building_name = serializers.CharField(source="building.name", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "user_detail",
            "building",
            "building_name",
            "role",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_user_detail(self, obj):
        return {
            "id": obj.user_id,
            "username": obj.user.username,
            "full_name": obj.user.get_full_name() or obj.user.username,
            "email": obj.user.email,
            "phone": obj.user.phone,
        }


class UnitOccupancySerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    unit_number = serializers.CharField(source="unit.number", read_only=True)

    class Meta:
        model = UnitOccupancy
        fields = [
            "id",
            "unit",
            "unit_number",
            "user",
            "user_detail",
            "relationship_type",
            "start_date",
            "end_date",
            "occupants_count",
            "is_current",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_user_detail(self, obj):
        return {
            "id": obj.user_id,
            "username": obj.user.username,
            "full_name": obj.user.get_full_name() or obj.user.username,
        }


class ResidentCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    unit_id = serializers.IntegerField()
    relationship_type = serializers.ChoiceField(
        choices=UnitOccupancy.Relationship.choices,
        default=UnitOccupancy.Relationship.TENANT,
    )
    occupants_count = serializers.IntegerField(min_value=1, default=1)
    start_date = serializers.DateField()