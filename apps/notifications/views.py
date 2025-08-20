"""
Views for advanced notification system.
"""

from django.db.models import Q, Count, F, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from .models import (
    NotificationTemplate, NotificationChannel, UserNotificationPreference,
    NotificationCategory, Notification, NotificationBatch, NotificationAnalytics
)
from .serializers import (
    NotificationTemplateSerializer, NotificationChannelSerializer,
    UserNotificationPreferenceSerializer, NotificationCategorySerializer,
    NotificationListSerializer, NotificationDetailSerializer,
    NotificationCreateSerializer, NotificationBatchSerializer,
    NotificationAnalyticsSerializer, NotificationStatsSerializer,
    BulkNotificationSerializer
)
from .tasks import send_notification, process_notification_batch
from apps.core.pagination import CustomPagination


class NotificationFilter(django_filters.FilterSet):
    """Advanced filtering for notifications."""
    
    status = django_filters.MultipleChoiceFilter(choices=Notification.STATUS_CHOICES)
    priority = django_filters.MultipleChoiceFilter(choices=Notification.PRIORITY_CHOICES)
    category = django_filters.ModelMultipleChoiceFilter(queryset=NotificationCategory.objects.all())
    is_read = django_filters.BooleanFilter(method='filter_is_read')
    date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    
    class Meta:
        model = Notification
        fields = []
    
    def filter_is_read(self, queryset, name, value):
        """Filter by read status."""
        if value is True:
            return queryset.filter(read_at__isnull=False)
        elif value is False:
            return queryset.filter(read_at__isnull=True)
        return queryset


