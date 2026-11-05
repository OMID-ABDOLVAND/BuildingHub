from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from buildings.models import Unit
from communications.models import Notification
from core.permissions import (
    can_access_unit,
    is_manager_of,
    managed_building_ids,
    resident_building_ids,
    user_unit_ids,
)
from core.utils import audit, notify_building_members, notify_user, safe_upload_name, validate_upload
from finance.models import Expense, ExpenseAllocation, Payment, PaymentReceipt
from finance.serializers import (
    ExpenseAllocationSerializer,
    ExpenseSerializer,
    ExpenseWriteSerializer,
    PaymentCreateSerializer,
    PaymentReviewSerializer,
    PaymentSerializer,
)
from finance.services import AllocationInput, compute_allocations


class ExpenseViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["title", "description"]
    filterset_fields = ["building", "status", "category", "allocation_method"]
    ordering_fields = ["expense_date", "due_date", "amount", "created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ExpenseWriteSerializer
        return ExpenseSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.select_related("building", "created_by").prefetch_related("included_units")
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        unit_ids = user_unit_ids(user)
        return qs.filter(
            Q(building_id__in=manager_ids)
            | Q(status=Expense.Status.FINALIZED, included_units__id__in=unit_ids)
        ).distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        building = serializer.validated_data["building"]
        if not is_manager_of(request.user, building.id):
            raise PermissionDenied("فقط مدیر می‌تواند هزینه ثبت کند.")
        included_ids = serializer.validated_data.pop("included_unit_ids", [])
        serializer.validated_data.pop("custom_shares", None)
        expense = serializer.save(created_by=request.user, status=Expense.Status.DRAFT)
        if included_ids:
            units = Unit.objects.filter(building=building, id__in=included_ids)
            expense.included_units.set(units)
        audit(
            request,
            action="expense.create",
            entity_type="Expense",
            entity_id=expense.id,
            building=building,
            changes={"title": expense.title, "amount": expense.amount},
        )
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        expense = self.get_object()
        if not is_manager_of(request.user, expense.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if expense.status != Expense.Status.DRAFT:
            raise ValidationError("فقط هزینه پیش‌نویس قابل ویرایش است.")
        serializer = self.get_serializer(expense, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        included_ids = serializer.validated_data.pop("included_unit_ids", None)
        serializer.validated_data.pop("custom_shares", None)
        expense = serializer.save()
        if included_ids is not None:
            units = Unit.objects.filter(building=expense.building, id__in=included_ids)
            expense.included_units.set(units)
        return Response(ExpenseSerializer(expense).data)

    def destroy(self, request, *args, **kwargs):
        expense = self.get_object()
        if not is_manager_of(request.user, expense.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if expense.status == Expense.Status.FINALIZED:
            raise ValidationError("هزینه نهایی‌شده قابل حذف نیست. از ابطال استفاده کنید.")
        return super().destroy(request, *args, **kwargs)

    def _preview_data(self, expense, custom_shares=None):
        units = list(expense.included_units.filter(is_active=True))
        if not units:
            raise ValidationError("حداقل یک واحد مشمول باید انتخاب شود.")
        items = [
            AllocationInput(
                unit_id=u.id,
                resident_count=u.resident_count,
                area_sqm=u.area_sqm,
                custom_amount=(custom_shares or {}).get(str(u.id), (custom_shares or {}).get(u.id)),
            )
            for u in units
        ]
        amounts = compute_allocations(expense.allocation_method, expense.amount, items)
        unit_map = {u.id: u for u in units}
        preview = []
        for unit_id, amount in amounts.items():
            u = unit_map[unit_id]
            preview.append(
                {
                    "unit_id": unit_id,
                    "unit_number": u.number,
                    "amount": amount,
                    "resident_count": u.resident_count,
                    "area_sqm": u.area_sqm,
                }
            )
        preview.sort(key=lambda x: x["unit_number"])
        return {
            "expense_id": expense.id,
            "total": expense.amount,
            "method": expense.allocation_method,
            "sum": sum(p["amount"] for p in preview),
            "items": preview,
        }

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        expense = self.get_object()
        if not is_manager_of(request.user, expense.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        custom_shares = request.data.get("custom_shares")
        # allow updating method/units before preview
        if "allocation_method" in request.data:
            if expense.status != Expense.Status.DRAFT:
                raise ValidationError("فقط پیش‌نویس قابل تغییر است.")
            expense.allocation_method = request.data["allocation_method"]
            expense.save(update_fields=["allocation_method", "updated_at"])
        if "included_unit_ids" in request.data:
            if expense.status != Expense.Status.DRAFT:
                raise ValidationError("فقط پیش‌نویس قابل تغییر است.")
            ids = request.data["included_unit_ids"]
            units = Unit.objects.filter(building=expense.building, id__in=ids)
            expense.included_units.set(units)
        try:
            data = self._preview_data(expense, custom_shares)
        except ValueError as exc:
            raise ValidationError(str(exc))
        return Response(data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def finalize(self, request, pk=None):
        expense = (
            Expense.objects.select_for_update()
            .prefetch_related("included_units")
            .get(pk=pk)
        )
        if not is_manager_of(request.user, expense.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if expense.status != Expense.Status.DRAFT:
            raise ValidationError("این هزینه قبلاً نهایی شده یا باطل است.")
        custom_shares = request.data.get("custom_shares")
        try:
            preview = self._preview_data(expense, custom_shares)
        except ValueError as exc:
            raise ValidationError(str(exc))

        ExpenseAllocation.objects.filter(expense=expense).delete()
        unit_map = {u.id: u for u in expense.included_units.all()}
        allocations = []
        for item in preview["items"]:
            u = unit_map[item["unit_id"]]
            allocations.append(
                ExpenseAllocation(
                    expense=expense,
                    unit=u,
                    amount=item["amount"],
                    snapshot_resident_count=u.resident_count,
                    snapshot_area_sqm=u.area_sqm,
                    status=ExpenseAllocation.Status.UNPAID,
                )
            )
        ExpenseAllocation.objects.bulk_create(allocations)
        expense.status = Expense.Status.FINALIZED
        expense.finalized_at = timezone.now()
        expense.finalized_by = request.user
        expense.save()

        audit(
            request,
            action="expense.finalize",
            entity_type="Expense",
            entity_id=expense.id,
            building=expense.building,
            changes={"amount": expense.amount, "allocations": len(allocations)},
        )
        notify_building_members(
            building=expense.building,
            title="هزینه جدید ثبت شد",
            body=f"{expense.title} به مبلغ {expense.amount:,} تومان نهایی شد.",
            type=Notification.Type.EXPENSE,
            link=f"/expenses/{expense.id}",
            exclude_user=request.user,
        )
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        expense = self.get_object()
        if not is_manager_of(request.user, expense.building_id):
            raise PermissionDenied("دسترسی غیرمجاز.")
        if expense.status == Expense.Status.CANCELLED:
            raise ValidationError("قبلاً باطل شده است.")
        if expense.allocations.filter(payments__status=Payment.Status.APPROVED).exists():
            raise ValidationError("هزینه‌ای که پرداخت تأییدشده دارد قابل ابطال نیست.")
        expense.status = Expense.Status.CANCELLED
        expense.save(update_fields=["status", "updated_at"])
        audit(
            request,
            action="expense.cancel",
            entity_type="Expense",
            entity_id=expense.id,
            building=expense.building,
        )
        return Response(ExpenseSerializer(expense).data)


class ExpenseAllocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExpenseAllocationSerializer
    filterset_fields = ["expense", "unit", "status"]
    ordering_fields = ["amount", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = ExpenseAllocation.objects.select_related("expense", "unit", "expense__building")
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        return qs.filter(
            Q(expense__building_id__in=manager_ids) | Q(unit_id__in=user_unit_ids(user))
        ).distinct()


class PaymentViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    serializer_class = PaymentSerializer
    filterset_fields = ["status", "allocation"]
    ordering_fields = ["created_at", "amount"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related(
            "allocation",
            "allocation__unit",
            "allocation__expense",
            "submitted_by",
            "receipt",
        )
        if user.is_superuser:
            return qs
        manager_ids = managed_building_ids(user)
        return qs.filter(
            Q(allocation__expense__building_id__in=manager_ids)
            | Q(allocation__unit_id__in=user_unit_ids(user))
        ).distinct()

    def create(self, request, *args, **kwargs):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            allocation = ExpenseAllocation.objects.select_related(
                "expense", "unit", "expense__building"
            ).get(id=data["allocation_id"])
        except ExpenseAllocation.DoesNotExist:
            raise ValidationError({"allocation_id": "بدهی یافت نشد."})

        if not can_access_unit(request.user, allocation.unit):
            raise PermissionDenied("شما به این واحد دسترسی ندارید.")
        if allocation.expense.status != Expense.Status.FINALIZED:
            raise ValidationError("فقط برای هزینه‌های نهایی‌شده می‌توان پرداخت ثبت کرد.")

        remaining = allocation.remaining
        if data["amount"] > remaining:
            raise ValidationError({"amount": f"مبلغ نباید از مانده ({remaining:,} تومان) بیشتر باشد."})

        receipt_file = data["receipt"]
        validate_upload(receipt_file)
        receipt_file.name = safe_upload_name(receipt_file.name)

        with transaction.atomic():
            payment = Payment.objects.create(
                allocation=allocation,
                amount=data["amount"],
                description=data.get("description", ""),
                status=Payment.Status.PENDING,
                submitted_by=request.user,
            )
            PaymentReceipt.objects.create(
                payment=payment,
                file=receipt_file,
                original_name=getattr(data["receipt"], "name", ""),
            )
        audit(
            request,
            action="payment.submit",
            entity_type="Payment",
            entity_id=payment.id,
            building=allocation.expense.building,
            changes={"amount": payment.amount},
        )
        from buildings.models import Membership

        managers = Membership.objects.filter(
            building=allocation.expense.building,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
        )
        for m in managers:
            notify_user(
                user=m.user,
                title="رسید جدید برای بررسی",
                body=f"پرداخت {payment.amount:,} تومان برای واحد {allocation.unit.number}",
                type=Notification.Type.PAYMENT,
                building=allocation.expense.building,
                link="/payments",
            )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def review(self, request, pk=None):
        payment = Payment.objects.select_for_update().select_related(
            "allocation",
            "allocation__expense",
            "allocation__unit",
            "allocation__expense__building",
        ).get(pk=pk)
        if not is_manager_of(request.user, payment.allocation.expense.building_id):
            raise PermissionDenied("فقط مدیر می‌تواند رسید را بررسی کند.")
        if payment.status != Payment.Status.PENDING:
            raise ValidationError("این پرداخت قبلاً بررسی شده است.")

        serializer = PaymentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_name = serializer.validated_data["action"]

        allocation = ExpenseAllocation.objects.select_for_update().get(pk=payment.allocation_id)

        if action_name == "approve":
            remaining = allocation.remaining
            if payment.amount > remaining:
                raise ValidationError("مبلغ پرداخت از مانده بدهی بیشتر است.")
            payment.status = Payment.Status.APPROVED
            payment.reviewed_by = request.user
            payment.reviewed_at = timezone.now()
            payment.save()
            allocation.refresh_status()
            audit(
                request,
                action="payment.approve",
                entity_type="Payment",
                entity_id=payment.id,
                building=allocation.expense.building,
                changes={"amount": payment.amount},
            )
            notify_user(
                user=payment.submitted_by,
                title="پرداخت تأیید شد",
                body=f"پرداخت {payment.amount:,} تومان تأیید شد.",
                type=Notification.Type.PAYMENT,
                building=allocation.expense.building,
                link="/payments",
            )
        else:
            reason = serializer.validated_data.get("rejection_reason", "").strip()
            if not reason:
                raise ValidationError({"rejection_reason": "دلیل رد الزامی است."})
            payment.status = Payment.Status.REJECTED
            payment.rejection_reason = reason
            payment.reviewed_by = request.user
            payment.reviewed_at = timezone.now()
            payment.save()
            audit(
                request,
                action="payment.reject",
                entity_type="Payment",
                entity_id=payment.id,
                building=allocation.expense.building,
                changes={"reason": reason},
            )
            notify_user(
                user=payment.submitted_by,
                title="پرداخت رد شد",
                body=f"پرداخت رد شد: {reason}",
                type=Notification.Type.PAYMENT,
                building=allocation.expense.building,
                link="/payments",
            )
        return Response(PaymentSerializer(payment).data)