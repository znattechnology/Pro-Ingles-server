"""
Tests for chat functionality including typing indicators.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta

from .models import Conversation, Message, TypingIndicator, ConversationParticipant

User = get_user_model()


class ConversationModelTest(TestCase):
    """Test Conversation model functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            name='User 1',
            password='testpass'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            name='User 2',
            password='testpass'
        )
        
        self.conversation = Conversation.objects.create(
            title='Test Conversation',
            conversation_type='general'
        )
        self.conversation.participants.add(self.user1, self.user2)
    
    def test_create_conversation(self):
        """Test creating a conversation."""
        self.assertEqual(self.conversation.title, 'Test Conversation')
        self.assertEqual(self.conversation.conversation_type, 'general')
        self.assertEqual(self.conversation.participants.count(), 2)
        self.assertTrue(self.conversation.is_active)
    
    def test_conversation_string_representation(self):
        """Test conversation string representation."""
        self.assertEqual(str(self.conversation), 'Test Conversation')
        
        # Test without title
        conv_no_title = Conversation.objects.create(conversation_type='general')
        conv_no_title.participants.add(self.user1, self.user2)
        
        # Order is not guaranteed, so check both possibilities
        result = str(conv_no_title)
        expected1 = f"Chat: {self.user1.email}, {self.user2.email}"
        expected2 = f"Chat: {self.user2.email}, {self.user1.email}"
        self.assertIn(result, [expected1, expected2])
    
    def test_get_other_participants(self):
        """Test getting other participants."""
        others = self.conversation.get_other_participants(self.user1)
        
        self.assertEqual(others.count(), 1)
        self.assertEqual(others.first(), self.user2)
    
    def test_mark_as_read(self):
        """Test marking conversation as read."""
        # Create a message
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content='Test message'
        )
        
        # Mark as read for user1
        self.conversation.mark_as_read_for_user(self.user1)
        
        # Should update message read status
        messages = Message.objects.filter(conversation=self.conversation)
        for msg in messages:
            if msg.sender != self.user1:
                self.assertTrue(msg.is_read)


class MessageModelTest(TestCase):
    """Test Message model functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='sender@test.com',
            name='Sender User',
            password='testpass'
        )
        self.user2 = User.objects.create_user(
            email='receiver@test.com',
            name='Receiver User',
            password='testpass'
        )
        
        self.conversation = Conversation.objects.create(
            conversation_type='general'
        )
        self.conversation.participants.add(self.user1, self.user2)
    
    def test_create_text_message(self):
        """Test creating a text message."""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Hello world!',
            message_type='text'
        )
        
        self.assertEqual(message.content, 'Hello world!')
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.message_type, 'text')
        self.assertFalse(message.is_read)
        self.assertFalse(message.is_edited)
    
    def test_message_string_representation(self):
        """Test message string representation."""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='This is a test message',
            message_type='text'
        )
        
        expected = f"{self.user1.email}: This is a test message"
        self.assertEqual(str(message), expected)
    
    def test_edit_message(self):
        """Test editing a message."""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Original content'
        )
        
        message.edit_message('Edited content')
        
        self.assertEqual(message.content, 'Edited content')
        self.assertTrue(message.is_edited)
        self.assertIsNotNone(message.edited_at)
    
    def test_soft_delete_message(self):
        """Test soft deleting a message."""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='To be deleted'
        )
        
        # User deletion
        message.soft_delete()
        self.assertTrue(message.is_deleted_by_user)
        self.assertTrue(message.is_deleted)
        
        # Admin deletion
        message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='To be deleted by admin'
        )
        message2.soft_delete(deleted_by_admin=True)
        self.assertTrue(message2.is_deleted_by_admin)
        self.assertTrue(message2.is_deleted)
    
    def test_reply_message(self):
        """Test replying to a message."""
        original = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Original message'
        )
        
        reply = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content='Reply message',
            reply_to=original
        )
        
        self.assertEqual(reply.reply_to, original)
        self.assertEqual(original.replies.count(), 1)
        self.assertEqual(original.replies.first(), reply)


class TypingIndicatorModelTest(TestCase):
    """Test TypingIndicator model functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='typer1@test.com',
            name='Typer 1',
            password='testpass'
        )
        self.user2 = User.objects.create_user(
            email='typer2@test.com',
            name='Typer 2',
            password='testpass'
        )
        
        self.conversation = Conversation.objects.create(
            conversation_type='general'
        )
        self.conversation.participants.add(self.user1, self.user2)
    
    def test_start_typing(self):
        """Test starting typing indicator."""
        indicator = TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        self.assertTrue(indicator.is_typing)
        self.assertEqual(indicator.conversation, self.conversation)
        self.assertEqual(indicator.user, self.user1)
        self.assertIsNotNone(indicator.started_typing_at)
    
    def test_stop_typing(self):
        """Test stopping typing indicator."""
        # Start typing first
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        # Stop typing
        stopped = TypingIndicator.stop_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        self.assertTrue(stopped)
        
        # Verify indicator is stopped
        indicator = TypingIndicator.objects.get(
            conversation=self.conversation,
            user=self.user1
        )
        self.assertFalse(indicator.is_typing)
    
    def test_get_typing_users(self):
        """Test getting currently typing users."""
        # Start typing for user1
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        # Get typing users excluding user1
        typing_users = TypingIndicator.get_typing_users(
            conversation=self.conversation,
            exclude_user=self.user1
        )
        self.assertEqual(len(typing_users), 0)
        
        # Get typing users excluding user2
        typing_users = TypingIndicator.get_typing_users(
            conversation=self.conversation,
            exclude_user=self.user2
        )
        self.assertEqual(len(typing_users), 1)
        self.assertEqual(typing_users[0], self.user1)
    
    def test_typing_indicator_stale(self):
        """Test stale typing indicator detection."""
        # Create old indicator
        old_time = timezone.now() - timedelta(seconds=20)
        
        indicator = TypingIndicator.objects.create(
            conversation=self.conversation,
            user=self.user1,
            is_typing=True
        )
        
        # Manually set old time
        TypingIndicator.objects.filter(id=indicator.id).update(
            last_activity=old_time
        )
        indicator.refresh_from_db()
        
        self.assertTrue(indicator.is_stale)
    
    def test_cleanup_stale_indicators(self):
        """Test cleaning up stale indicators."""
        # Create fresh indicator
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        # Create stale indicator
        old_time = timezone.now() - timedelta(seconds=60)
        stale_indicator = TypingIndicator.objects.create(
            conversation=self.conversation,
            user=self.user2,
            is_typing=True
        )
        TypingIndicator.objects.filter(id=stale_indicator.id).update(
            last_activity=old_time
        )
        
        # Cleanup stale indicators
        cleaned_count = TypingIndicator.cleanup_stale_indicators(max_age_seconds=30)
        
        self.assertEqual(cleaned_count, 1)
        
        # Verify stale indicator is marked as not typing
        stale_indicator.refresh_from_db()
        self.assertFalse(stale_indicator.is_typing)
    
    def test_update_activity(self):
        """Test updating typing activity."""
        indicator = TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1,
            context={'draft_length': 5}
        )
        
        original_activity = indicator.last_activity
        
        # Update activity with new context
        indicator.update_activity(context={'draft_length': 10})
        
        self.assertGreater(indicator.last_activity, original_activity)
        self.assertEqual(indicator.typing_context['draft_length'], 10)


