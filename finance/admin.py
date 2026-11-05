from django.contrib import admin

from finance.models import Expense, ExpenseAllocation, Payment, PaymentReceipt


class AllocationInline(admin.TabularInline):
    model = ExpenseAllocation
    extra = 0
    readonly_fields = ("unit", "amount", "snapshot_resident_count", "snapshot_area_sqm", "status")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "building", "amount", "status", "allocation_method", "due_date")
    list_filter = ("status", "allocation_method", "category")
    inlines = [AllocationInline]


@admin.register(ExpenseAllocation)
class ExpenseAllocationAdmin(admin.ModelAdmin):
    list_display = ("expense", "unit", "amount", "status")
    list_filter = ("status",)


class ReceiptInline(admin.StackedInline):
    model = PaymentReceipt
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "allocation", "amount", "status", "submitted_by", "created_at")
    list_filter = ("status",)
    inlines = [ReceiptInline]