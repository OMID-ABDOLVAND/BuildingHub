from django.urls import path
from rest_framework.routers import DefaultRouter

from buildings.invitations import AcceptInvitationView, InvitationPublicView, ResidentInvitationViewSet
from buildings.views import BuildingViewSet, MembershipViewSet, UnitOccupancyViewSet, UnitViewSet

router = DefaultRouter()
router.register("buildings", BuildingViewSet, basename="building")
router.register("units", UnitViewSet, basename="unit")
router.register("memberships", MembershipViewSet, basename="membership")
router.register("occupancies", UnitOccupancyViewSet, basename="occupancy")
router.register("invitations", ResidentInvitationViewSet, basename="invitation")

urlpatterns = [
    path("invitations/public/<str:token>/", InvitationPublicView.as_view()),
    path("invitations/accept/", AcceptInvitationView.as_view()),
] + router.urls
