"""
Django signals for chat functionality.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Message, Conversation, ConversationParticipant, ChatNotification


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """Handle new message creation."""
    if created and not instance.is_deleted:
        # Update conversation metadata
        conversation = instance.conversation
        conversation.last_message_at = instance.created_at
        conversation.save(update_fields=['last_message_at'])
        
        # Create notifications for other participants
        participants = conversation.participants.exclude(id=instance.sender.id)
        
        for participant in participants:
            # Get or create participant info
            participant_info, created = ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user=participant,
                defaults={'is_active': True}
            )
            
            # Only create notification if not muted and notifications enabled
            if participant_info.notifications_enabled and not participant_info.is_muted:
                ChatNotification.objects.create(
                    user=participant,
                    conversation=conversation,
                    message=instance,
                    notification_type='new_message',
                    title=f"New message from {instance.sender.email}",
                    content=instance.content[:100] + ('...' if len(instance.content) > 100 else '')
                )
        
        # Send real-time notification via WebSocket
        channel_layer = get_channel_layer()
        for participant in participants:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{participant.id}',
                {
                    'type': 'chat_notification',
                    'notification_type': 'new_message',
                    'title': f"New message from {instance.sender.email}",
                    'content': instance.content[:100] + ('...' if len(instance.content) > 100 else ''),
                    'conversation_id': str(conversation.id),
                    'message_id': str(instance.id),
                    'timestamp': instance.created_at.isoformat()
                }
            )


@receiver(post_save, sender=ConversationParticipant)
def handle_participant_join(sender, instance, created, **kwargs):
    """Handle participant joining conversation."""
    if created and instance.is_active:
        # Create notification for other participants
        other_participants = instance.conversation.participants.exclude(id=instance.user.id)
        
        for participant in other_participants:
            ChatNotification.objects.create(
                user=participant,
                conversation=instance.conversation,
                notification_type='participant_added',
                title=f"{instance.user.email} joined the conversation",
                content=f"{instance.user.email} has joined the conversation"
            )