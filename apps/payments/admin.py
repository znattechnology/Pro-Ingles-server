"""
Django admin configuration for payment models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from .models import (
    PaymentMethod, PaymentAccount, Payment, PaymentSplit,
    Refund, Wallet, WalletTransaction, PaymentIntent
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for PaymentMethod model."""
    
    list_display = [
        'user_email', 'method_display', 'is_default', 'is_verified',
        'is_active', 'created_at'
    ]
    list_filter = ['method_type', 'is_default', 'is_verified', 'is_active', 'created_at']
    search_fields = ['user__email', 'card_brand', 'bank_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'method_type', 'is_active', 'is_default', 'is_verified')
        }),
        ('Card Details', {
            'fields': ('card_last4', 'card_brand', 'card_exp_month', 'card_exp_year'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_last4'),
            'classes': ('collapse',)
        }),
        ('External Integration', {
            'fields': ('stripe_payment_method_id', 'paypal_payer_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def method_display(self, obj):
        """Display payment method with icon."""
        icons = {
            'card': '💳',
            'bank_transfer': '🏦',
            'paypal': '🅿️',
            'mbway': '📱',
            'multibanco': '🏧',
            'wallet': '👛',
        }
        icon = icons.get(obj.method_type, '💰')
        
        if obj.method_type == 'card':
            return f"{icon} {obj.card_brand} ****{obj.card_last4}"
        return f"{icon} {obj.get_method_type_display()}"
    method_display.short_description = "Method"


@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    """Admin interface for PaymentAccount model."""
    
    list_display = [
        'user_email', 'account_type_display', 'status_display',
        'is_verified', 'can_receive_payments', 'created_at'
    ]
    list_filter = ['account_type', 'status', 'is_verified', 'can_receive_payments', 'created_at']
    search_fields = ['user__email', 'bank_name', 'account_holder_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'account_type', 'status')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_holder_name', 'iban', 'swift_code')
        }),
        ('External Integration', {
            'fields': ('stripe_account_id', 'paypal_account_email')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_documents', 'verification_notes')
        }),
        ('Capabilities', {
            'fields': ('can_receive_payments', 'can_instant_payout')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def account_type_display(self, obj):
        """Display account type with icon."""
        icons = {
            'stripe_account': '💳',
            'bank_account': '🏦',
            'paypal_account': '🅿️',
        }
        icon = icons.get(obj.account_type, '💰')
        return f"{icon} {obj.get_account_type_display()}"
    account_type_display.short_description = "Type"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'active': '#28a745',
            'restricted': '#fd7e14',
            'suspended': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    
    list_display = [
        'internal_reference', 'payer_email', 'payee_email', 'amount_display',
        'payment_type_display', 'status_display', 'processed_at'
    ]
    list_filter = [
        'status', 'payment_type', 'currency', 'processed_at', 'created_at'
    ]
    search_fields = [
        'internal_reference', 'external_id', 'payer__email', 'payee__email', 'description'
    ]
    readonly_fields = [
        'id', 'internal_reference', 'external_id', 'total_fees',
        'processed_at', 'failed_at', 'refunded_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('id', 'internal_reference', 'external_id', 'description')
        }),
        ('Parties', {
            'fields': ('payer', 'payee')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'platform_fee', 'payment_processor_fee', 'net_amount', 'total_fees')
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'status', 'payment_method', 'payment_account')
        }),
        ('Related Objects', {
            'fields': ('booking',)
        }),
        ('Timing', {
            'fields': ('processed_at', 'failed_at', 'refunded_at')
        }),
        ('Error Information', {
            'fields': ('failure_reason', 'failure_code'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'provider_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processed', 'mark_as_failed']
    
    def payer_email(self, obj):
        """Display payer email with link."""
        url = reverse('admin:users_user_change', args=[obj.payer.id])
        return format_html('<a href="{}">{}</a>', url, obj.payer.email)
    payer_email.short_description = "Payer"
    
    def payee_email(self, obj):
        """Display payee email with link."""
        if obj.payee:
            url = reverse('admin:users_user_change', args=[obj.payee.id])
            return format_html('<a href="{}">{}</a>', url, obj.payee.email)
        return "-"
    payee_email.short_description = "Payee"
    
    def amount_display(self, obj):
        """Display amount with currency."""
        return f"€{obj.amount}"
    amount_display.short_description = "Amount"
    
    def payment_type_display(self, obj):
        """Display payment type with icon."""
        icons = {
            'booking_payment': '📅',
            'service_fee': '💼',
            'tip': '💡',
            'refund': '↩️',
            'payout': '💸',
            'commission': '🏛️',
        }
        icon = icons.get(obj.payment_type, '💰')
        return f"{icon} {obj.get_payment_type_display()}"
    payment_type_display.short_description = "Type"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'succeeded': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14',
            'partially_refunded': '#e83e8c',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def mark_as_processed(self, request, queryset):
        """Mark selected payments as processed."""
        updated = queryset.filter(status='pending').update(
            status='succeeded',
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated} payments marked as processed.')
    mark_as_processed.short_description = "Mark as processed"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed."""
        updated = queryset.filter(status__in=['pending', 'processing']).update(
            status='failed',
            failed_at=timezone.now(),
            failure_reason='Manually marked as failed by admin'
        )
        self.message_user(request, f'{updated} payments marked as failed.')
    mark_as_failed.short_description = "Mark as failed"


@admin.register(PaymentSplit)
class PaymentSplitAdmin(admin.ModelAdmin):
    """Admin interface for PaymentSplit model."""
    
    list_display = [
        'payment_reference', 'recipient_email', 'amount_display',
        'split_type_display', 'status_display', 'processed_at'
    ]
    list_filter = ['split_type', 'status', 'processed_at', 'created_at']
    search_fields = ['payment__internal_reference', 'recipient__email']
    readonly_fields = ['id', 'transfer_id', 'processed_at', 'created_at', 'updated_at']
    
    def payment_reference(self, obj):
        """Display payment reference with link."""
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">{}</a>', url, obj.payment.internal_reference)
    payment_reference.short_description = "Payment"
    
    def recipient_email(self, obj):
        """Display recipient email with link."""
        url = reverse('admin:users_user_change', args=[obj.recipient.id])
        return format_html('<a href="{}">{}</a>', url, obj.recipient.email)
    recipient_email.short_description = "Recipient"
    
    def amount_display(self, obj):
        """Display amount with currency."""
        return f"€{obj.amount}"
    amount_display.short_description = "Amount"
    
    def split_type_display(self, obj):
        """Display split type with icon."""
        icons = {
            'service_amount': '💼',
            'tip': '💡',
            'platform_fee': '🏛️',
            'referral_bonus': '🎁',
        }
        icon = icons.get(obj.split_type, '💰')
        return f"{icon} {obj.get_split_type_display()}"
    split_type_display.short_description = "Type"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'processed': '#28a745',
            'failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Admin interface for Refund model."""
    
    list_display = [
        'payment_reference', 'amount_display', 'reason_display',
        'status_display', 'initiated_by_email', 'processed_at'
    ]
    list_filter = ['reason', 'status', 'processed_at', 'created_at']
    search_fields = ['payment__internal_reference', 'external_refund_id', 'description']
    readonly_fields = [
        'id', 'external_refund_id', 'processed_at', 'failed_at',
        'created_at', 'updated_at'
    ]
    
    def payment_reference(self, obj):
        """Display payment reference with link."""
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">{}</a>', url, obj.payment.internal_reference)
    payment_reference.short_description = "Payment"
    
    def amount_display(self, obj):
        """Display amount with currency."""
        return f"€{obj.amount}"
    amount_display.short_description = "Amount"
    
    def reason_display(self, obj):
        """Display reason with color coding."""
        colors = {
            'requested_by_customer': '#007bff',
            'duplicate': '#ffc107',
            'fraudulent': '#dc3545',
            'service_not_provided': '#fd7e14',
            'booking_cancelled': '#6c757d',
            'other': '#6c757d',
        }
        color = colors.get(obj.reason, '#6c757d')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_reason_display()
        )
    reason_display.short_description = "Reason"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'succeeded': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def initiated_by_email(self, obj):
        """Display initiator email with link."""
        if obj.initiated_by:
            url = reverse('admin:users_user_change', args=[obj.initiated_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.initiated_by.email)
        return "-"
    initiated_by_email.short_description = "Initiated By"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin interface for Wallet model."""
    
    list_display = [
        'user_email', 'balance_display', 'available_balance_display',
        'pending_balance_display', 'is_active', 'is_frozen'
    ]
    list_filter = ['is_active', 'is_frozen', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'balance', 'available_balance', 'pending_balance', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'is_active', 'is_frozen')
        }),
        ('Balance Information', {
            'fields': ('balance', 'available_balance', 'pending_balance')
        }),
        ('Limits', {
            'fields': ('daily_spend_limit', 'monthly_spend_limit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def balance_display(self, obj):
        """Display total balance."""
        color = 'green' if obj.balance >= 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">€{}</span>',
            color,
            obj.balance
        )
    balance_display.short_description = "Total Balance"
    
    def available_balance_display(self, obj):
        """Display available balance."""
        color = 'green' if obj.available_balance >= 0 else 'red'
        return format_html(
            '<span style="color: {};">€{}</span>',
            color,
            obj.available_balance
        )
    available_balance_display.short_description = "Available"
    
    def pending_balance_display(self, obj):
        """Display pending balance."""
        if obj.pending_balance > 0:
            return format_html(
                '<span style="color: orange;">€{}</span>',
                obj.pending_balance
            )
        return "€0.00"
    pending_balance_display.short_description = "Pending"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Admin interface for WalletTransaction model."""
    
    list_display = [
        'wallet_user', 'amount_display', 'transaction_type_display',
        'description', 'balance_after_display', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['wallet__user__email', 'description', 'external_reference']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def wallet_user(self, obj):
        """Display wallet user email with link."""
        url = reverse('admin:users_user_change', args=[obj.wallet.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.wallet.user.email)
    wallet_user.short_description = "User"
    
    def amount_display(self, obj):
        """Display amount with color coding."""
        color = 'green' if obj.amount >= 0 else 'red'
        sign = '+' if obj.amount >= 0 else ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color,
            sign,
            f"€{obj.amount}"
        )
    amount_display.short_description = "Amount"
    
    def transaction_type_display(self, obj):
        """Display transaction type with icon."""
        icons = {
            'credit': '💰',
            'debit': '💸',
            'hold': '🔒',
            'release': '🔓',
            'transfer_in': '📥',
            'transfer_out': '📤',
            'refund': '↩️',
            'fee': '🏛️',
        }
        icon = icons.get(obj.transaction_type, '💳')
        return f"{icon} {obj.get_transaction_type_display()}"
    transaction_type_display.short_description = "Type"
    
    def balance_after_display(self, obj):
        """Display balance after transaction."""
        color = 'green' if obj.balance_after >= 0 else 'red'
        return format_html(
            '<span style="color: {};">€{}</span>',
            color,
            obj.balance_after
        )
    balance_after_display.short_description = "Balance After"


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    """Admin interface for PaymentIntent model."""
    
    list_display = [
        'external_intent_id', 'user_email', 'amount_display',
        'status_display', 'booking_reference', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['external_intent_id', 'user__email', 'description']
    readonly_fields = [
        'id', 'external_intent_id', 'client_secret', 'created_at', 'updated_at'
    ]
    
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def amount_display(self, obj):
        """Display amount with currency."""
        return f"{obj.currency.upper()} {obj.amount}"
    amount_display.short_description = "Amount"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'requires_payment_method': '#ffc107',
            'requires_confirmation': '#fd7e14',
            'requires_action': '#17a2b8',
            'processing': '#6f42c1',
            'succeeded': '#28a745',
            'cancelled': '#6c757d',
            'failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def booking_reference(self, obj):
        """Display booking reference if exists."""
        if obj.booking:
            url = reverse('admin:bookings_booking_change', args=[obj.booking.id])
            return format_html('<a href="{}">#{}</a>', url, obj.booking.id)
        return "-"
    booking_reference.short_description = "Booking"