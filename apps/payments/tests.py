"""
Tests for payments functionality including payment methods, transactions, and wallets.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
import uuid

from .models import (
    PaymentMethod, PaymentAccount, Payment, PaymentSplit, Refund,
    Wallet, WalletTransaction, PaymentIntent
)
from apps.braiders.models import Braider, Service
from apps.bookings.models import Booking

User = get_user_model()


class PaymentMethodModelTest(TestCase):
    """Test PaymentMethod model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='payment@test.com',
            name='Payment User',
            password='testpass'
        )
        
        self.payment_method_data = {
            'user': self.user,
            'method_type': 'card',
            'stripe_payment_method_id': 'pm_test123',
            'card_last4': '4242',
            'card_brand': 'visa',
            'card_exp_month': 12,
            'card_exp_year': 2025,
            'is_verified': True
        }
    
    def test_create_payment_method(self):
        """Test creating a payment method."""
        method = PaymentMethod.objects.create(**self.payment_method_data)
        
        self.assertEqual(method.user, self.user)
        self.assertEqual(method.method_type, 'card')
        self.assertEqual(method.card_last4, '4242')
        self.assertEqual(method.card_brand, 'visa')
        self.assertTrue(method.is_verified)
        self.assertTrue(method.is_active)
    
    def test_payment_method_string_representation(self):
        """Test payment method string representation."""
        method = PaymentMethod.objects.create(**self.payment_method_data)
        expected = "visa ****4242"
        self.assertEqual(str(method), expected)
    
    def test_default_payment_method_uniqueness(self):
        """Test that only one payment method can be default per user."""
        # Create first default method
        method1 = PaymentMethod.objects.create(
            **self.payment_method_data,
            is_default=True
        )
        self.assertTrue(method1.is_default)
        
        # Create second default method
        payment_method_data2 = self.payment_method_data.copy()
        payment_method_data2['stripe_payment_method_id'] = 'pm_test456'
        payment_method_data2['card_last4'] = '1234'
        
        method2 = PaymentMethod.objects.create(
            **payment_method_data2,
            is_default=True
        )
        
        # Check that first method is no longer default
        method1.refresh_from_db()
        self.assertFalse(method1.is_default)
        self.assertTrue(method2.is_default)
    
    def test_bank_payment_method(self):
        """Test creating bank transfer payment method."""
        method = PaymentMethod.objects.create(
            user=self.user,
            method_type='bank_transfer',
            bank_name='Millennium BCP',
            account_last4='5678',
            is_verified=True
        )
        
        self.assertEqual(method.method_type, 'bank_transfer')
        self.assertEqual(method.bank_name, 'Millennium BCP')
        self.assertEqual(str(method), 'Bank Transfer')
    
    def test_paypal_payment_method(self):
        """Test creating PayPal payment method."""
        method = PaymentMethod.objects.create(
            user=self.user,
            method_type='paypal',
            paypal_payer_id='PAYPAL123456'
        )
        
        self.assertEqual(method.method_type, 'paypal')
        self.assertEqual(method.paypal_payer_id, 'PAYPAL123456')


class PaymentAccountModelTest(TestCase):
    """Test PaymentAccount model functionality."""
    
    def setUp(self):
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        self.account_data = {
            'user': self.braider_user,
            'account_type': 'stripe_account',
            'stripe_account_id': 'acct_test123',
            'status': 'active',
            'is_verified': True,
            'can_receive_payments': True
        }
    
    def test_create_payment_account(self):
        """Test creating a payment account."""
        account = PaymentAccount.objects.create(**self.account_data)
        
        self.assertEqual(account.user, self.braider_user)
        self.assertEqual(account.account_type, 'stripe_account')
        self.assertEqual(account.status, 'active')
        self.assertTrue(account.is_verified)
        self.assertTrue(account.can_receive_payments)
    
    def test_payment_account_string_representation(self):
        """Test payment account string representation."""
        account = PaymentAccount.objects.create(**self.account_data)
        expected = f"{self.braider_user.email} - Stripe Express Account"
        self.assertEqual(str(account), expected)
    
    def test_bank_payment_account(self):
        """Test creating bank payment account."""
        account = PaymentAccount.objects.create(
            user=self.braider_user,
            account_type='bank_account',
            bank_name='Banco Santander',
            account_holder_name='João Silva',
            iban='PT50000000000000000000000',
            swift_code='BSCHPTPL',
            status='pending'
        )
        
        self.assertEqual(account.account_type, 'bank_account')
        self.assertEqual(account.bank_name, 'Banco Santander')
        self.assertEqual(account.iban, 'PT50000000000000000000000')
        self.assertEqual(account.status, 'pending')
    
    def test_paypal_payment_account(self):
        """Test creating PayPal payment account."""
        account = PaymentAccount.objects.create(
            user=self.braider_user,
            account_type='paypal_account',
            paypal_account_email='braider@paypal.com'
        )
        
        self.assertEqual(account.account_type, 'paypal_account')
        self.assertEqual(account.paypal_account_email, 'braider@paypal.com')


