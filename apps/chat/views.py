"""
Views for chat functionality.
"""

from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from .models import Conversation, Message, ConversationParticipant, ChatNotification, TypingIndicator
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    ConversationCreateSerializer, MessageListSerializer,
    MessageCreateSerializer, MessageReportSerializer,
    ChatNotificationSerializer, ConversationSearchSerializer
)
from apps.core.pagination import CustomPagination


class ConversationFilter(django_filters.FilterSet):
    """Advanced filtering for conversations."""
    
    conversation_type = django_filters.ChoiceFilter(choices=Conversation.CONVERSATION_TYPES)
    is_active = django_filters.BooleanFilter()
    is_archived = django_filters.BooleanFilter()
    has_unread = django_filters.BooleanFilter(method='filter_has_unread')
    
    class Meta:
        model = Conversation
        fields = []
    
    def filter_has_unread(self, queryset, name, value):
        """Filter conversations with unread messages."""
        user = self.request.user
        if value:
            # Get conversations where user has unread messages
            return queryset.filter(
                participant_info__user=user,
                participant_info__last_read_at__lt=F('last_message_at')
            ).distinct()
        return queryset


class ConversationListView(generics.ListAPIView):
    """List user's conversations."""
    
    serializer_class = ConversationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ConversationFilter
    ordering_fields = ['last_message_at', 'created_at']
    ordering = ['-last_message_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True
        ).select_related('booking', 'braider').prefetch_related(
            'participants', 'participant_info'
        ).distinct()


class ConversationDetailView(generics.RetrieveAPIView):
    """Retrieve individual conversation details."""
    
    serializer_class = ConversationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related('booking', 'braider').prefetch_related(
            'participants', 'participant_info', 'messages__sender'
        )
    
    def get_object(self):
        """Get conversation and mark as read."""
        conversation = super().get_object()
        
        # Mark conversation as read for current user
        try:
            participant = conversation.participant_info.get(user=self.request.user)
            participant.mark_as_read()
        except ConversationParticipant.DoesNotExist:
            pass
        
        return conversation


class ConversationCreateView(generics.CreateAPIView):
    """Create new conversation."""
    
    serializer_class = ConversationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        
        return Response({
            'message': 'Conversation created successfully',
            'conversation_id': str(conversation.id)
        }, status=status.HTTP_201_CREATED)


class MessageListView(generics.ListAPIView):
    """List messages in a conversation."""
    
    serializer_class = MessageListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        
        # Verify user has access to conversation
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )
        
        return Message.objects.filter(
            conversation=conversation,
            is_deleted_by_user=False,
            is_deleted_by_admin=False
        ).select_related('sender', 'reply_to')


class MessageCreateView(generics.CreateAPIView):
    """Create new message in conversation."""
    
    serializer_class = MessageCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['conversation_id'] = self.kwargs['conversation_id']
        return context
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        return Response({
            'message': 'Message sent successfully',
            'message_id': str(message.id)
        }, status=status.HTTP_201_CREATED)


class MessageReportView(generics.CreateAPIView):
    """Report a message as inappropriate."""
    
    serializer_class = MessageReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['message_id'] = self.kwargs['message_id']
        return context
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        
        return Response({
            'message': 'Message reported successfully',
            'report_id': str(report.id)
        }, status=status.HTTP_201_CREATED)


