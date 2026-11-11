from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from buildings.models import Building, Membership, Unit, UnitOccupancy
from communications.models import Announcement, Notification
from core.models import AuditLog
from core.receipt_images import make_bank_receipt, make_maintenance_photo
from finance.models import Expense, ExpenseAllocation, Payment, PaymentReceipt
from finance.services import AllocationInput, compute_allocations
from maintenance.models import MaintenanceRequest, RequestMessage
from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionPlan,
    SubscriptionPlanPricing,
)
from subscriptions.services import activate_subscription, create_subscription_for_building
from support.models import SupportTicket

User = get_user_model()


def finalize_expense(expense, units, method=None, custom_shares=None):
    if method:
        expense.allocation_method = method
    expense.included_units.set(units)
    items = [
        AllocationInput(
            unit_id=u.id,
            resident_count=u.resident_count,
            area_sqm=u.area_sqm,
            custom_amount=(custom_shares or {}).get(u.id),
        )
        for u in units
    ]
    amounts = compute_allocations(expense.allocation_method, expense.amount, items)
    ExpenseAllocation.objects.filter(expense=expense).delete()
    for unit in units:
        ExpenseAllocation.objects.create(
            expense=expense,
            unit=unit,
            amount=amounts[unit.id],
            snapshot_resident_count=unit.resident_count,
            snapshot_area_sqm=unit.area_sqm,
            status=ExpenseAllocation.Status.UNPAID,
        )
    expense.status = Expense.Status.FINALIZED
    expense.finalized_at = timezone.now()
    expense.finalized_by = expense.created_by
    expense.save()
    return expense


