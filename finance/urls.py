from rest_framework.routers import DefaultRouter

from finance.views import ExpenseAllocationViewSet, ExpenseViewSet, PaymentViewSet

router = DefaultRouter()
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("allocations", ExpenseAllocationViewSet, basename="allocation")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = router.urls