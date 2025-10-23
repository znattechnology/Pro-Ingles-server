"""
Django signals for user-related models.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import User, NotificationSettings


@receiver(post_save, sender=User)
def create_user_notification_settings(sender, instance, created, **kwargs):
    """
    Create default notification settings when a new user is created.
    """
    if created:
        NotificationSettings.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_notification_settings(sender, instance, **kwargs):
    """
    Ensure notification settings exist for all users.
    """
    if not hasattr(instance, 'notification_settings'):
        NotificationSettings.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_default_subscription(sender, instance, created, **kwargs):
    """
    Create default FREE subscription when a new user is created.
    This ensures all users have a subscription record for proper counting.
    """
    if created:
        try:
            from apps.subscriptions.models import SubscriptionPlan, UserSubscription
            
            # Get the FREE plan
            free_plan = SubscriptionPlan.objects.filter(plan_type='FREE').first()
            if free_plan:
                # Create subscription with 1 year expiry for free plan
                expires_at = timezone.now() + timedelta(days=365)
                
                UserSubscription.objects.create(
                    user=instance,
                    plan=free_plan,
                    status='ACTIVE',
                    expires_at=expires_at,
                    current_hearts=free_plan.hearts_limit
                )
        except Exception as e:
            # Log error but don't fail user creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create default subscription for user {instance.id}: {e}")