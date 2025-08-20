"""
Serializers for notification system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    NotificationTemplate, NotificationChannel, UserNotificationPreference,
    NotificationCategory, Notification, NotificationBatch, NotificationAnalytics
)

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates."""
    
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'subject_template', 'body_template', 'html_template',
            'is_active', 'description', 'variables',
            'created_at', 'updated_at'
        ]


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer for notification channels."""
    
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display',
            'is_active', 'rate_limit_per_minute', 'rate_limit_per_hour',
            'rate_limit_per_day', 'created_at', 'updated_at'
        ]
        # Hide sensitive config data
        extra_kwargs = {
            'config': {'write_only': True}
        }


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user notification preferences."""
    
    class Meta:
        model = UserNotificationPreference
        fields = [
            'id', 'email_enabled', 'push_enabled', 'sms_enabled', 'in_app_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'timezone',
            'marketing_enabled', 'promotional_enabled', 'system_enabled',
            'digest_frequency', 'category_preferences',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationCategorySerializer(serializers.ModelSerializer):
    """Serializer for notification categories."""
    
    class Meta:
        model = NotificationCategory
        fields = [
            'id', 'name', 'display_name', 'description', 'icon', 'color',
            'priority', 'is_system', 'created_at', 'updated_at'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for notification list view."""
    
    category_name = serializers.CharField(source='category.display_name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Calculated fields
    is_read = serializers.ReadOnlyField()
    is_clicked = serializers.ReadOnlyField()
    time_since_sent = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'status', 'status_display',
            'priority', 'priority_display', 'category_name', 'category_icon',
            'category_color', 'is_read', 'is_clicked', 'sent_at', 'read_at',
            'clicked_at', 'time_since_sent', 'data', 'created_at'
        ]
    
    def get_time_since_sent(self, obj):
        """Calculate time since notification was sent."""
        if not obj.sent_at:
            return None
        from django.utils import timezone
        delta = timezone.now() - obj.sent_at
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "Just now"


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed notification view."""
    
    category = NotificationCategorySerializer(read_only=True)
    template = NotificationTemplateSerializer(read_only=True)
    channel = NotificationChannelSerializer(read_only=True)
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    
    # Status displays
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Calculated fields
    is_read = serializers.ReadOnlyField()
    is_clicked = serializers.ReadOnlyField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'html_content', 'data',
            'category', 'template', 'channel', 'recipient_email',
            'status', 'status_display', 'priority', 'priority_display',
            'scheduled_at', 'sent_at', 'delivered_at', 'read_at', 'clicked_at',
            'action_taken', 'is_read', 'is_clicked', 'error_message',
            'retry_count', 'max_retries', 'external_id',
            'created_at', 'updated_at'
        ]


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications."""
    
    recipient_email = serializers.EmailField(write_only=True, required=False)
    recipient_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Notification
        fields = [
            'recipient_email', 'recipient_id', 'title', 'message', 'html_content',
            'data', 'category', 'template', 'channel', 'priority',
            'scheduled_at', 'max_retries'
        ]
    
    def validate(self, attrs):
        """Ensure either recipient_email or recipient_id is provided."""
        recipient_email = attrs.get('recipient_email')
        recipient_id = attrs.get('recipient_id')
        
        if not recipient_email and not recipient_id:
            raise serializers.ValidationError(
                "Either recipient_email or recipient_id must be provided."
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create notification with proper recipient lookup."""
        recipient_email = validated_data.pop('recipient_email', None)
        recipient_id = validated_data.pop('recipient_id', None)
        
        # Get recipient user
        if recipient_id:
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found.")
        else:
            try:
                recipient = User.objects.get(email=recipient_email)
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this email not found.")
        
        validated_data['recipient'] = recipient
        return super().create(validated_data)


class NotificationBatchSerializer(serializers.ModelSerializer):
    """Serializer for notification batches."""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    category_name = serializers.CharField(source='category.display_name', read_only=True)
    
    class Meta:
        model = NotificationBatch
        fields = [
            'id', 'name', 'description', 'recipient_count',
            'template', 'template_name', 'channel', 'channel_name',
            'category', 'category_name', 'context_data', 'recipient_data',
            'scheduled_at', 'is_processed', 'processed_at',
            'sent_count', 'failed_count', 'created_at', 'updated_at'
        ]


class NotificationAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for notification analytics."""
    
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    
    class Meta:
        model = NotificationAnalytics
        fields = [
            'id', 'notification_title', 'opens', 'clicks', 'conversions',
            'time_to_read', 'time_to_click', 'device_type', 'platform',
            'country', 'city', 'created_at', 'updated_at'
        ]


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    notifications_today = serializers.IntegerField()
    notifications_this_week = serializers.IntegerField()
    
    # By status
    pending_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    delivered_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    
    # By priority
    urgent_notifications = serializers.IntegerField()
    high_notifications = serializers.IntegerField()
    normal_notifications = serializers.IntegerField()
    low_notifications = serializers.IntegerField()
    
    # Engagement rates
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification creation."""
    
    template_id = serializers.UUIDField()
    channel_id = serializers.UUIDField()
    category_id = serializers.UUIDField(required=False)
    
    recipients = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=1000
    )
    
    context_data = serializers.JSONField(default=dict)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default=2
    )
    scheduled_at = serializers.DateTimeField(required=False)
    
    def validate_template_id(self, value):
        """Validate template exists and is active."""
        try:
            template = NotificationTemplate.objects.get(id=value, is_active=True)
            return template
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive.")
    
    def validate_channel_id(self, value):
        """Validate channel exists and is active."""
        try:
            channel = NotificationChannel.objects.get(id=value, is_active=True)
            return channel
        except NotificationChannel.DoesNotExist:
            raise serializers.ValidationError("Channel not found or inactive.")
    
    def validate_category_id(self, value):
        """Validate category exists."""
        if value:
            try:
                return NotificationCategory.objects.get(id=value)
            except NotificationCategory.DoesNotExist:
                raise serializers.ValidationError("Category not found.")
        return None