"""
Celery tasks for chat functionality.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import TypingIndicator, ChatNotification

logger = logging.getLogger(__name__)


@shared_task
def cleanup_stale_typing_indicators():
    """
    Clean up stale typing indicators.
    This task should run every 2 minutes to keep the database clean.
    """
    try:
        # Clean indicators older than 30 seconds
        cleaned_count = TypingIndicator.cleanup_stale_indicators(max_age_seconds=30)
        
        logger.info(f"Cleaned up {cleaned_count} stale typing indicators")
        
        # Also clean up very old indicators completely (older than 1 hour)
        cutoff_time = timezone.now() - timedelta(hours=1)
        deleted_count = TypingIndicator.objects.filter(
            last_activity__lt=cutoff_time
        ).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old typing indicator records")
        
        return {
            'cleaned_stale': cleaned_count,
            'deleted_old': deleted_count,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error cleaning typing indicators: {str(e)}")
        return {
            'error': str(e),
            'success': False
        }


@shared_task
def send_chat_notification(notification_id):
    """
    Send a chat notification via push/email.
    
    Args:
        notification_id: ID of ChatNotification to send
    """
    try:
        notification = ChatNotification.objects.get(id=notification_id)
        
        if notification.is_sent:
            logger.warning(f"Notification {notification_id} already sent")
            return {'already_sent': True}
        
        # Import notification service
        from apps.notifications.services import NotificationService
        
        # Create push notification
        notification_service = NotificationService()
        
        success = notification_service.send_push_notification(
            user=notification.user,
            title=notification.title,
            message=notification.content,
            data={
                'type': 'chat',
                'conversation_id': str(notification.conversation.id),
                'message_id': str(notification.message.id) if notification.message else None,
                'notification_type': notification.notification_type
            }
        )
        
        if success:
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save(update_fields=['is_sent', 'sent_at'])
            
            logger.info(f"Chat notification {notification_id} sent successfully")
            
        return {
            'notification_id': notification_id,
            'sent': success,
            'success': True
        }
        
    except ChatNotification.DoesNotExist:
        logger.error(f"Chat notification {notification_id} not found")
        return {
            'error': 'Notification not found',
            'success': False
        }
    except Exception as e:
        logger.error(f"Error sending chat notification {notification_id}: {str(e)}")
        return {
            'error': str(e),
            'success': False
        }


@shared_task
def process_message_mentions(message_id):
    """
    Process @mentions in a message and create notifications.
    
    Args:
        message_id: ID of Message to process for mentions
    """
    try:
        from .models import Message
        from apps.users.models import User
        import re
        
        message = Message.objects.get(id=message_id)
        
        # Find @mentions in message content
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, message.content)
        
        if not mentions:
            return {'mentions_found': 0, 'success': True}
        
        notifications_created = 0
        
        for mention in mentions:
            try:
                # Try to find user by username (email prefix) or name
                mentioned_user = User.objects.filter(
                    Q(email__istartswith=mention) |
                    Q(name__icontains=mention)
                ).first()
                
                if mentioned_user and mentioned_user in message.conversation.participants.all():
                    # Create mention notification
                    notification = ChatNotification.objects.create(
                        user=mentioned_user,
                        conversation=message.conversation,
                        message=message,
                        notification_type='mention',
                        title=f"Mentioned by {message.sender.name}",
                        content=f"You were mentioned in a conversation: {message.content[:100]}"
                    )
                    
                    # Schedule notification to be sent
                    send_chat_notification.delay(notification.id)
                    notifications_created += 1
                    
            except Exception as e:
                logger.warning(f"Error processing mention '{mention}': {str(e)}")
                continue
        
        logger.info(f"Processed {len(mentions)} mentions, created {notifications_created} notifications")
        
        return {
            'mentions_found': len(mentions),
            'notifications_created': notifications_created,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error processing message mentions {message_id}: {str(e)}")
        return {
            'error': str(e),
            'success': False
        }


@shared_task
def update_conversation_stats():
    """
    Update conversation statistics like message count, last message time, etc.
    This task should run every 10 minutes.
    """
    try:
        from .models import Conversation, Message
        from django.db.models import Count, Max
        
        # Update conversations with latest message stats
        conversations = Conversation.objects.annotate(
            msg_count=Count('messages'),
            last_msg_time=Max('messages__created_at')
        )
        
        updated_count = 0
        
        for conv in conversations:
            if conv.total_messages != conv.msg_count or conv.last_message_at != conv.last_msg_time:
                conv.total_messages = conv.msg_count or 0
                conv.last_message_at = conv.last_msg_time
                conv.save(update_fields=['total_messages', 'last_message_at'])
                updated_count += 1
        
        logger.info(f"Updated stats for {updated_count} conversations")
        
        return {
            'conversations_updated': updated_count,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error updating conversation stats: {str(e)}")
        return {
            'error': str(e),
            'success': False
        }


@shared_task
def cleanup_old_chat_data():
    """
    Clean up old chat data (notifications, typing indicators, etc.).
    This task should run daily.
    """
    try:
        from datetime import timedelta
        
        # Clean up old read notifications (older than 30 days)
        cutoff_time = timezone.now() - timedelta(days=30)
        
        old_notifications = ChatNotification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_time
        )
        deleted_notifications = old_notifications.count()
        old_notifications.delete()
        
        # Clean up all old typing indicators (older than 1 day)
        old_typing = TypingIndicator.objects.filter(
            last_activity__lt=timezone.now() - timedelta(days=1)
        )
        deleted_typing = old_typing.count()
        old_typing.delete()
        
        logger.info(f"Cleaned up {deleted_notifications} old notifications, {deleted_typing} old typing indicators")
        
        return {
            'deleted_notifications': deleted_notifications,
            'deleted_typing_indicators': deleted_typing,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old chat data: {str(e)}")
        return {
            'error': str(e),
            'success': False
        }