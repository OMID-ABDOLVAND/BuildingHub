from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from buildings.models import Membership, ResidentInvitation, Unit, UnitOccupancy
from communications.models import Notification
from core.permissions import assert_building_write_allowed, is_manager_of, managed_building_ids
from core.utils import audit, notify_user
from rest_framework import serializers

User = get_user_model()


class ResidentInvitationSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.number", read_only=True)
    building_name = serializers.CharField(source="building.name", read_only=True)
    invite_url = serializers.SerializerMethodField()
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ResidentInvitation
        fields = [
            "id",
            "building",
            "building_name",
            "unit",
            "unit_number",
            "invited_by",
            "invited_by_name",
            "first_name",
            "last_name",
            "phone",
            "email",
            "relationship_type",
            "start_date",
            "occupants_count",
            "token",
            "status",
            "expires_at",
            "accepted_at",
            "invite_url",
            "created_at",
        ]
        read_only_fields = [
            "invited_by",
            "token",
            "status",
            "expires_at",
            "accepted_at",
            "created_at",
        ]

    def get_invite_url(self, obj):
        request = self.context.get("request")
        path = f"/invite/{obj.token}"
        if request:
            return request.build_absolute_uri(path).replace("/api/v1", "")
        return path

    def get_invited_by_name(self, obj):
        return obj.invited_by.get_full_name() or obj.invited_by.username


class ResidentInvitationCreateSerializer(serializers.Serializer):
    building_id = serializers.IntegerField()
    unit_id = serializers.IntegerField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    relationship_type = serializers.ChoiceField(
        choices=UnitOccupancy.Relationship.choices,
        default=UnitOccupancy.Relationship.TENANT,
    )
    start_date = serializers.DateField()
    occupants_count = serializers.IntegerField(min_value=1, default=1)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=60, default=7)

    def validate(self, attrs):
        if not attrs.get("phone") and not attrs.get("email"):
            raise serializers.ValidationError("حداقل یکی از موبایل یا ایمیل الزامی است.")
        return attrs


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "رمز عبور و تکرار آن یکسان نیستند."})
        validate_password(attrs["password"])
        return attrs


class ResidentInvitationViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ResidentInvitationSerializer
    filterset_fields = ["building", "status", "unit"]
    search_fields = ["first_name", "last_name", "phone", "email"]

    def get_queryset(self):
        user = self.request.user
        qs = ResidentInvitation.objects.select_related("building", "unit", "invited_by")
        if user.is_superuser or getattr(user, "is_platform_super_admin", False):
            return qs
        return qs.filter(building_id__in=managed_building_ids(user))

    def create(self, request, *args, **kwargs):
        serializer = ResidentInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            unit = Unit.objects.select_related("building").get(pk=data["unit_id"])
        except Unit.DoesNotExist:
            raise ValidationError({"unit_id": "واحد یافت نشد."})
        if unit.building_id != data["building_id"]:
            raise ValidationError({"unit_id": "واحد متعلق به این ساختمان نیست."})
        if not is_manager_of(request.user, unit.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        assert_building_write_allowed(unit.building)

        invitation = ResidentInvitation.objects.create(
            building=unit.building,
            unit=unit,
            invited_by=request.user,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            relationship_type=data["relationship_type"],
            start_date=data["start_date"],
            occupants_count=data["occupants_count"],
            expires_at=timezone.now() + timedelta(days=data["expires_in_days"]),
        )
        audit(
            request,
            action="invitation.create",
            entity_type="ResidentInvitation",
            entity_id=invitation.id,
            building=unit.building,
            changes={"unit": unit.id, "phone": invitation.phone},
        )
        return Response(
            ResidentInvitationSerializer(invitation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        invitation = self.get_object()
        if not is_manager_of(request.user, invitation.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if invitation.status != ResidentInvitation.Status.PENDING:
            raise ValidationError("فقط دعوت در انتظار قابل ابطال است.")
        invitation.status = ResidentInvitation.Status.REVOKED
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["status", "revoked_at", "updated_at"])
        return Response(
            ResidentInvitationSerializer(invitation, context={"request": request}).data
        )


class InvitationPublicView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            invitation = ResidentInvitation.objects.select_related("building", "unit").get(token=token)
        except ResidentInvitation.DoesNotExist:
            raise ValidationError({"token": "دعوت‌نامه یافت نشد."})
        invitation.mark_expired_if_needed()
        invitation.refresh_from_db()
        return Response(
            {
                "valid": invitation.is_usable(),
                "status": invitation.status,
                "building_name": invitation.building.name,
                "unit_number": invitation.unit.number,
                "first_name": invitation.first_name,
                "last_name": invitation.last_name,
                "phone": invitation.phone,
                "email": invitation.email,
                "relationship_type": invitation.relationship_type,
                "expires_at": invitation.expires_at,
            }
        )


class AcceptInvitationView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            invitation = (
                ResidentInvitation.objects.select_for_update()
                .select_related("building", "unit")
                .get(token=data["token"])
            )
        except ResidentInvitation.DoesNotExist:
            raise ValidationError({"token": "دعوت‌نامه یافت نشد."})

        invitation.mark_expired_if_needed()
        invitation.refresh_from_db()
        if invitation.status == ResidentInvitation.Status.ACCEPTED:
            raise ValidationError("این دعوت‌نامه قبلاً استفاده شده است.")
        if invitation.status == ResidentInvitation.Status.REVOKED:
            raise ValidationError("این دعوت‌نامه باطل شده است.")
        if invitation.status == ResidentInvitation.Status.EXPIRED or not invitation.is_usable():
            raise ValidationError("این دعوت‌نامه منقضی شده است.")

        username = (data.get("username") or invitation.phone or invitation.email or "").strip()
        if not username:
            raise ValidationError({"username": "نام کاربری الزامی است."})
        if User.objects.filter(username=username).exists():
            raise ValidationError({"username": "نام کاربری تکراری است."})

        user = User.objects.create_user(
            username=username,
            password=data["password"],
            first_name=data.get("first_name") or invitation.first_name,
            last_name=data.get("last_name") or invitation.last_name,
            email=invitation.email,
            phone=invitation.phone,
        )
        Membership.objects.get_or_create(
            user=user,
            building=invitation.building,
            defaults={"role": Membership.Role.RESIDENT, "status": Membership.Status.ACTIVE},
        )
        UnitOccupancy.objects.create(
            unit=invitation.unit,
            user=user,
            relationship_type=invitation.relationship_type,
            start_date=invitation.start_date,
            occupants_count=invitation.occupants_count,
            is_current=True,
        )
        invitation.unit.resident_count = invitation.occupants_count
        invitation.unit.save(update_fields=["resident_count", "updated_at"])

        invitation.status = ResidentInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.accepted_user = user
        invitation.save(
            update_fields=["status", "accepted_at", "accepted_user", "updated_at"]
        )

        notify_user(
            user=invitation.invited_by,
            title="دعوت ساکن پذیرفته شد",
            body=f"{user.get_full_name() or user.username} دعوت واحد {invitation.unit.number} را پذیرفت.",
            type=Notification.Type.INVITATION,
            building=invitation.building,
            link="/app/invitations",
        )
        audit(
            request,
            action="invitation.accept",
            entity_type="ResidentInvitation",
            entity_id=invitation.id,
            building=invitation.building,
            changes={"user_id": user.id},
        )
        return Response(
            {
                "message": "ثبت‌نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.",
                "username": user.username,
                "building_id": invitation.building_id,
                "unit_id": invitation.unit_id,
            },
            status=status.HTTP_201_CREATED,
        )
