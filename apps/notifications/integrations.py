"""
Integration helpers for connecting notifications with other apps.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    Notification, NotificationTemplate, NotificationChannel, 
    NotificationCategory, UserNotificationPreference
)
from .tasks import send_notification

User = get_user_model()


class NotificationIntegrator:
    """Helper class for creating notifications from other apps."""
    
    @staticmethod
    def send_booking_notification(booking, notification_type, **extra_context):
        """Send booking-related notifications."""
        try:
            # Get template and channel
            template = NotificationTemplate.objects.get(
                name=f'booking_{notification_type}',
                is_active=True
            )
            
            # Determine channel based on urgency
            if notification_type in ['confirmed', 'cancelled']:
                channel = NotificationChannel.objects.get(
                    name='email_default', is_active=True
                )
                priority = 3  # High
            else:
                channel = NotificationChannel.objects.get(
                    name='push_default', is_active=True
                )
                priority = 2  # Normal
            
            category = NotificationCategory.objects.get(name='booking')
            
            # Create context
            context = {
                'booking': booking,
                'user': booking.client,
                **extra_context
            }
            
            # Create notification for client
            client_notification = Notification.objects.create(
                recipient=booking.client,
                title=template.render_subject(context),
                message=template.render_body(context),
                html_content=template.render_html(context) or '',
                category=category,
                template=template,
                channel=channel,
                priority=priority,
                data={
                    'booking_id': str(booking.id),
                    'notification_type': notification_type,
                    **extra_context
                }
            )
            
            # Create notification for braider if assigned
            if booking.braider:
                braider_context = {
                    'booking': booking,
                    'user': booking.braider.user,
                    **extra_context
                }
                
                braider_notification = Notification.objects.create(
                    recipient=booking.braider.user,
                    title=template.render_subject(braider_context),
                    message=template.render_body(braider_context),
                    html_content=template.render_html(braider_context) or '',
                    category=category,
                    template=template,
                    channel=channel,
                    priority=priority,
                    data={
                        'booking_id': str(booking.id),
                        'notification_type': notification_type,
                        **extra_context
                    }
                )
            
        except Exception as e:
            # Log error but don't fail the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send booking notification: {str(e)}")
    
    @staticmethod
    def send_chat_notification(message, **extra_context):
        """Send chat message notifications."""
        try:
            template = NotificationTemplate.objects.get(
                name='new_message', is_active=True
            )
            channel = NotificationChannel.objects.get(
                name='push_default', is_active=True
            )
            category = NotificationCategory.objects.get(name='chat')
            
            # Send to all participants except sender
            participants = message.conversation.participants.exclude(id=message.sender.id)
            
            for participant in participants:
                # Check user preferences
                preferences = getattr(participant, 'notification_preferences', None)
                if preferences and not preferences.should_receive_notification('push', 'chat'):
                    continue
                
                # Create notification
                notification = Notification.objects.create(
                    recipient=participant,
                    title=f"Nova mensagem de {message.sender.get_full_name() or message.sender.email}",
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
                        **extra_context
                    }
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send chat notification: {str(e)}")
    
    @staticmethod
    def send_rating_notification(rating, **extra_context):
        """Send rating notifications."""
        try:
            template = NotificationTemplate.objects.get(
                name='new_rating', is_active=True
            )
            channel = NotificationChannel.objects.get(
                name='email_default', is_active=True
            )
            category = NotificationCategory.objects.get(name='rating')
            
            # Send to braider
            context = {
                'user': rating.braider.user,
                'stars': rating.stars,
                'comment': getattr(rating, 'comment', ''),
                **extra_context
            }
            
            notification = Notification.objects.create(
                recipient=rating.braider.user,
                title=f"Nova avaliação: {rating.stars} estrelas",
                message=f"Você recebeu uma avaliação de {rating.stars} estrelas!",
                category=category,
                template=template,
                channel=channel,
                priority=2,
                data={
                    'rating_id': str(rating.id),
                    'stars': rating.stars,
                    'booking_id': str(rating.booking.id) if hasattr(rating, 'booking') and rating.booking else None,
                    **extra_context
                }
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send rating notification: {str(e)}")
    
    @staticmethod
    def send_welcome_notification(user, **extra_context):
        """Send welcome notification to new users."""
        try:
            template = NotificationTemplate.objects.get(
                name='welcome', is_active=True
            )
            channel = NotificationChannel.objects.get(
                name='email_default', is_active=True
            )
            category = NotificationCategory.objects.get(name='system')
            
            context = {
                'user': user,
                **extra_context
            }
            
            notification = Notification.objects.create(
                recipient=user,
                title="Bem-vindo à Tuwi Beauty!",
                message=template.render_body(context),
                html_content=template.render_html(context) or '',
                category=category,
                template=template,
                channel=channel,
                priority=2,
                data={
                    'welcome': True,
                    'user_id': str(user.id),
                    **extra_context
                }
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send welcome notification: {str(e)}")
    
    @staticmethod
    def send_system_notification(user, title, message, priority=2, **extra_context):
        """Send system notification."""
        try:
            channel = NotificationChannel.objects.get(
                name='in_app_default', is_active=True
            )
            category = NotificationCategory.objects.get(name='system')
            
            notification = Notification.objects.create(
                recipient=user,
                title=title,
                message=message,
                category=category,
                channel=channel,
                priority=priority,
                data={
                    'system_notification': True,
                    **extra_context
                }
            )
            
            return notification
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send system notification: {str(e)}")
            return None
    
    @staticmethod
    def schedule_notification(user, title, message, scheduled_at, category_name='system', **extra_context):
        """Schedule a notification for later delivery."""
        try:
            channel = NotificationChannel.objects.get(
                name='push_default', is_active=True
            )
            category = NotificationCategory.objects.get(name=category_name)
            
            notification = Notification.objects.create(
                recipient=user,
                title=title,
                message=message,
                category=category,
                channel=channel,
                priority=2,
                scheduled_at=scheduled_at,
                data={
                    'scheduled': True,
                    **extra_context
                }
            )
            
            return notification
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to schedule notification: {str(e)}")
            return None
    
    @staticmethod
    def send_bulk_notification(user_emails, title, message, category_name='marketing', **extra_context):
        """Send bulk notification to multiple users."""
        try:
            from .models import NotificationBatch
            
            template = NotificationTemplate.objects.get(
                name='marketing_default', is_active=True
            )
            channel = NotificationChannel.objects.get(
                name='email_default', is_active=True
            )
            category = NotificationCategory.objects.get(name=category_name)
            
            # Create batch
            batch = NotificationBatch.objects.create(
                name=f"Bulk notification - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                template=template,
                channel=channel,
                category=category,
                recipient_count=len(user_emails),
                context_data={'title': title, 'message': message, **extra_context},
                recipient_data=[{'email': email} for email in user_emails]
            )
            
            # Process batch
            batch.process_batch()
            
            return batch
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send bulk notification: {str(e)}")
            return None


# Convenience functions for easy integration
def notify_booking_confirmed(booking, **kwargs):
    """Shortcut to send booking confirmation notification."""
    NotificationIntegrator.send_booking_notification(booking, 'confirmation', **kwargs)

def notify_booking_cancelled(booking, **kwargs):
    """Shortcut to send booking cancellation notification."""
    NotificationIntegrator.send_booking_notification(booking, 'cancellation', **kwargs)

def notify_booking_reminder(booking, **kwargs):
    """Shortcut to send booking reminder notification."""
    NotificationIntegrator.send_booking_notification(booking, 'reminder', **kwargs)

def notify_new_message(message, **kwargs):
    """Shortcut to send new message notification."""
    NotificationIntegrator.send_chat_notification(message, **kwargs)

def notify_new_rating(rating, **kwargs):
    """Shortcut to send new rating notification."""
    NotificationIntegrator.send_rating_notification(rating, **kwargs)

def notify_welcome(user, **kwargs):
    """Shortcut to send welcome notification."""
    NotificationIntegrator.send_welcome_notification(user, **kwargs)

def notify_system(user, title, message, **kwargs):
    """Shortcut to send system notification."""
    return NotificationIntegrator.send_system_notification(user, title, message, **kwargs)