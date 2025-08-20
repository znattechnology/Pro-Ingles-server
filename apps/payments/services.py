"""
Payment processing services.
"""

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
import logging

from .models import (
    Payment, PaymentMethod, PaymentAccount, PaymentSplit,
    Refund, Wallet, PaymentIntent
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class StripeService:
    """Service for Stripe payment processing."""
    
    @staticmethod
    def create_customer(user):
        """Create Stripe customer for user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name() or user.email,
                metadata={
                    'user_id': str(user.id),
                    'platform': 'tuwi_beauty'
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            raise
    
    @staticmethod
    def create_payment_method(user, payment_method_data):
        """Create payment method in Stripe."""
        try:
            # Get or create Stripe customer
            stripe_customer_id = getattr(user, 'stripe_customer_id', None)
            if not stripe_customer_id:
                customer = StripeService.create_customer(user)
                stripe_customer_id = customer.id
                # Save customer ID to user profile
                # This would require adding stripe_customer_id field to User model
            
            # Create payment method
            payment_method = stripe.PaymentMethod.create(
                type='card',
                card=payment_method_data,
            )
            
            # Attach to customer
            payment_method.attach(customer=stripe_customer_id)
            
            # Create local payment method record
            local_payment_method = PaymentMethod.objects.create(
                user=user,
                method_type='card',
                stripe_payment_method_id=payment_method.id,
                card_last4=payment_method.card.last4,
                card_brand=payment_method.card.brand,
                card_exp_month=payment_method.card.exp_month,
                card_exp_year=payment_method.card.exp_year,
                is_verified=True
            )
            
            return local_payment_method, payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating payment method: {str(e)}")
            raise
    
    @staticmethod
    def create_payment_intent(amount, currency='EUR', user=None, booking=None, metadata=None):
        """Create Stripe payment intent."""
        try:
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            intent_data = {
                'amount': amount_cents,
                'currency': currency.lower(),
                'automatic_payment_methods': {'enabled': True},
                'metadata': metadata or {}
            }
            
            # Add customer if provided
            if user:
                stripe_customer_id = getattr(user, 'stripe_customer_id', None)
                if stripe_customer_id:
                    intent_data['customer'] = stripe_customer_id
            
            # Create Stripe payment intent
            stripe_intent = stripe.PaymentIntent.create(**intent_data)
            
            # Create local payment intent record
            local_intent = PaymentIntent.objects.create(
                external_intent_id=stripe_intent.id,
                client_secret=stripe_intent.client_secret,
                user=user,
                amount=amount,
                currency=currency,
                status=stripe_intent.status,
                booking=booking,
                metadata=metadata or {}
            )
            
            return local_intent, stripe_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    @staticmethod
    def confirm_payment_intent(intent_id, payment_method_id=None):
        """Confirm Stripe payment intent."""
        try:
            confirm_data = {}
            if payment_method_id:
                confirm_data['payment_method'] = payment_method_id
            
            stripe_intent = stripe.PaymentIntent.confirm(intent_id, **confirm_data)
            
            # Update local record
            try:
                local_intent = PaymentIntent.objects.get(external_intent_id=intent_id)
                local_intent.status = stripe_intent.status
                local_intent.save()
            except PaymentIntent.DoesNotExist:
                pass
            
            return stripe_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Error confirming payment intent: {str(e)}")
            raise
    
    @staticmethod
    def create_connected_account(user, account_type='express'):
        """Create Stripe connected account for braiders."""
        try:
            account = stripe.Account.create(
                type=account_type,
                country='PT',  # Portugal
                email=user.email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                business_type='individual',
                individual={
                    'email': user.email,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                },
                metadata={
                    'user_id': str(user.id),
                    'platform': 'tuwi_beauty'
                }
            )
            
            # Create local payment account record
            payment_account = PaymentAccount.objects.create(
                user=user,
                account_type='stripe_account',
                stripe_account_id=account.id,
                status='pending'
            )
            
            return payment_account, account
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating connected account: {str(e)}")
            raise
    
    @staticmethod
    def create_account_link(account_id, refresh_url, return_url):
        """Create account onboarding link for Stripe Express."""
        try:
            account_link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            return account_link
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating account link: {str(e)}")
            raise
    
    @staticmethod
    def create_transfer(amount, destination_account, source_transaction=None, metadata=None):
        """Create transfer to connected account."""
        try:
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            transfer_data = {
                'amount': amount_cents,
                'currency': 'eur',
                'destination': destination_account,
                'metadata': metadata or {}
            }
            
            if source_transaction:
                transfer_data['source_transaction'] = source_transaction
            
            transfer = stripe.Transfer.create(**transfer_data)
            return transfer
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating transfer: {str(e)}")
            raise
    
    @staticmethod
    def create_refund(payment_intent_id, amount=None, reason=None):
        """Create refund for payment."""
        try:
            refund_data = {
                'payment_intent': payment_intent_id,
                'reason': reason or 'requested_by_customer'
            }
            
            if amount:
                # Convert to cents
                refund_data['amount'] = int(amount * 100)
            
            stripe_refund = stripe.Refund.create(**refund_data)
            return stripe_refund
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating refund: {str(e)}")
            raise


class PaymentService:
    """Service for payment processing and business logic."""
    
    @staticmethod
    def calculate_fees(amount, payment_type='booking_payment'):
        """Calculate platform and processor fees."""
        amount = Decimal(str(amount))
        
        # Platform fee (5% for bookings, 2.5% for tips)
        if payment_type == 'booking_payment':
            platform_fee = amount * Decimal('0.05')  # 5%
        elif payment_type == 'tip':
            platform_fee = amount * Decimal('0.025')  # 2.5%
        else:
            platform_fee = Decimal('0.00')
        
        # Stripe fee (2.9% + €0.30)
        stripe_fee = amount * Decimal('0.029') + Decimal('0.30')
        
        return {
            'platform_fee': platform_fee.quantize(Decimal('0.01')),
            'processor_fee': stripe_fee.quantize(Decimal('0.01')),
            'net_amount': (amount - platform_fee - stripe_fee).quantize(Decimal('0.01'))
        }
    
    @staticmethod
    def process_booking_payment(booking, payment_method, amount=None):
        """Process payment for booking."""
        try:
            if not amount:
                amount = booking.total_price
            
            # Calculate fees
            fees = PaymentService.calculate_fees(amount, 'booking_payment')
            
            # Create payment record
            payment = Payment.objects.create(
                payer=booking.client,
                payee=booking.braider.user,
                amount=amount,
                payment_type='booking_payment',
                payment_method=payment_method,
                booking=booking,
                platform_fee=fees['platform_fee'],
                payment_processor_fee=fees['processor_fee'],
                net_amount=fees['net_amount'],
                description=f"Payment for booking {booking.id}"
            )
            
            # Create payment intent
            intent, stripe_intent = StripeService.create_payment_intent(
                amount=amount,
                user=booking.client,
                booking=booking,
                metadata={
                    'booking_id': str(booking.id),
                    'payment_id': str(payment.id),
                    'braider_id': str(booking.braider.id)
                }
            )
            
            payment.intent = intent
            payment.save()
            
            return payment, intent
            
        except Exception as e:
            logger.error(f"Error processing booking payment: {str(e)}")
            raise
    
    @staticmethod
    def process_payment_splits(payment):
        """Process payment splits after successful payment."""
        try:
            if payment.status != 'succeeded':
                raise ValueError("Payment must be successful to process splits")
            
            splits = []
            
            # Braider gets the service amount minus platform fee
            braider_amount = payment.net_amount
            if braider_amount > 0:
                braider_split = PaymentSplit.objects.create(
                    payment=payment,
                    recipient=payment.payee,
                    amount=braider_amount,
                    split_type='service_amount'
                )
                splits.append(braider_split)
                
                # Process transfer to braider's account
                try:
                    braider_account = PaymentAccount.objects.get(
                        user=payment.payee,
                        account_type='stripe_account',
                        can_receive_payments=True
                    )
                    
                    transfer = StripeService.create_transfer(
                        amount=braider_amount,
                        destination_account=braider_account.stripe_account_id,
                        source_transaction=payment.external_id,
                        metadata={
                            'payment_id': str(payment.id),
                            'split_id': str(braider_split.id),
                            'booking_id': str(payment.booking.id) if payment.booking else None
                        }
                    )
                    
                    braider_split.transfer_id = transfer.id
                    braider_split.status = 'processed'
                    braider_split.processed_at = timezone.now()
                    braider_split.save()
                    
                except PaymentAccount.DoesNotExist:
                    logger.warning(f"No payment account found for braider {payment.payee.id}")
                    # Could add to wallet instead
                    PaymentService.add_to_wallet(payment.payee, braider_amount, f"Payment from booking {payment.booking.id}")
            
            # Platform keeps the platform fee (automatically retained)
            
            return splits
            
        except Exception as e:
            logger.error(f"Error processing payment splits: {str(e)}")
            raise
    
    @staticmethod
    def process_refund(payment, amount=None, reason='requested_by_customer', initiated_by=None):
        """Process refund for payment."""
        try:
            if payment.status not in ['succeeded']:
                raise ValueError("Can only refund successful payments")
            
            refund_amount = amount or payment.amount
            
            if refund_amount > payment.amount:
                raise ValueError("Refund amount cannot exceed payment amount")
            
            # Create local refund record
            refund = Refund.objects.create(
                payment=payment,
                amount=refund_amount,
                reason=reason,
                initiated_by=initiated_by,
                description=f"Refund for payment {payment.internal_reference}"
            )
            
            # Process Stripe refund
            stripe_refund = StripeService.create_refund(
                payment_intent_id=payment.intent.external_intent_id,
                amount=refund_amount,
                reason=reason
            )
            
            refund.external_refund_id = stripe_refund.id
            refund.status = 'succeeded' if stripe_refund.status == 'succeeded' else 'processing'
            if refund.status == 'succeeded':
                refund.processed_at = timezone.now()
            refund.save()
            
            # Update payment status
            if refund_amount == payment.amount:
                payment.status = 'refunded'
            else:
                payment.status = 'partially_refunded'
            payment.refunded_at = timezone.now()
            payment.save()
            
            return refund
            
        except Exception as e:
            logger.error(f"Error processing refund: {str(e)}")
            raise
    
    @staticmethod
    def add_to_wallet(user, amount, description=""):
        """Add funds to user's wallet."""
        try:
            wallet, created = Wallet.objects.get_or_create(user=user)
            wallet.add_funds(amount, description)
            return wallet
            
        except Exception as e:
            logger.error(f"Error adding to wallet: {str(e)}")
            raise
    
    @staticmethod
    def deduct_from_wallet(user, amount, description=""):
        """Deduct funds from user's wallet."""
        try:
            wallet = Wallet.objects.get(user=user)
            wallet.deduct_funds(amount, description)
            return wallet
            
        except Wallet.DoesNotExist:
            raise ValueError("User does not have a wallet")
        except Exception as e:
            logger.error(f"Error deducting from wallet: {str(e)}")
            raise
    
    @staticmethod
    def get_user_payment_stats(user):
        """Get payment statistics for user."""
        payments_made = Payment.objects.filter(payer=user)
        payments_received = Payment.objects.filter(payee=user)
        
        stats = {
            'total_paid': payments_made.filter(status='succeeded').aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_received': payments_received.filter(status='succeeded').aggregate(
                total=models.Sum('net_amount')
            )['total'] or Decimal('0.00'),
            'pending_payments': payments_made.filter(status='pending').count(),
            'successful_payments': payments_made.filter(status='succeeded').count(),
            'failed_payments': payments_made.filter(status='failed').count(),
            'refunds_received': Refund.objects.filter(
                payment__payer=user, status='succeeded'
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        }
        
        return stats