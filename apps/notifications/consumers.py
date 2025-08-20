"""
WebSocket consumers for real-time notifications.
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import Notification, UserNotificationPreference


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Create user-specific notification room
        self.room_group_name = f"notifications_{self.user.id}"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial notification count
        await self.send_notification_count()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'mark_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_read(notification_id)
            elif action == 'mark_all_read':
                await self.mark_all_notifications_read()
            elif action == 'get_notifications':
                await self.send_recent_notifications()
            elif action == 'update_preferences':
                preferences = text_data_json.get('preferences', {})
                await self.update_user_preferences(preferences)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def notification_message(self, event):
        """Send notification to WebSocket."""
        notification_data = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))
    
    async def notification_count_update(self, event):
        """Send notification count update."""
        count_data = event['count_data']
        
        await self.send(text_data=json.dumps({
            'type': 'count_update',
            'count_data': count_data
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark specific notification as read."""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all user notifications as read."""
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=self.user,
            read_at__isnull=True
        ).update(read_at=now)
        return updated
    
    @database_sync_to_async
    def get_notification_counts(self):
        """Get notification counts for user."""
        total = Notification.objects.filter(recipient=self.user).count()
        unread = Notification.objects.filter(
            recipient=self.user,
            read_at__isnull=True
        ).count()
        
        # Count by priority
        urgent = Notification.objects.filter(
            recipient=self.user,
            priority=4,
            read_at__isnull=True
        ).count()
        
        return {
            'total': total,
            'unread': unread,
            'urgent': urgent
        }
    
    @database_sync_to_async
    def get_recent_notifications(self):
        """Get recent notifications for user."""
        notifications = Notification.objects.filter(
            recipient=self.user
        ).select_related('category').order_by('-created_at')[:20]
        
        return [
            {
                'id': str(n.id),
                'title': n.title,
                'message': n.message,
                'category': {
                    'name': n.category.display_name if n.category else 'General',
                    'icon': n.category.icon if n.category else '🔔',
                    'color': n.category.color if n.category else '#007bff'
                },
                'priority': n.priority,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'data': n.data
            }
            for n in notifications
        ]
    
    @database_sync_to_async
    def update_user_preferences(self, preferences):
        """Update user notification preferences."""
        try:
            user_prefs, created = UserNotificationPreference.objects.get_or_create(
                user=self.user
            )
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(user_prefs, key):
                    setattr(user_prefs, key, value)
            
            user_prefs.save()
            return True
        except Exception:
            return False
    
    async def send_notification_count(self):
        """Send current notification count to client."""
        count_data = await self.get_notification_counts()
        
        await self.send(text_data=json.dumps({
            'type': 'count_update',
            'count_data': count_data
        }))
    
    async def send_recent_notifications(self):
        """Send recent notifications to client."""
        notifications = await self.get_recent_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'notifications_list',
            'notifications': notifications
        }))


class NotificationAdminConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin notification dashboard."""
    
    async def connect(self):
        """Handle WebSocket connection for admin."""
        self.user = self.scope["user"]
        
        if isinstance(self.user, AnonymousUser) or not self.user.is_staff:
            await self.close()
            return
        
        # Join admin notifications group
        self.room_group_name = "notifications_admin"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dashboard data
        await self.send_dashboard_data()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle admin dashboard requests."""
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'get_stats':
                await self.send_notification_stats()
            elif action == 'get_recent':
                await self.send_recent_notifications()
            elif action == 'get_failed':
                await self.send_failed_notifications()
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def admin_notification_update(self, event):
        """Handle admin notification updates."""
        update_data = event['data']
        
        await self.send(text_data=json.dumps({
            'type': 'admin_update',
            'data': update_data
        }))
    
    @database_sync_to_async
    def get_notification_stats(self):
        """Get overall notification statistics."""
        from django.db.models import Count, Q
        
        # Overall counts
        total_notifications = Notification.objects.count()
        pending_notifications = Notification.objects.filter(status='pending').count()
        sent_notifications = Notification.objects.filter(status='sent').count()
        failed_notifications = Notification.objects.filter(status='failed').count()
        
        # Today's stats
        today = timezone.now().date()
        today_notifications = Notification.objects.filter(
            created_at__date=today
        ).count()
        today_sent = Notification.objects.filter(
            sent_at__date=today,
            status='sent'
        ).count()
        today_failed = Notification.objects.filter(
            created_at__date=today,
            status='failed'
        ).count()
        
        # Channel breakdown
        channel_stats = {}
        from .models import NotificationChannel
        for channel in NotificationChannel.objects.filter(is_active=True):
            channel_count = Notification.objects.filter(channel=channel).count()
            channel_success = Notification.objects.filter(
                channel=channel,
                status__in=['sent', 'delivered']
            ).count()
            
            channel_stats[channel.name] = {
                'total': channel_count,
                'success': channel_success,
                'success_rate': (channel_success / channel_count * 100) if channel_count > 0 else 0
            }
        
        return {
            'total_notifications': total_notifications,
            'pending_notifications': pending_notifications,
            'sent_notifications': sent_notifications,
            'failed_notifications': failed_notifications,
            'today_notifications': today_notifications,
            'today_sent': today_sent,
            'today_failed': today_failed,
            'channel_stats': channel_stats
        }
    
    @database_sync_to_async
    def get_recent_admin_notifications(self):
        """Get recent notifications for admin view."""
        notifications = Notification.objects.select_related(
            'recipient', 'category', 'channel'
        ).order_by('-created_at')[:50]
        
        return [
            {
                'id': str(n.id),
                'title': n.title,
                'recipient': n.recipient.email,
                'status': n.status,
                'channel': n.channel.name if n.channel else 'Unknown',
                'category': n.category.display_name if n.category else 'General',
                'priority': n.priority,
                'created_at': n.created_at.isoformat(),
                'sent_at': n.sent_at.isoformat() if n.sent_at else None
            }
            for n in notifications
        ]
    
    @database_sync_to_async
    def get_failed_notifications(self):
        """Get failed notifications for admin review."""
        failed_notifications = Notification.objects.filter(
            status='failed'
        ).select_related('recipient', 'channel').order_by('-created_at')[:100]
        
        return [
            {
                'id': str(n.id),
                'title': n.title,
                'recipient': n.recipient.email,
                'channel': n.channel.name if n.channel else 'Unknown',
                'error_message': n.error_message,
                'retry_count': n.retry_count,
                'can_retry': n.can_retry(),
                'created_at': n.created_at.isoformat()
            }
            for n in failed_notifications
        ]
    
    async def send_dashboard_data(self):
        """Send dashboard data to admin."""
        stats = await self.get_notification_stats()
        
        await self.send(text_data=json.dumps({
            'type': 'dashboard_data',
            'stats': stats
        }))
    
    async def send_notification_stats(self):
        """Send notification statistics."""
        stats = await self.get_notification_stats()
        
        await self.send(text_data=json.dumps({
            'type': 'stats',
            'data': stats
        }))
    
    async def send_recent_notifications(self):
        """Send recent notifications."""
        notifications = await self.get_recent_admin_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'recent_notifications',
            'notifications': notifications
        }))
    
    async def send_failed_notifications(self):
        """Send failed notifications."""
        failed = await self.get_failed_notifications()
        
        await self.send(text_data=json.dumps({
            'type': 'failed_notifications',
            'notifications': failed
        }))