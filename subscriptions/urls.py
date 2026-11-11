from django.urls import include, path
from rest_framework.routers import DefaultRouter

from subscriptions.views import (
    AdminBuildingViewSet,
    AdminDashboardStatsView,
    AdminManagerListView,
    AdminResidentListView,
    AdminSubscriptionPaymentViewSet,
    AdminSubscriptionViewSet,
    BuildingGateStatusView,
    ManagerRegisterView,
    MySubscriptionsView,
    OnboardingBuildingView,
    PlatformSettingsView,
    PublicPaymentSettingsView,
    PublicPlanListView,
    SelectSubscriptionPlanView,
    SubmitSubscriptionPaymentView,
    SubscriptionPlanViewSet,
)

router = DefaultRouter()
router.register("plans", SubscriptionPlanViewSet, basename="subscription-plan")
router.register(
    "admin/subscription-payments",
    AdminSubscriptionPaymentViewSet,
    basename="admin-subscription-payment",
)
router.register("admin/subscriptions", AdminSubscriptionViewSet, basename="admin-subscription")
router.register("admin/buildings", AdminBuildingViewSet, basename="admin-building")

urlpatterns = [
    path("subscriptions/plans/public/", PublicPlanListView.as_view()),
    path("subscriptions/payment-settings/public/", PublicPaymentSettingsView.as_view()),
    path("auth/register-manager/", ManagerRegisterView.as_view()),
    path("onboarding/building/", OnboardingBuildingView.as_view()),
    path("onboarding/select-plan/", SelectSubscriptionPlanView.as_view()),
    path("onboarding/submit-payment/", SubmitSubscriptionPaymentView.as_view()),
    path("subscriptions/mine/", MySubscriptionsView.as_view()),
    path("subscriptions/gate/", BuildingGateStatusView.as_view()),
    path("platform/settings/", PlatformSettingsView.as_view()),
    path("admin/dashboard/stats/", AdminDashboardStatsView.as_view()),
    path("admin/managers/", AdminManagerListView.as_view()),
    path("admin/residents/", AdminResidentListView.as_view()),
    path("", include(router.urls)),
]
