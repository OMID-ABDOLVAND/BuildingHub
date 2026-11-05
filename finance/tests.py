from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from buildings.models import Building, Membership, Unit, UnitOccupancy
from finance.models import Expense, ExpenseAllocation, Payment
from finance.services import AllocationInput, compute_allocations

User = get_user_model()


class AllocationAlgorithmTests(TestCase):
    def test_equal_allocation_exact(self):
        items = [AllocationInput(i, 1, 100) for i in range(1, 11)]
        result = compute_allocations("equal", 12_000_000, items)
        self.assertEqual(sum(result.values()), 12_000_000)
        self.assertTrue(all(v == 1_200_000 for v in result.values()))

    def test_equal_rounding_remainder(self):
        items = [AllocationInput(i, 1, 100) for i in range(1, 4)]
        result = compute_allocations("equal", 100, items)
        self.assertEqual(sum(result.values()), 100)
        self.assertEqual(sorted(result.values()), [33, 33, 34])

    def test_resident_based(self):
        items = [
            AllocationInput(1, 3, 90),
            AllocationInput(2, 5, 110),
            AllocationInput(3, 2, 80),
        ]
        # total residents 10, amount 12_000_000 -> base 1_200_000 per person
        result = compute_allocations("resident", 12_000_000, items)
        self.assertEqual(sum(result.values()), 12_000_000)
        self.assertEqual(result[1], 3_600_000)
        self.assertEqual(result[2], 6_000_000)
        self.assertEqual(result[3], 2_400_000)

    def test_area_based(self):
        items = [
            AllocationInput(1, 1, 50),
            AllocationInput(2, 1, 50),
        ]
        result = compute_allocations("area", 1_000_000, items)
        self.assertEqual(sum(result.values()), 1_000_000)
        self.assertEqual(result[1], 500_000)
        self.assertEqual(result[2], 500_000)

    def test_custom_must_match_total(self):
        items = [
            AllocationInput(1, 1, 50, custom_amount=400_000),
            AllocationInput(2, 1, 50, custom_amount=600_000),
        ]
        result = compute_allocations("custom", 1_000_000, items)
        self.assertEqual(sum(result.values()), 1_000_000)
        with self.assertRaises(ValueError):
            compute_allocations(
                "custom",
                1_000_000,
                [
                    AllocationInput(1, 1, 50, custom_amount=100),
                    AllocationInput(2, 1, 50, custom_amount=100),
                ],
            )


class PaymentWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("mgr", password="pass12345", first_name="مدیر")
        self.resident = User.objects.create_user("res", password="pass12345", first_name="ساکن")
        self.other = User.objects.create_user("other", password="pass12345")
        self.building = Building.objects.create(name="B1", manager=self.manager, address="x")
        Membership.objects.create(
            user=self.manager, building=self.building, role=Membership.Role.MANAGER
        )
        Membership.objects.create(
            user=self.resident, building=self.building, role=Membership.Role.RESIDENT
        )
        Membership.objects.create(
            user=self.other, building=self.building, role=Membership.Role.RESIDENT
        )
        self.unit = Unit.objects.create(
            building=self.building, number="101", floor=1, area_sqm=100, resident_count=3
        )
        self.unit2 = Unit.objects.create(
            building=self.building, number="102", floor=1, area_sqm=100, resident_count=3
        )
        UnitOccupancy.objects.create(
            unit=self.unit,
            user=self.resident,
            relationship_type="tenant",
            start_date=timezone.localdate(),
            occupants_count=3,
        )
        UnitOccupancy.objects.create(
            unit=self.unit2,
            user=self.other,
            relationship_type="tenant",
            start_date=timezone.localdate(),
            occupants_count=3,
        )
        self.expense = Expense.objects.create(
            building=self.building,
            title="Test",
            amount=1_000_000,
            expense_date=timezone.localdate(),
            due_date=timezone.localdate() + timedelta(days=10),
            allocation_method=Expense.AllocationMethod.EQUAL,
            status=Expense.Status.FINALIZED,
            created_by=self.manager,
            finalized_by=self.manager,
            finalized_at=timezone.now(),
        )
        self.expense.included_units.set([self.unit, self.unit2])
        self.alloc = ExpenseAllocation.objects.create(
            expense=self.expense,
            unit=self.unit,
            amount=500_000,
            snapshot_resident_count=3,
            snapshot_area_sqm=100,
        )
        ExpenseAllocation.objects.create(
            expense=self.expense,
            unit=self.unit2,
            amount=500_000,
            snapshot_resident_count=3,
            snapshot_area_sqm=100,
        )

    def test_pending_payment_does_not_reduce_debt(self):
        payment = Payment.objects.create(
            allocation=self.alloc,
            amount=200_000,
            status=Payment.Status.PENDING,
            submitted_by=self.resident,
        )
        self.alloc.refresh_from_db()
        self.assertEqual(self.alloc.remaining, 500_000)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_approved_partial_payment(self):
        payment = Payment.objects.create(
            allocation=self.alloc,
            amount=200_000,
            status=Payment.Status.APPROVED,
            submitted_by=self.resident,
        )
        self.alloc.refresh_status()
        self.assertEqual(self.alloc.remaining, 300_000)
        self.assertEqual(self.alloc.status, ExpenseAllocation.Status.PARTIALLY_PAID)

    def test_reject_requires_reason_via_api(self):
        payment = Payment.objects.create(
            allocation=self.alloc,
            amount=100_000,
            status=Payment.Status.PENDING,
            submitted_by=self.resident,
        )
        self.client.force_authenticate(self.manager)
        res = self.client.post(
            f"/api/v1/payments/{payment.id}/review/",
            {"action": "reject"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_resident_cannot_access_other_allocation(self):
        other_alloc = ExpenseAllocation.objects.get(unit=self.unit2)
        self.client.force_authenticate(self.resident)
        res = self.client.get(f"/api/v1/allocations/{other_alloc.id}/")
        self.assertIn(res.status_code, (403, 404))

    def test_finalize_snapshot_stable(self):
        self.unit.resident_count = 99
        self.unit.save()
        self.alloc.refresh_from_db()
        self.assertEqual(self.alloc.snapshot_resident_count, 3)