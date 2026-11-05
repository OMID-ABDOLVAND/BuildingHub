from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import (
    AuditLogView,
    ManagerDashboardView,
    ProtectedMediaView,
    ReportsView,
    ResidentDashboardView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("buildings.urls")),
    path("api/v1/", include("finance.urls")),
    path("api/v1/", include("maintenance.urls")),
    path("api/v1/", include("communications.urls")),
    path("api/v1/dashboard/manager/", ManagerDashboardView.as_view()),
    path("api/v1/dashboard/resident/", ResidentDashboardView.as_view()),
    path("api/v1/reports/", ReportsView.as_view()),
    path("api/v1/audit-logs/", AuditLogView.as_view()),
    path("api/v1/media/<str:kind>/<int:pk>/", ProtectedMediaView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
]