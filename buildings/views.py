from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from buildings.models import Building, Membership, Unit, UnitOccupancy
from buildings.serializers import (
    BuildingSerializer,
    MembershipSerializer,
    ResidentCreateSerializer,
    UnitOccupancySerializer,
    UnitSerializer,
)
from core.permissions import (
    IsBuildingManager,
    can_access_unit,
    is_manager_of,
    is_member_of,
    managed_building_ids,
    resident_building_ids,
)
from core.utils import audit

User = get_user_model()


class BuildingViewSet(viewsets.ModelViewSet):
    serializer_class = BuildingSerializer
    search_fields = ["name", "address"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Building.objects.all()
        ids = managed_building_ids(user) | resident_building_ids(user)
        return Building.objects.filter(id__in=ids)

    def perform_create(self, serializer):
        building = serializer.save(manager=self.request.user)
        Membership.objects.get_or_create(
            user=self.request.user,
            building=building,
            defaults={"role": Membership.Role.MANAGER, "status": Membership.Status.ACTIVE},
        )
        audit(
            self.request,
            action="building.create",
            entity_type="Building",
            entity_id=building.id,
            building=building,
            changes={"name": building.name},
        )

    def perform_update(self, serializer):
        building = self.get_object()
        if not is_manager_of(self.request.user, building.id):
            raise PermissionDenied("فقط مدیر ساختمان می‌تواند ویرایش کند.")
        building = serializer.save()
        audit(
            self.request,
            action="building.update",
            entity_type="Building",
            entity_id=building.id,
            building=building,
        )


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    search_fields = ["number", "description"]
    filterset_fields = ["building", "floor", "is_active"]
    ordering_fields = ["floor", "number", "area_sqm"]

    def get_queryset(self):
        user = self.request.user
        qs = Unit.objects.select_related("building")
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        from core.permissions import user_unit_ids

        return qs.filter(
            Q(building_id__in=manager_ids) | Q(id__in=user_unit_ids(user))
        ).distinct()

    def perform_create(self, serializer):
        building = serializer.validated_data["building"]
        if not is_manager_of(self.request.user, building.id):
            raise PermissionDenied("فقط مدیر می‌تواند واحد ایجاد کند.")
        unit = serializer.save()
        audit(
            self.request,
            action="unit.create",
            entity_type="Unit",
            entity_id=unit.id,
            building=building,
            changes={"number": unit.number},
        )

    def perform_update(self, serializer):
        unit = self.get_object()
        if not is_manager_of(self.request.user, unit.building_id):
            raise PermissionDenied("فقط مدیر می‌تواند واحد را ویرایش کند.")
        # Note: changing resident_count/area does NOT alter finalized allocations
        unit = serializer.save()
        audit(
            self.request,
            action="unit.update",
            entity_type="Unit",
            entity_id=unit.id,
            building=unit.building,
        )


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    filterset_fields = ["building", "role", "status", "user"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]

    def get_queryset(self):
        user = self.request.user
        qs = Membership.objects.select_related("user", "building")
        if user.is_superuser:
            return qs
        return qs.filter(building_id__in=managed_building_ids(user) | resident_building_ids(user))

    def perform_create(self, serializer):
        building = serializer.validated_data["building"]
        if not is_manager_of(self.request.user, building.id):
            raise PermissionDenied("فقط مدیر می‌تواند عضویت ایجاد کند.")
        membership = serializer.save()
        audit(
            self.request,
            action="membership.create",
            entity_type="Membership",
            entity_id=membership.id,
            building=building,
        )


class UnitOccupancyViewSet(viewsets.ModelViewSet):
    serializer_class = UnitOccupancySerializer
    filterset_fields = ["unit", "user", "is_current", "relationship_type"]

    def get_queryset(self):
        user = self.request.user
        qs = UnitOccupancy.objects.select_related("unit", "user", "unit__building")
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        return qs.filter(Q(unit__building_id__in=manager_ids) | Q(user=user)).distinct()

    def perform_create(self, serializer):
        unit = serializer.validated_data["unit"]
        if not is_manager_of(self.request.user, unit.building_id):
            raise PermissionDenied("فقط مدیر می‌تواند سکونت ثبت کند.")
        occupancy = serializer.save()
        Membership.objects.get_or_create(
            user=occupancy.user,
            building=unit.building,
            defaults={"role": Membership.Role.RESIDENT, "status": Membership.Status.ACTIVE},
        )
        audit(
            self.request,
            action="occupancy.create",
            entity_type="UnitOccupancy",
            entity_id=occupancy.id,
            building=unit.building,
        )

    @action(detail=False, methods=["post"], url_path="create-resident")
    @transaction.atomic
    def create_resident(self, request):
        serializer = ResidentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            unit = Unit.objects.select_related("building").get(id=data["unit_id"])
        except Unit.DoesNotExist:
            raise ValidationError({"unit_id": "واحد یافت نشد."})
        if not is_manager_of(request.user, unit.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")

        if User.objects.filter(username=data["username"]).exists():
            raise ValidationError({"username": "نام کاربری تکراری است."})

        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
        )
        Membership.objects.create(
            user=user,
            building=unit.building,
            role=Membership.Role.RESIDENT,
            status=Membership.Status.ACTIVE,
        )
        occupancy = UnitOccupancy.objects.create(
            unit=unit,
            user=user,
            relationship_type=data["relationship_type"],
            start_date=data["start_date"],
            occupants_count=data["occupants_count"],
            is_current=True,
        )
        unit.resident_count = data["occupants_count"]
        unit.save(update_fields=["resident_count", "updated_at"])
        audit(
            request,
            action="resident.create",
            entity_type="User",
            entity_id=user.id,
            building=unit.building,
            changes={"unit": unit.id, "username": user.username},
        )
        return Response(
            {
                "user": {"id": user.id, "username": user.username},
                "occupancy": UnitOccupancySerializer(occupancy).data,
            },
            status=status.HTTP_201_CREATED,
        )