class ChatAPITest(APITestCase):
    """Test chat API endpoints."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='api1@test.com',
            name='API User 1',
            password='testpass'
        )
        self.user2 = User.objects.create_user(
            email='api2@test.com',
            name='API User 2',
            password='testpass'
        )
        
        self.conversation = Conversation.objects.create(
            title='API Test Conversation',
            conversation_type='general'
        )
        self.conversation.participants.add(self.user1, self.user2)
        
        self.client.force_authenticate(user=self.user1)
    
    def test_list_conversations(self):
        """Test listing user conversations."""
        url = reverse('chat:conversation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Test Conversation')
    
    def test_conversation_detail(self):
        """Test getting conversation details."""
        url = reverse('chat:conversation-detail', kwargs={'pk': self.conversation.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'API Test Conversation')
    
    def test_send_message(self):
        """Test sending a message."""
        url = reverse('chat:message-create', kwargs={'conversation_id': self.conversation.id})
        data = {
            'content': 'Test API message',
            'message_type': 'text'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify message was created
        message = Message.objects.get(
            conversation=self.conversation,
            content='Test API message'
        )
        self.assertEqual(message.sender, self.user1)
    
    def test_list_messages(self):
        """Test listing conversation messages."""
        # Create a message first
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Test message'
        )
        
        url = reverse('chat:message-list', kwargs={'conversation_id': self.conversation.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['content'], 'Test message')
    
    def test_start_typing_indicator(self):
        """Test starting typing indicator."""
        url = reverse('chat:start-typing', kwargs={'conversation_id': self.conversation.id})
        data = {
            'draft_length': 5
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('indicator_id', response.data)
        
        # Verify indicator was created
        indicator = TypingIndicator.objects.get(
            conversation=self.conversation,
            user=self.user1
        )
        self.assertTrue(indicator.is_typing)
    
    def test_stop_typing_indicator(self):
        """Test stopping typing indicator."""
        # Start typing first
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        url = reverse('chat:stop-typing', kwargs={'conversation_id': self.conversation.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['was_typing'])
    
    def test_get_typing_users(self):
        """Test getting typing users."""
        # Start typing for user2
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user2
        )
        
        url = reverse('chat:get-typing-users', kwargs={'conversation_id': self.conversation.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['typing_count'], 1)
        self.assertEqual(len(response.data['typing_users']), 1)
        self.assertEqual(response.data['typing_users'][0]['email'], self.user2.email)
    
    def test_update_typing_activity(self):
        """Test updating typing activity."""
        # Start typing first
        TypingIndicator.start_typing(
            conversation=self.conversation,
            user=self.user1
        )
        
        url = reverse('chat:update-typing', kwargs={'conversation_id': self.conversation.id})
        data = {
            'draft_length': 15
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('duration_seconds', response.data)
    
    def test_chat_stats(self):
        """Test getting chat statistics."""
        url = reverse('chat:chat-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_conversations', response.data)
        self.assertIn('total_messages_sent', response.data)
    
    def test_typing_stats(self):
        """Test getting typing statistics."""
        url = reverse('chat:typing-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_active_indicators', response.data)
        self.assertIn('fresh_indicators', response.data)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to chat endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('chat:conversation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_other_users_conversation(self):
        """Test accessing conversation user is not part of."""
        other_user = User.objects.create_user(
            email='other@test.com',
            name='Other User',
            password='testpass'
        )
        self.client.force_authenticate(user=other_user)
        
        url = reverse('chat:conversation-detail', kwargs={'pk': self.conversation.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)