"""
Tests for notifications functionality including templates, channels, and delivery.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch, MagicMock

from .models import (
    NotificationTemplate, NotificationChannel, UserNotificationPreference,
    NotificationCategory, Notification, NotificationBatch, NotificationAnalytics
)

User = get_user_model()


class NotificationTemplateModelTest(TestCase):
    """Test NotificationTemplate model functionality."""
    
    def test_create_notification_template(self):
        """Test creating a notification template."""
        template = NotificationTemplate.objects.create(
            name='booking_confirmation',
            template_type='email',
            subject_template='Booking Confirmed - {booking_reference}',
            body_template='Hello {customer_name}, your booking {booking_reference} has been confirmed.',
            html_template='<h1>Booking Confirmed</h1><p>Hello {customer_name}</p>',
            variables={
                'customer_name': 'Customer\'s full name',
                'booking_reference': 'Unique booking reference number'
            }
        )
        
        self.assertEqual(template.name, 'booking_confirmation')
        self.assertEqual(template.template_type, 'email')
        self.assertTrue(template.is_active)
        self.assertIn('customer_name', template.variables)
    
    def test_template_string_representation(self):
        """Test template string representation."""
        template = NotificationTemplate.objects.create(
            name='welcome_message',
            template_type='push',
            subject_template='Welcome!',
            body_template='Welcome to Tuwi Beauty!'
        )
        
        expected = "welcome_message (Push Notification)"
        self.assertEqual(str(template), expected)
    
    def test_render_template(self):
        """Test template rendering with variables."""
        template = NotificationTemplate.objects.create(
            name='appointment_reminder',
            template_type='sms',
            subject_template='Appointment Reminder',
            body_template='Hi {customer_name}, you have an appointment on {appointment_date}.'
        )
        
        context = {
            'customer_name': 'John Doe',
            'appointment_date': '2024-12-25'
        }
        
        rendered_subject = template.render_subject(context)
        rendered_body = template.render_body(context)
        
        self.assertEqual(rendered_subject, 'Appointment Reminder')
        self.assertEqual(rendered_body, 'Hi John Doe, you have an appointment on 2024-12-25.')


class NotificationChannelModelTest(TestCase):
    """Test NotificationChannel model functionality."""
    
    def test_create_notification_channel(self):
        """Test creating a notification channel."""
        channel = NotificationChannel.objects.create(
            name='Email Marketing',
            channel_type='email',
            is_enabled=True,
            configuration={
                'smtp_host': 'smtp.example.com',
                'smtp_port': 587,
                'use_tls': True
            }
        )
        
        self.assertEqual(channel.name, 'Email Marketing')
        self.assertEqual(channel.channel_type, 'email')
        self.assertTrue(channel.is_enabled)
        self.assertIn('smtp_host', channel.configuration)
    
    def test_channel_string_representation(self):
        """Test channel string representation."""
        channel = NotificationChannel.objects.create(
            name='Push Notifications',
            channel_type='push'
        )
        
        expected = "Push Notifications (push)"
        self.assertEqual(str(channel), expected)


class UserNotificationPreferenceModelTest(TestCase):
    """Test UserNotificationPreference model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            name='Test User',
            password='testpass'
        )
        
        self.category = NotificationCategory.objects.create(
            name='Bookings',
            display_name='Bookings',
            description='Booking-related notifications'
        )
    
    def test_create_user_preference(self):
        """Test creating user notification preference."""
        preference = UserNotificationPreference.objects.create(
            user=self.user,
            category=self.category,
            email_enabled=True,
            push_enabled=False,
            sms_enabled=True
        )
        
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.category, self.category)
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.push_enabled)
        self.assertTrue(preference.sms_enabled)
    
    def test_preference_string_representation(self):
        """Test preference string representation."""
        preference = UserNotificationPreference.objects.create(
            user=self.user,
            category=self.category,
            email_enabled=True
        )
        
        expected = "Test User (user@test.com) - Bookings preferences"
        self.assertEqual(str(preference), expected)


