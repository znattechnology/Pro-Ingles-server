"""
Celery tasks for payment processing.
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal
import logging

from .models import Payment, PaymentSplit, Refund, Wallet, PaymentIntent, PaymentAccount
from .services import StripeService, PaymentService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_payment_splits(self, payment_id):
    """Process payment splits after successful payment."""
    try:
        payment = Payment.objects.select_related('payer', 'payee', 'booking').get(id=payment_id)
        
        if payment.status != 'succeeded':
            logger.info(f"Payment {payment_id} not succeeded, skipping splits")
            return
        
        if payment.splits.exists():
            logger.info(f"Payment {payment_id} splits already processed")
            return
        
        PaymentService.process_payment_splits(payment)
        logger.info(f"Successfully processed splits for payment {payment_id}")
        
    except Payment.DoesNotExist:
        logger.error(f"Payment {payment_id} not found")
    except Exception as exc:
        logger.error(f"Error processing payment splits for {payment_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=exc)
        raise


@shared_task(bind=True, max_retries=3)
def process_refund(self, refund_id):
    """Process refund asynchronously."""
    try:
        refund = Refund.objects.select_related('payment').get(id=refund_id)
        
        if refund.status != 'pending':
            logger.info(f"Refund {refund_id} already processed")
            return
        
        refund.status = 'processing'
        refund.save()
        
        # Process Stripe refund
        if refund.payment.intent and refund.payment.intent.external_intent_id:
            stripe_refund = StripeService.create_refund(
                payment_intent_id=refund.payment.intent.external_intent_id,
                amount=refund.amount,
                reason=refund.reason
            )
            
            refund.external_refund_id = stripe_refund.id
            refund.status = 'succeeded' if stripe_refund.status == 'succeeded' else 'processing'
            if refund.status == 'succeeded':
                refund.processed_at = timezone.now()
            refund.save()
            
            # Update payment status
            if refund.amount == refund.payment.amount:
                refund.payment.status = 'refunded'
            else:
                refund.payment.status = 'partially_refunded'
            refund.payment.refunded_at = timezone.now()
            refund.payment.save()
            
            logger.info(f"Successfully processed refund {refund_id}")
        
    except Refund.DoesNotExist:
        logger.error(f"Refund {refund_id} not found")
    except Exception as exc:
        logger.error(f"Error processing refund {refund_id}: {str(exc)}")
        try:
            refund = Refund.objects.get(id=refund_id)
            refund.status = 'failed'
            refund.failure_reason = str(exc)
            refund.save()
        except:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=exc)
        raise


@shared_task
def process_pending_payments():
    """Process pending payments and update their status."""
    pending_payments = Payment.objects.filter(
        status='pending',
        created_at__lt=timezone.now() - timezone.timedelta(hours=24)
    )
    
    processed_count = 0
    failed_count = 0
    
    for payment in pending_payments:
        try:
            # Check payment intent status
            if payment.intent and payment.intent.external_intent_id:
                import stripe
                stripe_intent = stripe.PaymentIntent.retrieve(payment.intent.external_intent_id)
                
                if stripe_intent.status == 'succeeded':
                    payment.mark_as_succeeded(
                        external_id=stripe_intent.latest_charge,
                        provider_response=stripe_intent
                    )
                    processed_count += 1
                elif stripe_intent.status in ['canceled', 'failed']:
                    payment.mark_as_failed(
                        reason=stripe_intent.get('last_payment_error', {}).get('message', 'Payment failed')
                    )
                    failed_count += 1
            else:
                # Mark as failed if no intent after 24 hours
                payment.mark_as_failed("No payment intent found")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Error processing pending payment {payment.id}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Processed pending payments: {processed_count} succeeded, {failed_count} failed")
    return {'processed': processed_count, 'failed': failed_count}


@shared_task
def update_payment_account_status():
    """Update payment account status from Stripe."""
    accounts = PaymentAccount.objects.filter(
        account_type='stripe_account',
        stripe_account_id__isnull=False
    )
    
    updated_count = 0
    
    for account in accounts:
        try:
            import stripe
            stripe_account = stripe.Account.retrieve(account.stripe_account_id)
            
            # Update status based on Stripe data
            old_status = account.status
            
            if stripe_account.charges_enabled and stripe_account.payouts_enabled:
                account.status = 'active'
                account.can_receive_payments = True
                account.can_instant_payout = stripe_account.get('capabilities', {}).get('transfers') == 'active'
            else:
                account.status = 'restricted'
                account.can_receive_payments = False
            
            account.is_verified = stripe_account.get('details_submitted', False)
            
            if old_status != account.status:
                account.save()
                updated_count += 1
                
                # Send notification if status changed
                try:
                    from apps.notifications.integrations import notify_system
                    if account.status == 'active':
                        notify_system(
                            account.user,
                            "Conta de Pagamento Ativada",
                            "Sua conta de pagamento foi ativada e você já pode receber pagamentos!",
                            priority=3
                        )
                    elif account.status == 'restricted':
                        notify_system(
                            account.user,
                            "Conta de Pagamento Restrita",
                            "Sua conta de pagamento foi restrita. Por favor, complete a verificação.",
                            priority=3
                        )
                except Exception as e:
                    logger.error(f"Error sending account status notification: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error updating account status for {account.id}: {str(e)}")
    
    logger.info(f"Updated {updated_count} payment account statuses")
    return updated_count


@shared_task
def calculate_daily_commissions():
    """Calculate and record daily platform commissions."""
    yesterday = timezone.now().date() - timezone.timedelta(days=1)
    
    # Get successful payments from yesterday
    daily_payments = Payment.objects.filter(
        status='succeeded',
        processed_at__date=yesterday,
        payment_type__in=['booking_payment', 'tip']
    )
    
    total_commission = Decimal('0.00')
    commission_count = 0
    
    with transaction.atomic():
        for payment in daily_payments:
            # Check if commission already calculated
            if Payment.objects.filter(
                payment_type='commission',
                metadata__original_payment_id=str(payment.id)
            ).exists():
                continue
            
            commission_rate = Decimal('0.05')  # 5%
            commission_amount = payment.platform_fee
            
            if commission_amount > 0:
                # Create commission record
                commission_payment = Payment.objects.create(
                    payer=payment.payee,  # Braider pays
                    payee=None,  # Platform receives
                    amount=commission_amount,
                    currency=payment.currency,
                    payment_type='commission',
                    status='succeeded',
                    processed_at=timezone.now(),
                    description=f'Platform commission for {payment.internal_reference}',
                    metadata={
                        'original_payment_id': str(payment.id),
                        'commission_date': yesterday.isoformat(),
                        'commission_rate': float(commission_rate)
                    }
                )
                
                total_commission += commission_amount
                commission_count += 1
    
    logger.info(f"Calculated daily commissions: €{total_commission} from {commission_count} payments")
    return {
        'date': yesterday.isoformat(),
        'total_commission': float(total_commission),
        'commission_count': commission_count
    }


@shared_task
def process_wallet_settlements():
    """Process wallet settlements for braiders."""
    # Find wallets with significant balances
    wallets_to_settle = Wallet.objects.filter(
        available_balance__gte=Decimal('50.00'),  # Minimum €50 to settle
        is_active=True,
        is_frozen=False
    )
    
    settled_count = 0
    total_settled = Decimal('0.00')
    
    for wallet in wallets_to_settle:
        try:
            # Check if user has active payment account
            payment_account = PaymentAccount.objects.filter(
                user=wallet.user,
                status='active',
                can_receive_payments=True
            ).first()
            
            if not payment_account:
                continue
            
            settlement_amount = wallet.available_balance
            
            # Create settlement transfer
            if payment_account.account_type == 'stripe_account':
                try:
                    transfer = StripeService.create_transfer(
                        amount=settlement_amount,
                        destination_account=payment_account.stripe_account_id,
                        metadata={
                            'wallet_settlement': True,
                            'user_id': str(wallet.user.id),
                            'settlement_date': timezone.now().isoformat()
                        }
                    )
                    
                    # Deduct from wallet
                    wallet.deduct_funds(
                        settlement_amount,
                        f"Settlement to {payment_account.account_type}"
                    )
                    
                    # Create settlement payment record
                    Payment.objects.create(
                        payer=None,  # Platform pays
                        payee=wallet.user,
                        amount=settlement_amount,
                        currency='EUR',
                        payment_type='payout',
                        status='succeeded',
                        processed_at=timezone.now(),
                        external_id=transfer.id,
                        description=f'Wallet settlement for {wallet.user.email}',
                        metadata={
                            'wallet_settlement': True,
                            'transfer_id': transfer.id
                        }
                    )
                    
                    settled_count += 1
                    total_settled += settlement_amount
                    
                    # Send notification
                    try:
                        from apps.notifications.integrations import notify_system
                        notify_system(
                            wallet.user,
                            "Transferência Processada",
                            f"Sua transferência de €{settlement_amount} foi processada com sucesso!",
                            priority=3
                        )
                    except Exception as e:
                        logger.error(f"Error sending settlement notification: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error processing wallet settlement for {wallet.user.id}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in wallet settlement for {wallet.id}: {str(e)}")
    
    logger.info(f"Processed wallet settlements: {settled_count} settlements, €{total_settled} total")
    return {
        'settled_count': settled_count,
        'total_settled': float(total_settled)
    }


@shared_task
def cleanup_old_payment_intents():
    """Clean up old payment intents."""
    # Clean up old failed/cancelled payment intents
    cutoff_date = timezone.now() - timezone.timedelta(days=7)
    
    old_intents = PaymentIntent.objects.filter(
        status__in=['failed', 'cancelled'],
        created_at__lt=cutoff_date
    )
    
    deleted_count = old_intents.count()
    old_intents.delete()
    
    logger.info(f"Cleaned up {deleted_count} old payment intents")
    return deleted_count


@shared_task
def generate_payment_reports():
    """Generate daily payment reports."""
    yesterday = timezone.now().date() - timezone.timedelta(days=1)
    
    # Calculate statistics
    daily_stats = {
        'date': yesterday.isoformat(),
        'total_payments': Payment.objects.filter(
            created_at__date=yesterday
        ).count(),
        'successful_payments': Payment.objects.filter(
            created_at__date=yesterday,
            status='succeeded'
        ).count(),
        'failed_payments': Payment.objects.filter(
            created_at__date=yesterday,
            status='failed'
        ).count(),
        'total_volume': float(Payment.objects.filter(
            created_at__date=yesterday,
            status='succeeded'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')),
        'total_fees': float(Payment.objects.filter(
            created_at__date=yesterday,
            status='succeeded'
        ).aggregate(
            total=models.Sum('platform_fee')
        )['total'] or Decimal('0.00')),
        'refunds': Refund.objects.filter(
            created_at__date=yesterday,
            status='succeeded'
        ).count(),
        'new_wallets': Wallet.objects.filter(
            created_at__date=yesterday
        ).count()
    }
    
    logger.info(f"Generated payment report for {yesterday}: {daily_stats}")
    
    # You could store this in a reporting table or send to external system
    return daily_stats


@shared_task
def sync_stripe_events():
    """Sync recent Stripe events to ensure consistency."""
    try:
        import stripe
        from datetime import timedelta
        
        # Get events from last hour
        created_since = int((timezone.now() - timedelta(hours=1)).timestamp())
        
        events = stripe.Event.list(
            created={'gte': created_since},
            limit=100
        )
        
        processed_count = 0
        
        for event in events:
            try:
                # Process only relevant event types
                if event.type == 'payment_intent.succeeded':
                    # Find and update payment intent
                    try:
                        intent = PaymentIntent.objects.get(
                            external_intent_id=event.data.object.id
                        )
                        if intent.status != 'succeeded':
                            intent.status = 'succeeded'
                            intent.save()
                            processed_count += 1
                    except PaymentIntent.DoesNotExist:
                        pass
                
                elif event.type == 'transfer.created':
                    # Update payment split status
                    transfer_id = event.data.object.id
                    split = PaymentSplit.objects.filter(transfer_id=transfer_id).first()
                    if split and split.status != 'processed':
                        split.status = 'processed'
                        split.processed_at = timezone.now()
                        split.save()
                        processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing Stripe event {event.id}: {str(e)}")
        
        logger.info(f"Synced {processed_count} Stripe events")
        return processed_count
        
    except Exception as e:
        logger.error(f"Error syncing Stripe events: {str(e)}")
        return 0