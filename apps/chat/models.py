"""
Models for real-time chat system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.core.models import BaseModel
from apps.braiders.models import Braider
from apps.bookings.models import Booking

User = get_user_model()


class Conversation(BaseModel):
    """
    Chat conversation between users.
    
    Can be between:
    - Client and Braider
    - Client and Support (admin)
    - Group conversations (future)
    """
    
    CONVERSATION_TYPES = [
        ('booking', 'Booking Discussion'),
        ('support', 'Customer Support'),
        ('general', 'General Chat'),
        ('group', 'Group Chat'),
    ]
    
    # Participants
    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        help_text="Users participating in this conversation"
    )
    
    # Conversation details
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional conversation title"
    )
    conversation_type = models.CharField(
        max_length=20,
        choices=CONVERSATION_TYPES,
        default='general'
    )
    
    # Related objects
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text="Related booking if conversation is about specific booking"
    )
    braider = models.ForeignKey(
        Braider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        help_text="Related braider for booking conversations"
    )
    
    # Conversation settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether conversation is active"
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether conversation is archived"
    )
    
    # Metadata
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last message"
    )
    total_messages = models.PositiveIntegerField(
        default=0,
        help_text="Total number of messages in conversation"
    )
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['conversation_type']),
            models.Index(fields=['booking']),
            models.Index(fields=['braider']),
            models.Index(fields=['is_active', 'is_archived']),
            models.Index(fields=['last_message_at']),
        ]
    
    def __str__(self):
        if self.title:
            return self.title
        elif self.booking:
            return f"Booking Chat: {self.booking.booking_reference}"
        else:
            participant_names = [user.email for user in self.participants.all().order_by('id')[:2]]
            return f"Chat: {', '.join(participant_names)}"
    
    @property
    def unread_count_for_user(self, user):
        """Get unread message count for specific user."""
        return self.messages.filter(
            is_read=False
        ).exclude(sender=user).count()
    
    def mark_as_read_for_user(self, user):
        """Mark all messages as read for specific user."""
        self.messages.exclude(sender=user).update(is_read=True)
    
    def get_other_participants(self, user):
        """Get other participants excluding the given user."""
        return self.participants.exclude(id=user.id)


class Message(BaseModel):
    """Individual message in a conversation."""
    
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System Message'),
        ('booking_update', 'Booking Update'),
    ]
    
    # Message details
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    
    # Message content
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text'
    )
    content = models.TextField(
        help_text="Message text content"
    )
    
    # File attachments
    attachment = models.FileField(
        upload_to='chat/attachments/%Y/%m/',
        blank=True,
        null=True,
        help_text="File attachment (image, document, etc.)"
    )
    attachment_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Original filename for attachment"
    )
    attachment_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    
    # Message status
    is_read = models.BooleanField(
        default=False,
        help_text="Whether message has been read by recipient(s)"
    )
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether message has been edited"
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When message was last edited"
    )
    
    # Reply/Thread functionality
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Message this is replying to"
    )
    
    # Moderation
    is_reported = models.BooleanField(
        default=False,
        help_text="Whether message has been reported"
    )
    is_deleted_by_user = models.BooleanField(
        default=False,
        help_text="Whether message was deleted by sender"
    )
    is_deleted_by_admin = models.BooleanField(
        default=False,
        help_text="Whether message was deleted by admin"
    )
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender']),
            models.Index(fields=['message_type']),
            models.Index(fields=['is_read']),
            models.Index(fields=['reply_to']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.sender.email}: {preview}"
    
    @property
    def is_deleted(self):
        """Check if message is deleted."""
        return self.is_deleted_by_user or self.is_deleted_by_admin
    
    def soft_delete(self, deleted_by_admin=False):
        """Soft delete message."""
        if deleted_by_admin:
            self.is_deleted_by_admin = True
        else:
            self.is_deleted_by_user = True
        self.save(update_fields=['is_deleted_by_admin', 'is_deleted_by_user'])
    
    def edit_message(self, new_content):
        """Edit message content."""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at'])


class MessageRead(BaseModel):
    """Track read status of messages per user."""
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_by'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='read_messages'
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} read message {self.message.id}"


class MessageReport(BaseModel):
    """Reports for inappropriate messages."""
    
    REPORT_REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('offensive', 'Offensive Language'),
        ('threats', 'Threats or Violence'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Report details
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_reports'
    )
    
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(
        help_text="Detailed description of the issue"
    )
    
    # Moderation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_message_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['message', 'reporter']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['reason']),
            models.Index(fields=['message']),
        ]
    
    def __str__(self):
        return f"Report by {self.reporter.email} for message {self.message.id}"


class ConversationParticipant(BaseModel):
    """Extended information about conversation participants."""
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participant_info'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversation_participations'
    )
    
    # Participation details
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Preferences
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="Whether to receive notifications for this conversation"
    )
    is_muted = models.BooleanField(
        default=False,
        help_text="Whether conversation is muted"
    )
    
    # Admin settings
    is_admin = models.BooleanField(
        default=False,
        help_text="Whether user is admin of this conversation"
    )
    can_add_participants = models.BooleanField(
        default=False,
        help_text="Whether user can add new participants"
    )
    
    # Read tracking
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user last read messages in this conversation"
    )
    
    class Meta:
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['conversation', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['last_read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.conversation}"
    
    @property
    def unread_count(self):
        """Get unread message count for this participant."""
        if not self.last_read_at:
            return self.conversation.messages.exclude(sender=self.user).count()
        
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.user).count()
    
    def mark_as_read(self):
        """Mark conversation as read up to now."""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class ChatNotification(BaseModel):
    """Notifications for chat events."""
    
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('mention', 'User Mention'),
        ('conversation_created', 'Conversation Created'),
        ('participant_added', 'Participant Added'),
        ('participant_left', 'Participant Left'),
    ]
    
    # Notification details
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_notifications'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['conversation']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"


class TypingIndicator(BaseModel):
    """
    Tracks when users are typing in conversations.
    Used for real-time typing indicators in chat interface.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    # Typing status
    is_typing = models.BooleanField(
        default=True,
        help_text="Whether user is currently typing"
    )
    started_typing_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When user started typing"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="Last typing activity (updated on each keystroke)"
    )
    
    # Typing context
    typing_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context about what user is typing (draft message length, etc.)"
    )
    
    class Meta:
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['conversation', 'is_typing']),
            models.Index(fields=['user', 'is_typing']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        status = "typing" if self.is_typing else "stopped typing"
        return f"{self.user.email} {status} in {self.conversation}"
    
    @classmethod
    def start_typing(cls, conversation, user, context=None):
        """
        Mark user as typing in conversation.
        
        Args:
            conversation: Conversation instance
            user: User instance
            context: Optional typing context (dict)
        
        Returns:
            TypingIndicator instance
        """
        indicator, created = cls.objects.update_or_create(
            conversation=conversation,
            user=user,
            defaults={
                'is_typing': True,
                'typing_context': context or {},
                'started_typing_at': timezone.now(),
            }
        )
        return indicator
    
    @classmethod
    def stop_typing(cls, conversation, user):
        """
        Mark user as stopped typing in conversation.
        
        Args:
            conversation: Conversation instance
            user: User instance
        
        Returns:
            Boolean indicating if indicator was updated
        """
        updated = cls.objects.filter(
            conversation=conversation,
            user=user
        ).update(is_typing=False)
        return updated > 0
    
    @classmethod
    def get_typing_users(cls, conversation, exclude_user=None):
        """
        Get list of users currently typing in conversation.
        
        Args:
            conversation: Conversation instance
            exclude_user: User to exclude from results (usually current user)
        
        Returns:
            QuerySet of User objects currently typing
        """
        # Consider typing indicators stale after 10 seconds
        cutoff_time = timezone.now() - timezone.timedelta(seconds=10)
        
        queryset = cls.objects.filter(
            conversation=conversation,
            is_typing=True,
            last_activity__gte=cutoff_time
        ).select_related('user')
        
        if exclude_user:
            queryset = queryset.exclude(user=exclude_user)
        
        return [indicator.user for indicator in queryset]
    
    @classmethod
    def cleanup_stale_indicators(cls, max_age_seconds=30):
        """
        Clean up stale typing indicators.
        
        Args:
            max_age_seconds: Maximum age in seconds before considering indicator stale
        
        Returns:
            Number of indicators cleaned up
        """
        cutoff_time = timezone.now() - timezone.timedelta(seconds=max_age_seconds)
        
        updated = cls.objects.filter(
            is_typing=True,
            last_activity__lt=cutoff_time
        ).update(is_typing=False)
        
        return updated
    
    def update_activity(self, context=None):
        """
        Update last activity timestamp and context.
        
        Args:
            context: Optional updated typing context
        """
        update_fields = ['last_activity']
        self.last_activity = timezone.now()
        
        if context is not None:
            self.typing_context = context
            update_fields.append('typing_context')
        
        self.save(update_fields=update_fields)
    
    @property
    def is_stale(self):
        """Check if typing indicator is stale (older than 10 seconds)."""
        cutoff_time = timezone.now() - timezone.timedelta(seconds=10)
        return self.last_activity < cutoff_time
    
    @property
    def duration_seconds(self):
        """Get typing duration in seconds."""
        if self.is_typing:
            return (timezone.now() - self.started_typing_at).total_seconds()
        return 0