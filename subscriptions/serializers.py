from rest_framework import serializers

from accounts.serializers import UserSerializer
from buildings.models import Building
from buildings.serializers import BuildingSerializer
from subscriptions.models import (
    PlatformSettings,
    Subscription,
    SubscriptionHistory,
    SubscriptionPayment,
    SubscriptionPaymentReceipt,
    SubscriptionPlan,
    SubscriptionPlanPricing,
)


class SubscriptionPlanPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlanPricing
        fields = ["id", "duration", "price_toman", "is_active", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    pricings = SubscriptionPlanPricingSerializer(many=True, read_only=True)
    monthly_price = serializers.SerializerMethodField()
    yearly_price = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "description",
            "min_apartments",
            "max_apartments",
            "monthly_features",
            "yearly_features",
            "is_active",
            "display_order",
            "pricings",
            "monthly_price",
            "yearly_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_monthly_price(self, obj):
        p = obj.pricings.filter(duration=SubscriptionPlanPricing.Duration.MONTHLY, is_active=True).first()
        return p.price_toman if p else None

    def get_yearly_price(self, obj):
        p = obj.pricings.filter(duration=SubscriptionPlanPricing.Duration.YEARLY, is_active=True).first()
        return p.price_toman if p else None


class SubscriptionPlanWriteSerializer(serializers.ModelSerializer):
    monthly_price = serializers.IntegerField(write_only=True, required=False, min_value=0)
    yearly_price = serializers.IntegerField(write_only=True, required=False, min_value=0)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "description",
            "min_apartments",
            "max_apartments",
            "monthly_features",
            "yearly_features",
            "is_active",
            "display_order",
            "monthly_price",
            "yearly_price",
        ]

    def create(self, validated_data):
        monthly = validated_data.pop("monthly_price", None)
        yearly = validated_data.pop("yearly_price", None)
        plan = SubscriptionPlan.objects.create(**validated_data)
        if monthly is not None:
            SubscriptionPlanPricing.objects.create(
                plan=plan,
                duration=SubscriptionPlanPricing.Duration.MONTHLY,
                price_toman=monthly,
            )
        if yearly is not None:
            SubscriptionPlanPricing.objects.create(
                plan=plan,
                duration=SubscriptionPlanPricing.Duration.YEARLY,
                price_toman=yearly,
            )
        return plan

    def update(self, instance, validated_data):
        monthly = validated_data.pop("monthly_price", None)
        yearly = validated_data.pop("yearly_price", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if monthly is not None:
            SubscriptionPlanPricing.objects.update_or_create(
                plan=instance,
                duration=SubscriptionPlanPricing.Duration.MONTHLY,
                defaults={"price_toman": monthly, "is_active": True},
            )
        if yearly is not None:
            SubscriptionPlanPricing.objects.update_or_create(
                plan=instance,
                duration=SubscriptionPlanPricing.Duration.YEARLY,
                defaults={"price_toman": yearly, "is_active": True},
            )
        return instance


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            "grace_period_days",
            "destination_card_number",
            "cardholder_name",
            "bank_name",
            "payment_instructions",
            "support_email",
            "support_phone",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionHistory
        fields = [
            "id",
            "event_type",
            "message",
            "metadata",
            "actor",
            "actor_name",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        return obj.actor.get_full_name() or obj.actor.username


class SubscriptionPaymentReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPaymentReceipt
        fields = ["id", "file", "original_name", "created_at"]


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    receipt = SubscriptionPaymentReceiptSerializer(read_only=True)
    building_name = serializers.CharField(source="subscription.building.name", read_only=True)
    plan_name = serializers.CharField(source="subscription.plan_name_snapshot", read_only=True)

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id",
            "subscription",
            "amount_toman",
            "payer_name",
            "tracking_number",
            "payment_date",
            "description",
            "status",
            "rejection_reason",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "approved_at",
            "receipt",
            "building_name",
            "plan_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "rejection_reason",
            "submitted_by",
            "reviewed_by",
            "reviewed_at",
            "approved_at",
            "created_at",
            "updated_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    building_detail = BuildingSerializer(source="building", read_only=True)
    history = SubscriptionHistorySerializer(many=True, read_only=True)
    latest_payment = serializers.SerializerMethodField()
    management_allowed = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "building",
            "building_detail",
            "plan",
            "plan_name_snapshot",
            "duration",
            "status",
            "apartment_capacity_snapshot",
            "price_snapshot_toman",
            "discount_toman",
            "final_price_toman",
            "is_free",
            "starts_at",
            "expires_at",
            "grace_ends_at",
            "activated_at",
            "notes",
            "history",
            "latest_payment",
            "management_allowed",
            "created_at",
            "updated_at",
        ]

    def get_latest_payment(self, obj):
        payment = obj.payments.order_by("-created_at").first()
        if not payment:
            return None
        return SubscriptionPaymentSerializer(payment).data

    def get_management_allowed(self, obj):
        from core.permissions import building_management_allowed

        return building_management_allowed(obj.building)


class ManagerRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "رمز عبور و تکرار آن یکسان نیستند."})
        validate_password(attrs["password"])
        return attrs


class OnboardingBuildingSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    address = serializers.CharField()
    floors_count = serializers.IntegerField(min_value=0)
    apartments_count = serializers.IntegerField(min_value=1)
    description = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)


class SelectPlanSerializer(serializers.Serializer):
    building_id = serializers.IntegerField()
    plan_id = serializers.IntegerField(required=False)
    duration = serializers.ChoiceField(choices=Subscription.Duration.choices)


class SubmitSubscriptionPaymentSerializer(serializers.Serializer):
    subscription_id = serializers.IntegerField()
    amount_toman = serializers.IntegerField(min_value=1)
    payer_name = serializers.CharField(max_length=120)
    tracking_number = serializers.CharField(max_length=100)
    payment_date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True)


class RejectPaymentSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField()


class GrantFreeSerializer(serializers.Serializer):
    building_id = serializers.IntegerField()
    plan_id = serializers.IntegerField(required=False)
    duration = serializers.ChoiceField(choices=Subscription.Duration.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class ExtendSubscriptionSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=3650)