class PaymentModelTest(TestCase):
    """Test Payment model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Customer User',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Payment Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Payment Test Service',
            description='Test service for payments',
            category='braids',
            base_price=Decimal('100.00'),
            duration_minutes=240
        )
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date() + timedelta(days=7),
            booking_time=timezone.now().time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            status='confirmed'
        )
        
        self.payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='card',
            stripe_payment_method_id='pm_test123',
            card_last4='4242',
            card_brand='visa'
        )
        
        self.payment_data = {
            'payer': self.customer,
            'payee': self.braider_user,
            'amount': Decimal('100.00'),
            'payment_type': 'booking_payment',
            'payment_method': self.payment_method,
            'booking': self.booking,
            'platform_fee': Decimal('10.00'),
            'payment_processor_fee': Decimal('3.50'),
            'description': 'Payment for braiding service'
        }
    
    def test_create_payment(self):
        """Test creating a payment."""
        payment = Payment.objects.create(**self.payment_data)
        
        self.assertEqual(payment.payer, self.customer)
        self.assertEqual(payment.payee, self.braider_user)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.payment_type, 'booking_payment')
        self.assertEqual(payment.status, 'pending')
        
        # Check auto-generated reference
        self.assertTrue(payment.internal_reference.startswith('PAY-'))
        
        # Check calculated net amount
        self.assertEqual(payment.net_amount, Decimal('86.50'))  # 100 - 10 - 3.5
    
    def test_payment_string_representation(self):
        """Test payment string representation."""
        payment = Payment.objects.create(**self.payment_data)
        expected = f"Payment {payment.internal_reference} - €100.00 (pending)"
        self.assertEqual(str(payment), expected)
    
    def test_payment_total_fees_property(self):
        """Test payment total fees calculation."""
        payment = Payment.objects.create(**self.payment_data)
        self.assertEqual(payment.total_fees, Decimal('13.50'))  # 10 + 3.5
    
    def test_mark_payment_as_succeeded(self):
        """Test marking payment as succeeded."""
        payment = Payment.objects.create(**self.payment_data)
        
        self.assertEqual(payment.status, 'pending')
        self.assertIsNone(payment.processed_at)
        
        payment.mark_as_succeeded(
            external_id='pi_test123',
            provider_response={'status': 'succeeded'}
        )
        
        self.assertEqual(payment.status, 'succeeded')
        self.assertIsNotNone(payment.processed_at)
        self.assertEqual(payment.external_id, 'pi_test123')
        self.assertEqual(payment.provider_response['status'], 'succeeded')
    
    def test_mark_payment_as_failed(self):
        """Test marking payment as failed."""
        payment = Payment.objects.create(**self.payment_data)
        
        payment.mark_as_failed(
            reason='Insufficient funds',
            code='card_declined'
        )
        
        self.assertEqual(payment.status, 'failed')
        self.assertIsNotNone(payment.failed_at)
        self.assertEqual(payment.failure_reason, 'Insufficient funds')
        self.assertEqual(payment.failure_code, 'card_declined')
    
    def test_tip_payment(self):
        """Test creating tip payment."""
        tip_payment = Payment.objects.create(
            payer=self.customer,
            payee=self.braider_user,
            amount=Decimal('15.00'),
            payment_type='tip',
            booking=self.booking,
            description='Tip for excellent service'
        )
        
        self.assertEqual(tip_payment.payment_type, 'tip')
        self.assertEqual(tip_payment.amount, Decimal('15.00'))


class PaymentSplitModelTest(TestCase):
    """Test PaymentSplit model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Customer User',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        self.platform_user = User.objects.create_user(
            email='platform@tuwi.com',
            name='Platform',
            password='testpass'
        )
        
        self.payment = Payment.objects.create(
            payer=self.customer,
            payee=self.braider_user,
            amount=Decimal('100.00'),
            payment_type='booking_payment'
        )
    
    def test_create_payment_split(self):
        """Test creating payment split."""
        split = PaymentSplit.objects.create(
            payment=self.payment,
            recipient=self.braider_user,
            amount=Decimal('85.00'),
            split_type='service_amount'
        )
        
        self.assertEqual(split.payment, self.payment)
        self.assertEqual(split.recipient, self.braider_user)
        self.assertEqual(split.amount, Decimal('85.00'))
        self.assertEqual(split.split_type, 'service_amount')
        self.assertEqual(split.status, 'pending')
    
    def test_payment_split_string_representation(self):
        """Test payment split string representation."""
        split = PaymentSplit.objects.create(
            payment=self.payment,
            recipient=self.braider_user,
            amount=Decimal('85.00'),
            split_type='service_amount'
        )
        
        expected = f"Split €85.00 to {self.braider_user.email}"
        self.assertEqual(str(split), expected)
    
    def test_platform_fee_split(self):
        """Test creating platform fee split."""
        platform_split = PaymentSplit.objects.create(
            payment=self.payment,
            recipient=self.platform_user,
            amount=Decimal('15.00'),
            percentage=Decimal('15.00'),
            split_type='platform_fee'
        )
        
        self.assertEqual(platform_split.split_type, 'platform_fee')
        self.assertEqual(platform_split.percentage, Decimal('15.00'))