class ChatNotificationListView(generics.ListAPIView):
    """List user's chat notifications."""
    
    serializer_class = ChatNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return ChatNotification.objects.filter(
            user=self.request.user
        ).select_related('conversation', 'message')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_conversation_read(request, conversation_id):
    """Mark conversation as read."""
    try:
        conversation = Conversation.objects.get(
            id=conversation_id,
            participants=request.user
        )
        
        participant, created = ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=request.user,
            defaults={'is_active': True}
        )
        
        participant.mark_as_read()
        
        return Response({
            'message': 'Conversation marked as read',
            'unread_count': participant.unread_count
        })
        
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def search_conversations(request):
    """Search conversations and messages."""
    serializer = ConversationSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    query = serializer.validated_data['query']
    conversation_type = serializer.validated_data.get('conversation_type')
    participant_email = serializer.validated_data.get('participant_email')
    
    # Base queryset
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    # Apply filters
    if conversation_type:
        conversations = conversations.filter(conversation_type=conversation_type)
    
    if participant_email:
        conversations = conversations.filter(participants__email=participant_email)
    
    # Search in conversation titles and messages
    conversations = conversations.filter(
        Q(title__icontains=query) |
        Q(messages__content__icontains=query)
    ).distinct()
    
    # Serialize results
    serializer = ConversationListSerializer(
        conversations[:20],  # Limit to 20 results
        many=True,
        context={'request': request}
    )
    
    return Response({
        'results': serializer.data,
        'total_found': conversations.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def chat_stats(request):
    """Get chat statistics for user."""
    user = request.user
    
    stats = {
        'total_conversations': Conversation.objects.filter(
            participants=user,
            is_active=True
        ).count(),
        'unread_conversations': ConversationParticipant.objects.filter(
            user=user,
            is_active=True
        ).annotate(
            unread=Count('conversation__messages', filter=Q(
                conversation__messages__created_at__gt=F('last_read_at')
            ) & ~Q(conversation__messages__sender=user))
        ).filter(unread__gt=0).count(),
        'total_messages_sent': Message.objects.filter(
            sender=user,
            is_deleted_by_user=False
        ).count(),
        'unread_notifications': ChatNotification.objects.filter(
            user=user,
            is_read=False
        ).count()
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_typing(request, conversation_id):
    """
    Indicate that user is typing in a conversation.
    """
    try:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
        
        # Get optional context from request
        context = {
            'draft_length': request.data.get('draft_length', 0),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': request.data.get('timestamp')
        }
        
        # Start typing indicator
        indicator = TypingIndicator.start_typing(
            conversation=conversation,
            user=request.user,
            context=context
        )
        
        # Get other typing users for response
        typing_users = TypingIndicator.get_typing_users(
            conversation=conversation,
            exclude_user=request.user
        )
        
        return Response({
            'message': 'Typing indicator started',
            'indicator_id': str(indicator.id),
            'other_typing_users': [
                {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email
                } for user in typing_users
            ],
            'typing_count': len(typing_users)
        })
        
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def stop_typing(request, conversation_id):
    """
    Stop typing indicator for user in conversation.
    """
    try:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
        
        # Stop typing indicator
        stopped = TypingIndicator.stop_typing(
            conversation=conversation,
            user=request.user
        )
        
        # Get remaining typing users
        typing_users = TypingIndicator.get_typing_users(
            conversation=conversation,
            exclude_user=request.user
        )
        
        return Response({
            'message': 'Typing indicator stopped',
            'was_typing': stopped,
            'other_typing_users': [
                {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email
                } for user in typing_users
            ],
            'typing_count': len(typing_users)
        })
        
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_typing_activity(request, conversation_id):
    """
    Update typing activity (heartbeat) for user in conversation.
    This should be called periodically while user is typing.
    """
    try:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
        
        # Get typing indicator
        try:
            indicator = TypingIndicator.objects.get(
                conversation=conversation,
                user=request.user,
                is_typing=True
            )
            
            # Update context if provided
            context = None
            if 'draft_length' in request.data:
                context = indicator.typing_context.copy()
                context.update({
                    'draft_length': request.data.get('draft_length', 0),
                    'last_update': request.data.get('timestamp')
                })
            
            indicator.update_activity(context=context)
            
            return Response({
                'message': 'Typing activity updated',
                'indicator_id': str(indicator.id),
                'last_activity': indicator.last_activity.isoformat(),
                'duration_seconds': indicator.duration_seconds
            })
            
        except TypingIndicator.DoesNotExist:
            return Response(
                {'error': 'No active typing indicator found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_typing_users(request, conversation_id):
    """
    Get list of users currently typing in conversation.
    """
    try:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
        
        typing_users = TypingIndicator.get_typing_users(
            conversation=conversation,
            exclude_user=request.user
        )
        
        # Clean up stale indicators
        cleaned_count = TypingIndicator.cleanup_stale_indicators()
        
        return Response({
            'typing_users': [
                {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': getattr(user, 'role', 'customer')
                } for user in typing_users
            ],
            'typing_count': len(typing_users),
            'cleaned_stale_indicators': cleaned_count
        })
        
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cleanup_typing_indicators(request):
    """
    Manually clean up stale typing indicators.
    This can be called periodically by the frontend or admin.
    """
    max_age = request.data.get('max_age_seconds', 30)
    
    # Validate max_age
    if not isinstance(max_age, int) or max_age < 5 or max_age > 300:
        return Response(
            {'error': 'max_age_seconds must be between 5 and 300'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    cleaned_count = TypingIndicator.cleanup_stale_indicators(max_age_seconds=max_age)
    
    return Response({
        'message': f'Cleaned up {cleaned_count} stale typing indicators',
        'cleaned_count': cleaned_count,
        'max_age_seconds': max_age
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def typing_stats(request):
    """
    Get typing statistics for debugging and monitoring.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    cutoff_time = now - timedelta(seconds=10)
    
    stats = {
        'total_active_indicators': TypingIndicator.objects.filter(is_typing=True).count(),
        'fresh_indicators': TypingIndicator.objects.filter(
            is_typing=True,
            last_activity__gte=cutoff_time
        ).count(),
        'stale_indicators': TypingIndicator.objects.filter(
            is_typing=True,
            last_activity__lt=cutoff_time
        ).count(),
        'user_typing_count': TypingIndicator.objects.filter(
            user=request.user,
            is_typing=True
        ).count(),
        'conversations_with_typing': TypingIndicator.objects.filter(
            is_typing=True,
            last_activity__gte=cutoff_time
        ).values('conversation').distinct().count()
    }
    
    return Response(stats)