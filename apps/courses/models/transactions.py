"""
Transaction and payment models.

This module contains models for handling course purchases, payments,
and financial transactions.
"""

from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel
from apps.users.models import User

from .base import TransactionChoices, TimestampedModelMixin, MetadataModelMixin


class Transaction(BaseModel, TimestampedModelMixin, MetadataModelMixin):
    """
    Transaction model for course purchases - maps from Express Transaction model.
    """
    
    # Transaction status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Keep same field names as Express for easier migration
    transactionId = models.CharField(
        max_length=255,
        unique=True,
        help_text="External transaction ID from payment provider"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    dateTime = models.DateTimeField(
        auto_now_add=True,
        help_text="Transaction timestamp"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Transaction amount"
    )
    
    currency = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Transaction currency code"
    )
    
    paymentProvider = models.CharField(
        max_length=20,
        choices=TransactionChoices.PROVIDER_CHOICES,
        default='stripe',
        help_text="Payment provider used"
    )
    
    # Enhanced transaction tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current transaction status"
    )
    
    payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Payment intent ID from payment provider"
    )
    
    # Fee tracking
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Platform fee amount"
    )
    
    payment_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Payment provider fee"
    )
    
    # Refund tracking
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Amount refunded (if any)"
    )
    
    refunded_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the refund was processed"
    )
    
    refund_reason = models.TextField(
        blank=True,
        help_text="Reason for refund"
    )
    
    # Additional tracking
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="IP address of the transaction"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['dateTime']),
            models.Index(fields=['transactionId']),
            models.Index(fields=['status']),
            models.Index(fields=['paymentProvider']),
            # Composite indexes for common queries
            models.Index(fields=['status', 'dateTime']),
            models.Index(fields=['user', 'status']),
        ]
        ordering = ['-dateTime']
    
    def __str__(self):
        return f"Transaction {self.transactionId} - {self.user.name} - {self.course.title}"
    
    def is_successful(self):
        """Check if the transaction was successful."""
        return self.status == 'completed'
    
    def is_refundable(self):
        """Check if the transaction can be refunded."""
        return (self.status == 'completed' and 
                self.refunded_amount < self.amount)
    
    def get_net_amount(self):
        """Get the net amount after fees."""
        return self.amount - self.platform_fee - self.payment_fee
    
    def get_refundable_amount(self):
        """Get the amount that can still be refunded."""
        return self.amount - self.refunded_amount
    
    def mark_completed(self, provider_transaction_id=None):
        """Mark the transaction as completed."""
        self.status = 'completed'
        if provider_transaction_id:
            self.set_metadata('provider_transaction_id', provider_transaction_id)
        self.save(update_fields=['status'])
        
        # Create enrollment if it doesn't exist
        from .enrollment import CourseEnrollment
        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=self.user,
            course=self.course,
            defaults={'enrollment_source': 'purchase'}
        )
        
        return enrollment
    
    def mark_failed(self, failure_reason=None):
        """Mark the transaction as failed."""
        self.status = 'failed'
        if failure_reason:
            self.set_metadata('failure_reason', failure_reason)
        self.save(update_fields=['status'])
    
    def process_refund(self, amount, reason=""):
        """Process a partial or full refund."""
        if not self.is_refundable():
            raise ValueError("Transaction is not refundable")
        
        if amount > self.get_refundable_amount():
            raise ValueError("Refund amount exceeds refundable amount")
        
        from django.utils import timezone
        
        self.refunded_amount += amount
        self.refunded_at = timezone.now()
        self.refund_reason = reason
        
        # Update status if fully refunded
        if self.refunded_amount >= self.amount:
            self.status = 'refunded'
        
        self.save(update_fields=['refunded_amount', 'refunded_at', 'refund_reason', 'status'])
        
        # Log the refund
        TransactionLog.objects.create(
            transaction=self,
            action='refund_processed',
            amount=amount,
            details=reason
        )


class TransactionLog(BaseModel):
    """
    Log of transaction events for auditing purposes.
    """
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    action = models.CharField(
        max_length=50,
        help_text="Action performed (created, completed, failed, refunded, etc.)"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True,
        help_text="Amount related to this action (if applicable)"
    )
    
    details = models.TextField(
        blank=True,
        help_text="Additional details about the action"
    )
    
    performed_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="User who performed the action (if manual)"
    )
    
    # Provider-specific fields
    provider_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Payment provider reference for this action"
    )
    
    class Meta:
        db_table = 'transaction_logs'
        verbose_name = 'Transaction Log'
        verbose_name_plural = 'Transaction Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction.transactionId} - {self.action}"


class PaymentMethod(BaseModel, TimestampedModelMixin):
    """
    Stored payment methods for users.
    """
    
    TYPE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text="Type of payment method"
    )
    
    # Card-specific fields
    last_four = models.CharField(
        max_length=4,
        blank=True,
        help_text="Last 4 digits of card number"
    )
    
    card_brand = models.CharField(
        max_length=20,
        blank=True,
        help_text="Card brand (Visa, Mastercard, etc.)"
    )
    
    exp_month = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Card expiration month"
    )
    
    exp_year = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Card expiration year"
    )
    
    # Provider-specific fields
    provider_id = models.CharField(
        max_length=255,
        help_text="Payment provider's ID for this method"
    )
    
    provider = models.CharField(
        max_length=20,
        choices=TransactionChoices.PROVIDER_CHOICES,
        default='stripe',
        help_text="Payment provider"
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default payment method"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is active"
    )
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.type == 'card' and self.last_four:
            return f"{self.card_brand} ending in {self.last_four}"
        return f"{self.get_type_display()}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if card is expired (only applies to cards)."""
        if self.type != 'card' or not self.exp_month or not self.exp_year:
            return False
        
        from datetime import datetime
        now = datetime.now()
        return (self.exp_year < now.year or 
                (self.exp_year == now.year and self.exp_month < now.month))
    
    def deactivate(self):
        """Deactivate this payment method."""
        self.is_active = False
        self.is_default = False
        self.save(update_fields=['is_active', 'is_default'])