class RefundModelTest(TestCase):
    """Test Refund model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Customer User',
            password='testpass'
        )
        
        self.payment = Payment.objects.create(
            payer=self.customer,
            amount=Decimal('100.00'),
            payment_type='booking_payment',
            status='succeeded'
        )
        
        self.refund_data = {
            'payment': self.payment,
            'amount': Decimal('50.00'),
            'reason': 'requested_by_customer',
            'description': 'Service was cancelled by customer',
            'initiated_by': self.customer
        }
    
    def test_create_refund(self):
        """Test creating a refund."""
        refund = Refund.objects.create(**self.refund_data)
        
        self.assertEqual(refund.payment, self.payment)
        self.assertEqual(refund.amount, Decimal('50.00'))
        self.assertEqual(refund.reason, 'requested_by_customer')
        self.assertEqual(refund.status, 'pending')
        self.assertEqual(refund.initiated_by, self.customer)
    
    def test_refund_string_representation(self):
        """Test refund string representation."""
        refund = Refund.objects.create(**self.refund_data)
        expected = f"Refund €50.00 for {self.payment.internal_reference}"
        self.assertEqual(str(refund), expected)
    
    def test_full_refund(self):
        """Test creating full refund."""
        full_refund = Refund.objects.create(
            payment=self.payment,
            amount=self.payment.amount,
            reason='booking_cancelled',
            description='Booking was cancelled due to weather'
        )
        
        self.assertEqual(full_refund.amount, self.payment.amount)
        self.assertEqual(full_refund.reason, 'booking_cancelled')


class WalletModelTest(TestCase):
    """Test Wallet model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='wallet@test.com',
            name='Wallet User',
            password='testpass'
        )
        
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal('100.00'),
            available_balance=Decimal('100.00')
        )
    
    def test_create_wallet(self):
        """Test creating a wallet."""
        new_user = User.objects.create_user(
            email='newwallet@test.com',
            name='New Wallet User',
            password='testpass'
        )
        
        wallet = Wallet.objects.create(user=new_user)
        
        self.assertEqual(wallet.user, new_user)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        self.assertEqual(wallet.available_balance, Decimal('0.00'))
        self.assertEqual(wallet.pending_balance, Decimal('0.00'))
        self.assertTrue(wallet.is_active)
        self.assertFalse(wallet.is_frozen)
    
    def test_wallet_string_representation(self):
        """Test wallet string representation."""
        expected = f"Wallet for {self.user.email} - €100.00"
        self.assertEqual(str(self.wallet), expected)
    
    def test_add_funds(self):
        """Test adding funds to wallet."""
        initial_balance = self.wallet.balance
        initial_available = self.wallet.available_balance
        
        self.wallet.add_funds(Decimal('50.00'), "Test deposit")
        
        self.assertEqual(self.wallet.balance, initial_balance + Decimal('50.00'))
        self.assertEqual(self.wallet.available_balance, initial_available + Decimal('50.00'))
        
        # Check transaction was created
        transaction = WalletTransaction.objects.filter(wallet=self.wallet).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertEqual(transaction.transaction_type, 'credit')
        self.assertEqual(transaction.description, 'Test deposit')
    
    def test_deduct_funds(self):
        """Test deducting funds from wallet."""
        initial_balance = self.wallet.balance
        initial_available = self.wallet.available_balance
        
        self.wallet.deduct_funds(Decimal('30.00'), "Test withdrawal")
        
        self.assertEqual(self.wallet.balance, initial_balance - Decimal('30.00'))
        self.assertEqual(self.wallet.available_balance, initial_available - Decimal('30.00'))
        
        # Check transaction was created
        transaction = WalletTransaction.objects.filter(wallet=self.wallet).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('-30.00'))
        self.assertEqual(transaction.transaction_type, 'debit')
    
    def test_insufficient_funds_error(self):
        """Test error when trying to deduct more than available balance."""
        with self.assertRaises(ValueError) as context:
            self.wallet.deduct_funds(Decimal('150.00'))
        
        self.assertEqual(str(context.exception), "Insufficient funds")
    
    def test_hold_and_release_funds(self):
        """Test holding and releasing funds."""
        # Hold funds
        self.wallet.hold_funds(Decimal('40.00'), "Hold for booking")
        
        self.assertEqual(self.wallet.available_balance, Decimal('60.00'))
        self.assertEqual(self.wallet.pending_balance, Decimal('40.00'))
        self.assertEqual(self.wallet.balance, Decimal('100.00'))  # Total unchanged
        
        # Release funds
        self.wallet.release_hold(Decimal('40.00'), "Booking completed")
        
        self.assertEqual(self.wallet.available_balance, Decimal('100.00'))
        self.assertEqual(self.wallet.pending_balance, Decimal('0.00'))
        
        # Check transactions were created
        transactions = WalletTransaction.objects.filter(wallet=self.wallet).order_by('created_at')
        self.assertEqual(transactions.count(), 2)
        self.assertEqual(transactions[0].transaction_type, 'hold')
        self.assertEqual(transactions[1].transaction_type, 'release')
    
    def test_invalid_amount_errors(self):
        """Test validation for invalid amounts."""
        with self.assertRaises(ValueError):
            self.wallet.add_funds(Decimal('0.00'))
        
        with self.assertRaises(ValueError):
            self.wallet.add_funds(Decimal('-10.00'))
        
        with self.assertRaises(ValueError):
            self.wallet.deduct_funds(Decimal('0.00'))


