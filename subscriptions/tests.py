from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from buildings.models import Building, Membership, ResidentInvitation, Unit
from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
    SubscriptionPlanPricing,
)
from subscriptions.services import (
    activate_subscription,
    create_subscription_for_building,
    process_subscription_lifecycle,
)
from support.models import SupportTicket

User = get_user_model()


def make_image(name="receipt.png"):
    buf = BytesIO()
    Image.new("RGB", (40, 40), color=(20, 180, 160)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def seed_plans():
    specs = [
        ("Basic", 1, 10, 500_000, 5_000_000, 1),
        ("Standard", 11, 30, 900_000, 9_000_000, 2),
        ("Professional", 31, 60, 1_500_000, 15_000_000, 3),
        ("Enterprise", 61, 100, 2_500_000, 25_000_000, 4),
        ("Custom", 101, 10000, 4_000_000, 40_000_000, 5),
    ]
    plans = []
    for name, mn, mx, monthly, yearly, order in specs:
        plan = SubscriptionPlan.objects.create(
            name=name,
            description=name,
            min_apartments=mn,
            max_apartments=mx,
            display_order=order,
            is_active=True,
        )
        SubscriptionPlanPricing.objects.create(
            plan=plan, duration=SubscriptionPlanPricing.Duration.MONTHLY, price_toman=monthly
        )
        SubscriptionPlanPricing.objects.create(
            plan=plan, duration=SubscriptionPlanPricing.Duration.YEARLY, price_toman=yearly
        )
        plans.append(plan)
    PlatformSettings.get_solo()
    settings = PlatformSettings.get_solo()
    settings.destination_card_number = "6037991234567890"
    settings.cardholder_name = "BuildingHub"
    settings.bank_name = "ملی"
    settings.payment_instructions = "کارت به کارت کنید"
    settings.grace_period_days = 7
    settings.save()
    return plans


@override_settings(MEDIA_ROOT="/tmp/buildinghub_test_media")
class SaaSFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.plans = seed_plans()
        self.admin = User.objects.create_superuser(
            "superadmin", "admin@test.com", "AdminPass123!", platform_role="SUPER_ADMIN"
        )

    def test_manager_registration_and_onboarding_monthly(self):
        res = self.client.post(
            "/api/v1/auth/register-manager/",
            {
                "first_name": "علی",
                "last_name": "مدیری",
                "phone": "09120001111",
                "email": "mgr@test.com",
                "password": "Manager123!",
                "password_confirm": "Manager123!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(username="09120001111")
        self.client.force_authenticate(user)

        building_res = self.client.post(
            "/api/v1/onboarding/building/",
            {
                "name": "برج تست",
                "address": "تهران",
                "floors_count": 4,
                "apartments_count": 8,
                "description": "demo",
            },
            format="json",
        )
        self.assertEqual(building_res.status_code, 201)
        building = Building.objects.get(pk=building_res.data["id"])
        self.assertEqual(building.status, Building.Status.PENDING)

        plan_res = self.client.post(
            "/api/v1/onboarding/select-plan/",
            {"building_id": building.id, "duration": "MONTHLY"},
            format="json",
        )
        self.assertEqual(plan_res.status_code, 201)
        sub = Subscription.objects.get(pk=plan_res.data["id"])
        self.assertEqual(sub.duration, Subscription.Duration.MONTHLY)
        self.assertEqual(sub.final_price_toman, 500_000)
        self.assertEqual(sub.status, Subscription.Status.PENDING_PAYMENT)

        pay = self.client.post(
            "/api/v1/onboarding/submit-payment/",
            {
                "subscription_id": sub.id,
                "amount_toman": sub.final_price_toman,
                "payer_name": "علی",
                "tracking_number": "TRX1",
                "payment_date": timezone.localdate().isoformat(),
                "receipt": make_image(),
            },
            format="multipart",
        )
        self.assertEqual(pay.status_code, 201)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.PENDING_APPROVAL)

        payment = SubscriptionPayment.objects.get(pk=pay.data["id"])
        self.client.force_authenticate(self.admin)
        approve = self.client.post(f"/api/v1/admin/subscription-payments/{payment.id}/approve/")
        self.assertEqual(approve.status_code, 200)
        sub.refresh_from_db()
        building.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)
        self.assertEqual(building.status, Building.Status.ACTIVE)
        self.assertTrue(building.is_active)

    def test_yearly_subscription_snapshot(self):
        manager = User.objects.create_user("m2", password="Manager123!", phone="0912")
        building = Building.objects.create(
            name="B2", manager=manager, apartments_count=15, address="x", status=Building.Status.PENDING
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.YEARLY, created_by=manager
        )
        self.assertEqual(sub.final_price_toman, 9_000_000)
        self.assertEqual(sub.plan_name_snapshot, "Standard")

    def test_payment_rejection_requires_reason_and_allows_resubmit(self):
        manager = User.objects.create_user("m3", password="Manager123!")
        building = Building.objects.create(
            name="B3", manager=manager, apartments_count=5, status=Building.Status.PENDING
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.MONTHLY, created_by=manager
        )
        payment = SubscriptionPayment.objects.create(
            subscription=sub,
            amount_toman=sub.final_price_toman,
            payer_name="x",
            tracking_number="1",
            payment_date=timezone.localdate(),
            status=SubscriptionPayment.Status.SUBMITTED,
            submitted_by=manager,
        )
        self.client.force_authenticate(self.admin)
        bad = self.client.post(
            f"/api/v1/admin/subscription-payments/{payment.id}/reject/",
            {},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            f"/api/v1/admin/subscription-payments/{payment.id}/reject/",
            {"rejection_reason": "رسید ناخوانا"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.REJECTED)

    def test_grace_period_and_expiry_and_notifications_dedupe(self):
        manager = User.objects.create_user("m4", password="Manager123!")
        building = Building.objects.create(
            name="B4", manager=manager, apartments_count=5, status=Building.Status.ACTIVE
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.MONTHLY, created_by=manager
        )
        activate_subscription(sub, actor=self.admin)
        sub.expires_at = timezone.now() - timedelta(minutes=1)
        sub.save(update_fields=["expires_at"])

        stats1 = process_subscription_lifecycle()
        self.assertEqual(stats1["grace_started"], 1)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.GRACE_PERIOD)

        stats2 = process_subscription_lifecycle()
        self.assertEqual(stats2["grace_started"], 0)  # dedupe

        sub.grace_ends_at = timezone.now() - timedelta(minutes=1)
        sub.save(update_fields=["grace_ends_at"])
        stats3 = process_subscription_lifecycle()
        self.assertEqual(stats3["expired"], 1)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.EXPIRED)

    def test_write_gate_blocks_expense_in_grace(self):
        manager = User.objects.create_user("m5", password="Manager123!")
        building = Building.objects.create(
            name="B5", manager=manager, apartments_count=5, status=Building.Status.ACTIVE
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.MONTHLY, created_by=manager
        )
        activate_subscription(sub, actor=self.admin)
        sub.status = Subscription.Status.GRACE_PERIOD
        sub.save(update_fields=["status"])
        self.client.force_authenticate(manager)
        res = self.client.post(
            "/api/v1/expenses/",
            {
                "building": building.id,
                "title": "x",
                "amount": 1000,
                "expense_date": timezone.localdate().isoformat(),
                "due_date": timezone.localdate().isoformat(),
                "allocation_method": "equal",
                "category": "cleaning",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_tenant_isolation(self):
        m1 = User.objects.create_user("iso1", password="x")
        m2 = User.objects.create_user("iso2", password="x")
        b1 = Building.objects.create(name="I1", manager=m1, status=Building.Status.ACTIVE, apartments_count=5)
        b2 = Building.objects.create(name="I2", manager=m2, status=Building.Status.ACTIVE, apartments_count=5)
        Membership.objects.create(user=m1, building=b1, role=Membership.Role.MANAGER)
        Membership.objects.create(user=m2, building=b2, role=Membership.Role.MANAGER)
        self.client.force_authenticate(m1)
        res = self.client.get("/api/v1/buildings/")
        ids = [b["id"] for b in res.data["results"]] if isinstance(res.data, dict) else [b["id"] for b in res.data]
        self.assertIn(b1.id, ids)
        self.assertNotIn(b2.id, ids)

    def test_invitation_single_use_and_expiry(self):
        manager = User.objects.create_user("invmgr", password="Manager123!")
        building = Building.objects.create(
            name="InvB", manager=manager, status=Building.Status.ACTIVE, apartments_count=5
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.MONTHLY, created_by=manager
        )
        activate_subscription(sub, actor=self.admin)
        unit = Unit.objects.create(building=building, number="101", floor=1, area_sqm=80)

        self.client.force_authenticate(manager)
        create = self.client.post(
            "/api/v1/invitations/",
            {
                "building_id": building.id,
                "unit_id": unit.id,
                "phone": "09123334455",
                "first_name": "رضا",
                "relationship_type": "tenant",
                "start_date": timezone.localdate().isoformat(),
                "occupants_count": 2,
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        token = create.data["token"]

        self.client.force_authenticate(user=None)
        accept1 = self.client.post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "password": "Resident123!",
                "password_confirm": "Resident123!",
                "username": "09123334455",
            },
            format="json",
        )
        self.assertEqual(accept1.status_code, 201, accept1.data)
        accept2 = self.client.post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "password": "Resident123!",
                "password_confirm": "Resident123!",
                "username": "otheruser",
            },
            format="json",
        )
        self.assertEqual(accept2.status_code, 400)

        # expired invite
        invite2 = ResidentInvitation.objects.create(
            building=building,
            unit=unit,
            invited_by=manager,
            phone="09120000000",
            start_date=timezone.localdate(),
            expires_at=timezone.now() - timedelta(hours=1),
        )
        expired = self.client.post(
            "/api/v1/invitations/accept/",
            {
                "token": invite2.token,
                "password": "Resident123!",
                "password_confirm": "Resident123!",
                "username": "expireduser",
            },
            format="json",
        )
        self.assertEqual(expired.status_code, 400)

    def test_support_ticket_flow(self):
        manager = User.objects.create_user("supmgr", password="Manager123!")
        building = Building.objects.create(name="SupB", manager=manager, status=Building.Status.PENDING)
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        self.client.force_authenticate(manager)
        create = self.client.post(
            "/api/v1/support/tickets/",
            {
                "building": building.id,
                "subject": "مشکل پرداخت",
                "category": "PAYMENT",
                "priority": "HIGH",
                "description": "رسید آپلود نمی‌شود",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        ticket_id = create.data["id"]
        reply = self.client.post(
            f"/api/v1/support/tickets/{ticket_id}/reply/",
            {"body": "پیگیری لطفا"},
            format="json",
        )
        self.assertEqual(reply.status_code, 200)
        self.assertTrue(SupportTicket.objects.filter(pk=ticket_id).exists())

    @override_settings(DEBUG=True)
    def test_password_recovery(self):
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = User.objects.create_user("resetme", password="OldPass123!", email="reset@test.com")
        req = self.client.post("/api/v1/auth/password-reset/", {"email": "reset@test.com"}, format="json")
        self.assertEqual(req.status_code, 200)
        self.assertIn("detail", req.data)
        # DEBUG mode returns token; otherwise construct the same generator token.
        if "reset_token" in req.data:
            reset_token = req.data["reset_token"]
        else:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_token = f"{uid}.{PasswordResetTokenGenerator().make_token(user)}"
        confirm = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "token": reset_token,
                "new_password": "NewPass123!",
                "new_password_confirm": "NewPass123!",
            },
            format="json",
        )
        self.assertEqual(confirm.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))

    def test_apartment_capacity_enforced(self):
        manager = User.objects.create_user("capmgr", password="Manager123!")
        building = Building.objects.create(
            name="CapB", manager=manager, status=Building.Status.ACTIVE, apartments_count=1
        )
        Membership.objects.create(user=manager, building=building, role=Membership.Role.MANAGER)
        sub = create_subscription_for_building(
            building=building, duration=Subscription.Duration.MONTHLY, created_by=manager
        )
        activate_subscription(sub, actor=self.admin)
        Unit.objects.create(building=building, number="1", floor=1, area_sqm=50)
        self.client.force_authenticate(manager)
        res = self.client.post(
            "/api/v1/units/",
            {"building": building.id, "number": "2", "floor": 1, "area_sqm": 50, "resident_count": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_admin_stats_real(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/v1/admin/dashboard/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("total_buildings", res.data)
        self.assertIn("recorded_subscription_revenue", res.data)

    def test_public_plans_and_pwa_assets_exist(self):
        res = self.client.get("/api/v1/subscriptions/plans/public/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.data) >= 1)
        from pathlib import Path

        frontend = Path(__file__).resolve().parents[1] / "frontend" / "public"
        self.assertTrue((frontend / "manifest.webmanifest").exists())
        self.assertTrue((frontend / "sw.js").exists())
        self.assertTrue((frontend / "offline.html").exists())
