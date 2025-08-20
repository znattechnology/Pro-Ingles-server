"""
Django signals for user-related models.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
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