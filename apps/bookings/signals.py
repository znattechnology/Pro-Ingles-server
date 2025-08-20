"""
Django signals for booking-related models.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking, BookingStatusHistory


@receiver(pre_save, sender=Booking)
def track_status_changes(sender, instance, **kwargs):
    """
    Track booking status changes before save.
    """
    if instance.pk:  # Only for updates
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Booking.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=Booking)
def handle_booking_status_change(sender, instance, created, **kwargs):
    """
    Handle booking status changes and create history records.
    """
    if created:
        # Create initial status history
        BookingStatusHistory.objects.create(
            booking=instance,
            old_status='',
            new_status=instance.status,
            automatic=True,
            reason='Initial booking creation'
        )
    else:
        # Check if status changed
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            BookingStatusHistory.objects.create(
                booking=instance,
                old_status=old_status,
                new_status=instance.status,
                automatic=True,
                reason=f'Status changed from {old_status} to {instance.status}'
            )
            
            # Set timestamps based on status
            now = timezone.now()
            if instance.status == 'confirmed' and not instance.confirmed_at:
                instance.confirmed_at = now
                # Save without triggering signals again
                Booking.objects.filter(pk=instance.pk).update(confirmed_at=now)
            elif instance.status in ['cancelled_client', 'cancelled_braider'] and not instance.cancelled_at:
                instance.cancelled_at = now
                Booking.objects.filter(pk=instance.pk).update(cancelled_at=now)
            elif instance.status == 'completed' and not instance.completed_at:
                instance.completed_at = now
                Booking.objects.filter(pk=instance.pk).update(completed_at=now)