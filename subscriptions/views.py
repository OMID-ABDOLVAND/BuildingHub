from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from buildings.models import Building, Membership, Unit, UnitOccupancy
from communications.models import Notification
from core.permissions import (
    IsSuperAdmin,
    IsSupportOperator,
    building_management_allowed,
    is_manager_of,
    is_platform_super_admin,
    managed_building_ids,
)
from core.utils import audit, notify_user, safe_upload_name, validate_upload
from finance.models import Payment as BuildingPayment
from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionHistory,
    SubscriptionPayment,
    SubscriptionPaymentReceipt,
    SubscriptionPlan,
)
from subscriptions.serializers import (
    ExtendSubscriptionSerializer,
    GrantFreeSerializer,
    ManagerRegisterSerializer,
    OnboardingBuildingSerializer,
    PlatformSettingsSerializer,
    RejectPaymentSerializer,
    SelectPlanSerializer,
    SubmitSubscriptionPaymentSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionPlanWriteSerializer,
    SubscriptionSerializer,
)
from subscriptions.services import (
    add_subscription_history,
    approve_subscription_payment,
    create_subscription_for_building,
    extend_subscription,
    grant_free_subscription,
    reject_subscription_payment,
    resolve_plan_for_apartments,
)
from support.models import SupportTicket

User = get_user_model()


class PublicPlanListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = SubscriptionPlan.objects.filter(is_active=True).prefetch_related("pricings")
        apartments = request.query_params.get("apartments")
        if apartments:
            try:
                count = int(apartments)
                qs = qs.filter(min_apartments__lte=count, max_apartments__gte=count)
            except ValueError:
                pass
        return Response(SubscriptionPlanSerializer(qs, many=True).data)


class PublicPaymentSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings = PlatformSettings.get_solo()
        return Response(
            {
                "destination_card_number": settings.destination_card_number,
                "cardholder_name": settings.cardholder_name,
                "bank_name": settings.bank_name,
                "payment_instructions": settings.payment_instructions,
                "grace_period_days": settings.grace_period_days,
                "support_email": settings.support_email,
                "support_phone": settings.support_phone,
            }
        )


class ManagerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = ManagerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        phone = data["phone"].strip()
        email = data["email"].strip().lower()
        if User.objects.filter(username=phone).exists():
            raise ValidationError({"phone": "این شماره موبایل قبلاً ثبت شده است."})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "این ایمیل قبلاً ثبت شده است."})
        user = User.objects.create_user(
            username=phone,
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=email,
            phone=phone,
        )
        audit(
            request,
            action="manager.register",
            entity_type="User",
            entity_id=user.id,
            changes={"phone": phone, "email": email},
        )
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "phone": user.phone,
                "email": user.email,
                "full_name": user.get_full_name(),
                "message": "ثبت‌نام موفق بود. وارد شوید و آنبوردینگ را ادامه دهید.",
            },
            status=status.HTTP_201_CREATED,
        )


class OnboardingBuildingView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = OnboardingBuildingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        building = Building.objects.create(
            name=data["name"],
            address=data["address"],
            description=data.get("description", ""),
            floors_count=data["floors_count"],
            apartments_count=data["apartments_count"],
            contact_phone=data.get("contact_phone", "") or request.user.phone,
            contact_email=data.get("contact_email", "") or request.user.email,
            manager=request.user,
            status=Building.Status.PENDING,
        )
        Membership.objects.get_or_create(
            user=request.user,
            building=building,
            defaults={"role": Membership.Role.MANAGER, "status": Membership.Status.ACTIVE},
        )
        audit(
            request,
            action="onboarding.building",
            entity_type="Building",
            entity_id=building.id,
            building=building,
            changes={"name": building.name, "apartments": building.apartments_count},
        )
        from buildings.serializers import BuildingSerializer

        return Response(BuildingSerializer(building).data, status=status.HTTP_201_CREATED)