class WalletTransactionModelTest(TestCase):
    """Test WalletTransaction model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='transaction@test.com',
            name='Transaction User',
            password='testpass'
        )
        
        self.wallet = Wallet.objects.create(user=self.user)
    
    def test_create_wallet_transaction(self):
        """Test creating wallet transaction."""
        transaction = WalletTransaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('25.00'),
            transaction_type='credit',
            description='Test transaction',
            balance_after=Decimal('25.00')
        )
        
        self.assertEqual(transaction.wallet, self.wallet)
        self.assertEqual(transaction.amount, Decimal('25.00'))
        self.assertEqual(transaction.transaction_type, 'credit')
        self.assertEqual(transaction.description, 'Test transaction')
        self.assertEqual(transaction.balance_after, Decimal('25.00'))
    
    def test_transaction_string_representation(self):
        """Test transaction string representation."""
        transaction = WalletTransaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('-15.00'),
            transaction_type='debit',
            description='Purchase payment',
            balance_after=Decimal('85.00')
        )
        
        expected = "Debit €15.00 - Purchase payment"
        self.assertEqual(str(transaction), expected)


class PaymentIntentModelTest(TestCase):
    """Test PaymentIntent model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='intent@test.com',
            name='Intent User',
            password='testpass'
        )
        
        self.intent_data = {
            'user': self.user,
            'amount': Decimal('75.00'),
            'currency': 'EUR',
            'external_intent_id': 'pi_test123',
            'client_secret': 'pi_test123_secret_xyz',
            'description': 'Payment for braiding service'
        }
    
    def test_create_payment_intent(self):
        """Test creating payment intent."""
        intent = PaymentIntent.objects.create(**self.intent_data)
        
        self.assertEqual(intent.user, self.user)
        self.assertEqual(intent.amount, Decimal('75.00'))
        self.assertEqual(intent.currency, 'EUR')
        self.assertEqual(intent.status, 'requires_payment_method')
        self.assertEqual(intent.external_intent_id, 'pi_test123')
        self.assertTrue(intent.automatic_payment_methods)
    
    def test_payment_intent_string_representation(self):
        """Test payment intent string representation."""
        intent = PaymentIntent.objects.create(**self.intent_data)
        expected = f"Payment Intent €75.00 - requires_payment_method"
        self.assertEqual(str(intent), expected)
    
    def test_payment_intent_with_booking(self):
        """Test payment intent associated with booking."""
        braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        braider = Braider.objects.create(
            user=braider_user,
            name='Intent Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        service = Service.objects.create(
            braider=braider,
            name='Intent Test Service',
            description='Test service',
            category='braids',
            base_price=Decimal('75.00'),
            duration_minutes=180
        )
        
        booking = Booking.objects.create(
            user=self.user,
            braider=braider,
            service=service,
            booking_date=timezone.now().date() + timedelta(days=5),
            booking_time=timezone.now().time(),
            client_name=self.user.name,
            client_phone='+1234567890',
            client_email=self.user.email,
            booking_type='home',
            base_price=Decimal('75.00'),
            total_price=Decimal('75.00'),
            status='pending'
        )
        
        intent = PaymentIntent.objects.create(
            **self.intent_data,
            booking=booking
        )
        
        self.assertEqual(intent.booking, booking)


