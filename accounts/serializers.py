from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from buildings.models import Membership
from core.permissions import managed_building_ids, resident_building_ids

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    managed_buildings = serializers.SerializerMethodField()
    member_buildings = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "national_id",
            "managed_buildings",
            "member_buildings",
            "roles",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_managed_buildings(self, obj):
        return list(managed_building_ids(obj))

    def get_member_buildings(self, obj):
        return list(resident_building_ids(obj))

    def get_roles(self, obj):
        roles = set(
            Membership.objects.filter(user=obj, status=Membership.Status.ACTIVE).values_list(
                "role", flat=True
            )
        )
        if obj.is_superuser:
            roles.add("manager")
        return sorted(roles)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "رمز عبور و تکرار آن یکسان نیستند."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "national_id"]