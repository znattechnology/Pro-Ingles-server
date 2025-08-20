"""
Tests for integrations functionality including external APIs, webhooks, and social authentication.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
import json
import uuid

from .models import (
    IntegrationProvider, IntegrationLog, Webhook, APIQuota, FileUpload,
    SocialAuthProfile, LocationData
)

User = get_user_model()


class IntegrationProviderModelTest(TestCase):
    """Test IntegrationProvider model functionality."""
    
    def setUp(self):
        self.provider_data = {
            'name': 'stripe_payments',
            'display_name': 'Stripe Payment Gateway',
            'provider_type': 'payment',
            'base_url': 'https://api.stripe.com',
            'api_version': 'v1',
            'documentation_url': 'https://docs.stripe.com',
            'api_key': 'sk_test_123456789',
            'api_secret': 'secret_key_789',
            'rate_limit_per_minute': 100,
            'rate_limit_per_hour': 1000,
            'rate_limit_per_day': 10000
        }
    
    def test_create_integration_provider(self):
        """Test creating integration provider."""
        provider = IntegrationProvider.objects.create(**self.provider_data)
        
        self.assertEqual(provider.name, 'stripe_payments')
        self.assertEqual(provider.display_name, 'Stripe Payment Gateway')
        self.assertEqual(provider.provider_type, 'payment')
        self.assertEqual(provider.base_url, 'https://api.stripe.com')
        self.assertEqual(provider.status, 'active')
        self.assertEqual(provider.error_count, 0)
        self.assertEqual(provider.success_count, 0)
    
    def test_provider_string_representation(self):
        """Test provider string representation."""
        provider = IntegrationProvider.objects.create(**self.provider_data)
        expected = "Stripe Payment Gateway (Payment Gateway)"
        self.assertEqual(str(provider), expected)
    
    def test_config_dict_operations(self):
        """Test configuration dictionary operations."""
        provider = IntegrationProvider.objects.create(**self.provider_data)
        
        # Set configuration
        config = {
            'webhook_secret': 'whsec_test123',
            'connect_enabled': True,
            'supported_currencies': ['EUR', 'USD', 'GBP']
        }
        provider.set_config_dict(config)
        provider.save()
        
        # Get configuration
        retrieved_config = provider.get_config_dict()
        self.assertEqual(retrieved_config['webhook_secret'], 'whsec_test123')
        self.assertTrue(retrieved_config['connect_enabled'])
        self.assertIn('EUR', retrieved_config['supported_currencies'])
    
    def test_health_status_check(self):
        """Test health status checking."""
        provider = IntegrationProvider.objects.create(
            **self.provider_data,
            health_status='healthy'
        )
        
        self.assertTrue(provider.is_healthy())
        
        # Test unhealthy status
        provider.health_status = 'unhealthy'
        provider.save()
        self.assertFalse(provider.is_healthy())
        
        # Test inactive status
        provider.health_status = 'healthy'
        provider.status = 'inactive'
        provider.save()
        self.assertFalse(provider.is_healthy())
    
    def test_counter_operations(self):
        """Test success and error counter operations."""
        provider = IntegrationProvider.objects.create(**self.provider_data)
        
        # Test success increment
        initial_success = provider.success_count
        provider.increment_success()
        self.assertEqual(provider.success_count, initial_success + 1)
        
        # Test error increment
        initial_error = provider.error_count
        provider.increment_error()
        self.assertEqual(provider.error_count, initial_error + 1)
    
    def test_maps_provider(self):
        """Test creating maps integration provider."""
        maps_provider = IntegrationProvider.objects.create(
            name='google_maps',
            display_name='Google Maps Platform',
            provider_type='maps',
            base_url='https://maps.googleapis.com',
            api_key='AIza_test_key_123',
            rate_limit_per_day=25000
        )
        
        self.assertEqual(maps_provider.provider_type, 'maps')
        self.assertEqual(maps_provider.rate_limit_per_day, 25000)
    
    def test_sms_provider(self):
        """Test creating SMS service provider."""
        sms_provider = IntegrationProvider.objects.create(
            name='twilio_sms',
            display_name='Twilio SMS Service',
            provider_type='sms',
            base_url='https://api.twilio.com',
            api_key='AC_test_account_sid',
            api_secret='auth_token_test',
            rate_limit_per_minute=60
        )
        
        self.assertEqual(sms_provider.provider_type, 'sms')
        self.assertEqual(sms_provider.rate_limit_per_minute, 60)
    
    def test_storage_provider(self):
        """Test creating storage service provider."""
        storage_provider = IntegrationProvider.objects.create(
            name='aws_s3',
            display_name='Amazon S3 Storage',
            provider_type='storage',
            base_url='https://s3.amazonaws.com',
            api_key='AKIA_access_key',
            api_secret='secret_access_key',
            status='testing'
        )
        
        self.assertEqual(storage_provider.provider_type, 'storage')
        self.assertEqual(storage_provider.status, 'testing')


class IntegrationLogModelTest(TestCase):
    """Test IntegrationLog model functionality."""
    
    def setUp(self):
        self.provider = IntegrationProvider.objects.create(
            name='test_provider',
            display_name='Test Provider',
            provider_type='payment'
        )
        
        self.user = User.objects.create_user(
            email='integration@test.com',
            name='Integration User',
            password='testpass'
        )
        
        self.log_data = {
            'provider': self.provider,
            'log_type': 'request',
            'status': 'success',
            'endpoint': '/v1/payments',
            'method': 'POST',
            'status_code': 200,
            'response_time': 0.245,
            'user': self.user
        }
    
    def test_create_integration_log(self):
        """Test creating integration log."""
        log = IntegrationLog.objects.create(**self.log_data)
        
        self.assertEqual(log.provider, self.provider)
        self.assertEqual(log.log_type, 'request')
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.endpoint, '/v1/payments')
        self.assertEqual(log.method, 'POST')
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.response_time, 0.245)
        self.assertIsNotNone(log.correlation_id)
    
    def test_log_string_representation(self):
        """Test log string representation."""
        log = IntegrationLog.objects.create(**self.log_data)
        expected = f"{self.provider.name} - API Request (success)"
        self.assertEqual(str(log), expected)
    
    def test_api_request_with_data(self):
        """Test API request log with request/response data."""
        request_data = {
            'amount': 10000,
            'currency': 'eur',
            'description': 'Test payment'
        }
        
        response_data = {
            'id': 'pi_test123',
            'status': 'succeeded',
            'amount_received': 10000
        }
        
        log = IntegrationLog.objects.create(
            **self.log_data,
            request_data=request_data,
            response_data=response_data
        )
        
        self.assertEqual(log.request_data['amount'], 10000)
        self.assertEqual(log.response_data['id'], 'pi_test123')
        self.assertEqual(log.response_data['status'], 'succeeded')
    
    def test_error_log(self):
        """Test error log creation."""
        error_log = IntegrationLog.objects.create(
            provider=self.provider,
            log_type='error',
            status='error',
            endpoint='/v1/payments',
            method='POST',
            status_code=400,
            error_message='Invalid payment method',
            response_time=0.123
        )
        
        self.assertEqual(error_log.log_type, 'error')
        self.assertEqual(error_log.status, 'error')
        self.assertEqual(error_log.status_code, 400)
        self.assertEqual(error_log.error_message, 'Invalid payment method')
    
    def test_webhook_log(self):
        """Test webhook log creation."""
        webhook_data = {
            'event': 'payment.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test123',
                    'amount': 5000
                }
            }
        }
        
        webhook_log = IntegrationLog.objects.create(
            provider=self.provider,
            log_type='webhook',
            status='success',
            endpoint='/webhooks/stripe',
            method='POST',
            request_data=webhook_data,
            ip_address='52.89.214.238'
        )
        
        self.assertEqual(webhook_log.log_type, 'webhook')
        self.assertEqual(webhook_log.request_data['event'], 'payment.succeeded')
        self.assertEqual(webhook_log.ip_address, '52.89.214.238')
    
    def test_health_check_log(self):
        """Test health check log creation."""
        health_log = IntegrationLog.objects.create(
            provider=self.provider,
            log_type='health_check',
            status='success',
            endpoint='/health',
            method='GET',
            status_code=200,
            response_time=0.089,
            response_data={'status': 'ok', 'timestamp': '2024-01-15T10:30:00Z'}
        )
        
        self.assertEqual(health_log.log_type, 'health_check')
        self.assertEqual(health_log.response_data['status'], 'ok')


class WebhookModelTest(TestCase):
    """Test Webhook model functionality."""
    
    def setUp(self):
        self.provider = IntegrationProvider.objects.create(
            name='payment_provider',
            display_name='Payment Provider',
            provider_type='payment'
        )
        
        self.webhook_data = {
            'name': 'Payment Success Webhook',
            'provider': self.provider,
            'event_type': 'payment.success',
            'url': 'https://api.tuwi.com/webhooks/payment-success',
            'secret_key': 'whsec_test123456789',
            'max_retries': 3,
            'timeout': 30
        }
    
    def test_create_webhook(self):
        """Test creating webhook."""
        webhook = Webhook.objects.create(**self.webhook_data)
        
        self.assertEqual(webhook.name, 'Payment Success Webhook')
        self.assertEqual(webhook.provider, self.provider)
        self.assertEqual(webhook.event_type, 'payment.success')
        self.assertEqual(webhook.url, 'https://api.tuwi.com/webhooks/payment-success')
        self.assertEqual(webhook.status, 'active')
        self.assertEqual(webhook.success_count, 0)
        self.assertEqual(webhook.failure_count, 0)
    
    def test_webhook_string_representation(self):
        """Test webhook string representation."""
        webhook = Webhook.objects.create(**self.webhook_data)
        expected = "Payment Success Webhook - Payment Successful"
        self.assertEqual(str(webhook), expected)
    
    def test_webhook_with_headers(self):
        """Test webhook with custom headers."""
        webhook = Webhook.objects.create(
            **self.webhook_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer token123',
                'X-Custom-Header': 'custom-value'
            }
        )
        
        self.assertEqual(webhook.headers['Content-Type'], 'application/json')
        self.assertEqual(webhook.headers['Authorization'], 'Bearer token123')
        self.assertIn('X-Custom-Header', webhook.headers)
    
    def test_webhook_counter_operations(self):
        """Test webhook success and failure counters."""
        webhook = Webhook.objects.create(**self.webhook_data)
        
        # Test success increment
        initial_success = webhook.success_count
        webhook.increment_success()
        self.assertEqual(webhook.success_count, initial_success + 1)
        self.assertIsNotNone(webhook.last_triggered)
        
        # Test failure increment
        initial_failure = webhook.failure_count
        webhook.increment_failure()
        self.assertEqual(webhook.failure_count, initial_failure + 1)
    
    def test_user_created_webhook(self):
        """Test user creation webhook."""
        user_webhook = Webhook.objects.create(
            name='User Registration Webhook',
            provider=self.provider,
            event_type='user.created',
            url='https://analytics.tuwi.com/webhooks/user-created',
            timeout=15,
            status='testing'
        )
        
        self.assertEqual(user_webhook.event_type, 'user.created')
        self.assertEqual(user_webhook.timeout, 15)
        self.assertEqual(user_webhook.status, 'testing')
    
    def test_custom_webhook(self):
        """Test custom event webhook."""
        custom_webhook = Webhook.objects.create(
            name='Custom Business Event',
            provider=self.provider,
            event_type='custom',
            url='https://external.service.com/webhook',
            max_retries=5,
            retry_delay=120
        )
        
        self.assertEqual(custom_webhook.event_type, 'custom')
        self.assertEqual(custom_webhook.max_retries, 5)
        self.assertEqual(custom_webhook.retry_delay, 120)


class APIQuotaModelTest(TestCase):
    """Test APIQuota model functionality."""
    
    def setUp(self):
        self.provider = IntegrationProvider.objects.create(
            name='quota_provider',
            display_name='Quota Test Provider',
            provider_type='sms'
        )
        
        self.quota_data = {
            'provider': self.provider,
            'quota_type': 'requests',
            'period_type': 'day',
            'limit_value': 1000,
            'warning_threshold': 80,
            'reset_at': timezone.now() + timedelta(days=1)
        }
    
    def test_create_api_quota(self):
        """Test creating API quota."""
        quota = APIQuota.objects.create(**self.quota_data)
        
        self.assertEqual(quota.provider, self.provider)
        self.assertEqual(quota.quota_type, 'requests')
        self.assertEqual(quota.period_type, 'day')
        self.assertEqual(quota.limit_value, 1000)
        self.assertEqual(quota.current_usage, 0)
        self.assertEqual(quota.warning_threshold, 80)
        self.assertFalse(quota.alert_sent)
    
    def test_quota_string_representation(self):
        """Test quota string representation."""
        quota = APIQuota.objects.create(**self.quota_data)
        expected = f"{self.provider.name} - API Requests (Per Day)"
        self.assertEqual(str(quota), expected)
    
    def test_usage_percentage_calculation(self):
        """Test usage percentage calculation."""
        quota = APIQuota.objects.create(**self.quota_data)
        
        # Test 0% usage
        self.assertEqual(quota.usage_percentage(), 0)
        
        # Test 50% usage
        quota.current_usage = 500
        quota.save()
        self.assertEqual(quota.usage_percentage(), 50)
        
        # Test 100% usage
        quota.current_usage = 1000
        quota.save()
        self.assertEqual(quota.usage_percentage(), 100)
    
    def test_limit_checking(self):
        """Test limit checking methods."""
        quota = APIQuota.objects.create(**self.quota_data)
        
        # Test under limit
        quota.current_usage = 500
        quota.save()
        self.assertFalse(quota.is_over_limit())
        self.assertFalse(quota.is_warning_level())
        
        # Test at warning level
        quota.current_usage = 850  # 85% of 1000
        quota.save()
        self.assertFalse(quota.is_over_limit())
        self.assertTrue(quota.is_warning_level())
        
        # Test over limit
        quota.current_usage = 1100
        quota.save()
        self.assertTrue(quota.is_over_limit())
        self.assertTrue(quota.is_warning_level())
    
    def test_increment_usage(self):
        """Test incrementing usage counter."""
        quota = APIQuota.objects.create(**self.quota_data)
        
        initial_usage = quota.current_usage
        quota.increment_usage()
        self.assertEqual(quota.current_usage, initial_usage + 1)
        
        # Test increment by custom amount
        quota.increment_usage(50)
        self.assertEqual(quota.current_usage, initial_usage + 51)
    
    def test_reset_usage(self):
        """Test resetting usage counter."""
        quota = APIQuota.objects.create(
            **self.quota_data,
            current_usage=750,
            alert_sent=True
        )
        
        # Reset usage
        quota.reset_usage()
        
        self.assertEqual(quota.current_usage, 0)
        self.assertFalse(quota.alert_sent)
        self.assertGreater(quota.reset_at, timezone.now())
    
    def test_sms_quota(self):
        """Test SMS-specific quota."""
        sms_quota = APIQuota.objects.create(
            provider=self.provider,
            quota_type='sms',
            period_type='month',
            limit_value=10000,
            warning_threshold=90,
            reset_at=timezone.now() + timedelta(days=30)
        )
        
        self.assertEqual(sms_quota.quota_type, 'sms')
        self.assertEqual(sms_quota.period_type, 'month')
        self.assertEqual(sms_quota.warning_threshold, 90)
    
    def test_storage_quota(self):
        """Test storage quota."""
        storage_quota = APIQuota.objects.create(
            provider=self.provider,
            quota_type='storage',
            period_type='month',
            limit_value=107374182400,  # 100GB in bytes
            warning_threshold=85,
            reset_at=timezone.now() + timedelta(days=30)
        )
        
        self.assertEqual(storage_quota.quota_type, 'storage')
        self.assertEqual(storage_quota.limit_value, 107374182400)


class FileUploadModelTest(TestCase):
    """Test FileUpload model functionality."""
    
    def setUp(self):
        self.provider = IntegrationProvider.objects.create(
            name='file_storage',
            display_name='File Storage Service',
            provider_type='storage'
        )
        
        self.user = User.objects.create_user(
            email='upload@test.com',
            name='Upload User',
            password='testpass'
        )
        
        self.upload_data = {
            'provider': self.provider,
            'user': self.user,
            'original_filename': 'profile_photo.jpg',
            'file_type': 'image',
            'file_size': 2048576,  # 2MB
            'mime_type': 'image/jpeg',
            'external_id': 'file_abc123def456',
            'storage_path': '/uploads/users/profile_photo.jpg'
        }
    
    def test_create_file_upload(self):
        """Test creating file upload record."""
        upload = FileUpload.objects.create(**self.upload_data)
        
        self.assertEqual(upload.provider, self.provider)
        self.assertEqual(upload.user, self.user)
        self.assertEqual(upload.original_filename, 'profile_photo.jpg')
        self.assertEqual(upload.file_type, 'image')
        self.assertEqual(upload.file_size, 2048576)
        self.assertEqual(upload.status, 'uploading')
        self.assertIsNotNone(upload.upload_started)
    
    def test_upload_string_representation(self):
        """Test upload string representation."""
        upload = FileUpload.objects.create(**self.upload_data)
        expected = "profile_photo.jpg (Uploading)"
        self.assertEqual(str(upload), expected)
    
    def test_mark_upload_completed(self):
        """Test marking upload as completed."""
        upload = FileUpload.objects.create(**self.upload_data)
        
        public_url = 'https://cdn.tuwi.com/uploads/users/profile_photo.jpg'
        upload.mark_completed(public_url)
        
        self.assertEqual(upload.status, 'completed')
        self.assertEqual(upload.public_url, public_url)
        self.assertIsNotNone(upload.upload_completed)
    
    def test_mark_upload_failed(self):
        """Test marking upload as failed."""
        upload = FileUpload.objects.create(**self.upload_data)
        
        error_message = 'File size exceeds maximum allowed size'
        upload.mark_failed(error_message)
        
        self.assertEqual(upload.status, 'failed')
        self.assertEqual(upload.error_message, error_message)
    
    def test_upload_with_metadata(self):
        """Test upload with additional metadata."""
        upload = FileUpload.objects.create(
            **self.upload_data,
            metadata={
                'dimensions': {'width': 1920, 'height': 1080},
                'exif': {'camera': 'iPhone 13', 'location': 'Lisbon'},
                'compression': 85,
                'uploaded_from': 'mobile_app'
            }
        )
        
        self.assertEqual(upload.metadata['dimensions']['width'], 1920)
        self.assertEqual(upload.metadata['exif']['camera'], 'iPhone 13')
        self.assertEqual(upload.metadata['compression'], 85)
    
    def test_document_upload(self):
        """Test document file upload."""
        doc_upload = FileUpload.objects.create(
            provider=self.provider,
            user=self.user,
            original_filename='contract.pdf',
            file_type='document',
            file_size=1024000,  # 1MB
            mime_type='application/pdf',
            external_id='doc_xyz789abc123',
            storage_path='/uploads/documents/contract.pdf'
        )
        
        self.assertEqual(doc_upload.file_type, 'document')
        self.assertEqual(doc_upload.mime_type, 'application/pdf')
    
    def test_video_upload(self):
        """Test video file upload."""
        video_upload = FileUpload.objects.create(
            provider=self.provider,
            user=self.user,
            original_filename='tutorial.mp4',
            file_type='video',
            file_size=52428800,  # 50MB
            mime_type='video/mp4',
            external_id='vid_mno456pqr789',
            storage_path='/uploads/videos/tutorial.mp4',
            metadata={
                'duration': 180,  # 3 minutes
                'resolution': '1080p',
                'bitrate': 2500
            }
        )
        
        self.assertEqual(video_upload.file_type, 'video')
        self.assertEqual(video_upload.metadata['duration'], 180)


class SocialAuthProfileModelTest(TestCase):
    """Test SocialAuthProfile model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='social@test.com',
            name='Social User',
            password='testpass'
        )
        
        self.profile_data = {
            'user': self.user,
            'provider': 'google',
            'social_id': '1234567890123456789',
            'email': 'social@gmail.com',
            'username': 'socialuser123',
            'full_name': 'Social Test User',
            'avatar_url': 'https://lh3.googleusercontent.com/a/default-user',
            'access_token': 'ya29.test_access_token',
            'refresh_token': 'refresh_token_example',
            'token_expires_at': timezone.now() + timedelta(hours=1)
        }
    
    def test_create_social_auth_profile(self):
        """Test creating social auth profile."""
        profile = SocialAuthProfile.objects.create(**self.profile_data)
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.provider, 'google')
        self.assertEqual(profile.social_id, '1234567890123456789')
        self.assertEqual(profile.email, 'social@gmail.com')
        self.assertEqual(profile.full_name, 'Social Test User')
        self.assertFalse(profile.is_verified)
    
    def test_profile_string_representation(self):
        """Test profile string representation."""
        profile = SocialAuthProfile.objects.create(**self.profile_data)
        expected = f"{self.user.email} - Google"
        self.assertEqual(str(profile), expected)
    
    def test_token_validity_check(self):
        """Test token validity checking."""
        profile = SocialAuthProfile.objects.create(**self.profile_data)
        
        # Test valid token
        self.assertTrue(profile.is_token_valid())
        
        # Test expired token
        profile.token_expires_at = timezone.now() - timedelta(minutes=30)
        profile.save()
        self.assertFalse(profile.is_token_valid())
        
        # Test no expiration set
        profile.token_expires_at = None
        profile.save()
        self.assertTrue(profile.is_token_valid())
    
    def test_update_last_login(self):
        """Test updating last login timestamp."""
        profile = SocialAuthProfile.objects.create(**self.profile_data)
        
        initial_login = profile.last_login
        profile.update_last_login()
        
        self.assertIsNotNone(profile.last_login)
        self.assertNotEqual(profile.last_login, initial_login)
    
    def test_profile_with_additional_data(self):
        """Test profile with additional profile data."""
        profile = SocialAuthProfile.objects.create(
            **self.profile_data,
            profile_data={
                'locale': 'pt_PT',
                'timezone': 'Europe/Lisbon',
                'verified_email': True,
                'picture_high_res': 'https://lh3.googleusercontent.com/a/high-res',
                'friends_count': 150
            },
            is_verified=True
        )
        
        self.assertEqual(profile.profile_data['locale'], 'pt_PT')
        self.assertTrue(profile.profile_data['verified_email'])
        self.assertEqual(profile.profile_data['friends_count'], 150)
        self.assertTrue(profile.is_verified)
    
    def test_facebook_profile(self):
        """Test Facebook social profile."""
        facebook_profile = SocialAuthProfile.objects.create(
            user=self.user,
            provider='facebook',
            social_id='fb_1234567890',
            email='user@facebook.com',
            full_name='Facebook User',
            avatar_url='https://graph.facebook.com/1234567890/picture',
            profile_data={
                'gender': 'male',
                'age_range': {'min': 21},
                'location': {'name': 'Lisbon, Portugal'}
            }
        )
        
        self.assertEqual(facebook_profile.provider, 'facebook')
        self.assertEqual(facebook_profile.profile_data['gender'], 'male')
    
    def test_instagram_profile(self):
        """Test Instagram social profile."""
        instagram_profile = SocialAuthProfile.objects.create(
            user=self.user,
            provider='instagram',
            social_id='ig_9876543210',
            username='instagramuser',
            full_name='Instagram User',
            profile_data={
                'account_type': 'PERSONAL',
                'media_count': 42,
                'followers_count': 1250
            }
        )
        
        self.assertEqual(instagram_profile.provider, 'instagram')
        self.assertEqual(instagram_profile.profile_data['media_count'], 42)
    
    def test_apple_profile(self):
        """Test Apple ID social profile."""
        apple_profile = SocialAuthProfile.objects.create(
            user=self.user,
            provider='apple',
            social_id='apple_001234.567890abcdef',
            email='appleid@privaterelay.appleid.com',
            full_name='Apple User',
            profile_data={
                'real_user_status': 'likelyReal',
                'is_private_email': True
            }
        )
        
        self.assertEqual(apple_profile.provider, 'apple')
        self.assertTrue(apple_profile.profile_data['is_private_email'])


class LocationDataModelTest(TestCase):
    """Test LocationData model functionality."""
    
    def setUp(self):
        self.provider = IntegrationProvider.objects.create(
            name='google_maps',
            display_name='Google Maps',
            provider_type='maps'
        )
        
        self.location_data = {
            'location_type': 'business',
            'name': 'Tuwi Beauty Studio',
            'street_address': 'Rua Augusta, 123',
            'city': 'Lisboa',
            'state': 'Lisboa',
            'postal_code': '1100-048',
            'country': 'Portugal',
            'latitude': Decimal('38.7112500'),
            'longitude': Decimal('-9.1385100'),
            'provider': self.provider,
            'external_place_id': 'ChIJN1t_tDeuEmsRUsoyG83frY4'
        }
    
    def test_create_location_data(self):
        """Test creating location data."""
        location = LocationData.objects.create(**self.location_data)
        
        self.assertEqual(location.location_type, 'business')
        self.assertEqual(location.name, 'Tuwi Beauty Studio')
        self.assertEqual(location.city, 'Lisboa')
        self.assertEqual(location.country, 'Portugal')
        self.assertEqual(location.latitude, Decimal('38.7112500'))
        self.assertEqual(location.longitude, Decimal('-9.1385100'))
        self.assertEqual(location.used_count, 0)
    
    def test_location_string_representation(self):
        """Test location string representation."""
        location = LocationData.objects.create(
            **self.location_data,
            formatted_address='Rua Augusta, 123, 1100-048 Lisboa, Portugal'
        )
        
        expected = 'Rua Augusta, 123, 1100-048 Lisboa, Portugal'
        self.assertEqual(str(location), expected)
    
    def test_increment_usage(self):
        """Test incrementing location usage."""
        location = LocationData.objects.create(**self.location_data)
        
        initial_count = location.used_count
        location.increment_usage()
        
        self.assertEqual(location.used_count, initial_count + 1)
        self.assertIsNotNone(location.last_used)
    
    def test_address_location(self):
        """Test street address location."""
        address_location = LocationData.objects.create(
            location_type='address',
            street_address='Avenida da Liberdade, 456',
            city='Lisboa',
            state='Lisboa',
            postal_code='1250-096',
            country='Portugal',
            latitude=Decimal('38.7223000'),
            longitude=Decimal('-9.1414400'),
            formatted_address='Avenida da Liberdade, 456, 1250-096 Lisboa, Portugal'
        )
        
        self.assertEqual(address_location.location_type, 'address')
        self.assertEqual(address_location.street_address, 'Avenida da Liberdade, 456')
    
    def test_landmark_location(self):
        """Test landmark location."""
        landmark = LocationData.objects.create(
            location_type='landmark',
            name='Torre de Belém',
            city='Lisboa',
            state='Lisboa',
            country='Portugal',
            latitude=Decimal('38.6915900'),
            longitude=Decimal('-9.2159700'),
            place_data={
                'monument_type': 'Tower',
                'built_year': 1519,
                'unesco_site': True,
                'visitor_info': {
                    'opening_hours': '10:00-17:30',
                    'ticket_price': 6
                }
            }
        )
        
        self.assertEqual(landmark.location_type, 'landmark')
        self.assertEqual(landmark.name, 'Torre de Belém')
        self.assertTrue(landmark.place_data['unesco_site'])
    
    def test_coordinates_only_location(self):
        """Test GPS coordinates only location."""
        coords_location = LocationData.objects.create(
            location_type='coordinates',
            latitude=Decimal('38.7150000'),
            longitude=Decimal('-9.1550000'),
            place_data={
                'accuracy': 'high',
                'source': 'gps',
                'altitude': 42.5
            }
        )
        
        self.assertEqual(coords_location.location_type, 'coordinates')
        self.assertEqual(coords_location.place_data['source'], 'gps')


class IntegrationSystemTest(TestCase):
    """Test integration system scenarios."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='integration_system@test.com',
            name='Integration System User',
            password='testpass'
        )
        
        # Create multiple providers
        self.payment_provider = IntegrationProvider.objects.create(
            name='stripe',
            display_name='Stripe',
            provider_type='payment',
            status='active',
            health_status='healthy'
        )
        
        self.storage_provider = IntegrationProvider.objects.create(
            name='aws_s3',
            display_name='AWS S3',
            provider_type='storage',
            status='active',
            health_status='healthy'
        )
        
        self.sms_provider = IntegrationProvider.objects.create(
            name='twilio',
            display_name='Twilio',
            provider_type='sms',
            status='active',
            health_status='healthy'
        )
    
    def test_payment_webhook_flow(self):
        """Test complete payment webhook flow."""
        # Create payment webhook
        webhook = Webhook.objects.create(
            name='Payment Success',
            provider=self.payment_provider,
            event_type='payment.success',
            url='https://api.tuwi.com/webhooks/payment-success'
        )
        
        # Simulate webhook received
        webhook_data = {
            'event': 'payment.success',
            'data': {
                'object': {
                    'id': 'pi_test123',
                    'amount': 10000,
                    'currency': 'eur',
                    'status': 'succeeded'
                }
            }
        }
        
        # Log webhook reception
        log = IntegrationLog.objects.create(
            provider=self.payment_provider,
            log_type='webhook',
            status='success',
            endpoint='/webhooks/payment-success',
            method='POST',
            request_data=webhook_data,
            status_code=200,
            response_time=0.156
        )
        
        # Update webhook success count
        webhook.increment_success()
        self.payment_provider.increment_success()
        
        # Verify flow
        self.assertEqual(webhook.success_count, 1)
        self.assertEqual(self.payment_provider.success_count, 1)
        self.assertEqual(log.request_data['event'], 'payment.success')
    
    def test_file_upload_workflow(self):
        """Test complete file upload workflow."""
        # Create API quota for storage
        quota = APIQuota.objects.create(
            provider=self.storage_provider,
            quota_type='storage',
            period_type='month',
            limit_value=107374182400,  # 100GB
            warning_threshold=85,
            reset_at=timezone.now() + timedelta(days=30)
        )
        
        # Create file upload
        upload = FileUpload.objects.create(
            provider=self.storage_provider,
            user=self.user,
            original_filename='braiding_portfolio.jpg',
            file_type='image',
            file_size=5242880,  # 5MB
            mime_type='image/jpeg',
            external_id='img_abcd1234efgh5678',
            storage_path='/uploads/portfolio/braiding_portfolio.jpg'
        )
        
        # Log upload request
        upload_log = IntegrationLog.objects.create(
            provider=self.storage_provider,
            log_type='request',
            status='success',
            endpoint='/upload',
            method='POST',
            status_code=200,
            response_time=2.345,
            user=self.user
        )
        
        # Complete upload
        public_url = 'https://cdn.tuwi.com/uploads/portfolio/braiding_portfolio.jpg'
        upload.mark_completed(public_url)
        
        # Update quota usage
        quota.increment_usage(upload.file_size)
        self.storage_provider.increment_success()
        
        # Verify workflow
        self.assertEqual(upload.status, 'completed')
        self.assertEqual(upload.public_url, public_url)
        self.assertEqual(quota.current_usage, 5242880)
        self.assertEqual(self.storage_provider.success_count, 1)
    
    def test_social_auth_integration(self):
        """Test social authentication integration."""
        # Create social profile
        social_profile = SocialAuthProfile.objects.create(
            user=self.user,
            provider='google',
            social_id='google_123456789',
            email='user@gmail.com',
            full_name='Test User',
            avatar_url='https://lh3.googleusercontent.com/a/test',
            access_token='access_token_example',
            refresh_token='refresh_token_example',
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_verified=True
        )
        
        # Update last login
        social_profile.update_last_login()
        
        # Log authentication
        auth_log = IntegrationLog.objects.create(
            provider=self.payment_provider,  # Using existing provider for test
            log_type='request',
            status='success',
            endpoint='/oauth/token',
            method='POST',
            status_code=200,
            response_time=0.234,
            user=self.user
        )
        
        # Verify integration
        self.assertTrue(social_profile.is_verified)
        self.assertTrue(social_profile.is_token_valid())
        self.assertIsNotNone(social_profile.last_login)
    
    def test_multi_provider_health_check(self):
        """Test health check across multiple providers."""
        providers = [self.payment_provider, self.storage_provider, self.sms_provider]
        
        for provider in providers:
            # Simulate health check
            health_log = IntegrationLog.objects.create(
                provider=provider,
                log_type='health_check',
                status='success',
                endpoint='/health',
                method='GET',
                status_code=200,
                response_time=0.089,
                response_data={'status': 'ok', 'version': '1.0'}
            )
            
            # Update provider health
            provider.last_health_check = timezone.now()
            provider.health_status = 'healthy'
            provider.save()
        
        # Verify all providers are healthy
        healthy_providers = IntegrationProvider.objects.filter(health_status='healthy')
        self.assertEqual(healthy_providers.count(), 3)
        
        # Verify health check logs
        health_logs = IntegrationLog.objects.filter(log_type='health_check')
        self.assertEqual(health_logs.count(), 3)


class IntegrationAPITest(APITestCase):
    """Test integration API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='integration_api@test.com',
            name='Integration API User',
            password='testpass'
        )
        
        self.provider = IntegrationProvider.objects.create(
            name='test_api_provider',
            display_name='Test API Provider',
            provider_type='analytics'
        )
        
        # Create test data
        self.location = LocationData.objects.create(
            location_type='business',
            name='Test Business',
            city='Lisboa',
            country='Portugal',
            latitude=Decimal('38.7223000'),
            longitude=Decimal('-9.1414400')
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_provider_health_status(self):
        """Test getting provider health status."""
        url = reverse('integrations:provider-health', kwargs={'provider_id': self.provider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('health_status', response.data)
        self.assertIn('last_health_check', response.data)
    
    def test_upload_file(self):
        """Test file upload endpoint."""
        url = reverse('integrations:upload-file')
        
        # Mock file upload data
        data = {
            'filename': 'test_image.jpg',
            'file_type': 'image',
            'file_size': 1024000
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('upload_id', response.data)
    
    def test_webhook_logs(self):
        """Test getting webhook logs."""
        # Create test logs
        IntegrationLog.objects.create(
            provider=self.provider,
            log_type='webhook',
            status='success',
            endpoint='/webhooks/test'
        )
        
        url = reverse('integrations:webhook-logs')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_location_search(self):
        """Test location search endpoint."""
        url = reverse('integrations:location-search')
        response = self.client.get(url, {'q': 'Lisboa'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_quota_status(self):
        """Test API quota status."""
        # Create quota
        APIQuota.objects.create(
            provider=self.provider,
            quota_type='requests',
            period_type='day',
            limit_value=1000,
            current_usage=250,
            warning_threshold=80,
            reset_at=timezone.now() + timedelta(days=1)
        )
        
        url = reverse('integrations:quota-status', kwargs={'provider_id': self.provider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['usage_percentage'], 25.0)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to integration endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('integrations:provider-health', kwargs={'provider_id': self.provider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)