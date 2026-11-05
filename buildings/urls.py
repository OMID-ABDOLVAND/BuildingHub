from rest_framework.routers import DefaultRouter

from buildings.views import BuildingViewSet, MembershipViewSet, UnitOccupancyViewSet, UnitViewSet

router = DefaultRouter()
router.register("buildings", BuildingViewSet, basename="building")
router.register("units", UnitViewSet, basename="unit")
router.register("memberships", MembershipViewSet, basename="membership")
router.register("occupancies", UnitOccupancyViewSet, basename="occupancy")

urlpatterns = router.urls