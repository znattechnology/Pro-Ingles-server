"""
Serializers for chat functionality.
"""

from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import (
    Conversation, Message, ConversationParticipant, MessageReport,
    ChatNotification
)
from apps.braiders.models import Braider
from apps.bookings.models import Booking

User = get_user_model()


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer for conversation participants."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    unread_count = serializers.ReadOnlyField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'user_email', 'user_name', 'joined_at', 'is_active',
            'notifications_enabled', 'is_muted', 'last_read_at', 'unread_count'
        ]
    
    def get_user_name(self, obj):
        """Get user display name."""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.email


class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message listings."""
    
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    sender_name = serializers.SerializerMethodField()
    reply_to_content = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender_email', 'sender_name', 'message_type', 'content',
            'attachment_url', 'attachment_name', 'is_read', 'is_edited',
            'reply_to', 'reply_to_content', 'created_at', 'edited_at'
        ]
    
    def get_sender_name(self, obj):
        """Get sender display name."""
        if obj.sender.first_name and obj.sender.last_name:
            return f"{obj.sender.first_name} {obj.sender.last_name}"
        return obj.sender.email
    
    def get_reply_to_content(self, obj):
        """Get content of message being replied to."""
        if obj.reply_to and not obj.reply_to.is_deleted:
            content = obj.reply_to.content
            return content[:50] + '...' if len(content) > 50 else content
        return None
    
    def get_attachment_url(self, obj):
        """Get attachment URL if exists."""
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation listings."""
    
    participants = ConversationParticipantSerializer(many=True, source='participant_info', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'conversation_type', 'participants',
            'other_participants', 'last_message', 'last_message_at',
            'total_messages', 'unread_count', 'is_active', 'created_at'
        ]
    
    def get_last_message(self, obj):
        """Get last message preview."""
        last_message = obj.messages.filter(is_deleted_by_user=False, is_deleted_by_admin=False).last()
        if last_message:
            return {
                'id': str(last_message.id),
                'sender': last_message.sender.email,
                'content': last_message.content[:100] + ('...' if len(last_message.content) > 100 else ''),
                'message_type': last_message.message_type,
                'created_at': last_message.created_at.isoformat()
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        try:
            participant = obj.participant_info.get(user=request.user)
            return participant.unread_count
        except ConversationParticipant.DoesNotExist:
            return 0
    
    def get_other_participants(self, obj):
        """Get other participants excluding current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        other_participants = obj.participants.exclude(id=request.user.id)
        return [
            {
                'email': user.email,
                'name': f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email
            }
            for user in other_participants
        ]


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual conversation view."""
    
    participants = ConversationParticipantSerializer(many=True, source='participant_info', read_only=True)
    messages = MessageListSerializer(many=True, read_only=True)
    booking_info = serializers.SerializerMethodField()
    braider_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'conversation_type', 'participants', 'messages',
            'booking_info', 'braider_info', 'last_message_at', 'total_messages',
            'is_active', 'is_archived', 'created_at'
        ]
    
    def get_booking_info(self, obj):
        """Get booking information if conversation is booking-related."""
        if obj.booking:
            return {
                'id': str(obj.booking.id),
                'booking_reference': obj.booking.booking_reference,
                'service_name': obj.booking.service.name,
                'booking_date': obj.booking.booking_date.isoformat(),
                'status': obj.booking.status
            }
        return None
    
    def get_braider_info(self, obj):
        """Get braider information if conversation is with a braider."""
        if obj.braider:
            return {
                'id': str(obj.braider.id),
                'name': obj.braider.name,
                'profile_image': obj.braider.profile_image.url if obj.braider.profile_image else None
            }
        return None


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversations."""
    
    participant_emails = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        help_text="List of participant email addresses"
    )
    booking_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Conversation
        fields = [
            'title', 'conversation_type', 'participant_emails', 'booking_id'
        ]
    
    def validate_participant_emails(self, value):
        """Validate participant emails."""
        if not value:
            raise serializers.ValidationError("At least one participant is required")
        
        # Check if users exist
        users = User.objects.filter(email__in=value)
        found_emails = set(users.values_list('email', flat=True))
        missing_emails = set(value) - found_emails
        
        if missing_emails:
            raise serializers.ValidationError(
                f"Users with these emails not found: {', '.join(missing_emails)}"
            )
        
        return value
    
    def validate_booking_id(self, value):
        """Validate booking exists and user has access."""
        if value:
            user = self.context['request'].user
            try:
                booking = Booking.objects.get(id=value)
                # Check if user is involved in the booking
                if booking.user != user and booking.braider.user != user:
                    raise serializers.ValidationError("You don't have access to this booking")
                return booking
            except Booking.DoesNotExist:
                raise serializers.ValidationError("Booking not found")
        return None
    
    @transaction.atomic
    def create(self, validated_data):
        """Create conversation with participants."""
        participant_emails = validated_data.pop('participant_emails')
        booking = validated_data.pop('booking_id', None)
        user = self.context['request'].user
        
        # Create conversation
        conversation = Conversation.objects.create(**validated_data)
        
        if booking:
            conversation.booking = booking
            conversation.braider = booking.braider
            conversation.save(update_fields=['booking', 'braider'])
        
        # Add participants
        participant_users = User.objects.filter(email__in=participant_emails)
        conversation.participants.add(user)  # Add creator
        conversation.participants.add(*participant_users)
        
        # Create participant info records
        for participant in conversation.participants.all():
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=participant,
                is_active=True
            )
        
        return conversation


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""
    
    class Meta:
        model = Message
        fields = [
            'content', 'message_type', 'attachment', 'reply_to'
        ]
    
    def validate_reply_to(self, value):
        """Validate reply_to message exists in same conversation."""
        if value:
            conversation_id = self.context.get('conversation_id')
            if value.conversation.id != conversation_id:
                raise serializers.ValidationError("Cannot reply to message from different conversation")
            if value.is_deleted:
                raise serializers.ValidationError("Cannot reply to deleted message")
        return value
    
    def create(self, validated_data):
        """Create message in conversation."""
        user = self.context['request'].user
        conversation_id = self.context['conversation_id']
        
        # Get conversation
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Check if user is participant
        if not conversation.participants.filter(id=user.id).exists():
            raise serializers.ValidationError("You are not a participant in this conversation")
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            **validated_data
        )
        
        # Handle file attachment info
        if message.attachment:
            message.attachment_name = message.attachment.name.split('/')[-1]
            message.attachment_size = message.attachment.size
            message.save(update_fields=['attachment_name', 'attachment_size'])
        
        return message


class MessageReportSerializer(serializers.ModelSerializer):
    """Serializer for reporting messages."""
    
    class Meta:
        model = MessageReport
        fields = ['reason', 'description']
    
    def create(self, validated_data):
        """Create message report."""
        user = self.context['request'].user
        message_id = self.context['message_id']
        
        # Get message
        message = Message.objects.get(id=message_id)
        
        # Check if user already reported this message
        if MessageReport.objects.filter(message=message, reporter=user).exists():
            raise serializers.ValidationError("You have already reported this message")
        
        # Create report
        report = MessageReport.objects.create(
            message=message,
            reporter=user,
            **validated_data
        )
        
        # Mark message as reported
        message.is_reported = True
        message.save(update_fields=['is_reported'])
        
        return report


class ChatNotificationSerializer(serializers.ModelSerializer):
    """Serializer for chat notifications."""
    
    conversation_title = serializers.CharField(source='conversation.title', read_only=True)
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'notification_type', 'title', 'content', 'conversation',
            'conversation_title', 'message', 'is_read', 'created_at'
        ]


class ConversationSearchSerializer(serializers.Serializer):
    """Serializer for conversation search."""
    
    query = serializers.CharField(max_length=200)
    conversation_type = serializers.ChoiceField(
        choices=Conversation.CONVERSATION_TYPES,
        required=False
    )
    participant_email = serializers.EmailField(required=False)