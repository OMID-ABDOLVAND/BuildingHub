from rest_framework.permissions import BasePermission, SAFE_METHODS

from buildings.models import Membership, UnitOccupancy


def user_memberships(user):
    if not user or not user.is_authenticated:
        return Membership.objects.none()
    return Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)


def managed_building_ids(user):
    return set(
        user_memberships(user)
        .filter(role=Membership.Role.MANAGER)
        .values_list("building_id", flat=True)
    ) | set(user.managed_buildings.values_list("id", flat=True))


def resident_building_ids(user):
    return set(user_memberships(user).values_list("building_id", flat=True))


def user_unit_ids(user):
    return set(
        UnitOccupancy.objects.filter(user=user, is_current=True).values_list("unit_id", flat=True)
    )


def is_manager_of(user, building_id: int) -> bool:
    return building_id in managed_building_ids(user) or user.is_superuser


def is_member_of(user, building_id: int) -> bool:
    return building_id in resident_building_ids(user) or is_manager_of(user, building_id)


def can_access_unit(user, unit) -> bool:
    if user.is_superuser or is_manager_of(user, unit.building_id):
        return True
    return unit.id in user_unit_ids(user)


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsBuildingManager(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return bool(managed_building_ids(request.user))

    def has_object_permission(self, request, view, obj):
        building_id = getattr(obj, "building_id", None)
        if building_id is None and hasattr(obj, "building"):
            building_id = obj.building.id
        if building_id is None and obj.__class__.__name__ == "Building":
            building_id = obj.id
        return is_manager_of(request.user, building_id)


class IsBuildingMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        building_id = getattr(obj, "building_id", None)
        if building_id is None and hasattr(obj, "building"):
            building_id = obj.building.id
        if building_id is None and obj.__class__.__name__ == "Building":
            building_id = obj.id
        return is_member_of(request.user, building_id)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS