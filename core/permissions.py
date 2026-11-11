from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

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


def is_platform_super_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, "is_platform_super_admin", False) or user.is_superuser)


def is_support_operator(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, "is_support_operator", False) or is_platform_super_admin(user))


def is_manager_of(user, building_id: int) -> bool:
    return building_id in managed_building_ids(user) or is_platform_super_admin(user)


def is_member_of(user, building_id: int) -> bool:
    return building_id in resident_building_ids(user) or is_manager_of(user, building_id)


def can_access_unit(user, unit) -> bool:
    if is_platform_super_admin(user) or is_manager_of(user, unit.building_id):
        return True
    return unit.id in user_unit_ids(user)


def get_building_subscription(building):
    if building is None:
        return None
    return building.current_subscription()


def building_management_allowed(building) -> bool:
    """Full write access for building management operations."""
    if building is None:
        return False
    from buildings.models import Building
    from subscriptions.models import Subscription

    if building.status != Building.Status.ACTIVE:
        return False
    sub = get_building_subscription(building)
    if sub is None:
        return False
    return sub.status == Subscription.Status.ACTIVE


def building_read_allowed(building) -> bool:
    """Read historical data while ACTIVE / GRACE / EXPIRED (building not rejected)."""
    if building is None:
        return False
    from buildings.models import Building
    from subscriptions.models import Subscription

    if building.status == Building.Status.REJECTED:
        return False
    if building.status == Building.Status.PENDING:
        return True  # manager can see own pending building
    sub = get_building_subscription(building)
    if sub is None:
        return building.status == Building.Status.ACTIVE
    return sub.status in {
        Subscription.Status.ACTIVE,
        Subscription.Status.GRACE_PERIOD,
        Subscription.Status.EXPIRED,
        Subscription.Status.PENDING_PAYMENT,
        Subscription.Status.PENDING_APPROVAL,
        Subscription.Status.SUSPENDED,
    }


def building_renewal_allowed(building) -> bool:
    from subscriptions.models import Subscription

    sub = get_building_subscription(building)
    if sub is None:
        return True
    return sub.status in {
        Subscription.Status.ACTIVE,
        Subscription.Status.GRACE_PERIOD,
        Subscription.Status.EXPIRED,
        Subscription.Status.PENDING_PAYMENT,
        Subscription.Status.REJECTED,
        Subscription.Status.SUSPENDED,
    }


def assert_building_write_allowed(building):
    if not building_management_allowed(building):
        raise PermissionDenied(
            "عملیات مدیریتی ساختمان فقط با اشتراک فعال مجاز است. "
            "در دوره ارفاق یا پس از انقضا فقط مشاهده و تمدید امکان‌پذیر است."
        )


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_platform_super_admin(request.user)


class IsSupportOperator(BasePermission):
    def has_permission(self, request, view):
        return is_support_operator(request.user)


class IsBuildingManager(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if is_platform_super_admin(request.user):
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


class BuildingWriteGate(BasePermission):
    """Block mutating building-management ops unless subscription is ACTIVE."""

    message = "اشتراک فعال برای این عملیات لازم است."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if is_platform_super_admin(request.user):
            return True
        return True  # object-level / view-level checks apply

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if is_platform_super_admin(request.user):
            return True
        building = obj if obj.__class__.__name__ == "Building" else getattr(obj, "building", None)
        if building is None and hasattr(obj, "unit"):
            building = obj.unit.building
        return building_management_allowed(building)
