"""
Serializers for integrations app.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    IntegrationProvider, IntegrationLog, Webhook, APIQuota,
    FileUpload, SocialAuthProfile, LocationData
)

User = get_user_model()


class IntegrationProviderSerializer(serializers.ModelSerializer):
    """Serializer for integration providers."""
    
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_healthy = serializers.BooleanField(read_only=True)
    config_dict = serializers.JSONField(source='get_config_dict', read_only=True)
    
    class Meta:
        model = IntegrationProvider
        fields = [
            'id', 'name', 'display_name', 'provider_type', 'provider_type_display',
            'base_url', 'api_version', 'documentation_url', 'status', 'status_display',
            'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day',
            'last_health_check', 'health_status', 'error_count', 'success_count',
            'is_healthy', 'config_dict', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'last_health_check', 'health_status', 'error_count', 'success_count'
        ]
    
    def to_representation(self, instance):
        """Hide sensitive fields."""
        data = super().to_representation(instance)
        # Remove sensitive fields from API response
        data.pop('api_key', None)
        data.pop('api_secret', None)
        data.pop('access_token', None)
        data.pop('additional_config', None)
        return data


class IntegrationLogSerializer(serializers.ModelSerializer):
    """Serializer for integration logs."""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = IntegrationLog
        fields = [
            'id', 'provider', 'provider_name', 'log_type', 'log_type_display',
            'status', 'status_display', 'endpoint', 'method', 'request_data',
            'response_data', 'status_code', 'response_time', 'error_message',
            'user', 'user_email', 'correlation_id', 'ip_address', 'created_at'
        ]


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer for webhooks."""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Webhook
        fields = [
            'id', 'name', 'provider', 'provider_name', 'event_type', 'event_type_display',
            'url', 'headers', 'status', 'status_display', 'max_retries', 'retry_delay',
            'timeout', 'last_triggered', 'success_count', 'failure_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['last_triggered', 'success_count', 'failure_count']
    
    def to_representation(self, instance):
        """Hide sensitive fields."""
        data = super().to_representation(instance)
        data.pop('secret_key', None)
        return data


class APIQuotaSerializer(serializers.ModelSerializer):
    """Serializer for API quotas."""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    quota_type_display = serializers.CharField(source='get_quota_type_display', read_only=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    usage_percentage = serializers.FloatField(read_only=True)
    is_over_limit = serializers.BooleanField(read_only=True)
    is_warning_level = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = APIQuota
        fields = [
            'id', 'provider', 'provider_name', 'quota_type', 'quota_type_display',
            'period_type', 'period_type_display', 'limit_value', 'current_usage',
            'reset_at', 'warning_threshold', 'alert_sent', 'usage_percentage',
            'is_over_limit', 'is_warning_level', 'created_at', 'updated_at'
        ]
        read_only_fields = ['current_usage', 'reset_at', 'alert_sent']


class FileUploadSerializer(serializers.ModelSerializer):
    """Serializer for file uploads."""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    upload_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'provider', 'provider_name', 'user', 'user_email',
            'original_filename', 'file_type', 'file_type_display', 'file_size',
            'file_size_mb', 'mime_type', 'external_id', 'storage_path',
            'public_url', 'status', 'status_display', 'upload_started',
            'upload_completed', 'upload_duration', 'error_message',
            'metadata', 'created_at'
        ]
        read_only_fields = [
            'external_id', 'storage_path', 'public_url', 'upload_started',
            'upload_completed', 'error_message'
        ]
    
    def get_file_size_mb(self, obj):
        """Get file size in MB."""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_upload_duration(self, obj):
        """Get upload duration in seconds."""
        if obj.upload_started and obj.upload_completed:
            delta = obj.upload_completed - obj.upload_started
            return delta.total_seconds()
        return None


class SocialAuthProfileSerializer(serializers.ModelSerializer):
    """Serializer for social auth profiles."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    is_token_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SocialAuthProfile
        fields = [
            'id', 'user', 'user_email', 'provider', 'provider_display',
            'social_id', 'email', 'username', 'full_name', 'avatar_url',
            'token_expires_at', 'profile_data', 'is_verified', 'last_login',
            'is_token_valid', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'social_id', 'email', 'username', 'full_name', 'avatar_url',
            'token_expires_at', 'profile_data', 'last_login'
        ]
    
    def to_representation(self, instance):
        """Hide sensitive fields."""
        data = super().to_representation(instance)
        data.pop('access_token', None)
        data.pop('refresh_token', None)
        return data


class LocationDataSerializer(serializers.ModelSerializer):
    """Serializer for location data."""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    coordinates = serializers.SerializerMethodField()
    
    class Meta:
        model = LocationData
        fields = [
            'id', 'location_type', 'location_type_display', 'name',
            'street_address', 'city', 'state', 'postal_code', 'country',
            'latitude', 'longitude', 'coordinates', 'provider', 'provider_name',
            'external_place_id', 'formatted_address', 'place_data',
            'used_count', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['used_count', 'last_used', 'external_place_id']
    
    def get_coordinates(self, obj):
        """Get coordinates as [longitude, latitude] for GeoJSON compatibility."""
        if obj.latitude and obj.longitude:
            return [float(obj.longitude), float(obj.latitude)]
        return None


# API request/response serializers
class SMSMessageSerializer(serializers.Serializer):
    """Serializer for SMS message requests."""
    
    to_phone = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=1600)
    from_phone = serializers.CharField(max_length=20, required=False)


class GeocodeRequestSerializer(serializers.Serializer):
    """Serializer for geocoding requests."""
    
    address = serializers.CharField(max_length=500)


class ReverseGeocodeRequestSerializer(serializers.Serializer):
    """Serializer for reverse geocoding requests."""
    
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for image upload requests."""
    
    image = serializers.ImageField()
    folder = serializers.CharField(max_length=100, required=False, default='uploads')
    
    def validate_image(self, value):
        """Validate image file."""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large (max 10MB)")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Unsupported image format")
        
        return value


class EmailSubscriberSerializer(serializers.Serializer):
    """Serializer for email subscriber requests."""
    
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        max_length=10
    )


class WebhookTriggerSerializer(serializers.Serializer):
    """Serializer for webhook trigger requests."""
    
    event_type = serializers.CharField(max_length=50)
    data = serializers.JSONField()


class SocialAuthTokenSerializer(serializers.Serializer):
    """Serializer for social auth token exchange."""
    
    provider = serializers.ChoiceField(choices=SocialAuthProfile.PROVIDERS)
    authorization_code = serializers.CharField(max_length=500)
    redirect_uri = serializers.URLField()


class ProviderHealthCheckSerializer(serializers.Serializer):
    """Serializer for provider health check results."""
    
    provider_name = serializers.CharField()
    is_healthy = serializers.BooleanField()
    response_time = serializers.FloatField()
    last_check = serializers.DateTimeField()
    error_message = serializers.CharField(required=False)


class IntegrationStatsSerializer(serializers.Serializer):
    """Serializer for integration statistics."""
    
    total_providers = serializers.IntegerField()
    active_providers = serializers.IntegerField()
    total_requests_today = serializers.IntegerField()
    successful_requests_today = serializers.IntegerField()
    failed_requests_today = serializers.IntegerField()
    success_rate = serializers.FloatField()
    quota_warnings = serializers.IntegerField()
    quota_exceeded = serializers.IntegerField()