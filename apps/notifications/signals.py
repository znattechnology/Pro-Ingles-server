"""
Signals for notification system integration.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    UserNotificationPreference, Notification, NotificationCategory
)
from .tasks import send_notification

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences when user is created."""
    if created:
        UserNotificationPreference.objects.create(user=instance)


@receiver(post_save, sender=Notification)
def process_notification_on_creation(sender, instance, created, **kwargs):
    """Process notification when it's created."""
    if created and instance.status == 'pending':
        # If no scheduled time, send immediately
        if not instance.scheduled_at:
            send_notification.delay(instance.id)


# Integration signals for other apps
def create_booking_notification(booking, notification_type, **context):
    """Create notification for booking events."""
    from apps.bookings.models import Booking
    
    # Notification templates mapping
    template_mapping = {
        'booking_confirmed': 'booking_confirmation',
        'booking_cancelled': 'booking_cancellation', 
        'booking_reminder': 'booking_reminder',
        'payment_received': 'payment_confirmation',
        'braider_assigned': 'braider_assignment',
    }
    
    template_name = template_mapping.get(notification_type)
    if not template_name:
        return
    
    try:
        from .models import NotificationTemplate, NotificationChannel
        
        # Get email template and channel
        template = NotificationTemplate.objects.get(name=template_name, is_active=True)
        channel = NotificationChannel.objects.get(channel_type='email', is_active=True)
        category = NotificationCategory.objects.get(name='booking')
        
        # Create notification for client
        client_notification = Notification.objects.create(
            recipient=booking.client,
            title=template.render_subject({
                'booking': booking,
                'user': booking.client,
                **context
            }),
            message=template.render_body({
                'booking': booking,
                'user': booking.client,
                **context
            }),
            html_content=template.render_html({
                'booking': booking, 
                'user': booking.client,
                **context
            }) if template.html_template else '',
            category=category,
            template=template,
            channel=channel,
            priority=3 if notification_type in ['booking_confirmed', 'payment_received'] else 2,
            data={
                'booking_id': str(booking.id),
                'notification_type': notification_type,
                **context
            }
        )
        
        # Create notification for braider if assigned
        if booking.braider:
            braider_notification = Notification.objects.create(
                recipient=booking.braider.user,
                title=template.render_subject({
                    'booking': booking,
                    'user': booking.braider.user,
                    **context
                }),
                message=template.render_body({
                    'booking': booking,
                    'user': booking.braider.user,
                    **context
                }),
                html_content=template.render_html({
                    'booking': booking,
                    'user': booking.braider.user,
                    **context
                }) if template.html_template else '',
                category=category,
                template=template,
                channel=channel,
                priority=3 if notification_type in ['booking_confirmed'] else 2,
                data={
                    'booking_id': str(booking.id),
                    'notification_type': notification_type,
                    **context
                }
            )
        
    except Exception as e:
        # Log error but don't fail the main operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create booking notification: {str(e)}")


def create_chat_notification(message, **context):
    """Create notification for new chat messages."""
    from apps.chat.models import Message
    
    try:
        from .models import NotificationTemplate, NotificationChannel
        
        # Get template and channel
        template = NotificationTemplate.objects.get(name='new_message', is_active=True)
        channel = NotificationChannel.objects.get(channel_type='push', is_active=True)
        category = NotificationCategory.objects.get(name='chat')
        
        # Create notifications for all participants except sender
        participants = message.conversation.participants.exclude(id=message.sender.id)
        
        for participant in participants:
            # Check if user wants to receive chat notifications
            try:
                preferences = participant.notification_preferences
                if not preferences.should_receive_notification('push', 'chat'):
                    continue
            except:
                pass  # Create notification if no preferences exist
            
            notification = Notification.objects.create(
                recipient=participant,
                title=f"New message from {message.sender.get_full_name() or message.sender.email}",
                message=message.content[:100] + ('...' if len(message.content) > 100 else ''),
                category=category,
                template=template,
                channel=channel,
                priority=2,
                data={
                    'conversation_id': str(message.conversation.id),
                    'message_id': str(message.id),
                    'sender_id': str(message.sender.id),
                    'sender_name': message.sender.get_full_name() or message.sender.email,
                    **context
                }
            )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create chat notification: {str(e)}")


def create_rating_notification(rating, **context):
    """Create notification for new ratings."""
    from apps.ratings.models import Rating
    
    try:
        from .models import NotificationTemplate, NotificationChannel
        
        # Get template and channel
        template = NotificationTemplate.objects.get(name='new_rating', is_active=True)
        channel = NotificationChannel.objects.get(channel_type='email', is_active=True)
        category = NotificationCategory.objects.get(name='rating')
        
        # Notify the braider about new rating
        notification = Notification.objects.create(
            recipient=rating.braider.user,
            title=f"New {rating.stars}-star rating received",
            message=f"You received a {rating.stars}-star rating for your service.",
            category=category,
            template=template,
            channel=channel,
            priority=2,
            data={
                'rating_id': str(rating.id),
                'stars': rating.stars,
                'booking_id': str(rating.booking.id) if rating.booking else None,
                **context
            }
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create rating notification: {str(e)}")


def create_system_notification(user, notification_type, title, message, **context):
    """Create system notification for user."""
    try:
        from .models import NotificationChannel
        
        # Get in-app channel
        channel = NotificationChannel.objects.get(channel_type='in_app', is_active=True)
        category = NotificationCategory.objects.get(name='system')
        
        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            category=category,
            channel=channel,
            priority=3 if notification_type == 'security' else 2,
            data={
                'notification_type': notification_type,
                **context
            }
        )
        
        return notification
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create system notification: {str(e)}")
        return None