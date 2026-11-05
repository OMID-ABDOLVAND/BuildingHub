from rest_framework import serializers

from finance.models import Expense, ExpenseAllocation, Payment, PaymentReceipt


class ExpenseSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    included_unit_ids = serializers.SerializerMethodField()
    allocations_count = serializers.IntegerField(source="allocations.count", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "building",
            "title",
            "description",
            "category",
            "amount",
            "expense_date",
            "due_date",
            "invoice_image",
            "allocation_method",
            "status",
            "created_by",
            "created_by_name",
            "finalized_at",
            "finalized_by",
            "included_unit_ids",
            "maintenance_request",
            "allocations_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "finalized_at",
            "finalized_by",
            "created_at",
            "updated_at",
        ]

    def get_included_unit_ids(self, obj):
        return list(obj.included_units.values_list("id", flat=True))


class ExpenseWriteSerializer(serializers.ModelSerializer):
    included_unit_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )
    custom_shares = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Expense
        fields = [
            "building",
            "title",
            "description",
            "category",
            "amount",
            "expense_date",
            "due_date",
            "invoice_image",
            "allocation_method",
            "included_unit_ids",
            "custom_shares",
            "maintenance_request",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        return value


class AllocationPreviewItemSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField()
    unit_number = serializers.CharField()
    amount = serializers.IntegerField()
    resident_count = serializers.IntegerField()
    area_sqm = serializers.IntegerField()


class ExpenseAllocationSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.number", read_only=True)
    expense_title = serializers.CharField(source="expense.title", read_only=True)
    expense_due_date = serializers.DateField(source="expense.due_date", read_only=True)
    approved_paid = serializers.IntegerField(read_only=True)
    remaining = serializers.IntegerField(read_only=True)
    building = serializers.IntegerField(source="expense.building_id", read_only=True)

    class Meta:
        model = ExpenseAllocation
        fields = [
            "id",
            "expense",
            "expense_title",
            "expense_due_date",
            "unit",
            "unit_number",
            "building",
            "amount",
            "snapshot_resident_count",
            "snapshot_area_sqm",
            "status",
            "approved_paid",
            "remaining",
            "created_at",
            "updated_at",
        ]


class PaymentReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReceipt
        fields = ["id", "file", "original_name", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    receipt = PaymentReceiptSerializer(read_only=True)
    submitted_by_name = serializers.CharField(source="submitted_by.get_full_name", read_only=True)
    unit_number = serializers.CharField(source="allocation.unit.number", read_only=True)
    expense_title = serializers.CharField(source="allocation.expense.title", read_only=True)
    allocation_remaining = serializers.IntegerField(source="allocation.remaining", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "allocation",
            "amount",
            "description",
            "status",
            "submitted_by",
            "submitted_by_name",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "receipt",
            "unit_number",
            "expense_title",
            "allocation_remaining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(serializers.Serializer):
    allocation_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)
    description = serializers.CharField(required=False, allow_blank=True)
    receipt = serializers.FileField()


class PaymentReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)