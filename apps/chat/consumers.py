"""
WebSocket consumers for real-time chat functionality.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import Conversation, Message, ConversationParticipant

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat functionality."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope["user"]
        
        # Reject anonymous users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # Verify user has access to this conversation
        has_access = await self.check_conversation_access()
        if not has_access:
            await self.close()
            return
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Mark user as online
        await self.set_user_online_status(True)
        
        # Send user join notification to group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'online',
                'username': self.user.email
            }
        )
        
        logger.info(f"User {self.user.email} connected to conversation {self.conversation_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'conversation_group_name'):
            # Mark user as offline
            await self.set_user_online_status(False)
            
            # Send user leave notification to group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_status',
                    'user_id': str(self.user.id),
                    'status': 'offline',
                    'username': self.user.email
                }
            )
            
            # Leave conversation group
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.email} disconnected from conversation {self.conversation_id}")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'send_message':
                await self.handle_send_message(text_data_json)
            elif action == 'mark_as_read':
                await self.handle_mark_as_read(text_data_json)
            elif action == 'typing':
                await self.handle_typing(text_data_json)
            elif action == 'edit_message':
                await self.handle_edit_message(text_data_json)
            elif action == 'delete_message':
                await self.handle_delete_message(text_data_json)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid action'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Server error'
            }))
    
    async def handle_send_message(self, data):
        """Handle sending a new message."""
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to')
        
        if not content and message_type == 'text':
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content cannot be empty'
            }))
            return
        
        # Create message in database
        message = await self.create_message(
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id
        )
        
        if message:
            # Send message to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(message.id),
                    'sender_id': str(self.user.id),
                    'sender_name': self.get_user_display_name(),
                    'content': message.content,
                    'message_type': message.message_type,
                    'reply_to': str(message.reply_to.id) if message.reply_to else None,
                    'timestamp': message.created_at.isoformat(),
                    'is_edited': False
                }
            )
    
    async def handle_mark_as_read(self, data):
        """Handle marking messages as read."""
        await self.mark_conversation_as_read()
        
        # Notify other participants that messages were read
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'messages_read',
                'user_id': str(self.user.id),
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_typing(self, data):
        """Handle typing indicators."""
        is_typing = data.get('is_typing', False)
        
        # Send typing status to other participants
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_status',
                'user_id': str(self.user.id),
                'username': self.user.email,
                'is_typing': is_typing
            }
        )
    
    async def handle_edit_message(self, data):
        """Handle editing a message."""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        
        if not message_id or not new_content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message ID and content required'
            }))
            return
        
        # Edit message in database
        success = await self.edit_message(message_id, new_content)
        
        if success:
            # Notify group about message edit
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'content': new_content,
                    'edited_by': str(self.user.id),
                    'edited_at': timezone.now().isoformat()
                }
            )
    
    async def handle_delete_message(self, data):
        """Handle deleting a message."""
        message_id = data.get('message_id')
        
        if not message_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message ID required'
            }))
            return
        
        # Delete message in database
        success = await self.delete_message(message_id)
        
        if success:
            # Notify group about message deletion
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'deleted_by': str(self.user.id),
                    'deleted_at': timezone.now().isoformat()
                }
            )
    
    # Group message handlers
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'message_type': event['message_type'],
            'reply_to': event['reply_to'],
            'timestamp': event['timestamp'],
            'is_edited': event['is_edited']
        }))
    
    async def user_status(self, event):
        """Send user status update to WebSocket."""
        # Don't send own status updates back to self
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'status': event['status']
            }))
    
    async def typing_status(self, event):
        """Send typing status to WebSocket."""
        # Don't send own typing status back to self
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def messages_read(self, event):
        """Send messages read status to WebSocket."""
        # Don't send own read status back to self
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'user_id': event['user_id'],
                'timestamp': event['timestamp']
            }))
    
    async def message_edited(self, event):
        """Send message edit notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'edited_by': event['edited_by'],
            'edited_at': event['edited_at']
        }))
    
    async def message_deleted(self, event):
        """Send message deletion notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
            'deleted_at': event['deleted_at']
        }))
    
    # Database operations
    @database_sync_to_async
    def check_conversation_access(self):
        """Check if user has access to the conversation."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except ObjectDoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content, message_type='text', reply_to_id=None):
        """Create a new message in the database."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Check if user is participant
            if not conversation.participants.filter(id=self.user.id).exists():
                return None
            
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(
                        id=reply_to_id,
                        conversation=conversation
                    )
                except Message.DoesNotExist:
                    pass
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type=message_type,
                reply_to=reply_to
            )
            
            # Update conversation metadata
            conversation.last_message_at = message.created_at
            conversation.total_messages += 1
            conversation.save(update_fields=['last_message_at', 'total_messages'])
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    @database_sync_to_async
    def mark_conversation_as_read(self):
        """Mark conversation as read for current user."""
        try:
            participant, created = ConversationParticipant.objects.get_or_create(
                conversation_id=self.conversation_id,
                user=self.user,
                defaults={'is_active': True}
            )
            participant.mark_as_read()
            return True
        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return False
    
    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit a message."""
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user
            )
            message.edit_message(new_content)
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """Soft delete a message."""
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user
            )
            message.soft_delete()
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
    
    @database_sync_to_async
    def set_user_online_status(self, is_online):
        """Update user's online status for this conversation."""
        try:
            participant, created = ConversationParticipant.objects.get_or_create(
                conversation_id=self.conversation_id,
                user=self.user,
                defaults={'is_active': True}
            )
            # Here you could update online status if you have such field
            # For now, we just ensure participant exists
            return True
        except Exception as e:
            logger.error(f"Error updating online status: {e}")
            return False
    
    def get_user_display_name(self):
        """Get display name for user."""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.email


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for general notifications."""
    
    async def connect(self):
        """Handle WebSocket connection for notifications."""
        self.user = self.scope["user"]
        
        # Reject anonymous users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.notification_group_name = f'notifications_{self.user.id}'
        
        # Join notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {self.user.email} connected to notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user.email} disconnected from notifications")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'mark_notification_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_read(notification_id)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Group message handlers
    async def chat_notification(self, event):
        """Send chat notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': event['notification_type'],
            'title': event['title'],
            'content': event['content'],
            'conversation_id': event.get('conversation_id'),
            'message_id': event.get('message_id'),
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read."""
        try:
            from .models import ChatNotification
            notification = ChatNotification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False