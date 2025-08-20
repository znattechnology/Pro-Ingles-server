"""
Models for external integrations and API management.
"""

import json
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField

from apps.core.models import BaseModel

User = get_user_model()


class IntegrationProvider(BaseModel):
    """External service providers and their configurations."""
    
    PROVIDER_TYPES = [
        ('maps', 'Maps & Location'),
        ('sms', 'SMS Service'),
        ('email', 'Email Marketing'),
        ('storage', 'File Storage'),
        ('social', 'Social Authentication'),
        ('payment', 'Payment Gateway'),
        ('analytics', 'Analytics'),
        ('backup', 'Backup Service'),
        ('verification', 'Identity Verification'),
        ('other', 'Other Services'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
        ('deprecated', 'Deprecated'),
    ]
    
    # Provider identification
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    
    # Configuration
    base_url = models.URLField(blank=True, help_text="Base API URL")
    api_version = models.CharField(max_length=20, blank=True)
    documentation_url = models.URLField(blank=True)
    
    # Credentials (encrypted)
    api_key = EncryptedCharField(max_length=500, blank=True)
    api_secret = EncryptedCharField(max_length=500, blank=True)
    access_token = EncryptedTextField(blank=True)
    additional_config = EncryptedTextField(blank=True, help_text="JSON configuration")
    
    # Status and limits
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    rate_limit_per_minute = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_per_hour = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_per_day = models.PositiveIntegerField(null=True, blank=True)
    
    # Monitoring
    last_health_check = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=20, default='unknown')
    error_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['provider_type', 'name']
        indexes = [
            models.Index(fields=['provider_type', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.get_provider_type_display()})"
    
    def get_config_dict(self):
        """Get additional configuration as dictionary."""
        try:
            return json.loads(self.additional_config) if self.additional_config else {}
        except json.JSONDecodeError:
            return {}
    
    def set_config_dict(self, config_dict):
        """Set additional configuration from dictionary."""
        self.additional_config = json.dumps(config_dict)
    
    def is_healthy(self):
        """Check if provider is considered healthy."""
        return self.health_status == 'healthy' and self.status == 'active'
    
    def increment_success(self):
        """Increment success counter."""
        self.success_count += 1
        self.save(update_fields=['success_count'])
    
    def increment_error(self):
        """Increment error counter."""
        self.error_count += 1
        self.save(update_fields=['error_count'])


class IntegrationLog(BaseModel):
    """Log of integration API calls and responses."""
    
    LOG_TYPES = [
        ('request', 'API Request'),
        ('response', 'API Response'),
        ('webhook', 'Webhook Received'),
        ('error', 'Error'),
        ('health_check', 'Health Check'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]
    
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE, related_name='logs')
    
    # Log details
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Request/Response data
    endpoint = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    # Metadata
    status_code = models.PositiveIntegerField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    error_message = models.TextField(blank=True)
    
    # Context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, help_text="For tracking related requests")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['log_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.provider.name} - {self.get_log_type_display()} ({self.status})"


class Webhook(BaseModel):
    """Webhook endpoints for external services."""
    
    EVENT_TYPES = [
        ('payment.success', 'Payment Successful'),
        ('payment.failed', 'Payment Failed'),
        ('user.created', 'User Created'),
        ('booking.confirmed', 'Booking Confirmed'),
        ('file.uploaded', 'File Uploaded'),
        ('email.sent', 'Email Sent'),
        ('sms.sent', 'SMS Sent'),
        ('verification.completed', 'Verification Completed'),
        ('custom', 'Custom Event'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
    ]
    
    # Webhook identification
    name = models.CharField(max_length=100)
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE, related_name='webhooks')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    
    # Configuration
    url = models.URLField(help_text="Webhook endpoint URL")
    secret_key = EncryptedCharField(max_length=200, blank=True, help_text="Secret for signature verification")
    headers = models.JSONField(default=dict, help_text="Additional headers to send")
    
    # Settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    max_retries = models.PositiveIntegerField(default=3)
    retry_delay = models.PositiveIntegerField(default=60, help_text="Retry delay in seconds")
    timeout = models.PositiveIntegerField(default=30, help_text="Request timeout in seconds")
    
    # Monitoring
    last_triggered = models.DateTimeField(null=True, blank=True)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['provider', 'event_type']
        unique_together = [['provider', 'event_type', 'url']]
        indexes = [
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['event_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_event_type_display()}"
    
    def increment_success(self):
        """Increment success counter."""
        self.success_count += 1
        self.last_triggered = timezone.now()
        self.save(update_fields=['success_count', 'last_triggered'])
    
    def increment_failure(self):
        """Increment failure counter."""
        self.failure_count += 1
        self.save(update_fields=['failure_count'])


class APIQuota(BaseModel):
    """Track API usage and quotas for different providers."""
    
    QUOTA_TYPES = [
        ('requests', 'API Requests'),
        ('storage', 'Storage Usage'),
        ('bandwidth', 'Bandwidth Usage'),
        ('sms', 'SMS Messages'),
        ('emails', 'Email Messages'),
        ('custom', 'Custom Metric'),
    ]
    
    PERIOD_TYPES = [
        ('hour', 'Per Hour'),
        ('day', 'Per Day'),
        ('month', 'Per Month'),
        ('year', 'Per Year'),
    ]
    
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE, related_name='quotas')
    
    # Quota definition
    quota_type = models.CharField(max_length=20, choices=QUOTA_TYPES)
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    limit_value = models.PositiveIntegerField(help_text="Maximum allowed usage")
    
    # Current usage
    current_usage = models.PositiveIntegerField(default=0)
    reset_at = models.DateTimeField(help_text="When usage counter resets")
    
    # Alerts
    warning_threshold = models.PositiveIntegerField(help_text="Percentage to trigger warning (e.g., 80)")
    alert_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['provider', 'quota_type']
        unique_together = [['provider', 'quota_type', 'period_type']]
        indexes = [
            models.Index(fields=['provider', 'reset_at']),
            models.Index(fields=['reset_at']),
        ]
    
    def __str__(self):
        return f"{self.provider.name} - {self.get_quota_type_display()} ({self.get_period_type_display()})"
    
    def usage_percentage(self):
        """Calculate current usage percentage."""
        if self.limit_value == 0:
            return 0
        return (self.current_usage / self.limit_value) * 100
    
    def is_over_limit(self):
        """Check if usage is over the limit."""
        return self.current_usage >= self.limit_value
    
    def is_warning_level(self):
        """Check if usage is at warning level."""
        return self.usage_percentage() >= self.warning_threshold
    
    def increment_usage(self, amount=1):
        """Increment usage counter."""
        self.current_usage += amount
        self.save(update_fields=['current_usage'])
    
    def reset_usage(self):
        """Reset usage counter and update reset time."""
        from datetime import timedelta
        
        self.current_usage = 0
        self.alert_sent = False
        
        # Calculate next reset time
        if self.period_type == 'hour':
            self.reset_at = timezone.now() + timedelta(hours=1)
        elif self.period_type == 'day':
            self.reset_at = timezone.now() + timedelta(days=1)
        elif self.period_type == 'month':
            # Approximate month
            self.reset_at = timezone.now() + timedelta(days=30)
        elif self.period_type == 'year':
            self.reset_at = timezone.now() + timedelta(days=365)
        
        self.save(update_fields=['current_usage', 'alert_sent', 'reset_at'])


class FileUpload(BaseModel):
    """Track file uploads to external storage services."""
    
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('deleted', 'Deleted'),
    ]
    
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE, related_name='uploads')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    
    # File details
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    
    # Storage details
    external_id = models.CharField(max_length=500, help_text="External service file ID")
    storage_path = models.CharField(max_length=1000, help_text="Path in storage service")
    public_url = models.URLField(blank=True, help_text="Public access URL")
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    upload_started = models.DateTimeField(default=timezone.now)
    upload_completed = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Optional metadata
    metadata = models.JSONField(default=dict, help_text="Additional file metadata")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['file_type', '-created_at']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"
    
    def mark_completed(self, public_url=None):
        """Mark upload as completed."""
        self.status = 'completed'
        self.upload_completed = timezone.now()
        if public_url:
            self.public_url = public_url
        self.save(update_fields=['status', 'upload_completed', 'public_url'])
    
    def mark_failed(self, error_message):
        """Mark upload as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


class SocialAuthProfile(BaseModel):
    """Social authentication profiles linked to users."""
    
    PROVIDERS = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('apple', 'Apple'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_profiles')
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    
    # Social profile data
    social_id = models.CharField(max_length=100, help_text="User ID in social platform")
    email = models.EmailField(blank=True)
    username = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    
    # OAuth tokens (encrypted)
    access_token = EncryptedTextField(blank=True)
    refresh_token = EncryptedTextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Profile data
    profile_data = models.JSONField(default=dict, help_text="Additional profile information")
    
    # Status
    is_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['provider', 'user']
        unique_together = [['user', 'provider'], ['provider', 'social_id']]
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['provider', 'social_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_provider_display()}"
    
    def is_token_valid(self):
        """Check if access token is still valid."""
        if not self.token_expires_at:
            return True  # No expiration set
        return timezone.now() < self.token_expires_at
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class LocationData(BaseModel):
    """Store location data from mapping services."""
    
    LOCATION_TYPES = [
        ('address', 'Street Address'),
        ('business', 'Business Location'),
        ('landmark', 'Landmark'),
        ('coordinates', 'GPS Coordinates'),
    ]
    
    # Location identification
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    name = models.CharField(max_length=200, blank=True)
    
    # Address components
    street_address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # External service data
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.SET_NULL, null=True, blank=True)
    external_place_id = models.CharField(max_length=200, blank=True)
    
    # Additional data
    formatted_address = models.CharField(max_length=500, blank=True)
    place_data = models.JSONField(default=dict, help_text="Additional place information")
    
    # Usage tracking
    used_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-used_count', 'name']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['postal_code']),
            models.Index(fields=['external_place_id']),
        ]
    
    def __str__(self):
        return self.formatted_address or f"{self.city}, {self.state}"
    
    def increment_usage(self):
        """Increment usage counter."""
        self.used_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['used_count', 'last_used'])
