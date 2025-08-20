"""
Celery tasks for notification processing.
"""

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
import logging
import requests
import json

from .models import (
    Notification, NotificationBatch, NotificationChannel,
    NotificationTemplate, UserNotificationPreference,
    NotificationAnalytics
)

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification(self, notification_id):
    """Send individual notification through appropriate channel."""
    try:
        notification = Notification.objects.select_related(
            'recipient', 'template', 'channel', 'category'
        ).get(id=notification_id)
        
        # Check if notification should be sent
        if notification.status != 'pending':
            logger.info(f"Notification {notification_id} already processed: {notification.status}")
            return
        
        # Check user preferences
        preferences, created = UserNotificationPreference.objects.get_or_create(
            user=notification.recipient
        )
        
        if not preferences.should_receive_notification(
            notification.channel.channel_type,
            notification.category.name if notification.category else None
        ):
            notification.status = 'cancelled'
            notification.error_message = "User preferences disabled this notification type"
            notification.save()
            logger.info(f"Notification {notification_id} cancelled due to user preferences")
            return
        
        # Check channel rate limits
        can_send, reason = notification.channel.can_send_notification()
        if not can_send:
            # Retry later if rate limited
            raise self.retry(countdown=300, reason=reason)  # Retry in 5 minutes
        
        # Send based on channel type
        if notification.channel.channel_type == 'email':
            result = _send_email_notification(notification)
        elif notification.channel.channel_type == 'push':
            result = _send_push_notification(notification)
        elif notification.channel.channel_type == 'sms':
            result = _send_sms_notification(notification)
        elif notification.channel.channel_type == 'webhook':
            result = _send_webhook_notification(notification)
        else:
            raise ValueError(f"Unsupported channel type: {notification.channel.channel_type}")
        
        if result['success']:
            notification.mark_as_sent(
                external_id=result.get('external_id'),
                provider_response=result.get('response')
            )
            logger.info(f"Notification {notification_id} sent successfully")
        else:
            notification.mark_as_failed(result.get('error'))
            if notification.can_retry():
                raise self.retry(countdown=60 * (notification.retry_count + 1))
            logger.error(f"Notification {notification_id} failed: {result.get('error')}")
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as exc:
        logger.error(f"Error sending notification {notification_id}: {str(exc)}")
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.mark_as_failed(str(exc))
            if notification.can_retry():
                raise self.retry(countdown=60 * (notification.retry_count + 1), exc=exc)
        except Notification.DoesNotExist:
            pass
        raise


