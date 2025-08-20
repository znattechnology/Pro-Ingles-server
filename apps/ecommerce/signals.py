"""
Django signals for e-commerce models.
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Order, Product, ProductVariation, CouponUsage


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Handle order status changes and set timestamps."""
    if not created:
        # Update timestamps based on status changes
        now = timezone.now()
        
        if instance.status == 'shipped' and not instance.shipped_at:
            Order.objects.filter(pk=instance.pk).update(shipped_at=now)
        elif instance.status == 'delivered' and not instance.delivered_at:
            Order.objects.filter(pk=instance.pk).update(delivered_at=now)


@receiver(pre_save, sender=Product)
def update_product_rating(sender, instance, **kwargs):
    """Update product average rating when saved."""
    # This would be called when reviews are added/updated
    # For now, this is a placeholder for future review integration
    pass


@receiver(post_save, sender=CouponUsage)
def increment_coupon_usage(sender, instance, created, **kwargs):
    """Increment coupon usage count when a coupon is used."""
    if created:
        instance.coupon.used_count += 1
        instance.coupon.save(update_fields=['used_count'])


@receiver(post_delete, sender=CouponUsage)
def decrement_coupon_usage(sender, instance, **kwargs):
    """Decrement coupon usage count when usage is deleted."""
    instance.coupon.used_count = max(0, instance.coupon.used_count - 1)
    instance.coupon.save(update_fields=['used_count'])