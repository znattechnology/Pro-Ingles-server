"""
Django admin configuration for notification models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from .models import (
    NotificationTemplate, NotificationChannel, UserNotificationPreference,
    NotificationCategory, Notification, NotificationBatch, NotificationAnalytics
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin interface for NotificationTemplate model."""
    
    list_display = [
        'name', 'template_type_display', 'is_active', 'usage_count', 'created_at'
    ]
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'template_type', 'is_active')
        }),
        ('Templates', {
            'fields': ('subject_template', 'body_template', 'html_template')
        }),
        ('Configuration', {
            'fields': ('description', 'variables')
        }),
        ('Statistics', {
            'fields': ('usage_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def template_type_display(self, obj):
        """Display template type with color coding."""
        colors = {
            'email': '#007bff',
            'push': '#28a745',
            'sms': '#ffc107',
            'in_app': '#6f42c1',
        }
        color = colors.get(obj.template_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_template_type_display()
        )
    template_type_display.short_description = "Type"
    
    def usage_count(self, obj):
        """Count how many notifications use this template."""
        return obj.notification_set.count()
    usage_count.short_description = "Usage Count"
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            usage_count=Count('notification')
        )


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    """Admin interface for NotificationChannel model."""
    
    list_display = [
        'name', 'channel_type_display', 'is_active', 'rate_limits_display',
        'usage_count', 'success_rate', 'created_at'
    ]
    list_filter = ['channel_type', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'usage_count', 'success_rate', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'channel_type', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('usage_count', 'success_rate')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def channel_type_display(self, obj):
        """Display channel type with icon."""
        icons = {
            'email': '📧',
            'push': '📱',
            'sms': '💬',
            'webhook': '🔗',
            'in_app': '🔔',
        }
        icon = icons.get(obj.channel_type, '❓')
        return f"{icon} {obj.get_channel_type_display()}"
    channel_type_display.short_description = "Type"
    
    def rate_limits_display(self, obj):
        """Display rate limits in readable format."""
        return f"{obj.rate_limit_per_minute}/min, {obj.rate_limit_per_hour}/hr, {obj.rate_limit_per_day}/day"
    rate_limits_display.short_description = "Rate Limits"
    
    def usage_count(self, obj):
        """Count notifications sent through this channel."""
        return obj.notification_set.count()
    usage_count.short_description = "Total Sent"
    
    def success_rate(self, obj):
        """Calculate success rate for this channel."""
        total = obj.notification_set.count()
        if total == 0:
            return "N/A"
        
        successful = obj.notification_set.filter(status__in=['sent', 'delivered']).count()
        rate = (successful / total) * 100
        
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            rate
        )
    success_rate.short_description = "Success Rate"


@admin.register(NotificationCategory)
class NotificationCategoryAdmin(admin.ModelAdmin):
    """Admin interface for NotificationCategory model."""
    
    list_display = [
        'display_name', 'name', 'priority', 'color_display', 'is_system',
        'notification_count', 'created_at'
    ]
    list_filter = ['is_system', 'priority', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['id', 'notification_count', 'created_at', 'updated_at']
    
    def color_display(self, obj):
        """Display color as colored circle."""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%; display: inline-block;"></div>',
            obj.color
        )
    color_display.short_description = "Color"
    
    def notification_count(self, obj):
        """Count notifications in this category."""
        return obj.notification_set.count()
    notification_count.short_description = "Notifications"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model."""
    
    list_display = [
        'title_preview', 'recipient_email', 'status_display', 'priority_display',
        'category_name', 'channel_name', 'sent_at', 'is_read_display'
    ]
    list_filter = [
        'status', 'priority', 'category', 'channel', 'created_at', 'sent_at'
    ]
    search_fields = ['title', 'message', 'recipient__email']
    readonly_fields = [
        'id', 'sent_at', 'delivered_at', 'read_at', 'clicked_at',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('id', 'title', 'message', 'html_content', 'data')
        }),
        ('Recipients & Classification', {
            'fields': ('recipient', 'category', 'template', 'channel')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'scheduled_at')
        }),
        ('Tracking', {
            'fields': (
                'sent_at', 'delivered_at', 'read_at', 'clicked_at', 'action_taken'
            )
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries')
        }),
        ('External Integration', {
            'fields': ('external_id', 'provider_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'resend_notification', 'cancel_notification']
    
    def title_preview(self, obj):
        """Display title preview with status indicator."""
        title = obj.title[:50] + ('...' if len(obj.title) > 50 else '')
        
        if obj.is_read:
            return format_html('✓ {}', title)
        elif obj.status == 'failed':
            return format_html('❌ {}', title)
        elif obj.status == 'pending':
            return format_html('⏳ {}', title)
        else:
            return format_html('📤 {}', title)
    title_preview.short_description = "Title"
    
    def recipient_email(self, obj):
        """Display recipient email with link to user admin."""
        url = reverse('admin:users_user_change', args=[obj.recipient.id])
        return format_html('<a href="{}">{}</a>', url, obj.recipient.email)
    recipient_email.short_description = "Recipient"
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'sent': '#28a745',
            'delivered': '#007bff',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def priority_display(self, obj):
        """Display priority with visual indicator."""
        indicators = {1: '🔵', 2: '🟡', 3: '🟠', 4: '🔴'}
        indicator = indicators.get(obj.priority, '⚪')
        return f"{indicator} {obj.get_priority_display()}"
    priority_display.short_description = "Priority"
    
    def category_name(self, obj):
        """Display category name."""
        return obj.category.display_name if obj.category else '-'
    category_name.short_description = "Category"
    
    def channel_name(self, obj):
        """Display channel name."""
        return obj.channel.name if obj.channel else '-'
    channel_name.short_description = "Channel"
    
    def is_read_display(self, obj):
        """Display read status."""
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">Unread</span>')
    is_read_display.short_description = "Read Status"
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = queryset.filter(read_at__isnull=True).update(
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark as read"
    
    def resend_notification(self, request, queryset):
        """Resend failed notifications."""
        from .tasks import send_notification
        
        count = 0
        for notification in queryset.filter(status='failed'):
            if notification.can_retry():
                notification.increment_retry()
                send_notification.delay(notification.id)
                count += 1
        
        self.message_user(request, f'{count} notifications queued for resending.')
    resend_notification.short_description = "Resend failed notifications"
    
    def cancel_notification(self, request, queryset):
        """Cancel pending notifications."""
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{updated} notifications cancelled.')
    cancel_notification.short_description = "Cancel pending notifications"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'recipient', 'category', 'template', 'channel'
        )


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for UserNotificationPreference model."""
    
    list_display = [
        'user_email', 'channels_enabled', 'digest_frequency', 'has_quiet_hours', 'created_at'
    ]
    list_filter = [
        'email_enabled', 'push_enabled', 'sms_enabled', 'in_app_enabled',
        'digest_frequency', 'created_at'
    ]
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = "User"
    
    def channels_enabled(self, obj):
        """Display enabled channels."""
        channels = []
        if obj.email_enabled:
            channels.append('📧')
        if obj.push_enabled:
            channels.append('📱')
        if obj.sms_enabled:
            channels.append('💬')
        if obj.in_app_enabled:
            channels.append('🔔')
        return ' '.join(channels) if channels else 'None'
    channels_enabled.short_description = "Enabled Channels"
    
    def has_quiet_hours(self, obj):
        """Check if user has quiet hours configured."""
        if obj.quiet_hours_start and obj.quiet_hours_end:
            return format_html(
                '<span style="color: green;">✓ {}-{}</span>',
                obj.quiet_hours_start.strftime('%H:%M'),
                obj.quiet_hours_end.strftime('%H:%M')
            )
        return format_html('<span style="color: gray;">No</span>')
    has_quiet_hours.short_description = "Quiet Hours"


@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    """Admin interface for NotificationBatch model."""
    
    list_display = [
        'name', 'recipient_count', 'template_name', 'channel_name',
        'status_display', 'success_rate', 'processed_at'
    ]
    list_filter = ['is_processed', 'template', 'channel', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'is_processed', 'processed_at', 'sent_count', 'failed_count',
        'created_at', 'updated_at'
    ]
    
    def template_name(self, obj):
        """Display template name."""
        return obj.template.name
    template_name.short_description = "Template"
    
    def channel_name(self, obj):
        """Display channel name."""
        return obj.channel.name
    channel_name.short_description = "Channel"
    
    def status_display(self, obj):
        """Display processing status."""
        if obj.is_processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    status_display.short_description = "Status"
    
    def success_rate(self, obj):
        """Calculate success rate for batch."""
        if not obj.is_processed or obj.recipient_count == 0:
            return "N/A"
        
        rate = (obj.sent_count / obj.recipient_count) * 100
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}% ({}/{})</span>',
            color,
            rate,
            obj.sent_count,
            obj.recipient_count
        )
    success_rate.short_description = "Success Rate"


@admin.register(NotificationAnalytics)
class NotificationAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for NotificationAnalytics model."""
    
    list_display = [
        'notification_title', 'opens', 'clicks', 'conversions',
        'engagement_rate', 'time_to_read_display', 'platform'
    ]
    list_filter = ['platform', 'device_type', 'country', 'created_at']
    search_fields = ['notification__title', 'notification__recipient__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def notification_title(self, obj):
        """Display notification title."""
        return obj.notification.title[:50]
    notification_title.short_description = "Notification"
    
    def engagement_rate(self, obj):
        """Calculate engagement rate."""
        if obj.opens > 0:
            rate = (obj.clicks / obj.opens) * 100
            color = 'green' if rate >= 20 else 'orange' if rate >= 10 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color,
                rate
            )
        return "N/A"
    engagement_rate.short_description = "Click Rate"
    
    def time_to_read_display(self, obj):
        """Display time to read in human format."""
        if obj.time_to_read:
            total_seconds = int(obj.time_to_read.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                return f"{total_seconds // 60}m"
            else:
                return f"{total_seconds // 3600}h"
        return "N/A"
    time_to_read_display.short_description = "Time to Read"