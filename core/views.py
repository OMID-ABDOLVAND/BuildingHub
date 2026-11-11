from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from buildings.models import Building, Unit, UnitOccupancy
from communications.models import Announcement, Notification
from core.models import AuditLog
from core.permissions import (
    can_access_unit,
    is_manager_of,
    managed_building_ids,
    resident_building_ids,
    user_unit_ids,
)
from finance.models import Expense, ExpenseAllocation, Payment, PaymentReceipt
from maintenance.models import MaintenanceRequest


class AuditLogView(APIView):
    def get(self, request):
        qs = AuditLog.objects.select_related("user", "building")
        if not request.user.is_superuser:
            qs = qs.filter(building_id__in=managed_building_ids(request.user))
        building = request.query_params.get("building")
        if building:
            qs = qs.filter(building_id=building)
        data = [
            {
                "id": a.id,
                "user": a.user.get_full_name() if a.user else None,
                "building": a.building_id,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "changes": a.changes,
                "created_at": a.created_at,
            }
            for a in qs[:100]
        ]
        return Response({"results": data})


class ManagerDashboardView(APIView):
    def get(self, request):
        building_id = request.query_params.get("building")
        manager_ids = managed_building_ids(request.user)
        if request.user.is_superuser and building_id:
            building_ids = [int(building_id)]
        elif building_id:
            bid = int(building_id)
            if bid not in manager_ids and not request.user.is_superuser:
                return Response({"detail": "دسترسی غیرمجاز."}, status=403)
            building_ids = [bid]
        else:
            building_ids = list(manager_ids)

        expenses = Expense.objects.filter(building_id__in=building_ids, status=Expense.Status.FINALIZED)
        allocations = ExpenseAllocation.objects.filter(expense__building_id__in=building_ids)
        payments = Payment.objects.filter(
            allocation__expense__building_id__in=building_ids,
            status=Payment.Status.APPROVED,
        )
        open_maint = MaintenanceRequest.objects.filter(
            building_id__in=building_ids,
        ).exclude(
            status__in=[
                MaintenanceRequest.Status.RESOLVED,
                MaintenanceRequest.Status.REJECTED,
            ]
        )
        return Response(
            {
                "total_expenses": expenses.aggregate(t=Sum("amount"))["t"] or 0,
                "total_approved_payments": payments.aggregate(t=Sum("amount"))["t"] or 0,
                "total_outstanding": sum(a.remaining for a in allocations),
                "total_overdue": sum(
                    a.remaining
                    for a in allocations.filter(status=ExpenseAllocation.Status.OVERDUE)
                ),
                "units_count": Unit.objects.filter(building_id__in=building_ids, is_active=True).count(),
                "residents_count": UnitOccupancy.objects.filter(
                    unit__building_id__in=building_ids, is_current=True
                )
                .values("user")
                .distinct()
                .count(),
                "open_maintenance": open_maint.count(),
                "resolved_maintenance": MaintenanceRequest.objects.filter(
                    building_id__in=building_ids,
                    status=MaintenanceRequest.Status.RESOLVED,
                ).count(),
                "pending_payments": Payment.objects.filter(
                    allocation__expense__building_id__in=building_ids,
                    status=Payment.Status.PENDING,
                ).count(),
                "recent_expenses": list(
                    expenses.order_by("-created_at").values("id", "title", "amount", "expense_date")[:5]
                ),
                "recent_maintenance": list(
                    MaintenanceRequest.objects.filter(building_id__in=building_ids)
                    .order_by("-created_at")
                    .values("id", "title", "status", "tracking_code", "priority")[:5]
                ),
            }
        )


class ResidentDashboardView(APIView):
    def get(self, request):
        unit_ids = user_unit_ids(request.user)
        allocations = ExpenseAllocation.objects.filter(unit_id__in=unit_ids).select_related(
            "expense", "unit"
        )
        payments = Payment.objects.filter(
            allocation__unit_id__in=unit_ids, status=Payment.Status.APPROVED
        )
        occupancy = (
            UnitOccupancy.objects.filter(user=request.user, is_current=True)
            .select_related("unit", "unit__building")
            .first()
        )
        return Response(
            {
                "apartment": {
                    "unit_id": occupancy.unit_id if occupancy else None,
                    "number": occupancy.unit.number if occupancy else None,
                    "building": occupancy.unit.building.name if occupancy else None,
                    "floor": occupancy.unit.floor if occupancy else None,
                    "area_sqm": occupancy.unit.area_sqm if occupancy else None,
                }
                if occupancy
                else None,
                "outstanding_debts": sum(a.remaining for a in allocations),
                "total_paid": payments.aggregate(t=Sum("amount"))["t"] or 0,
                "upcoming_deadlines": [
                    {
                        "id": a.id,
                        "title": a.expense.title,
                        "due_date": a.expense.due_date,
                        "remaining": a.remaining,
                        "status": a.status,
                    }
                    for a in allocations.exclude(status=ExpenseAllocation.Status.PAID).order_by(
                        "expense__due_date"
                    )[:10]
                ],
                "recent_payments": list(
                    Payment.objects.filter(allocation__unit_id__in=unit_ids)
                    .order_by("-created_at")
                    .values("id", "amount", "status", "created_at")[:5]
                ),
                "my_maintenance": list(
                    MaintenanceRequest.objects.filter(unit_id__in=unit_ids)
                    .order_by("-created_at")
                    .values("id", "title", "status", "tracking_code")[:5]
                ),
                "recent_announcements": list(
                    Announcement.objects.filter(
                        building_id__in=resident_building_ids(request.user),
                        is_published=True,
                    )
                    .order_by("-created_at")
                    .values("id", "title", "created_at")[:5]
                ),
                "unread_notifications": Notification.objects.filter(
                    user=request.user, is_read=False
                ).count(),
            }
        )