def _send_email_notification(notification):
    """Send email notification."""
    try:
        # Render email content
        context = {
            'user': notification.recipient,
            'notification': notification,
            **notification.data
        }
        
        subject = notification.template.render_subject(context) if notification.template else notification.title
        text_content = notification.template.render_body(context) if notification.template else notification.message
        html_content = notification.template.render_html(context) if notification.template and notification.template.html_template else notification.html_content
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification.recipient.email]
        )
        
        if html_content:
            email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        return {
            'success': True,
            'external_id': f"email_{notification.id}",
            'response': {'status': 'sent', 'to': notification.recipient.email}
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _send_push_notification(notification):
    """Send push notification via Firebase FCM."""
    try:
        channel_config = notification.channel.config
        fcm_token = channel_config.get('fcm_server_key')
        
        if not fcm_token:
            return {'success': False, 'error': 'FCM server key not configured'}
        
        # Get user's device token (assuming it's stored somewhere)
        device_token = notification.data.get('device_token')
        if not device_token:
            # Try to get from user profile or device registration
            return {'success': False, 'error': 'Device token not found'}
        
        # Prepare FCM payload
        payload = {
            'to': device_token,
            'notification': {
                'title': notification.title,
                'body': notification.message,
                'icon': notification.category.icon if notification.category else 'default',
                'color': notification.category.color if notification.category else '#007bff',
            },
            'data': {
                'notification_id': str(notification.id),
                'category': notification.category.name if notification.category else 'general',
                **notification.data
            }
        }
        
        # Send to FCM
        headers = {
            'Authorization': f'key={fcm_token}',
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            'https://fcm.googleapis.com/fcm/send',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'external_id': result.get('results', [{}])[0].get('message_id'),
                'response': result
            }
        else:
            return {
                'success': False,
                'error': f'FCM returned status {response.status_code}: {response.text}'
            }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _send_sms_notification(notification):
    """Send SMS notification (placeholder for SMS provider integration)."""
    try:
        # This would integrate with SMS providers like Twilio, AWS SNS, etc.
        channel_config = notification.channel.config
        
        # Placeholder implementation
        logger.info(f"SMS notification sent to {notification.recipient.email}: {notification.message}")
        
        return {
            'success': True,
            'external_id': f"sms_{notification.id}",
            'response': {'status': 'sent'}
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _send_webhook_notification(notification):
    """Send webhook notification."""
    try:
        channel_config = notification.channel.config
        webhook_url = channel_config.get('webhook_url')
        
        if not webhook_url:
            return {'success': False, 'error': 'Webhook URL not configured'}
        
        # Prepare webhook payload
        payload = {
            'notification_id': str(notification.id),
            'recipient': notification.recipient.email,
            'title': notification.title,
            'message': notification.message,
            'category': notification.category.name if notification.category else None,
            'priority': notification.priority,
            'data': notification.data,
            'timestamp': notification.created_at.isoformat()
        }
        
        # Send webhook
        headers = channel_config.get('headers', {})
        headers['Content-Type'] = 'application/json'
        
        response = requests.post(
            webhook_url,
            headers=headers,
            json=payload,
            timeout=channel_config.get('timeout', 10)
        )
        
        if response.status_code in [200, 201, 202]:
            return {
                'success': True,
                'external_id': response.headers.get('X-Message-ID', str(notification.id)),
                'response': {
                    'status_code': response.status_code,
                    'response_body': response.text[:1000]  # Limit response size
                }
            }
        else:
            return {
                'success': False,
                'error': f'Webhook returned status {response.status_code}: {response.text[:500]}'
            }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


@shared_task
def process_notification_batch(batch_id):
    """Process notification batch and create individual notifications."""
    try:
        batch = NotificationBatch.objects.select_related(
            'template', 'channel', 'category'
        ).get(id=batch_id)
        
        if batch.is_processed:
            logger.info(f"Batch {batch_id} already processed")
            return
        
        # Create individual notifications
        notifications_created = []
        failed_count = 0
        
        with transaction.atomic():
            for recipient_data in batch.recipient_data:
                try:
                    # Get recipient user
                    email = recipient_data.get('email')
                    if not email:
                        failed_count += 1
                        continue
                    
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        failed_count += 1
                        continue
                    
                    # Merge context data
                    context = {**batch.context_data, **recipient_data}
                    
                    # Render content
                    title = batch.template.render_subject(context)
                    message = batch.template.render_body(context)
                    html_content = batch.template.render_html(context)
                    
                    # Create notification
                    notification = Notification.objects.create(
                        recipient=user,
                        title=title,
                        message=message,
                        html_content=html_content or '',
                        data=context,
                        category=batch.category,
                        template=batch.template,
                        channel=batch.channel,
                        priority=2,  # Normal priority for batch
                        scheduled_at=batch.scheduled_at
                    )
                    
                    notifications_created.append(notification.id)
                    
                except Exception as e:
                    logger.error(f"Error creating notification for {recipient_data}: {str(e)}")
                    failed_count += 1
            
            # Update batch status
            batch.is_processed = True
            batch.processed_at = timezone.now()
            batch.sent_count = len(notifications_created)
            batch.failed_count = failed_count
            batch.save()
        
        # Send notifications asynchronously
        for notification_id in notifications_created:
            send_notification.delay(notification_id)
        
        logger.info(f"Batch {batch_id} processed: {len(notifications_created)} notifications created, {failed_count} failed")
        
    except NotificationBatch.DoesNotExist:
        logger.error(f"Batch {batch_id} not found")
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")


@shared_task
def process_scheduled_notifications():
    """Process notifications scheduled for sending."""
    now = timezone.now()
    
    # Get pending notifications that are scheduled for now or past
    scheduled_notifications = Notification.objects.filter(
        status='pending',
        scheduled_at__lte=now
    ).values_list('id', flat=True)
    
    count = 0
    for notification_id in scheduled_notifications:
        send_notification.delay(notification_id)
        count += 1
    
    logger.info(f"Queued {count} scheduled notifications for sending")
    return count


@shared_task
def cleanup_old_notifications():
    """Clean up old notifications based on retention policy."""
    from datetime import timedelta
    
    # Delete notifications older than 90 days
    ninety_days_ago = timezone.now() - timedelta(days=90)
    
    # Delete read notifications older than 90 days
    deleted_read = Notification.objects.filter(
        read_at__isnull=False,
        created_at__lt=ninety_days_ago
    ).delete()
    
    # Delete failed notifications older than 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    deleted_failed = Notification.objects.filter(
        status='failed',
        created_at__lt=thirty_days_ago
    ).delete()
    
    logger.info(f"Cleaned up notifications: {deleted_read[0]} read, {deleted_failed[0]} failed")
    return {
        'deleted_read': deleted_read[0],
        'deleted_failed': deleted_failed[0]
    }


@shared_task
def update_notification_analytics():
    """Update notification analytics and metrics."""
    # This would run periodically to update engagement metrics
    # Calculate open rates, click rates, etc.
    
    # Example: Update analytics for notifications sent in last 24 hours
    yesterday = timezone.now() - timezone.timedelta(days=1)
    recent_notifications = Notification.objects.filter(
        sent_at__gte=yesterday,
        status__in=['sent', 'delivered']
    )
    
    updated_count = 0
    for notification in recent_notifications:
        analytics, created = NotificationAnalytics.objects.get_or_create(
            notification=notification
        )
        
        # Update metrics
        if notification.read_at:
            analytics.opens = 1
            if not analytics.time_to_read:
                analytics.time_to_read = notification.read_at - notification.sent_at
        
        if notification.clicked_at:
            analytics.clicks = 1
            if not analytics.time_to_click:
                analytics.time_to_click = notification.clicked_at - notification.sent_at
        
        analytics.save()
        updated_count += 1
    
    logger.info(f"Updated analytics for {updated_count} notifications")
    return updated_count


@shared_task
def send_digest_notifications():
    """Send digest notifications based on user preferences."""
    # Get users who have digest enabled
    users_with_digest = UserNotificationPreference.objects.filter(
        digest_frequency__in=['daily', 'weekly', 'hourly']
    ).select_related('user')
    
    now = timezone.now()
    sent_count = 0
    
    for preference in users_with_digest:
        try:
            # Determine if it's time to send digest
            should_send = False
            
            if preference.digest_frequency == 'hourly':
                should_send = now.minute == 0
            elif preference.digest_frequency == 'daily':
                should_send = now.hour == 9 and now.minute == 0  # 9 AM
            elif preference.digest_frequency == 'weekly':
                should_send = now.weekday() == 0 and now.hour == 9 and now.minute == 0  # Monday 9 AM
            
            if not should_send:
                continue
            
            # Get unread notifications for user
            unread_notifications = Notification.objects.filter(
                recipient=preference.user,
                read_at__isnull=True,
                status='sent'
            ).order_by('-created_at')[:20]  # Limit to 20 most recent
            
            if not unread_notifications.exists():
                continue
            
            # Create digest notification
            digest_content = f"You have {unread_notifications.count()} unread notifications:\n\n"
            for notif in unread_notifications:
                digest_content += f"• {notif.title}\n"
            
            digest_notification = Notification.objects.create(
                recipient=preference.user,
                title=f"Notification Digest - {unread_notifications.count()} unread",
                message=digest_content,
                category_id='digest',  # Assuming digest category exists
                priority=1,  # Low priority
                data={'digest': True, 'notification_count': unread_notifications.count()}
            )
            
            send_notification.delay(digest_notification.id)
            sent_count += 1
            
        except Exception as e:
            logger.error(f"Error sending digest for user {preference.user.id}: {str(e)}")
    
    logger.info(f"Sent {sent_count} digest notifications")
    return sent_count