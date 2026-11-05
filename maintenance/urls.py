from rest_framework.routers import DefaultRouter

from maintenance.views import MaintenanceRequestViewSet

router = DefaultRouter()
router.register("maintenance", MaintenanceRequestViewSet, basename="maintenance")

urlpatterns = router.urls