"""
Models for payment system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_HALF_UP
import uuid

from apps.core.models import BaseModel

User = get_user_model()


class PaymentMethod(BaseModel):
    """User's payment methods."""
    
    METHOD_TYPES = [
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('mbway', 'MB WAY'),
        ('multibanco', 'Multibanco'),
        ('wallet', 'Digital Wallet'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    
    # External provider info
    stripe_payment_method_id = models.CharField(max_length=200, blank=True)
    paypal_payer_id = models.CharField(max_length=200, blank=True)
    
    # Card info (last 4 digits, brand for display)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    card_exp_month = models.PositiveIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveIntegerField(null=True, blank=True)
    
    # Bank info
    bank_name = models.CharField(max_length=100, blank=True)
    account_last4 = models.CharField(max_length=4, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['stripe_payment_method_id']),
        ]
    
    def __str__(self):
        if self.method_type == 'card':
            return f"{self.card_brand} ****{self.card_last4}"
        return f"{self.get_method_type_display()}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default payment method per user."""
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user, is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentAccount(BaseModel):
    """Payment accounts for braiders to receive money."""
    
    ACCOUNT_TYPES = [
        ('stripe_account', 'Stripe Express Account'),
        ('bank_account', 'Bank Account'),
        ('paypal_account', 'PayPal Account'),
    ]
    
    ACCOUNT_STATUS = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('restricted', 'Restricted'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_accounts')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    status = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='pending')
    
    # External account info
    stripe_account_id = models.CharField(max_length=200, blank=True)
    paypal_account_email = models.EmailField(blank=True)
    
    # Bank account info
    bank_name = models.CharField(max_length=100, blank=True)
    account_holder_name = models.CharField(max_length=200, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    swift_code = models.CharField(max_length=11, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_documents = models.JSONField(default=dict)
    verification_notes = models.TextField(blank=True)
    
    # Capabilities
    can_receive_payments = models.BooleanField(default=False)
    can_instant_payout = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_account_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_account_type_display()}"


class Payment(BaseModel):
    """Individual payment transaction."""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_TYPES = [
        ('booking_payment', 'Booking Payment'),
        ('service_fee', 'Service Fee'),
        ('tip', 'Tip'),
        ('refund', 'Refund'),
        ('payout', 'Payout'),
        ('commission', 'Platform Commission'),
    ]
    
    # Payment identification
    external_id = models.CharField(max_length=200, blank=True, help_text="External payment ID (Stripe, PayPal, etc.)")
    internal_reference = models.CharField(max_length=50, unique=True, help_text="Internal payment reference")
    
    # Parties involved
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received', null=True, blank=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='EUR')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='booking_payment')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Payment method
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    payment_account = models.ForeignKey(PaymentAccount, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Related objects
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    
    # Fees and splits
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_processor_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timing
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    failure_reason = models.TextField(blank=True)
    failure_code = models.CharField(max_length=100, blank=True)
    
    # Metadata
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict)
    
    # External data
    provider_response = models.JSONField(default=dict, help_text="Response from payment provider")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payer', 'status']),
            models.Index(fields=['payee', 'status']),
            models.Index(fields=['booking']),
            models.Index(fields=['external_id']),
            models.Index(fields=['internal_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.internal_reference} - €{self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-generate internal reference and calculate fees."""
        if not self.internal_reference:
            self.internal_reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate net amount if not set
        if self.net_amount == Decimal('0.00'):
            self.net_amount = self.amount - self.platform_fee - self.payment_processor_fee
        
        super().save(*args, **kwargs)
    
    @property
    def total_fees(self):
        """Calculate total fees."""
        return self.platform_fee + self.payment_processor_fee
    
    def mark_as_succeeded(self, external_id=None, provider_response=None):
        """Mark payment as successful."""
        self.status = 'succeeded'
        self.processed_at = timezone.now()
        if external_id:
            self.external_id = external_id
        if provider_response:
            self.provider_response = provider_response
        self.save(update_fields=['status', 'processed_at', 'external_id', 'provider_response'])
    
    def mark_as_failed(self, reason=None, code=None):
        """Mark payment as failed."""
        self.status = 'failed'
        self.failed_at = timezone.now()
        if reason:
            self.failure_reason = reason
        if code:
            self.failure_code = code
        self.save(update_fields=['status', 'failed_at', 'failure_reason', 'failure_code'])


class PaymentSplit(BaseModel):
    """Payment splits for distributing money between parties."""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='splits')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_splits_received')
    
    # Split details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))])
    
    # Split type
    split_type = models.CharField(max_length=20, choices=[
        ('service_amount', 'Service Amount'),
        ('tip', 'Tip'),
        ('platform_fee', 'Platform Fee'),
        ('referral_bonus', 'Referral Bonus'),
    ], default='service_amount')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Transfer info
    transfer_id = models.CharField(max_length=200, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment']),
            models.Index(fields=['recipient', 'status']),
        ]
    
    def __str__(self):
        return f"Split €{self.amount} to {self.recipient.email}"


class Refund(BaseModel):
    """Payment refunds."""
    
    REFUND_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REFUND_REASONS = [
        ('requested_by_customer', 'Requested by Customer'),
        ('duplicate', 'Duplicate Payment'),
        ('fraudulent', 'Fraudulent'),
        ('service_not_provided', 'Service Not Provided'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('other', 'Other'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    
    # Refund details
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    reason = models.CharField(max_length=30, choices=REFUND_REASONS, default='requested_by_customer')
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    
    # External info
    external_refund_id = models.CharField(max_length=200, blank=True)
    
    # Timing
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Details
    description = models.TextField(blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='refunds_initiated')
    
    # Error handling
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['external_refund_id']),
        ]
    
    def __str__(self):
        return f"Refund €{self.amount} for {self.payment.internal_reference}"


class Wallet(BaseModel):
    """Digital wallet for users."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    
    # Balance
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    available_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)
    
    # Limits
    daily_spend_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    monthly_spend_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10000.00'))
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Wallet for {self.user.email} - €{self.available_balance}"
    
    def add_funds(self, amount, description="", transaction_type="credit"):
        """Add funds to wallet."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += amount
        self.available_balance += amount
        self.save(update_fields=['balance', 'available_balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.balance
        )
    
    def deduct_funds(self, amount, description="", transaction_type="debit"):
        """Deduct funds from wallet."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < amount:
            raise ValueError("Insufficient funds")
        
        self.balance -= amount
        self.available_balance -= amount
        self.save(update_fields=['balance', 'available_balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            amount=-amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.balance
        )
    
    def hold_funds(self, amount, description=""):
        """Hold funds (move from available to pending)."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.available_balance < amount:
            raise ValueError("Insufficient available funds")
        
        self.available_balance -= amount
        self.pending_balance += amount
        self.save(update_fields=['available_balance', 'pending_balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type="hold",
            description=description,
            balance_after=self.balance
        )
    
    def release_hold(self, amount, description=""):
        """Release held funds back to available."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.pending_balance < amount:
            raise ValueError("Insufficient pending funds")
        
        self.available_balance += amount
        self.pending_balance -= amount
        self.save(update_fields=['available_balance', 'pending_balance'])
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type="release",
            description=description,
            balance_after=self.balance
        )


class WalletTransaction(BaseModel):
    """Wallet transaction history."""
    
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('hold', 'Hold'),
        ('release', 'Release'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('refund', 'Refund'),
        ('fee', 'Fee'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=500)
    
    # Balance tracking
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Related objects
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    refund = models.ForeignKey(Refund, on_delete=models.SET_NULL, null=True, blank=True)
    
    # External reference
    external_reference = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type.title()} €{abs(self.amount)} - {self.description}"


class PaymentIntent(BaseModel):
    """Payment intent for processing payments."""
    
    INTENT_STATUS = [
        ('requires_payment_method', 'Requires Payment Method'),
        ('requires_confirmation', 'Requires Confirmation'),
        ('requires_action', 'Requires Action'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    # Intent identification
    external_intent_id = models.CharField(max_length=200, blank=True)
    client_secret = models.CharField(max_length=500, blank=True)
    
    # Payment details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_intents')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, default='EUR')
    
    # Status
    status = models.CharField(max_length=30, choices=INTENT_STATUS, default='requires_payment_method')
    
    # Related objects
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name='intent')
    
    # Configuration
    automatic_payment_methods = models.BooleanField(default=True)
    capture_method = models.CharField(max_length=20, default='automatic', choices=[
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ])
    
    # Metadata
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['external_intent_id']),
            models.Index(fields=['booking']),
        ]
    
    def __str__(self):
        return f"Payment Intent €{self.amount} - {self.status}"