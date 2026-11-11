from django.contrib import admin

from buildings.models import Building, Membership, ResidentInvitation, Unit, UnitOccupancy


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "status", "is_active", "created_at")
    list_filter = ("status", "is_active")
    search_fields = ("name", "address")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("number", "building", "floor", "area_sqm", "resident_count", "is_active")
    list_filter = ("building", "floor")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "building", "role", "status")
    list_filter = ("role", "status", "building")


@admin.register(UnitOccupancy)
class UnitOccupancyAdmin(admin.ModelAdmin):
    list_display = ("user", "unit", "relationship_type", "is_current", "start_date")
    list_filter = ("relationship_type", "is_current")
@admin.register(ResidentInvitation)
class ResidentInvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "building", "unit", "phone", "email", "status", "expires_at")
    list_filter = ("status", "building")
