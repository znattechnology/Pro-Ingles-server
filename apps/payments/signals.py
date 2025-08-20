"""
Signals for payment system integration.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from .models import Payment, PaymentSplit, Refund, Wallet, PaymentIntent
from .services import PaymentService

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create wallet when user is created."""
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=Payment)
def handle_payment_status_change(sender, instance, created, **kwargs):
    """Handle payment status changes."""
    if not created and instance.status == 'succeeded':
        # Process payment splits when payment succeeds
        if instance.payee and not instance.splits.exists():
            try:
                PaymentService.process_payment_splits(instance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing payment splits for payment {instance.id}: {str(e)}")
        
        # Send notification
        try:
            from apps.notifications.integrations import notify_system
            notify_system(
                instance.payer,
                "Pagamento Processado",
                f"Seu pagamento de €{instance.amount} foi processado com sucesso.",
                priority=3
            )
            
            if instance.payee:
                notify_system(
                    instance.payee,
                    "Pagamento Recebido",
                    f"Você recebeu um pagamento de €{instance.net_amount}.",
                    priority=3
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending payment notification: {str(e)}")
    
    elif not created and instance.status == 'failed':
        # Send failure notification
        try:
            from apps.notifications.integrations import notify_system
            notify_system(
                instance.payer,
                "Falha no Pagamento",
                f"Houve um problema com o seu pagamento de €{instance.amount}. Por favor, tente novamente.",
                priority=3
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending payment failure notification: {str(e)}")


@receiver(post_save, sender=Refund)
def handle_refund_completion(sender, instance, created, **kwargs):
    """Handle refund completion."""
    if not created and instance.status == 'succeeded':
        # Send refund notification
        try:
            from apps.notifications.integrations import notify_system
            notify_system(
                instance.payment.payer,
                "Reembolso Processado",
                f"Seu reembolso de €{instance.amount} foi processado com sucesso.",
                priority=3
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending refund notification: {str(e)}")


@receiver(pre_save, sender=Payment)
def calculate_payment_fees(sender, instance, **kwargs):
    """Calculate fees before saving payment."""
    if not instance.platform_fee or not instance.payment_processor_fee:
        fees = PaymentService.calculate_fees(instance.amount, instance.payment_type)
        instance.platform_fee = fees['platform_fee']
        instance.payment_processor_fee = fees['processor_fee']
        instance.net_amount = fees['net_amount']


# Integration functions for other apps
def create_booking_payment(booking, **kwargs):
    """Create payment for booking."""
    try:
        # Calculate total amount
        total_amount = booking.total_price
        
        # Get or create payment
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            payer=booking.client,
            defaults={
                'payee': booking.braider.user,
                'amount': total_amount,
                'currency': 'EUR',
                'payment_type': 'booking_payment',
                'description': f'Payment for booking #{booking.id}',
                'metadata': {
                    'booking_id': str(booking.id),
                    'service_name': booking.service_name,
                    'braider_id': str(booking.braider.id)
                }
            }
        )
        
        return payment
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating booking payment: {str(e)}")
        return None


def process_tip_payment(booking, tip_amount, **kwargs):
    """Process tip payment for booking."""
    try:
        # Calculate fees for tip
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
                'is_tip': True,
                'braider_id': str(booking.braider.id)
            }
        )
        
        return tip_payment
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing tip payment: {str(e)}")
        return None


def create_platform_commission(payment, commission_rate=0.05):
    """Create platform commission record."""
    try:
        if payment.status != 'succeeded' or payment.payment_type not in ['booking_payment', 'tip']:
            return None
        
        commission_amount = payment.amount * Decimal(str(commission_rate))
        
        # Create commission payment record
        commission_payment = Payment.objects.create(
            payer=payment.payee,  # Braider pays the commission
            payee=None,  # Platform receives
            amount=commission_amount,
            currency=payment.currency,
            payment_type='commission',
            status='succeeded',  # Automatically collected
            processed_at=timezone.now(),
            description=f'Platform commission for payment {payment.internal_reference}',
            metadata={
                'original_payment_id': str(payment.id),
                'commission_rate': float(commission_rate),
                'booking_id': str(payment.booking.id) if payment.booking else None
            }
        )
        
        return commission_payment
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating platform commission: {str(e)}")
        return None


def process_wallet_payment(user, amount, description="", **kwargs):
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
                **kwargs.get('metadata', {})
            }
        )
        
        # Deduct from wallet
        wallet.deduct_funds(amount, f"Payment: {description}")
        
        return payment
        
    except Wallet.DoesNotExist:
        raise ValueError("User wallet not found or not active")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing wallet payment: {str(e)}")
        raise


def handle_booking_cancellation(booking, **kwargs):
    """Handle payment refund when booking is cancelled."""
    try:
        # Find the booking payment
        booking_payments = Payment.objects.filter(
            booking=booking,
            payment_type='booking_payment',
            status='succeeded'
        )
        
        for payment in booking_payments:
            # Process refund based on cancellation policy
            cancellation_policy = kwargs.get('cancellation_policy', 'full_refund')
            
            if cancellation_policy == 'full_refund':
                refund_amount = payment.amount
            elif cancellation_policy == 'partial_refund':
                # Charge 20% cancellation fee
                refund_amount = payment.amount * Decimal('0.80')
            else:  # no_refund
                continue
            
            # Create refund
            refund = PaymentService.process_refund(
                payment=payment,
                amount=refund_amount,
                reason='booking_cancelled',
                initiated_by=None
            )
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error handling booking cancellation refund: {str(e)}")


# Convenience functions for integration
def get_user_payment_summary(user):
    """Get user's payment summary."""
    try:
        payments_made = Payment.objects.filter(payer=user, status='succeeded')
        payments_received = Payment.objects.filter(payee=user, status='succeeded')
        
        summary = {
            'total_spent': payments_made.aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_earned': payments_received.aggregate(
                total=models.Sum('net_amount')
            )['total'] or Decimal('0.00'),
            'platform_fees_paid': payments_made.aggregate(
                total=models.Sum('platform_fee')
            )['total'] or Decimal('0.00'),
            'successful_transactions': payments_made.count() + payments_received.count(),
            'pending_payments': Payment.objects.filter(
                models.Q(payer=user) | models.Q(payee=user),
                status='pending'
            ).count()
        }
        
        # Add wallet balance if exists
        try:
            wallet = Wallet.objects.get(user=user)
            summary['wallet_balance'] = wallet.available_balance
        except Wallet.DoesNotExist:
            summary['wallet_balance'] = Decimal('0.00')
        
        return summary
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting user payment summary: {str(e)}")
        return {}