class NotificationCategoryModelTest(TestCase):
    """Test NotificationCategory model functionality."""
    
    def test_create_notification_category(self):
        """Test creating a notification category."""
        category = NotificationCategory.objects.create(
            name='Promotions',
            display_name='Promotions',
            description='Promotional and marketing notifications',
            is_system=False
        )
        
        self.assertEqual(category.name, 'Promotions')
        self.assertEqual(category.display_name, 'Promotions')
        self.assertFalse(category.is_system)
    
    def test_category_string_representation(self):
        """Test category string representation."""
        category = NotificationCategory.objects.create(
            name='System Alerts',
            display_name='System Alerts'
        )
        
        self.assertEqual(str(category), 'System Alerts')


class NotificationModelTest(TestCase):
    """Test Notification model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='recipient@test.com',
            name='Test Recipient',
            password='testpass'
        )
        
        self.category = NotificationCategory.objects.create(
            name='Test Category',
            display_name='Test Category'
        )
        
        self.template = NotificationTemplate.objects.create(
            name='test_template',
            template_type='in_app',
            subject_template='Test Subject',
            body_template='Test message for {user_name}'
        )
    
    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            recipient=self.user,
            category=self.category,
            template=self.template,
            title='Test Notification',
            message='This is a test notification'
        )
        
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.category, self.category)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.status, 'pending')
    
    def test_notification_string_representation(self):
        """Test notification string representation."""
        notification = Notification.objects.create(
            user=self.user,
            category=self.category,
            subject='Welcome Message',
            message='Welcome to our platform!',
            notification_type='email'
        )
        
        expected = f"Welcome Message - {self.user.email}"
        self.assertEqual(str(notification), expected)
    
    def test_mark_as_read(self):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            category=self.category,
            subject='Test Notification',
            message='Test message',
            notification_type='in_app'
        )
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_delivery_status(self):
        """Test notification delivery status."""
        notification = Notification.objects.create(
            user=self.user,
            category=self.category,
            subject='Delivery Test',
            message='Testing delivery status',
            notification_type='email'
        )
        
        # Initially pending
        self.assertEqual(notification.status, 'pending')
        
        # Mark as sent
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        
        self.assertEqual(notification.status, 'sent')
        self.assertIsNotNone(notification.sent_at)


class NotificationBatchModelTest(TestCase):
    """Test NotificationBatch model functionality."""
    
    def setUp(self):
        self.template = NotificationTemplate.objects.create(
            name='batch_template',
            template_type='email',
            subject_template='Batch Notification',
            body_template='This is a batch notification'
        )
    
    def test_create_notification_batch(self):
        """Test creating a notification batch."""
        batch = NotificationBatch.objects.create(
            name='Weekly Newsletter',
            template=self.template,
            total_recipients=100,
            status='pending'
        )
        
        self.assertEqual(batch.name, 'Weekly Newsletter')
        self.assertEqual(batch.template, self.template)
        self.assertEqual(batch.total_recipients, 100)
        self.assertEqual(batch.status, 'pending')
    
    def test_batch_string_representation(self):
        """Test batch string representation."""
        batch = NotificationBatch.objects.create(
            name='Product Launch Announcement',
            template=self.template,
            total_recipients=500
        )
        
        expected = "Product Launch Announcement (500 recipients)"
        self.assertEqual(str(batch), expected)


class NotificationAnalyticsModelTest(TestCase):
    """Test NotificationAnalytics model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='analytics@test.com',
            name='Analytics User',
            password='testpass'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            subject='Analytics Test',
            message='Test notification for analytics',
            notification_type='email'
        )
    
    def test_create_notification_analytics(self):
        """Test creating notification analytics."""
        analytics = NotificationAnalytics.objects.create(
            notification=self.notification,
            event_type='delivered',
            metadata={
                'delivery_time_ms': 1500,
                'provider': 'test_provider'
            }
        )
        
        self.assertEqual(analytics.notification, self.notification)
        self.assertEqual(analytics.event_type, 'delivered')
        self.assertIn('delivery_time_ms', analytics.metadata)
    
    def test_analytics_string_representation(self):
        """Test analytics string representation."""
        analytics = NotificationAnalytics.objects.create(
            notification=self.notification,
            event_type='opened'
        )
        
        expected = f"Analytics Test - opened"
        self.assertEqual(str(analytics), expected)