class ReportsView(APIView):
    def get(self, request):
        building_id = request.query_params.get("building")
        if not building_id:
            return Response({"detail": "building الزامی است."}, status=400)
        bid = int(building_id)
        if not is_manager_of(request.user, bid) and not request.user.is_superuser:
            return Response({"detail": "دسترسی غیرمجاز."}, status=403)

        expenses = Expense.objects.filter(building_id=bid, status=Expense.Status.FINALIZED)
        by_category = list(
            expenses.values("category").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
        )
        allocations = ExpenseAllocation.objects.filter(expense__building_id=bid).select_related("unit")
        per_unit = {}
        for a in allocations:
            item = per_unit.setdefault(
                a.unit_id,
                {"unit": a.unit.number, "debt": 0, "paid": 0, "remaining": 0},
            )
            item["debt"] += a.amount
            item["paid"] += a.approved_paid
            item["remaining"] += a.remaining

        return Response(
            {
                "expenses_total": expenses.aggregate(t=Sum("amount"))["t"] or 0,
                "approved_payments": Payment.objects.filter(
                    allocation__expense__building_id=bid,
                    status=Payment.Status.APPROVED,
                ).aggregate(t=Sum("amount"))["t"]
                or 0,
                "by_category": by_category,
                "per_unit": list(per_unit.values()),
                "overdue_count": allocations.filter(status=ExpenseAllocation.Status.OVERDUE).count(),
            }
        )


class ProtectedMediaView(APIView):
    """Serve private media only to authorized users."""

    permission_classes = [IsAuthenticated]

    def get(self, request, kind, pk):
        if kind == "invoice":
            expense = get_object_or_404(Expense, pk=pk)
            if not (
                is_manager_of(request.user, expense.building_id)
                or expense.included_units.filter(id__in=user_unit_ids(request.user)).exists()
            ):
                raise Http404()
            if not expense.invoice_image:
                raise Http404()
            return FileResponse(expense.invoice_image.open("rb"), as_attachment=False)

        if kind == "receipt":
            payment = get_object_or_404(
                Payment.objects.select_related("allocation__unit", "allocation__expense", "receipt"),
                pk=pk,
            )
            unit = payment.allocation.unit
            if not can_access_unit(request.user, unit):
                raise Http404()
            try:
                receipt = payment.receipt
            except PaymentReceipt.DoesNotExist:
                raise Http404()
            if not receipt.file:
                raise Http404()
            filename = receipt.original_name or receipt.file.name
            return FileResponse(
                receipt.file.open("rb"),
                as_attachment=False,
                filename=filename,
            )

        if kind == "maintenance":
            req = get_object_or_404(MaintenanceRequest, pk=pk)
            if not (
                is_manager_of(request.user, req.building_id)
                or req.unit_id in user_unit_ids(request.user)
            ):
                raise Http404()
            if not req.image:
                raise Http404()
            return FileResponse(req.image.open("rb"), as_attachment=False)

        if kind == "subscription_receipt":
            from core.permissions import is_platform_super_admin
            from subscriptions.models import SubscriptionPayment

            payment = get_object_or_404(
                SubscriptionPayment.objects.select_related("subscription__building", "receipt"),
                pk=pk,
            )
            building = payment.subscription.building
            if not (
                is_platform_super_admin(request.user)
                or is_manager_of(request.user, building.id)
            ):
                raise Http404()
            try:
                receipt = payment.receipt
            except Exception:
                raise Http404()
            if not receipt.file:
                raise Http404()
            return FileResponse(
                receipt.file.open("rb"),
                as_attachment=False,
                filename=receipt.original_name or receipt.file.name,
            )

        raise Http404()