"""
Integration helpers for connecting payments with other apps.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from .models import Payment, PaymentIntent, Wallet, PaymentMethod
from .services import StripeService, PaymentService
from .signals import create_booking_payment, process_tip_payment

User = get_user_model()


class PaymentIntegrator:
    """Helper class for payment integrations with other apps."""
    
    @staticmethod
    def create_booking_payment_intent(booking, payment_method_id=None):
        """Create payment intent for booking."""
        try:
            # Calculate total amount
            total_amount = booking.total_price
            
            # Create payment intent
            intent, stripe_intent = StripeService.create_payment_intent(
                amount=total_amount,
                currency='EUR',
                user=booking.client,
                booking=booking,
                metadata={
                    'booking_id': str(booking.id),
                    'braider_id': str(booking.braider.id),
                    'service_name': booking.service_name
                }
            )
            
            # Create local payment record
            payment = Payment.objects.create(
                payer=booking.client,
                payee=booking.braider.user,
                amount=total_amount,
                currency='EUR',
                payment_type='booking_payment',
                booking=booking,
                description=f'Payment for booking #{booking.id}',
                metadata={
                    'booking_id': str(booking.id),
                    'service_name': booking.service_name
                }
            )
            
            # Link intent to payment
            intent.payment = payment
            intent.save()
            
            return intent, payment
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating booking payment intent: {str(e)}")
            raise
    
    @staticmethod
    def process_booking_payment_success(payment_intent_id, charge_id=None):
        """Handle successful booking payment."""
        try:
            intent = PaymentIntent.objects.get(external_intent_id=payment_intent_id)
            
            if intent.payment:
                payment = intent.payment
                payment.mark_as_succeeded(
                    external_id=charge_id,
                    provider_response={'payment_intent_id': payment_intent_id}
                )
                
                # Update booking status
                if intent.booking:
                    intent.booking.payment_status = 'paid'
                    intent.booking.save()
                
                # Send notifications
                from apps.notifications.integrations import NotificationIntegrator
                NotificationIntegrator.send_booking_notification(
                    intent.booking, 'confirmation'
                )
                
                return payment
            
        except PaymentIntent.DoesNotExist:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Payment intent not found: {payment_intent_id}")
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing booking payment success: {str(e)}")
            raise
    
    @staticmethod
    def handle_booking_cancellation(booking, cancellation_policy='partial_refund'):
        """Handle payment refund when booking is cancelled."""
        try:
            # Find booking payment
            payment = Payment.objects.filter(
                booking=booking,
                payment_type='booking_payment',
                status='succeeded'
            ).first()
            
            if not payment:
                return None
            
            # Calculate refund amount based on policy
            if cancellation_policy == 'full_refund':
                refund_amount = payment.amount
            elif cancellation_policy == 'partial_refund':
                # 80% refund (20% cancellation fee)
                refund_amount = payment.amount * Decimal('0.80')
            else:  # no_refund
                return None
            
            # Process refund
            refund = PaymentService.process_refund(
                payment=payment,
                amount=refund_amount,
                reason='booking_cancelled'
            )
            
            # Update booking status
            booking.payment_status = 'refunded'
            booking.save()
            
            # Send notification
            from apps.notifications.integrations import NotificationIntegrator
            NotificationIntegrator.send_booking_notification(
                booking, 'cancellation'
            )
            
            return refund
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error handling booking cancellation: {str(e)}")
            raise
    
    @staticmethod
    def create_tip_payment(booking, tip_amount):
        """Create tip payment for completed booking."""
        try:
            # Calculate fees
            fees = PaymentService.calculate_fees(tip_amount, 'tip')
            
            # Create tip payment
            tip_payment = Payment.objects.create(
                payer=booking.client,
                payee=booking.braider.user,
                amount=tip_amount,
                currency='EUR',
                payment_type='tip',
                platform_fee=fees['platform_fee'],
                payment_processor_fee=fees['processor_fee'],
                net_amount=fees['net_amount'],
                booking=booking,
                description=f'Tip for booking #{booking.id}',
                metadata={
                    'booking_id': str(booking.id),
                    'is_tip': True
                }
            )
            
            # Create payment intent for tip
            intent, stripe_intent = StripeService.create_payment_intent(
                amount=tip_amount,
                currency='EUR',
                user=booking.client,
                metadata={
                    'payment_id': str(tip_payment.id),
                    'booking_id': str(booking.id),
                    'payment_type': 'tip'
                }
            )
            
            tip_payment.intent = intent
            tip_payment.save()
            
            return tip_payment, intent
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating tip payment: {str(e)}")
            raise
    
    @staticmethod
    def get_user_payment_summary(user):
        """Get comprehensive payment summary for user."""
        try:
            # Get wallet info
            try:
                wallet = Wallet.objects.get(user=user)
                wallet_balance = wallet.available_balance
                wallet_pending = wallet.pending_balance
            except Wallet.DoesNotExist:
                wallet_balance = Decimal('0.00')
                wallet_pending = Decimal('0.00')
            
            # Calculate payment statistics
            payments_made = Payment.objects.filter(payer=user, status='succeeded')
            payments_received = Payment.objects.filter(payee=user, status='succeeded')
            
            summary = {
                'wallet': {
                    'available_balance': wallet_balance,
                    'pending_balance': wallet_pending,
                    'total_balance': wallet_balance + wallet_pending
                },
                'payments_made': {
                    'total_amount': payments_made.aggregate(
                        total=models.Sum('amount')
                    )['total'] or Decimal('0.00'),
                    'count': payments_made.count(),
                    'fees_paid': payments_made.aggregate(
                        total=models.Sum('platform_fee')
                    )['total'] or Decimal('0.00')
                },
                'payments_received': {
                    'total_amount': payments_received.aggregate(
                        total=models.Sum('amount')
                    )['total'] or Decimal('0.00'),
                    'net_amount': payments_received.aggregate(
                        total=models.Sum('net_amount')
                    )['total'] or Decimal('0.00'),
                    'count': payments_received.count()
                },
                'pending_payments': Payment.objects.filter(
                    models.Q(payer=user) | models.Q(payee=user),
                    status='pending'
                ).count(),
                'failed_payments': Payment.objects.filter(
                    payer=user,
                    status='failed'
                ).count()
            }
            
            return summary
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting payment summary: {str(e)}")
            return {}
    
    @staticmethod
    def setup_braider_payments(braider):
        """Set up payment capabilities for braider."""
        try:
            # Create Stripe Connect account
            account, stripe_account = StripeService.create_connected_account(
                user=braider.user,
                account_type='express'
            )
            
            # Create wallet
            wallet, created = Wallet.objects.get_or_create(
                user=braider.user,
                defaults={
                    'is_active': True
                }
            )
            
            return {
                'payment_account': account,
                'wallet': wallet,
                'onboarding_required': True
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error setting up braider payments: {str(e)}")
            raise
    
    @staticmethod
    def process_wallet_payment(user, amount, description="", **metadata):
        """Process payment using user's wallet."""
        try:
            wallet = Wallet.objects.get(user=user, is_active=True, is_frozen=False)
            
            if wallet.available_balance < amount:
                raise ValueError("Insufficient wallet balance")
            
            # Create payment record
            payment = Payment.objects.create(
                payer=user,
                amount=amount,
                currency='EUR',
                payment_type='booking_payment',
                status='succeeded',
                processed_at=timezone.now(),
                description=description,
                metadata={
                    'payment_method': 'wallet',
                    **metadata
                }
            )
            
            # Deduct from wallet
            wallet.deduct_funds(amount, description)
            
            return payment
            
        except Wallet.DoesNotExist:
            raise ValueError("User wallet not found")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing wallet payment: {str(e)}")
            raise
    
    @staticmethod
    def add_funds_to_wallet(user, amount, source="manual", description=""):
        """Add funds to user's wallet."""
        try:
            wallet, created = Wallet.objects.get_or_create(user=user)
            
            wallet.add_funds(
                amount=amount,
                description=description or f"Funds added - {source}",
                transaction_type="credit"
            )
            
            # Send notification
            from apps.notifications.integrations import notify_system
            notify_system(
                user,
                "Fundos Adicionados",
                f"€{amount} foram adicionados à sua carteira.",
                priority=2
            )
            
            return wallet
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error adding funds to wallet: {str(e)}")
            raise
    
    @staticmethod
    def get_braider_earnings(braider, period='month'):
        """Get braider earnings for specified period."""
        try:
            from datetime import datetime, timedelta
            
            now = timezone.now()
            
            if period == 'day':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'week':
                start_date = now - timedelta(days=7)
            elif period == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now - timedelta(days=30)
            
            earnings = Payment.objects.filter(
                payee=braider.user,
                status='succeeded',
                processed_at__gte=start_date
            ).aggregate(
                total_gross=models.Sum('amount'),
                total_net=models.Sum('net_amount'),
                total_fees=models.Sum('platform_fee')
            )
            
            return {
                'period': period,
                'start_date': start_date,
                'total_gross': earnings['total_gross'] or Decimal('0.00'),
                'total_net': earnings['total_net'] or Decimal('0.00'),
                'total_fees': earnings['total_fees'] or Decimal('0.00'),
                'payment_count': Payment.objects.filter(
                    payee=braider.user,
                    status='succeeded',
                    processed_at__gte=start_date
                ).count()
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting braider earnings: {str(e)}")
            return {}


# Convenience functions for easy integration
def create_booking_payment_flow(booking):
    """Complete booking payment flow."""
    return PaymentIntegrator.create_booking_payment_intent(booking)

def handle_payment_success(payment_intent_id, charge_id=None):
    """Handle successful payment."""
    return PaymentIntegrator.process_booking_payment_success(payment_intent_id, charge_id)

def cancel_booking_with_refund(booking, policy='partial_refund'):
    """Cancel booking and process refund."""
    return PaymentIntegrator.handle_booking_cancellation(booking, policy)

def add_tip_to_booking(booking, tip_amount):
    """Add tip to completed booking."""
    return PaymentIntegrator.create_tip_payment(booking, tip_amount)

def get_payment_stats(user):
    """Get user payment statistics."""
    return PaymentIntegrator.get_user_payment_summary(user)

def setup_braider_account(braider):
    """Set up payment account for braider."""
    return PaymentIntegrator.setup_braider_payments(braider)

def pay_with_wallet(user, amount, description="", **kwargs):
    """Pay using wallet balance."""
    return PaymentIntegrator.process_wallet_payment(user, amount, description, **kwargs)

def top_up_wallet(user, amount, description=""):
    """Add funds to wallet."""
    return PaymentIntegrator.add_funds_to_wallet(user, amount, "top_up", description)