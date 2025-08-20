"""
Django signals for braider-related models.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Braider


@receiver(pre_save, sender=Braider)
def set_approval_timestamp(sender, instance, **kwargs):
    """
    Set approved_at timestamp when status changes to approved.
    """
    if instance.pk:  # Only for updates, not new instances
        try:
            old_instance = Braider.objects.get(pk=instance.pk)
            # If status changed to approved and wasn't approved before
            if (instance.status == 'approved' and 
                old_instance.status != 'approved' and 
                not instance.approved_at):
                instance.approved_at = timezone.now()
        except Braider.DoesNotExist:
            pass


@receiver(post_save, sender=Braider)
def handle_braider_approval(sender, instance, created, **kwargs):
    """
    Handle actions when braider is approved.
    """
    if not created and instance.status == 'approved':
        # Here you could send approval email, create notifications, etc.
        # For now, we'll just ensure the user role is set correctly
        if instance.user and instance.user.role != 'braider':
            instance.user.role = 'braider'
            instance.user.save(update_fields=['role'])