class NotificationsAPITest(APITestCase):
    """Test notifications API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        
        self.category = NotificationCategory.objects.create(
            name='API Category',
            slug='api-category'
        )
        
        self.template = NotificationTemplate.objects.create(
            name='api_template',
            template_type='in_app',
            subject_template='API Test',
            body_template='API test message'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            category=self.category,
            template=self.template,
            subject='API Test Notification',
            message='This is an API test notification',
            notification_type='in_app'
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_user_notifications(self):
        """Test listing user notifications."""
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['subject'], 'API Test Notification')
    
    def test_notification_detail(self):
        """Test getting notification details."""
        url = reverse('notifications:notification-detail', kwargs={'pk': self.notification.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], 'API Test Notification')
        self.assertEqual(response.data['message'], 'This is an API test notification')
    
    def test_mark_notification_as_read(self):
        """Test marking notification as read."""
        url = reverse('notifications:notification-read', kwargs={'notification_id': self.notification.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
    
    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read."""
        # Create additional unread notification
        Notification.objects.create(
            user=self.user,
            category=self.category,
            subject='Second Notification',
            message='Another test notification',
            notification_type='in_app'
        )
        
        url = reverse('notifications:mark-all-read')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all notifications are marked as read
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_notification_preferences(self):
        """Test getting user notification preferences."""
        url = reverse('notifications:preferences')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('preferences', response.data)
    
    def test_update_notification_preferences(self):
        """Test updating notification preferences."""
        url = reverse('notifications:preferences')
        data = {
            'preferences': [
                {
                    'category_id': self.category.id,
                    'email_enabled': True,
                    'push_enabled': False,
                    'sms_enabled': True
                }
            ]
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check preference was created/updated
        preference = UserNotificationPreference.objects.get(
            user=self.user,
            category=self.category
        )
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.push_enabled)
    
    def test_notification_statistics(self):
        """Test getting notification statistics."""
        url = reverse('notifications:stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_notifications', response.data)
        self.assertIn('unread_count', response.data)
        self.assertIn('read_count', response.data)
    
    def test_create_notification(self):
        """Test creating a notification via API."""
        url = reverse('notifications:notification-create')
        data = {
            'recipient_id': self.user.id,
            'category_id': self.category.id,
            'template_name': 'api_template',
            'context': {
                'user_name': 'API User'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check notification was created
        new_notification = Notification.objects.get(id=response.data['id'])
        self.assertEqual(new_notification.user, self.user)
        self.assertEqual(new_notification.template, self.template)
    
    def test_notification_categories(self):
        """Test listing notification categories."""
        url = reverse('notifications:category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Category')
    
    def test_filter_notifications_by_category(self):
        """Test filtering notifications by category."""
        url = reverse('notifications:notification-list')
        response = self.client.get(url, {'category': self.category.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_notifications_by_read_status(self):
        """Test filtering notifications by read status."""
        url = reverse('notifications:notification-list')
        response = self.client.get(url, {'is_read': 'false'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_unauthorized_notification_access(self):
        """Test unauthorized access to notifications."""
        other_user = User.objects.create_user(
            email='other@test.com',
            name='Other User',
            password='testpass'
        )
        self.client.force_authenticate(user=other_user)
        
        url = reverse('notifications:notification-detail', kwargs={'pk': self.notification.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('apps.notifications.services.send_notification')
    def test_send_notification_service(self, mock_send):
        """Test notification sending service."""
        mock_send.return_value = True
        
        url = reverse('notifications:send-notification')
        data = {
            'user_id': self.user.id,
            'template_name': 'api_template',
            'notification_type': 'email',
            'context': {'user_name': 'Test User'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()
    
    def test_notification_templates_list(self):
        """Test listing notification templates."""
        url = reverse('notifications:template-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'api_template')