class Command(BaseCommand):
    help = "Seed rich demo data for BuildingHub (users, finance, maintenance, notifications)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete demo domain data before seeding (keeps users if recreate)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting demo domain data…")
            SupportTicket.objects.all().delete()
            Subscription.objects.all().delete()
            SubscriptionPlanPricing.objects.all().delete()
            SubscriptionPlan.objects.all().delete()
            PaymentReceipt.objects.all().delete()
            Payment.objects.all().delete()
            ExpenseAllocation.objects.all().delete()
            Expense.objects.all().delete()
            RequestMessage.objects.all().delete()
            MaintenanceRequest.objects.all().delete()
            Notification.objects.all().delete()
            Announcement.objects.all().delete()
            AuditLog.objects.all().delete()
            UnitOccupancy.objects.all().delete()
            Membership.objects.all().delete()
            Unit.objects.all().delete()
            Building.objects.all().delete()

        today = timezone.localdate()
        now = timezone.now()

        # ---- SaaS plans + platform settings ----
        plan_specs = [
            ("Basic", "۱ تا ۱۰ واحد", 1, 10, 500_000, 5_000_000, 1),
            ("Standard", "۱۱ تا ۳۰ واحد", 11, 30, 900_000, 9_000_000, 2),
            ("Professional", "۳۱ تا ۶۰ واحد", 31, 60, 1_500_000, 15_000_000, 3),
            ("Enterprise", "۶۱ تا ۱۰۰ واحد", 61, 100, 2_500_000, 25_000_000, 4),
            ("Custom", "بالای ۱۰۰ واحد", 101, 10000, 4_000_000, 40_000_000, 5),
        ]
        for name, desc, mn, mx, monthly, yearly, order in plan_specs:
            plan, _ = SubscriptionPlan.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "min_apartments": mn,
                    "max_apartments": mx,
                    "display_order": order,
                    "is_active": True,
                    "monthly_features": ["مدیریت ساختمان", "هزینه و پرداخت"],
                    "yearly_features": ["همه امکانات ماهانه", "تخفیف سالانه"],
                },
            )
            SubscriptionPlanPricing.objects.update_or_create(
                plan=plan,
                duration=SubscriptionPlanPricing.Duration.MONTHLY,
                defaults={"price_toman": monthly, "is_active": True},
            )
            SubscriptionPlanPricing.objects.update_or_create(
                plan=plan,
                duration=SubscriptionPlanPricing.Duration.YEARLY,
                defaults={"price_toman": yearly, "is_active": True},
            )

        settings = PlatformSettings.get_solo()
        settings.grace_period_days = 7
        settings.destination_card_number = "6037-9912-3456-7890"
        settings.cardholder_name = "شرکت BuildingHub"
        settings.bank_name = "بانک ملی"
        settings.payment_instructions = "مبلغ را کارت‌به‌کارت کنید و رسید را آپلود نمایید."
        settings.support_email = "support@buildinghub.local"
        settings.support_phone = "02191000000"
        settings.save()

        # ---- users ----
        manager, _ = User.objects.get_or_create(
            username="manager",
            defaults={
                "first_name": "علی",
                "last_name": "مدیری",
                "email": "manager@buildinghub.local",
                "phone": "09121234567",
            },
        )
        manager.first_name = "علی"
        manager.last_name = "مدیری"
        manager.email = "manager@buildinghub.local"
        manager.phone = "09121234567"
        manager.set_password("Manager123!")
        manager.save()

        assistant, _ = User.objects.get_or_create(
            username="assistant",
            defaults={
                "first_name": "مریم",
                "last_name": "کاظمی",
                "email": "assistant@buildinghub.local",
                "phone": "09123334455",
            },
        )
        assistant.set_password("Assistant123!")
        assistant.first_name = "مریم"
        assistant.last_name = "کاظمی"
        assistant.save()

        resident_profiles = [
            ("resident1", "رضا", "احمدی", "09121110001", "owner"),
            ("resident2", "سارا", "محمدی", "09121110002", "tenant"),
            ("resident3", "حسین", "کریمی", "09121110003", "owner"),
            ("resident4", "نگار", "حسینی", "09121110004", "tenant"),
            ("resident5", "امیر", "رضایی", "09121110005", "owner"),
            ("resident6", "فاطمه", "موسوی", "09121110006", "tenant"),
            ("resident7", "کیان", "جعفری", "09121110007", "tenant"),
            ("resident8", "الهام", "نوری", "09121110008", "owner"),
        ]
        residents = []
        for username, first, last, phone, _rel in resident_profiles:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@buildinghub.local",
                    "phone": phone,
                },
            )
            user.first_name = first
            user.last_name = last
            user.email = f"{username}@buildinghub.local"
            user.phone = phone
            user.set_password("Resident123!")
            user.save()
            residents.append(user)

        # ---- buildings ----
        building, _ = Building.objects.get_or_create(
            name="برج آسمان",
            defaults={
                "address": "تهران، خیابان ولیعصر، پلاک ۱۰۰",
                "description": "ساختمان ۱۲ واحدی نمونه با آسانسور و نگهبانی",
                "manager": manager,
                "contact_phone": "02188887766",
                "contact_email": "info@aseman.local",
                "floors_count": 4,
                "apartments_count": 12,
                "status": Building.Status.ACTIVE,
            },
        )
        building.manager = manager
        building.description = "ساختمان ۱۲ واحدی نمونه با آسانسور و نگهبانی"
        building.floors_count = 4
        building.apartments_count = 12
        building.status = Building.Status.ACTIVE
        building.save()

        building2, _ = Building.objects.get_or_create(
            name="مجتمع سپیدار",
            defaults={
                "address": "تهران، سعادت‌آباد، میدان کاج",
                "description": "ساختمان دوم برای نمایش پشتیبانی چندساختمانه",
                "manager": manager,
                "contact_phone": "02122001122",
                "contact_email": "info@sepidar.local",
                "floors_count": 2,
                "apartments_count": 6,
                "status": Building.Status.ACTIVE,
            },
        )
        building2.floors_count = 2
        building2.apartments_count = 6
        building2.status = Building.Status.ACTIVE
        building2.save()

        pending_building, _ = Building.objects.get_or_create(
            name="برج در انتظار تأیید",
            defaults={
                "address": "تهران، نیاوران",
                "description": "نمونه ساختمان PENDING برای آنبوردینگ",
                "manager": manager,
                "floors_count": 3,
                "apartments_count": 8,
                "status": Building.Status.PENDING,
                "contact_phone": "02111112222",
            },
        )

        for b in (building, building2):
            Membership.objects.update_or_create(
                user=manager,
                building=b,
                defaults={"role": Membership.Role.MANAGER, "status": Membership.Status.ACTIVE},
            )
        Membership.objects.update_or_create(
            user=assistant,
            building=building,
            defaults={"role": Membership.Role.MANAGER, "status": Membership.Status.ACTIVE},
        )

        unit_specs = [
            ("101", 1, 90, 3),
            ("102", 1, 110, 4),
            ("201", 2, 85, 2),
            ("202", 2, 120, 5),
            ("301", 3, 95, 3),
            ("302", 3, 100, 4),
            ("401", 4, 130, 5),
            ("402", 4, 88, 2),
        ]
        units = []
        for number, floor, area, count in unit_specs:
            unit, _ = Unit.objects.get_or_create(
                building=building,
                number=number,
                defaults={
                    "floor": floor,
                    "area_sqm": area,
                    "resident_count": count,
                    "description": f"واحد {number} برج آسمان",
                    "is_active": True,
                },
            )
            unit.floor = floor
            unit.area_sqm = area
            unit.resident_count = count
            unit.save()
            units.append(unit)

        # second building units
        b2_units = []
        for number, floor, area, count in [("11", 1, 75, 2), ("12", 1, 80, 3), ("21", 2, 95, 4)]:
            unit, _ = Unit.objects.get_or_create(
                building=building2,
                number=number,
                defaults={
                    "floor": floor,
                    "area_sqm": area,
                    "resident_count": count,
                    "description": f"واحد {number} سپیدار",
                },
            )
            b2_units.append(unit)

        # occupancies for building 1
        for idx, (unit, profile) in enumerate(zip(units, resident_profiles)):
            user = residents[idx]
            _username, _f, _l, _p, rel = profile
            Membership.objects.update_or_create(
                user=user,
                building=building,
                defaults={"role": Membership.Role.RESIDENT, "status": Membership.Status.ACTIVE},
            )
            UnitOccupancy.objects.update_or_create(
                unit=unit,
                user=user,
                is_current=True,
                defaults={
                    "relationship_type": (
                        UnitOccupancy.Relationship.OWNER
                        if rel == "owner"
                        else UnitOccupancy.Relationship.TENANT
                    ),
                    "start_date": today - timedelta(days=400 - idx * 20),
                    "occupants_count": unit.resident_count,
                },
            )

        # put resident1 also as member of building2 for multi-building demo
        Membership.objects.update_or_create(
            user=residents[0],
            building=building2,
            defaults={"role": Membership.Role.RESIDENT, "status": Membership.Status.ACTIVE},
        )
        UnitOccupancy.objects.update_or_create(
            unit=b2_units[0],
            user=residents[0],
            is_current=True,
            defaults={
                "relationship_type": UnitOccupancy.Relationship.OWNER,
                "start_date": today - timedelta(days=200),
                "occupants_count": b2_units[0].resident_count,
            },
        )

        # ---- expenses ----
        def get_or_make_expense(title, **kwargs):
            expense, created = Expense.objects.get_or_create(
                building=kwargs.pop("building", building),
                title=title,
                defaults=kwargs,
            )
            if created or expense.status != Expense.Status.FINALIZED:
                for k, v in kwargs.items():
                    setattr(expense, k, v)
                expense.save()
            return expense, created

        elevator, _ = get_or_make_expense(
            "سرویس آسانسور آبان",
            description="قرارداد ماهانه سرویس و بازدید آسانسور",
            category=Expense.Category.ELEVATOR,
            amount=12_000_000,
            expense_date=today - timedelta(days=5),
            due_date=today + timedelta(days=10),
            allocation_method=Expense.AllocationMethod.EQUAL,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )
        if elevator.status != Expense.Status.FINALIZED:
            finalize_expense(elevator, units, Expense.AllocationMethod.EQUAL)
        if not elevator.invoice_image:
            elevator.invoice_image.save(
                "invoice-elevator.png",
                make_bank_receipt(
                    amount=elevator.amount,
                    payer_name="پیمانکار آسانسور آریا",
                    unit_number="مشاعات",
                    title=elevator.title,
                    status_label="فاکتور رسمی",
                    ref_code="INV-ELV-110",
                    bank_name="فاکتور فروشنده",
                ),
                save=True,
            )

        water, _ = get_or_make_expense(
            "آب مشاع مهر",
            description="قبض آب مشاع بر اساس تعداد نفرات",
            category=Expense.Category.WATER,
            amount=9_000_000,
            expense_date=today - timedelta(days=25),
            due_date=today - timedelta(days=5),
            allocation_method=Expense.AllocationMethod.RESIDENT,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )
        if water.status != Expense.Status.FINALIZED:
            finalize_expense(water, units, Expense.AllocationMethod.RESIDENT)

        painting, _ = get_or_make_expense(
            "رنگ‌آمیزی راهروها",
            description="هزینه رنگ و مصالح مشاعات بر اساس متراژ",
            category=Expense.Category.REPAIR,
            amount=18_000_000,
            expense_date=today - timedelta(days=12),
            due_date=today + timedelta(days=20),
            allocation_method=Expense.AllocationMethod.AREA,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )
        if painting.status != Expense.Status.FINALIZED:
            finalize_expense(painting, units[:6], Expense.AllocationMethod.AREA)

        cleaning, _ = get_or_make_expense(
            "نظافت مشاعات آبان",
            description="قرارداد شرکت نظافتی",
            category=Expense.Category.CLEANING,
            amount=4_800_000,
            expense_date=today - timedelta(days=2),
            due_date=today + timedelta(days=12),
            allocation_method=Expense.AllocationMethod.EQUAL,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )
        if cleaning.status != Expense.Status.FINALIZED:
            finalize_expense(cleaning, units, Expense.AllocationMethod.EQUAL)

        # custom draft for manager to finalize in UI
        custom_draft, _ = get_or_make_expense(
            "تعمیر درب پارکینگ (پیش‌نویس سفارشی)",
            description="نمونه تقسیم سفارشی — هنوز نهایی نشده",
            category=Expense.Category.REPAIR,
            amount=3_500_000,
            expense_date=today,
            due_date=today + timedelta(days=14),
            allocation_method=Expense.AllocationMethod.CUSTOM,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )
        custom_draft.included_units.set(units[:4])

        # water draft second building
        get_or_make_expense(
            "شارژ نگهبانی سپیدار",
            building=building2,
            description="هزینه نگهبانی ماهانه",
            category=Expense.Category.SECURITY,
            amount=6_000_000,
            expense_date=today,
            due_date=today + timedelta(days=15),
            allocation_method=Expense.AllocationMethod.EQUAL,
            status=Expense.Status.DRAFT,
            created_by=manager,
        )

        # ---- payments ----
        def ensure_payment(allocation, amount, user, status, description="", rejection=""):
            existing = Payment.objects.filter(
                allocation=allocation,
                submitted_by=user,
                amount=amount,
                status=status,
            ).first()
            receipt_file = make_bank_receipt(
                amount=amount,
                payer_name=user.get_full_name() or user.username,
                unit_number=allocation.unit.number,
                title=allocation.expense.title,
                status_label="تأیید بانکی" if status == Payment.Status.APPROVED else (
                    "رد شده" if status == Payment.Status.REJECTED else "در انتظار تأیید"
                ),
                ref_code=f"BH-{allocation.id}-{amount // 1000}",
            )
            if existing:
                receipt, _ = PaymentReceipt.objects.get_or_create(payment=existing)
                receipt.file.save(f"receipt-{existing.id}.png", receipt_file, save=True)
                receipt.original_name = f"receipt-{existing.id}.png"
                receipt.save(update_fields=["original_name", "updated_at"])
                return existing
            payment = Payment.objects.create(
                allocation=allocation,
                amount=amount,
                description=description,
                status=status,
                submitted_by=user,
                reviewed_by=manager if status != Payment.Status.PENDING else None,
                reviewed_at=now if status != Payment.Status.PENDING else None,
                rejection_reason=rejection,
            )
            PaymentReceipt.objects.create(
                payment=payment,
                file=receipt_file,
                original_name=f"receipt-{payment.id}.png",
            )
            allocation.refresh_status()
            return payment

        # resident1: full pay elevator, partial water, pending cleaning
        alloc_e1 = ExpenseAllocation.objects.get(expense=elevator, unit=units[0])
        alloc_w1 = ExpenseAllocation.objects.get(expense=water, unit=units[0])
        alloc_c1 = ExpenseAllocation.objects.get(expense=cleaning, unit=units[0])
        ensure_payment(
            alloc_e1,
            alloc_e1.amount,
            residents[0],
            Payment.Status.APPROVED,
            "واریز کامل سهم آسانسور",
        )
        ensure_payment(
            alloc_w1,
            max(alloc_w1.amount // 2, 1),
            residents[0],
            Payment.Status.APPROVED,
            "پرداخت جزئی آب",
        )
        ensure_payment(
            alloc_c1,
            alloc_c1.amount,
            residents[0],
            Payment.Status.PENDING,
            "رسید در انتظار بررسی",
        )

        # resident2: rejected then corrected pending
        alloc_e2 = ExpenseAllocation.objects.get(expense=elevator, unit=units[1])
        ensure_payment(
            alloc_e2,
            alloc_e2.amount,
            residents[1],
            Payment.Status.REJECTED,
            "رسید ناخوانا",
            rejection="تصویر رسید تار است؛ لطفاً مجدداً ارسال کنید.",
        )
        ensure_payment(
            alloc_e2,
            alloc_e2.amount,
            residents[1],
            Payment.Status.PENDING,
            "رسید اصلاح‌شده",
        )

        # resident3: approved painting partial
        if ExpenseAllocation.objects.filter(expense=painting, unit=units[2]).exists():
            alloc_p3 = ExpenseAllocation.objects.get(expense=painting, unit=units[2])
            ensure_payment(
                alloc_p3,
                max(alloc_p3.amount // 3, 1),
                residents[2],
                Payment.Status.APPROVED,
                "قسط اول رنگ‌آمیزی",
            )

        # resident4 overdue water unpaid (no payment) — already overdue by due_date
        for alloc in ExpenseAllocation.objects.filter(expense=water):
            alloc.refresh_status()

        # ---- maintenance ----
        def ensure_maint(**kwargs):
            obj = MaintenanceRequest.objects.filter(
                building=kwargs["building"],
                title=kwargs["title"],
                unit=kwargs["unit"],
            ).first()
            if obj:
                return obj
            return MaintenanceRequest.objects.create(**kwargs)

        m1 = ensure_maint(
            building=building,
            unit=units[0],
            created_by=residents[0],
            title="نشتی شیر آب آشپزخانه",
            category=MaintenanceRequest.Category.PLUMBING,
            description="از دو روز پیش شیر ظرفشویی چکه می‌کند و کابینت خیس شده.",
            priority=MaintenanceRequest.Priority.HIGH,
            status=MaintenanceRequest.Status.IN_PROGRESS,
            action_taken="لوله کش هماهنگ شد؛ قطعه سفارش داده شده.",
        )
        if not m1.image:
            m1.image.save("maint-leak.png", make_maintenance_photo(label="نشتی شیر آب آشپزخانه"), save=True)
        if not m1.messages.exists():
            RequestMessage.objects.create(
                request=m1,
                sender=residents[0],
                body="لطفاً هرچه سریع‌تر رسیدگی شود؛ مصرف آب بالا رفته.",
            )
            RequestMessage.objects.create(
                request=m1,
                sender=manager,
                body="درخواست ثبت شد. فردا بین ۱۰ تا ۱۲ مراجعه می‌کنند.",
            )

        m2 = ensure_maint(
            building=building,
            unit=units[1],
            created_by=residents[1],
            title="صدای غیرعادی آسانسور",
            category=MaintenanceRequest.Category.ELEVATOR,
            description="هنگام توقف در طبقه ۲ صدای تق‌تق شنیده می‌شود.",
            priority=MaintenanceRequest.Priority.URGENT,
            status=MaintenanceRequest.Status.UNDER_REVIEW,
        )
        if not m2.image:
            m2.image.save("maint-elevator.png", make_maintenance_photo(label="آسانسور — صدای غیرعادی"), save=True)
        if not m2.messages.exists():
            RequestMessage.objects.create(
                request=m2,
                sender=manager,
                body="شرکت آسانسور برای بازدید هماهنگ شد.",
            )

        m3 = ensure_maint(
            building=building,
            unit=units[3],
            created_by=residents[3],
            title="خرابی لامپ راهرو طبقه ۲",
            category=MaintenanceRequest.Category.ELECTRICAL,
            description="دو عدد لامپ راهرو سوخته است.",
            priority=MaintenanceRequest.Priority.LOW,
            status=MaintenanceRequest.Status.RESOLVED,
            resolution_notes="لامپ‌ها تعویض شدند.",
            action_taken="تعویض ۲ عدد لامپ LED",
        )
        if not m3.image:
            m3.image.save("maint-light.png", make_maintenance_photo(label="لامپ سوخته راهرو"), save=True)

        ensure_maint(
            building=building,
            unit=units[4],
            created_by=residents[4],
            title="بو نامطبوع از چاهک پارکینگ",
            category=MaintenanceRequest.Category.OTHER,
            description="از هفته گذشته بوی نامطبوع در پارکینگ احساس می‌شود.",
            priority=MaintenanceRequest.Priority.MEDIUM,
            status=MaintenanceRequest.Status.NEEDS_INFORMATION,
        )

        ensure_maint(
            building=building,
            unit=units[5],
            created_by=residents[5],
            title="درخواست نصب دوربین اضافه",
            category=MaintenanceRequest.Category.OTHER,
            description="لطفاً امکان نصب دوربین در راهروی طبقه ۳ بررسی شود.",
            priority=MaintenanceRequest.Priority.LOW,
            status=MaintenanceRequest.Status.REJECTED,
            rejection_reason="خارج از بودجه امسال است؛ در مجمع بعدی مطرح شود.",
        )

        # ---- announcements ----
        announcements = [
            (
                building,
                "قطع آب روز جمعه",
                "به دلیل تعمیرات شبکه، آب ساختمان روز جمعه از ساعت ۹ تا ۱۴ قطع خواهد بود.",
            ),
            (
                building,
                "سرویس آسانسور هفته آینده",
                "روز دوشنبه آسانسور بین ۱۰ تا ۱۲ برای سرویس از مدار خارج می‌شود.",
            ),
            (
                building,
                "جلسه مجمع عمومی",
                "مجمع عمومی ساختمان سه‌شنبه ساعت ۱۹ در لابی برگزار می‌شود. حضور ساکنین الزامی است.",
            ),
            (
                building2,
                "ورود خودروهای مهمان",
                "از این ماه ورود خودرو مهمان فقط با هماهنگی نگهبانی امکان‌پذیر است.",
            ),
        ]
        for b, title, body in announcements:
            Announcement.objects.get_or_create(
                building=b,
                title=title,
                defaults={
                    "body": body,
                    "created_by": manager,
                    "is_published": True,
                    "published_at": now - timedelta(hours=6),
                },
            )

        # ---- notifications ----
        notif_specs = [
            (residents[0], Notification.Type.EXPENSE, "هزینه جدید", "سرویس آسانسور آبان برای واحد شما ثبت شد.", "/app/my-expenses"),
            (residents[0], Notification.Type.PAYMENT, "پرداخت تأیید شد", "پرداخت سهم آسانسور تأیید شد.", "/app/my-payments"),
            (residents[0], Notification.Type.PAYMENT, "رسید در انتظار", "رسید نظافت در صف بررسی مدیر است.", "/app/my-payments"),
            (residents[1], Notification.Type.PAYMENT, "پرداخت رد شد", "رسید شما رد شد؛ لطفاً مجدداً ارسال کنید.", "/app/payments/submit"),
            (residents[1], Notification.Type.MAINTENANCE, "پیگیری آسانسور", "وضعیت درخواست آسانسور: در حال بررسی", "/app/maintenance"),
            (manager, Notification.Type.PAYMENT, "رسید جدید", "ساکن واحد ۱۰۲ رسید اصلاح‌شده ارسال کرد.", "/app/payments"),
            (manager, Notification.Type.MAINTENANCE, "درخواست فوری", "صدای غیرعادی آسانسور — اولویت فوری", "/app/maintenance"),
            (assistant, Notification.Type.ANNOUNCEMENT, "اطلاعیه منتشر شد", "اطلاعیه قطع آب منتشر شد.", "/app/announcements"),
        ]
        for user, typ, title, body, link in notif_specs:
            if not Notification.objects.filter(user=user, title=title, body=body).exists():
                Notification.objects.create(
                    user=user,
                    building=building,
                    type=typ,
                    title=title,
                    body=body,
                    link=link,
                    is_read=False,
                )

        # ---- audit samples ----
        # ---- subscriptions for active buildings ----
        for b, duration in ((building, Subscription.Duration.YEARLY), (building2, Subscription.Duration.MONTHLY)):
            existing = b.subscriptions.filter(status=Subscription.Status.ACTIVE).first()
            if not existing:
                sub = create_subscription_for_building(building=b, duration=duration, created_by=manager)
                activate_subscription(sub, actor=manager)

        if not pending_building.subscriptions.exists():
            create_subscription_for_building(
                building=pending_building,
                duration=Subscription.Duration.MONTHLY,
                created_by=manager,
            )

        if not SupportTicket.objects.filter(subject="سوال درباره تمدید").exists():
            SupportTicket.objects.create(
                building=building,
                created_by=manager,
                subject="سوال درباره تمدید",
                category=SupportTicket.Category.SUBSCRIPTION,
                priority=SupportTicket.Priority.NORMAL,
                description="چطور اشتراک سالانه را تمدید کنم؟",
            )

        if not AuditLog.objects.filter(action="seed.demo").exists():
            AuditLog.objects.create(
                user=manager,
                building=building,
                action="seed.demo",
                entity_type="System",
                entity_id="demo",
                changes={
                    "buildings": Building.objects.count(),
                    "units": Unit.objects.count(),
                    "residents": len(residents),
                    "expenses": Expense.objects.count(),
                    "payments": Payment.objects.count(),
                    "plans": SubscriptionPlan.objects.count(),
                },
            )
            AuditLog.objects.create(
                user=manager,
                building=building,
                action="expense.finalize",
                entity_type="Expense",
                entity_id=str(elevator.id),
                changes={"title": elevator.title, "amount": elevator.amount},
            )
            AuditLog.objects.create(
                user=manager,
                building=building,
                action="payment.approve",
                entity_type="Payment",
                entity_id=str(Payment.objects.filter(status=Payment.Status.APPROVED).first().id),
                changes={"note": "demo approved payment"},
            )

        self.stdout.write(self.style.SUCCESS("Rich demo data ready.\n"))
        self.stdout.write("=" * 56)
        self.stdout.write("DEMO ACCOUNTS")
        self.stdout.write("=" * 56)
        self.stdout.write("manager     / Manager123!     (مدیر برج آسمان + سپیدار)")
        self.stdout.write("assistant   / Assistant123!   (مدیر کمکی برج آسمان)")
        self.stdout.write("resident1   / Resident123!    (رضا احمدی — واحد ۱۰۱ + سپیدار ۱۱)")
        self.stdout.write("resident2   / Resident123!    (سارا محمدی — واحد ۱۰۲)")
        self.stdout.write("resident3   / Resident123!    (حسین کریمی — واحد ۲۰۱)")
        self.stdout.write("resident4   / Resident123!    (نگار حسینی — واحد ۲۰۲)")
        self.stdout.write("resident5   / Resident123!    (امیر رضایی — واحد ۳۰۱)")
        self.stdout.write("resident6   / Resident123!    (فاطمه موسوی — واحد ۳۰۲)")
        self.stdout.write("resident7   / Resident123!    (کیان جعفری — واحد ۴۰۱)")
        self.stdout.write("resident8   / Resident123!    (الهام نوری — واحد ۴۰۲)")
        self.stdout.write("=" * 56)
        self.stdout.write("Create SUPER_ADMIN with:")
        self.stdout.write(
            '  python manage.py createsuperadmin --username admin --email admin@local --password "ChangeMe123!"'
        )
        self.stdout.write("=" * 56)
        self.stdout.write(
            f"Stats: buildings={Building.objects.count()} units={Unit.objects.count()} "
            f"expenses={Expense.objects.count()} payments={Payment.objects.count()} "
            f"maintenance={MaintenanceRequest.objects.count()} "
            f"announcements={Announcement.objects.count()} "
            f"notifications={Notification.objects.count()} "
            f"plans={SubscriptionPlan.objects.count()} "
            f"subscriptions={Subscription.objects.count()}"
        )
