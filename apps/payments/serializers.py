"""
Serializers for payment system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import (
    PaymentMethod, PaymentAccount, Payment, PaymentSplit,
    Refund, Wallet, WalletTransaction, PaymentIntent
)

User = get_user_model()


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods."""
    
    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'method_type_display', 'card_last4', 'card_brand',
            'card_exp_month', 'card_exp_year', 'bank_name', 'account_last4',
            'is_active', 'is_default', 'is_verified', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified']
    
    def get_is_expired(self, obj):
        """Check if card is expired."""
        if obj.method_type == 'card' and obj.card_exp_month and obj.card_exp_year:
            from datetime import date
            current_date = date.today()
            return (obj.card_exp_year < current_date.year or 
                   (obj.card_exp_year == current_date.year and obj.card_exp_month < current_date.month))
        return False


class PaymentAccountSerializer(serializers.ModelSerializer):
    """Serializer for payment accounts."""
    
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentAccount
        fields = [
            'id', 'account_type', 'account_type_display', 'status', 'status_display',
            'bank_name', 'account_holder_name', 'is_verified',
            'can_receive_payments', 'can_instant_payout',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'is_verified', 'can_receive_payments', 'can_instant_payout',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'iban': {'write_only': True},
            'swift_code': {'write_only': True},
            'stripe_account_id': {'write_only': True},
            'paypal_account_email': {'write_only': True}
        }


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer for payment list view."""
    
    payer_email = serializers.CharField(source='payer.email', read_only=True)
    payee_email = serializers.CharField(source='payee.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'internal_reference', 'payer_email', 'payee_email',
            'amount', 'currency', 'payment_type', 'payment_type_display',
            'status', 'status_display', 'platform_fee', 'payment_processor_fee',
            'net_amount', 'processed_at', 'created_at'
        ]


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed payment view."""
    
    payer = serializers.StringRelatedField()
    payee = serializers.StringRelatedField()
    payment_method = PaymentMethodSerializer(read_only=True)
    payment_account = PaymentAccountSerializer(read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    total_fees = serializers.ReadOnlyField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'internal_reference', 'external_id', 'payer', 'payee',
            'amount', 'currency', 'payment_type', 'payment_type_display',
            'status', 'status_display', 'payment_method', 'payment_account',
            'platform_fee', 'payment_processor_fee', 'net_amount', 'total_fees',
            'description', 'processed_at', 'failed_at', 'refunded_at',
            'failure_reason', 'failure_code', 'metadata',
            'created_at', 'updated_at'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""
    
    payee_email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = Payment
        fields = [
            'payee_email', 'amount', 'currency', 'payment_type',
            'payment_method', 'description', 'metadata'
        ]
    
    def validate_amount(self, value):
        """Validate payment amount."""
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be greater than zero.")
        if value > Decimal('10000.00'):
            raise serializers.ValidationError("Amount cannot exceed €10,000.")
        return value
    
    def create(self, validated_data):
        """Create payment with proper payee lookup."""
        payee_email = validated_data.pop('payee_email', None)
        
        if payee_email:
            try:
                payee = User.objects.get(email=payee_email)
                validated_data['payee'] = payee
            except User.DoesNotExist:
                raise serializers.ValidationError("Payee user not found.")
        
        # Set payer from request context
        validated_data['payer'] = self.context['request'].user
        
        return super().create(validated_data)


class PaymentSplitSerializer(serializers.ModelSerializer):
    """Serializer for payment splits."""
    
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    split_type_display = serializers.CharField(source='get_split_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentSplit
        fields = [
            'id', 'recipient_email', 'amount', 'percentage',
            'split_type', 'split_type_display', 'status', 'status_display',
            'processed_at', 'created_at'
        ]


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds."""
    
    payment_reference = serializers.CharField(source='payment.internal_reference', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    initiated_by_email = serializers.CharField(source='initiated_by.email', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment_reference', 'amount', 'reason', 'reason_display',
            'status', 'status_display', 'initiated_by_email', 'description',
            'processed_at', 'failed_at', 'failure_reason', 'created_at'
        ]


class RefundCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating refunds."""
    
    class Meta:
        model = Refund
        fields = ['amount', 'reason', 'description']
    
    def validate_amount(self, value):
        """Validate refund amount."""
        payment = self.context['payment']
        if value > payment.amount:
            raise serializers.ValidationError("Refund amount cannot exceed payment amount.")
        
        # Check existing refunds
        existing_refunds = payment.refunds.filter(status='succeeded').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if existing_refunds + value > payment.amount:
            raise serializers.ValidationError("Total refunds cannot exceed payment amount.")
        
        return value


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user_email', 'balance', 'available_balance', 'pending_balance',
            'is_active', 'is_frozen', 'daily_spend_limit', 'monthly_spend_limit',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'balance', 'available_balance', 'pending_balance',
            'created_at', 'updated_at'
        ]


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions."""
    
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'amount', 'transaction_type', 'transaction_type_display',
            'description', 'balance_after', 'external_reference', 'created_at'
        ]


class PaymentIntentSerializer(serializers.ModelSerializer):
    """Serializer for payment intents."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'external_intent_id', 'client_secret', 'user_email',
            'amount', 'currency', 'status', 'status_display',
            'capture_method', 'description', 'created_at'
        ]
        read_only_fields = [
            'id', 'external_intent_id', 'client_secret', 'status',
            'created_at'
        ]


class PaymentIntentCreateSerializer(serializers.Serializer):
    """Serializer for creating payment intents."""
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.50'))
    currency = serializers.CharField(default='EUR', max_length=3)
    booking_id = serializers.UUIDField(required=False)
    description = serializers.CharField(max_length=500, required=False)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_amount(self, value):
        """Validate payment intent amount."""
        if value > Decimal('10000.00'):
            raise serializers.ValidationError("Amount cannot exceed €10,000.")
        return value


class PaymentStatsSerializer(serializers.Serializer):
    """Serializer for payment statistics."""
    
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    refunds_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Monthly breakdown
    monthly_paid = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    monthly_received = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Wallet info
    wallet_balance = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    wallet_pending = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class StripeConnectSerializer(serializers.Serializer):
    """Serializer for Stripe Connect account creation."""
    
    account_type = serializers.ChoiceField(choices=['express', 'standard'], default='express')
    business_type = serializers.ChoiceField(choices=['individual', 'company'], default='individual')
    
    # Individual info
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    
    # Address info
    country = serializers.CharField(max_length=2, default='PT')
    city = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    address_line1 = serializers.CharField(max_length=200, required=False)


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for webhook events."""
    
    event_type = serializers.CharField(max_length=100)
    event_id = serializers.CharField(max_length=200)
    object_id = serializers.CharField(max_length=200)
    object_type = serializers.CharField(max_length=50)
    data = serializers.JSONField()
    
    def validate_event_type(self, value):
        """Validate supported event types."""
        supported_events = [
            'payment_intent.succeeded',
            'payment_intent.payment_failed',
            'charge.dispute.created',
            'invoice.payment_succeeded',
            'customer.subscription.created',
            'account.updated',
            'transfer.created',
        ]
        
        if value not in supported_events:
            raise serializers.ValidationError(f"Unsupported event type: {value}")
        
        return value