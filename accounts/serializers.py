from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from buildings.models import Membership
from core.permissions import is_platform_super_admin, managed_building_ids, resident_building_ids

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    managed_buildings = serializers.SerializerMethodField()
    member_buildings = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    platform_role = serializers.CharField(read_only=True)

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
            "platform_role",
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
        roles = set()
        if is_platform_super_admin(obj):
            roles.add("super_admin")
        membership_roles = set(
            Membership.objects.filter(user=obj, status=Membership.Status.ACTIVE).values_list(
                "role", flat=True
            )
        )
        if Membership.Role.MANAGER in membership_roles or obj.managed_buildings.exists():
            roles.add("building_manager")
            roles.add("manager")  # backward compatible
        if Membership.Role.RESIDENT in membership_roles:
            roles.add("resident")
        if obj.is_superuser and "building_manager" not in roles and "resident" not in roles:
            roles.add("building_manager")
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


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "رمز عبور و تکرار آن یکسان نیستند."}
            )
        validate_password(attrs["new_password"])
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("ایمیل یا موبایل الزامی است.")
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "رمز عبور و تکرار آن یکسان نیستند."}
            )
        validate_password(attrs["new_password"])
        return attrs