class NotificationTemplateListView(generics.ListCreateAPIView):
    """List and create notification templates."""
    
    queryset = NotificationTemplate.objects.filter(is_active=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    pagination_class = CustomPagination


class NotificationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete notification template."""
    
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationChannelListView(generics.ListCreateAPIView):
    """List and create notification channels."""
    
    queryset = NotificationChannel.objects.filter(is_active=True)
    serializer_class = NotificationChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['channel_type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class NotificationChannelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete notification channel."""
    
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserNotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """Get and update user's notification preferences."""
    
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create user preferences."""
        preferences, created = UserNotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class NotificationCategoryListView(generics.ListAPIView):
    """List notification categories."""
    
    queryset = NotificationCategory.objects.all()
    serializer_class = NotificationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-priority', 'name']


class NotificationListView(generics.ListAPIView):
    """List user's notifications."""
    
    serializer_class = NotificationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = NotificationFilter
    ordering_fields = ['created_at', 'sent_at', 'priority']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('category', 'template', 'channel')


class NotificationDetailView(generics.RetrieveAPIView):
    """Retrieve detailed notification."""
    
    serializer_class = NotificationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Mark notification as read when retrieved."""
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NotificationCreateView(generics.CreateAPIView):
    """Create new notification."""
    
    serializer_class = NotificationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        
        # Send notification asynchronously
        send_notification.delay(notification.id)
        
        return Response({
            'message': 'Notification created successfully',
            'notification_id': str(notification.id)
        }, status=status.HTTP_201_CREATED)


class NotificationBatchListView(generics.ListCreateAPIView):
    """List and create notification batches."""
    
    queryset = NotificationBatch.objects.all()
    serializer_class = NotificationBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_processed', 'template', 'channel']
    ordering = ['-created_at']
    pagination_class = CustomPagination


class NotificationBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete notification batch."""
    
    queryset = NotificationBatch.objects.all()
    serializer_class = NotificationBatchSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark specific notification as read."""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marked as read',
            'read_at': notification.read_at
        })
        
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all user's notifications as read."""
    now = timezone.now()
    updated = Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).update(read_at=now)
    
    return Response({
        'message': f'{updated} notifications marked as read'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def notification_clicked(request, notification_id):
    """Track notification click."""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        
        action = request.data.get('action', '')
        notification.mark_as_clicked(action)
        
        # Update analytics if exists
        analytics, created = NotificationAnalytics.objects.get_or_create(
            notification=notification
        )
        analytics.clicks += 1
        if not analytics.time_to_click and notification.sent_at:
            analytics.time_to_click = timezone.now() - notification.sent_at
        analytics.save()
        
        return Response({
            'message': 'Click tracked successfully',
            'clicked_at': notification.clicked_at
        })
        
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """Get user's notification statistics."""
    user = request.user
    now = timezone.now()
    today = now.date()
    week_ago = now - timezone.timedelta(days=7)
    
    # Base queryset
    notifications = Notification.objects.filter(recipient=user)
    
    # Count statistics
    stats = {
        'total_notifications': notifications.count(),
        'unread_notifications': notifications.filter(read_at__isnull=True).count(),
        'notifications_today': notifications.filter(created_at__date=today).count(),
        'notifications_this_week': notifications.filter(created_at__gte=week_ago).count(),
        
        # By status
        'pending_notifications': notifications.filter(status='pending').count(),
        'sent_notifications': notifications.filter(status='sent').count(),
        'delivered_notifications': notifications.filter(status='delivered').count(),
        'failed_notifications': notifications.filter(status='failed').count(),
        
        # By priority
        'urgent_notifications': notifications.filter(priority=4, read_at__isnull=True).count(),
        'high_notifications': notifications.filter(priority=3, read_at__isnull=True).count(),
        'normal_notifications': notifications.filter(priority=2, read_at__isnull=True).count(),
        'low_notifications': notifications.filter(priority=1, read_at__isnull=True).count(),
    }
    
    # Calculate engagement rates
    sent_notifications = notifications.filter(status__in=['sent', 'delivered'])
    total_sent = sent_notifications.count()
    
    if total_sent > 0:
        read_count = sent_notifications.filter(read_at__isnull=False).count()
        clicked_count = sent_notifications.filter(clicked_at__isnull=False).count()
        
        stats['open_rate'] = round((read_count / total_sent) * 100, 2)
        stats['click_rate'] = round((clicked_count / total_sent) * 100, 2)
    else:
        stats['open_rate'] = 0.0
        stats['click_rate'] = 0.0
    
    serializer = NotificationStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_create_notifications(request):
    """Create notifications in bulk."""
    serializer = BulkNotificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create notification batch
    batch = NotificationBatch.objects.create(
        name=f"Bulk notification - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        template=serializer.validated_data['template_id'],
        channel=serializer.validated_data['channel_id'],
        category=serializer.validated_data.get('category_id'),
        recipient_count=len(serializer.validated_data['recipients']),
        context_data=serializer.validated_data['context_data'],
        recipient_data=[
            {'email': email} for email in serializer.validated_data['recipients']
        ],
        scheduled_at=serializer.validated_data.get('scheduled_at')
    )
    
    # Process batch asynchronously
    process_notification_batch.delay(batch.id)
    
    return Response({
        'message': 'Bulk notifications queued successfully',
        'batch_id': str(batch.id),
        'recipient_count': batch.recipient_count
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_analytics(request, notification_id):
    """Get analytics for specific notification."""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )
        
        analytics, created = NotificationAnalytics.objects.get_or_create(
            notification=notification
        )
        
        serializer = NotificationAnalyticsSerializer(analytics)
        return Response(serializer.data)
        
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_data(request):
    """Get dashboard data for notifications."""
    user = request.user
    now = timezone.now()
    
    # Recent notifications (last 10)
    recent_notifications = Notification.objects.filter(
        recipient=user
    ).select_related('category')[:10]
    
    # Category breakdown
    category_stats = NotificationCategory.objects.annotate(
        notification_count=Count('notification', filter=Q(notification__recipient=user))
    ).order_by('-notification_count')[:5]
    
    # Daily notification count for last 30 days
    thirty_days_ago = now - timezone.timedelta(days=30)
    daily_counts = []
    
    for i in range(30):
        day = thirty_days_ago + timezone.timedelta(days=i)
        count = Notification.objects.filter(
            recipient=user,
            created_at__date=day.date()
        ).count()
        daily_counts.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return Response({
        'recent_notifications': NotificationListSerializer(
            recent_notifications, many=True, context={'request': request}
        ).data,
        'category_stats': [
            {
                'name': cat.display_name,
                'count': cat.notification_count,
                'color': cat.color
            }
            for cat in category_stats
        ],
        'daily_counts': daily_counts
    })