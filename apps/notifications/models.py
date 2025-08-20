"""
Models for advanced notification system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
import json

from apps.core.models import BaseModel

User = get_user_model()


class NotificationTemplate(BaseModel):
    """Template for notification messages."""
    
    TEMPLATE_TYPES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
        ('in_app', 'In-App Notification'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Unique template name")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    subject_template = models.CharField(max_length=200, help_text="Subject line template")
    body_template = models.TextField(help_text="Message body template with variables")
    html_template = models.TextField(blank=True, help_text="HTML template for rich content")
    is_active = models.BooleanField(default=True)
    
    # Template metadata
    description = models.TextField(blank=True)
    variables = models.JSONField(
        default=dict,
        help_text="Available template variables and their descriptions"
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['template_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def render_subject(self, context):
        """Render subject with context variables."""
        from django.template import Template, Context
        template = Template(self.subject_template)
        return template.render(Context(context))
    
    def render_body(self, context):
        """Render body with context variables."""
        from django.template import Template, Context
        template = Template(self.body_template)
        return template.render(Context(context))
    
    def render_html(self, context):
        """Render HTML with context variables."""
        if not self.html_template:
            return None
        from django.template import Template, Context
        template = Template(self.html_template)
        return template.render(Context(context))


class NotificationChannel(BaseModel):
    """Configuration for notification channels."""
    
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('sms', 'SMS'),
        ('in_app', 'In-App'),
        ('webhook', 'Webhook'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    is_active = models.BooleanField(default=True)
    
    # Channel configuration
    config = models.JSONField(
        default=dict,
        help_text="Channel-specific configuration (API keys, URLs, etc.)"
    )
    
    # Rate limiting
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    rate_limit_per_hour = models.PositiveIntegerField(default=1000)
    rate_limit_per_day = models.PositiveIntegerField(default=10000)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['channel_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
    
    def can_send_notification(self):
        """Check if channel can send notification based on rate limits."""
        now = timezone.now()
        
        # Check minute rate limit
        minute_ago = now - timezone.timedelta(minutes=1)
        minute_count = Notification.objects.filter(
            channel=self,
            created_at__gte=minute_ago,
            status='sent'
        ).count()
        
        if minute_count >= self.rate_limit_per_minute:
            return False, "Rate limit exceeded (per minute)"
        
        # Check hour rate limit
        hour_ago = now - timezone.timedelta(hours=1)
        hour_count = Notification.objects.filter(
            channel=self,
            created_at__gte=hour_ago,
            status='sent'
        ).count()
        
        if hour_count >= self.rate_limit_per_hour:
            return False, "Rate limit exceeded (per hour)"
        
        # Check day rate limit
        day_ago = now - timezone.timedelta(days=1)
        day_count = Notification.objects.filter(
            channel=self,
            created_at__gte=day_ago,
            status='sent'
        ).count()
        
        if day_count >= self.rate_limit_per_day:
            return False, "Rate limit exceeded (per day)"
        
        return True, "OK"


class UserNotificationPreference(BaseModel):
    """User preferences for notifications."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Global preferences
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    
    # Timing preferences
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Start of quiet hours")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="End of quiet hours")
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Content preferences
    marketing_enabled = models.BooleanField(default=True)
    promotional_enabled = models.BooleanField(default=True)
    system_enabled = models.BooleanField(default=True)
    
    # Frequency preferences
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('instant', 'Instant'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('never', 'Never')
        ],
        default='daily'
    )
    
    # Category-specific preferences
    category_preferences = models.JSONField(
        default=dict,
        help_text="Preferences by notification category"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
    
    def is_quiet_time(self):
        """Check if current time is within user's quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        import pytz
        user_tz = pytz.timezone(self.timezone)
        now = timezone.now().astimezone(user_tz).time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day quiet hours
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Cross-midnight quiet hours
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
    
    def should_receive_notification(self, channel_type, category=None):
        """Check if user should receive notification on specific channel."""
        # Check global preferences
        if channel_type == 'email' and not self.email_enabled:
            return False
        elif channel_type == 'push' and not self.push_enabled:
            return False
        elif channel_type == 'sms' and not self.sms_enabled:
            return False
        elif channel_type == 'in_app' and not self.in_app_enabled:
            return False
        
        # Check quiet hours for push notifications
        if channel_type == 'push' and self.is_quiet_time():
            return False
        
        # Check category preferences
        if category and category in self.category_preferences:
            return self.category_preferences[category].get(channel_type, True)
        
        return True


class NotificationCategory(BaseModel):
    """Categories for organizing notifications."""
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    
    # Priority settings
    priority = models.IntegerField(default=1, help_text="Higher numbers = higher priority")
    is_system = models.BooleanField(default=False, help_text="System notifications cannot be disabled")
    
    class Meta:
        verbose_name_plural = "Notification Categories"
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['priority']),
            models.Index(fields=['is_system']),
        ]
    
    def __str__(self):
        return self.display_name


class Notification(BaseModel):
    """Individual notification instance."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Urgent'),
    ]
    
    # Recipients
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    html_content = models.TextField(blank=True)
    data = models.JSONField(default=dict, help_text="Additional data for rich notifications")
    
    # Classification
    category = models.ForeignKey(NotificationCategory, on_delete=models.SET_NULL, null=True)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True)
    channel = models.ForeignKey(NotificationChannel, on_delete=models.SET_NULL, null=True)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    
    # Scheduling
    scheduled_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When to send notification (null = send immediately)"
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Interaction tracking
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.CharField(max_length=100, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # External tracking
    external_id = models.CharField(max_length=200, blank=True, help_text="External provider ID")
    provider_response = models.JSONField(default=dict, help_text="Response from notification provider")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['category']),
            models.Index(fields=['priority']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.title} -> {self.recipient.email}"
    
    @property
    def is_read(self):
        """Check if notification has been read."""
        return self.read_at is not None
    
    @property
    def is_clicked(self):
        """Check if notification has been clicked."""
        return self.clicked_at is not None
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
    
    def mark_as_clicked(self, action=None):
        """Mark notification as clicked with optional action."""
        now = timezone.now()
        if not self.clicked_at:
            self.clicked_at = now
        if not self.read_at:
            self.read_at = now
        if action:
            self.action_taken = action
        self.save(update_fields=['clicked_at', 'read_at', 'action_taken'])
    
    def mark_as_sent(self, external_id=None, provider_response=None):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        if provider_response:
            self.provider_response = provider_response
        self.save(update_fields=['status', 'sent_at', 'external_id', 'provider_response'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_failed(self, error_message=None):
        """Mark notification as failed."""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])
    
    def can_retry(self):
        """Check if notification can be retried."""
        return self.status == 'failed' and self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.status = 'pending'
        self.save(update_fields=['retry_count', 'status'])


class NotificationBatch(BaseModel):
    """Batch processing for bulk notifications."""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Recipients
    recipient_count = models.PositiveIntegerField(default=0)
    
    # Template and channel
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)
    category = models.ForeignKey(NotificationCategory, on_delete=models.SET_NULL, null=True)
    
    # Batch data
    context_data = models.JSONField(default=dict, help_text="Common context for all notifications")
    recipient_data = models.JSONField(default=list, help_text="Individual recipient data")
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_processed']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"Batch: {self.name} ({self.recipient_count} recipients)"
    
    def process_batch(self):
        """Process batch and create individual notifications."""
        from .tasks import process_notification_batch
        if not self.is_processed:
            process_notification_batch.delay(self.id)


class NotificationAnalytics(BaseModel):
    """Analytics for notification performance."""
    
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Engagement metrics
    opens = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    
    # Timing metrics
    time_to_read = models.DurationField(null=True, blank=True)
    time_to_click = models.DurationField(null=True, blank=True)
    
    # Device/platform info
    device_type = models.CharField(max_length=50, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Location data
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name_plural = "Notification Analytics"
        indexes = [
            models.Index(fields=['notification']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.notification.title}"