"""
Subscription Tasks - Background jobs for subscription management.

This module contains Celery tasks for:
- Expiring subscriptions that have passed their expiration date
- Sending expiration warning emails
- Processing subscription renewals
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='apps.subscriptions.tasks.expire_subscriptions',
    max_retries=3,
    default_retry_delay=60,
)
def expire_subscriptions(self):
    """
    Transition ACTIVE/TRIAL subscriptions to EXPIRED when past expiration date.

    This task should be run periodically (e.g., hourly) via Celery Beat.
    It finds all subscriptions that:
    - Have status ACTIVE or TRIAL
    - Have expires_at < now

    And transitions them to EXPIRED status, creating history records.
    """
    from apps.subscriptions.models import UserSubscription, SubscriptionHistory

    now = timezone.now()
    expired_count = 0
    error_count = 0

    # Find subscriptions to expire
    subscriptions_to_expire = UserSubscription.objects.filter(
        status__in=['ACTIVE', 'TRIAL'],
        expires_at__lt=now
    ).select_related('plan', 'user')

    logger.info(f"Found {subscriptions_to_expire.count()} subscriptions to expire")

    for subscription in subscriptions_to_expire:
        try:
            with transaction.atomic():
                old_status = subscription.status

                # Update status to EXPIRED
                subscription.status = 'EXPIRED'
                subscription.save(update_fields=['status', 'updated_at'])

                # Create history record
                SubscriptionHistory.objects.create(
                    subscription=subscription,
                    event_type='EXPIRED',
                    previous_plan=subscription.plan,
                    new_plan=subscription.plan,
                    notes=f'Auto-expired from {old_status}. Expires_at: {subscription.expires_at}'
                )

                expired_count += 1
                logger.info(
                    f"Expired subscription {subscription.id} for user {subscription.user.username}"
                )

        except Exception as e:
            error_count += 1
            logger.error(
                f"Error expiring subscription {subscription.id}: {e}",
                exc_info=True
            )

    logger.info(f"Expiration task complete: {expired_count} expired, {error_count} errors")

    return {
        'expired': expired_count,
        'errors': error_count,
        'checked': subscriptions_to_expire.count()
    }


@shared_task(
    bind=True,
    name='apps.subscriptions.tasks.send_expiration_warnings',
    max_retries=3,
    default_retry_delay=60,
)
def send_expiration_warnings(self):
    """
    Send warning emails to users whose subscriptions are about to expire.

    This task should be run daily via Celery Beat.
    Sends warnings at:
    - 7 days before expiration
    - 3 days before expiration
    - 1 day before expiration
    """
    from apps.subscriptions.models import UserSubscription
    from datetime import timedelta

    now = timezone.now()
    warning_days = [7, 3, 1]
    warnings_sent = 0

    for days in warning_days:
        target_date = now + timedelta(days=days)
        target_date_start = target_date.replace(hour=0, minute=0, second=0)
        target_date_end = target_date.replace(hour=23, minute=59, second=59)

        subscriptions = UserSubscription.objects.filter(
            status='ACTIVE',
            expires_at__gte=target_date_start,
            expires_at__lte=target_date_end
        ).select_related('plan', 'user')

        for subscription in subscriptions:
            try:
                # TODO: Implement email sending
                # send_expiration_warning_email(subscription.user, days)
                warnings_sent += 1
                logger.info(
                    f"Would send {days}-day warning to {subscription.user.username}"
                )
            except Exception as e:
                logger.error(
                    f"Error sending warning to {subscription.user.username}: {e}"
                )

    logger.info(f"Expiration warnings task complete: {warnings_sent} warnings sent")

    return {'warnings_sent': warnings_sent}


@shared_task(
    bind=True,
    name='apps.subscriptions.tasks.reset_daily_usage',
    max_retries=3,
    default_retry_delay=60,
)
def reset_daily_usage(self):
    """
    Reset daily usage counters for all active subscriptions.

    This task runs at midnight UTC and resets:
    - daily_lessons_used
    - daily_speaking_minutes_used
    - daily_listening_minutes_used
    - daily_ai_analyses_used

    Note: This is a fallback mechanism. The primary reset happens
    in reset_daily_usage_if_needed() when users access the system.
    """
    from apps.subscriptions.models import UserSubscription

    today = timezone.now().date()

    # Only reset for subscriptions that haven't been reset today
    updated = UserSubscription.objects.filter(
        status__in=['ACTIVE', 'TRIAL'],
        last_reset_date__lt=today
    ).update(
        daily_lessons_used=0,
        daily_speaking_minutes_used=0,
        daily_listening_minutes_used=0,
        daily_ai_analyses_used=0,
        last_reset_date=today
    )

    logger.info(f"Reset daily usage for {updated} subscriptions")

    return {'reset_count': updated}


@shared_task(
    bind=True,
    name='apps.subscriptions.tasks.recharge_hearts',
    max_retries=3,
    default_retry_delay=60,
)
def recharge_hearts(self):
    """
    Recharge hearts for all active subscriptions based on their plan's recharge rate.

    This task runs hourly and adds hearts based on time elapsed since last recharge.
    """
    from apps.subscriptions.models import UserSubscription

    now = timezone.now()
    recharged_count = 0

    subscriptions = UserSubscription.objects.filter(
        status__in=['ACTIVE', 'TRIAL']
    ).select_related('plan')

    for subscription in subscriptions:
        try:
            plan = subscription.plan

            # Skip if unlimited hearts
            if plan.hearts_limit == 0:
                continue

            # Skip if already at max
            if subscription.current_hearts >= plan.hearts_limit:
                continue

            # Calculate hearts to add
            hours_since_recharge = (now - subscription.last_heart_recharge).total_seconds() / 3600
            hearts_to_add = int(hours_since_recharge / plan.hearts_recharge_hours)

            if hearts_to_add > 0:
                new_hearts = min(
                    subscription.current_hearts + hearts_to_add,
                    plan.hearts_limit
                )
                subscription.current_hearts = new_hearts
                subscription.last_heart_recharge = now
                subscription.save(update_fields=['current_hearts', 'last_heart_recharge'])
                recharged_count += 1

        except Exception as e:
            logger.error(
                f"Error recharging hearts for subscription {subscription.id}: {e}"
            )

    logger.info(f"Heart recharge task complete: {recharged_count} subscriptions recharged")

    return {'recharged': recharged_count}