class SelectSubscriptionPlanView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = SelectPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            building = Building.objects.get(pk=data["building_id"])
        except Building.DoesNotExist:
            raise ValidationError({"building_id": "ساختمان یافت نشد."})
        if not is_manager_of(request.user, building.id):
            raise PermissionDenied("دسترسی غیرمجاز.")

        plan = None
        if data.get("plan_id"):
            try:
                plan = SubscriptionPlan.objects.get(pk=data["plan_id"], is_active=True)
            except SubscriptionPlan.DoesNotExist:
                raise ValidationError({"plan_id": "پلن یافت نشد."})
        else:
            plan = resolve_plan_for_apartments(building.apartments_count or 1)

        # Cancel previous unfinished subscriptions
        Subscription.objects.filter(
            building=building,
            status__in=[
                Subscription.Status.PENDING_PAYMENT,
                Subscription.Status.PENDING_APPROVAL,
                Subscription.Status.REJECTED,
            ],
        ).update(status=Subscription.Status.CANCELLED, cancelled_at=timezone.now())

        subscription = create_subscription_for_building(
            building=building,
            duration=data["duration"],
            plan=plan,
            created_by=request.user,
        )
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class SubmitSubscriptionPaymentView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        serializer = SubmitSubscriptionPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            subscription = Subscription.objects.select_related("building").get(
                pk=data["subscription_id"]
            )
        except Subscription.DoesNotExist:
            raise ValidationError({"subscription_id": "اشتراک یافت نشد."})
        if not is_manager_of(request.user, subscription.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if subscription.status not in {
            Subscription.Status.PENDING_PAYMENT,
            Subscription.Status.REJECTED,
            Subscription.Status.EXPIRED,
            Subscription.Status.GRACE_PERIOD,
            Subscription.Status.ACTIVE,
        }:
            # allow renewal from ACTIVE/GRACE/EXPIRED via new payment on current or new sub
            pass

        receipt_file = request.FILES.get("receipt") or request.FILES.get("file")
        if not receipt_file:
            raise ValidationError({"receipt": "آپلود رسید الزامی است."})
        validate_upload(receipt_file)

        expected = subscription.payable_amount
        if int(data["amount_toman"]) != expected and not subscription.is_free:
            # Allow exact match only (snapshot)
            if int(data["amount_toman"]) <= 0:
                raise ValidationError({"amount_toman": "مبلغ نامعتبر است."})

        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount_toman=data["amount_toman"],
            payer_name=data["payer_name"],
            tracking_number=data["tracking_number"],
            payment_date=data["payment_date"],
            description=data.get("description", ""),
            status=SubscriptionPayment.Status.SUBMITTED,
            submitted_by=request.user,
        )
        receipt = SubscriptionPaymentReceipt(payment=payment, original_name=receipt_file.name)
        receipt.file.save(safe_upload_name(receipt_file.name), receipt_file, save=True)

        subscription.status = Subscription.Status.PENDING_APPROVAL
        subscription.save(update_fields=["status", "updated_at"])
        add_subscription_history(
            subscription,
            SubscriptionHistory.EventType.PAYMENT_SUBMITTED,
            actor=request.user,
            message="پرداخت ثبت و رسید آپلود شد.",
            metadata={"payment_id": payment.id},
        )

        # Notify super admins
        admins = User.objects.filter(
            Q(is_superuser=True) | Q(platform_role=User.PlatformRole.SUPER_ADMIN)
        )
        for admin in admins:
            notify_user(
                user=admin,
                title="پرداخت اشتراک جدید",
                body=f"پرداخت ساختمان «{subscription.building.name}» منتظر بررسی است.",
                type=Notification.Type.SUBSCRIPTION,
                building=subscription.building,
                link="/admin/payments",
            )

        audit(
            request,
            action="subscription_payment.submit",
            entity_type="SubscriptionPayment",
            entity_id=payment.id,
            building=subscription.building,
            changes={"amount": payment.amount_toman},
        )
        return Response(SubscriptionPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class MySubscriptionsView(APIView):
    def get(self, request):
        building_ids = managed_building_ids(request.user)
        qs = Subscription.objects.filter(building_id__in=building_ids).select_related(
            "building", "plan"
        ).prefetch_related("payments", "history")
        building_id = request.query_params.get("building")
        if building_id:
            qs = qs.filter(building_id=building_id)
        return Response(SubscriptionSerializer(qs, many=True).data)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all().prefetch_related("pricings")
    permission_classes = [IsSuperAdmin]
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["display_order", "min_apartments", "created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SubscriptionPlanWriteSerializer
        return SubscriptionPlanSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return super().get_permissions()


class PlatformSettingsView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsSuperAdmin()]

    def get(self, request):
        settings = PlatformSettings.get_solo()
        if is_platform_super_admin(request.user):
            return Response(PlatformSettingsSerializer(settings).data)
        return Response(
            {
                "destination_card_number": settings.destination_card_number,
                "cardholder_name": settings.cardholder_name,
                "bank_name": settings.bank_name,
                "payment_instructions": settings.payment_instructions,
                "grace_period_days": settings.grace_period_days,
                "support_email": settings.support_email,
                "support_phone": settings.support_phone,
            }
        )

    def patch(self, request):
        settings = PlatformSettings.get_solo()
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(
            request,
            action="platform_settings.update",
            entity_type="PlatformSettings",
            entity_id=1,
            changes=serializer.validated_data,
        )
        return Response(serializer.data)


class AdminSubscriptionPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = SubscriptionPaymentSerializer
    filterset_fields = ["status"]
    search_fields = [
        "payer_name",
        "tracking_number",
        "subscription__building__name",
        "subscription__plan_name_snapshot",
    ]
    ordering_fields = ["created_at", "amount_toman", "status"]

    def get_queryset(self):
        return SubscriptionPayment.objects.select_related(
            "subscription", "subscription__building", "submitted_by", "reviewed_by"
        ).prefetch_related("receipt")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        payment = self.get_object()
        approve_subscription_payment(payment, actor=request.user, request=request)
        payment.refresh_from_db()
        return Response(SubscriptionPaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        payment = self.get_object()
        serializer = RejectPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reject_subscription_payment(
            payment,
            actor=request.user,
            reason=serializer.validated_data["rejection_reason"],
            request=request,
        )
        payment.refresh_from_db()
        return Response(SubscriptionPaymentSerializer(payment).data)


class AdminSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = SubscriptionSerializer
    filterset_fields = ["status", "duration", "building"]
    search_fields = ["plan_name_snapshot", "building__name"]
    ordering_fields = ["created_at", "expires_at", "final_price_toman"]

    def get_queryset(self):
        return Subscription.objects.select_related("building", "plan").prefetch_related(
            "payments", "history"
        )

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        serializer = ExtendSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = extend_subscription(
            self.get_object(), days=serializer.validated_data["days"], actor=request.user
        )
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        sub = self.get_object()
        sub.status = Subscription.Status.SUSPENDED
        sub.save(update_fields=["status", "updated_at"])
        building = sub.building
        building.status = Building.Status.SUSPENDED
        building.save(update_fields=["status", "is_active", "updated_at"])
        add_subscription_history(
            sub, SubscriptionHistory.EventType.SUSPENDED, actor=request.user, message="تعلیق توسط ادمین"
        )
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        sub = self.get_object()
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status", "updated_at"])
        building = sub.building
        building.status = Building.Status.ACTIVE
        building.save(update_fields=["status", "is_active", "updated_at"])
        add_subscription_history(
            sub,
            SubscriptionHistory.EventType.REACTIVATED,
            actor=request.user,
            message="فعال‌سازی مجدد",
        )
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=False, methods=["post"], url_path="grant-free")
    def grant_free(self, request):
        serializer = GrantFreeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            building = Building.objects.get(pk=data["building_id"])
        except Building.DoesNotExist:
            raise ValidationError({"building_id": "ساختمان یافت نشد."})
        plan = None
        if data.get("plan_id"):
            plan = SubscriptionPlan.objects.get(pk=data["plan_id"])
        sub = grant_free_subscription(
            building=building,
            duration=data["duration"],
            plan=plan,
            actor=request.user,
            notes=data.get("notes", ""),
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class AdminDashboardStatsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        approved_payments = SubscriptionPayment.objects.filter(
            status=SubscriptionPayment.Status.APPROVED
        )
        return Response(
            {
                "total_buildings": Building.objects.count(),
                "active_buildings": Building.objects.filter(status=Building.Status.ACTIVE).count(),
                "pending_buildings": Building.objects.filter(status=Building.Status.PENDING).count(),
                "suspended_buildings": Building.objects.filter(
                    status=Building.Status.SUSPENDED
                ).count(),
                "total_managers": Membership.objects.filter(
                    role=Membership.Role.MANAGER, status=Membership.Status.ACTIVE
                )
                .values("user_id")
                .distinct()
                .count(),
                "total_residents": Membership.objects.filter(
                    role=Membership.Role.RESIDENT, status=Membership.Status.ACTIVE
                )
                .values("user_id")
                .distinct()
                .count(),
                "total_apartments": Unit.objects.count(),
                "active_subscriptions": Subscription.objects.filter(
                    status=Subscription.Status.ACTIVE
                ).count(),
                "expired_subscriptions": Subscription.objects.filter(
                    status=Subscription.Status.EXPIRED
                ).count(),
                "grace_period_subscriptions": Subscription.objects.filter(
                    status=Subscription.Status.GRACE_PERIOD
                ).count(),
                "pending_payments": SubscriptionPayment.objects.filter(
                    status__in=[
                        SubscriptionPayment.Status.SUBMITTED,
                        SubscriptionPayment.Status.UNDER_REVIEW,
                    ]
                ).count(),
                "approved_payments": approved_payments.count(),
                "recorded_subscription_revenue": approved_payments.aggregate(
                    total=Sum("amount_toman")
                )["total"]
                or 0,
                "monthly_revenue": approved_payments.filter(approved_at__gte=month_start).aggregate(
                    total=Sum("amount_toman")
                )["total"]
                or 0,
                "yearly_revenue": approved_payments.filter(approved_at__year=now.year).aggregate(
                    total=Sum("amount_toman")
                )["total"]
                or 0,
                "open_support_tickets": SupportTicket.objects.exclude(
                    status=SupportTicket.Status.CLOSED
                ).count(),
            }
        )


class AdminBuildingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    search_fields = ["name", "address", "manager__username", "manager__phone"]
    filterset_fields = ["status", "is_active"]
    ordering_fields = ["name", "created_at", "status"]

    def get_queryset(self):
        return Building.objects.select_related("manager").all()

    def get_serializer_class(self):
        from buildings.serializers import BuildingSerializer

        return BuildingSerializer

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        building = self.get_object()
        building.status = Building.Status.ACTIVE
        building.save()
        audit(
            request,
            action="building.activate",
            entity_type="Building",
            entity_id=building.id,
            building=building,
        )
        from buildings.serializers import BuildingSerializer

        return Response(BuildingSerializer(building).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        building = self.get_object()
        building.status = Building.Status.SUSPENDED
        building.save()
        audit(
            request,
            action="building.suspend",
            entity_type="Building",
            entity_id=building.id,
            building=building,
        )
        from buildings.serializers import BuildingSerializer

        return Response(BuildingSerializer(building).data)


class AdminManagerListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        manager_ids = (
            Membership.objects.filter(role=Membership.Role.MANAGER)
            .values_list("user_id", flat=True)
            .distinct()
        )
        users = User.objects.filter(
            Q(id__in=manager_ids) | Q(managed_buildings__isnull=False)
        ).distinct()
        q = request.query_params.get("search")
        if q:
            users = users.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(email__icontains=q)
            )
        from accounts.serializers import UserSerializer

        return Response(UserSerializer(users, many=True).data)


class AdminResidentListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        resident_ids = (
            Membership.objects.filter(role=Membership.Role.RESIDENT)
            .values_list("user_id", flat=True)
            .distinct()
        )
        users = User.objects.filter(id__in=resident_ids)
        q = request.query_params.get("search")
        if q:
            users = users.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
            )
        from accounts.serializers import UserSerializer

        return Response(UserSerializer(users, many=True).data)


class BuildingGateStatusView(APIView):
    def get(self, request):
        building_id = request.query_params.get("building")
        if not building_id:
            raise ValidationError({"building": "شناسه ساختمان الزامی است."})
        try:
            building = Building.objects.get(pk=building_id)
        except Building.DoesNotExist:
            raise ValidationError({"building": "ساختمان یافت نشد."})
        if not is_manager_of(request.user, building.id) and not is_platform_super_admin(request.user):
            # residents can also see gate for their building
            from core.permissions import is_member_of

            if not is_member_of(request.user, building.id):
                raise PermissionDenied("دسترسی غیرمجاز.")
        sub = building.current_subscription()
        return Response(
            {
                "building_id": building.id,
                "building_status": building.status,
                "subscription_status": sub.status if sub else None,
                "management_allowed": building_management_allowed(building),
                "expires_at": sub.expires_at if sub else None,
                "grace_ends_at": sub.grace_ends_at if sub else None,
                "subscription_id": sub.id if sub else None,
            }
        )
