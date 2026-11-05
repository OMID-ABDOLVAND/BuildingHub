from django.contrib import admin

from buildings.models import Building, Membership, Unit, UnitOccupancy


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "is_active", "created_at")
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