class PaymentIntegrationTest(TestCase):
    """Test payment system integration scenarios."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Customer User',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        # Create customer wallet
        self.customer_wallet = Wallet.objects.create(
            user=self.customer,
            balance=Decimal('200.00'),
            available_balance=Decimal('200.00')
        )
        
        # Create braider wallet
        self.braider_wallet = Wallet.objects.create(
            user=self.braider_user,
            balance=Decimal('0.00'),
            available_balance=Decimal('0.00')
        )
        
        # Create payment method
        self.payment_method = PaymentMethod.objects.create(
            user=self.customer,
            method_type='wallet',
            is_default=True
        )
    
    def test_complete_payment_workflow(self):
        """Test complete payment workflow from creation to completion."""
        # 1. Create payment
        payment = Payment.objects.create(
            payer=self.customer,
            payee=self.braider_user,
            amount=Decimal('100.00'),
            payment_type='booking_payment',
            payment_method=self.payment_method,
            platform_fee=Decimal('10.00'),
            payment_processor_fee=Decimal('2.50')
        )
        
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.net_amount, Decimal('87.50'))
        
        # 2. Process payment (deduct from customer)
        self.customer_wallet.deduct_funds(payment.amount, f"Payment {payment.internal_reference}")
        
        # 3. Mark payment as succeeded
        payment.mark_as_succeeded(external_id='txn_123')
        
        # 4. Create payment splits
        braider_split = PaymentSplit.objects.create(
            payment=payment,
            recipient=self.braider_user,
            amount=payment.net_amount,
            split_type='service_amount',
            status='processed'
        )
        
        platform_split = PaymentSplit.objects.create(
            payment=payment,
            recipient=self.customer,  # Platform user would be different
            amount=payment.platform_fee,
            split_type='platform_fee',
            status='processed'
        )
        
        # 5. Add funds to braider wallet
        self.braider_wallet.add_funds(
            braider_split.amount,
            f"Payment from {payment.internal_reference}"
        )
        
        # Verify final state
        self.customer_wallet.refresh_from_db()
        self.braider_wallet.refresh_from_db()
        
        self.assertEqual(self.customer_wallet.available_balance, Decimal('100.00'))
        self.assertEqual(self.braider_wallet.available_balance, Decimal('87.50'))
        self.assertEqual(payment.status, 'succeeded')
    
    def test_refund_workflow(self):
        """Test refund workflow."""
        # Create successful payment
        payment = Payment.objects.create(
            payer=self.customer,
            payee=self.braider_user,
            amount=Decimal('80.00'),
            payment_type='booking_payment',
            status='succeeded'
        )
        
        # Process initial payment
        self.customer_wallet.deduct_funds(payment.amount, "Initial payment")
        self.braider_wallet.add_funds(payment.amount, "Payment received")
        
        # Create refund
        refund = Refund.objects.create(
            payment=payment,
            amount=Decimal('40.00'),
            reason='requested_by_customer',
            initiated_by=self.customer
        )
        
        # Process refund
        self.braider_wallet.deduct_funds(refund.amount, f"Refund {refund.id}")
        self.customer_wallet.add_funds(refund.amount, f"Refund {refund.id}")
        
        # Update refund status
        refund.status = 'succeeded'
        refund.processed_at = timezone.now()
        refund.save()
        
        # Verify final balances
        self.customer_wallet.refresh_from_db()
        self.braider_wallet.refresh_from_db()
        
        self.assertEqual(self.customer_wallet.available_balance, Decimal('160.00'))  # 200 - 80 + 40
        self.assertEqual(self.braider_wallet.available_balance, Decimal('40.00'))    # 0 + 80 - 40
        self.assertEqual(refund.status, 'succeeded')


class PaymentAPITest(APITestCase):
    """Test payment API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal('500.00'),
            available_balance=Decimal('500.00')
        )
        
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            method_type='card',
            stripe_payment_method_id='pm_test123',
            card_last4='4242',
            card_brand='visa',
            is_default=True
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_payment_methods(self):
        """Test listing user's payment methods."""
        url = reverse('payments:payment-methods')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['method_type'], 'card')
    
    def test_create_payment_method(self):
        """Test creating new payment method."""
        url = reverse('payments:payment-methods')
        data = {
            'method_type': 'bank_transfer',
            'bank_name': 'BPI',
            'account_last4': '9876'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PaymentMethod.objects.filter(user=self.user).count(), 2)
    
    def test_wallet_details(self):
        """Test getting wallet details."""
        url = reverse('payments:wallet-detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['balance']), 500.00)
        self.assertEqual(float(response.data['available_balance']), 500.00)
    
    def test_wallet_transactions(self):
        """Test listing wallet transactions."""
        # Create some transactions
        self.wallet.add_funds(Decimal('100.00'), "Test deposit")
        self.wallet.deduct_funds(Decimal('50.00'), "Test purchase")
        
        url = reverse('payments:wallet-transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_create_payment_intent(self):
        """Test creating payment intent."""
        url = reverse('payments:create-payment-intent')
        data = {
            'amount': '120.00',
            'currency': 'EUR',
            'description': 'Payment for braiding service'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)
        
        # Verify intent was created
        intent = PaymentIntent.objects.get(id=response.data['id'])
        self.assertEqual(intent.user, self.user)
        self.assertEqual(intent.amount, Decimal('120.00'))
    
    def test_payment_history(self):
        """Test getting payment history."""
        # Create test payment
        Payment.objects.create(
            payer=self.user,
            amount=Decimal('75.00'),
            payment_type='booking_payment'
        )
        
        url = reverse('payments:payment-history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(float(response.data['results'][0]['amount']), 75.00)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to payment endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('payments:wallet-detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)