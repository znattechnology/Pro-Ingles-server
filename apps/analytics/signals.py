"""
Django signals for automatic analytics data collection.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from decimal import Decimal
import logging

from .services import MetricsCalculator

logger = logging.getLogger(__name__)


# User Activity Tracking
@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track user login activity."""
    try:
        from .models import UserActivity
        
        # Get session info
        session_id = request.session.session_key if request.session else None
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            description=f'User {user.email} logged in',
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Update login metrics
        MetricsCalculator.store_metric_datapoint(
            metric_name='daily_logins',
            value=1.0
        )
        
    except Exception as e:
        logger.error(f"Error tracking login for user {user.email}: {str(e)}")


@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout activity."""
    try:
        from .models import UserActivity
        
        if user:
            # Get session info
            session_id = request.session.session_key if request.session else None
            ip_address = request.META.get('REMOTE_ADDR') if request else None
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            UserActivity.objects.create(
                user=user,
                activity_type='logout',
                description=f'User {user.email} logged out',
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
    except Exception as e:
        logger.error(f"Error tracking logout: {str(e)}")


# User Registration Tracking
@receiver(post_save, sender='users.User')
def track_user_registration(sender, instance, created, **kwargs):
    """Track new user registrations."""
    if created:
        try:
            # Track registration activity
            from .models import UserActivity
            
            UserActivity.objects.create(
                user=instance,
                activity_type='registration',
                description=f'New user registered: {instance.email}',
                metadata={
                    'user_type': getattr(instance, 'user_type', 'client'),
                    'registration_date': instance.date_joined.isoformat()
                }
            )
            
            # Update registration metrics
            MetricsCalculator.store_metric_datapoint(
                metric_name='new_user_registrations',
                value=1.0
            )
            
        except Exception as e:
            logger.error(f"Error tracking user registration: {str(e)}")


# Booking Tracking
@receiver(post_save, sender='bookings.Booking')
def track_booking_activity(sender, instance, created, **kwargs):
    """Track booking creation and status changes."""
    try:
        from .models import UserActivity
        
        if created:
            # Track booking creation
            UserActivity.objects.create(
                user=instance.client,
                activity_type='booking_created',
                description=f'Booking created for {instance.service_name}',
                metadata={
                    'booking_id': str(instance.id),
                    'service_name': instance.service_name,
                    'total_amount': float(instance.total_amount),
                    'braider_id': str(instance.braider.id) if instance.braider else None
                }
            )
            
            # Update booking metrics
            MetricsCalculator.store_metric_datapoint(
                metric_name='total_bookings',
                value=1.0
            )
            
            MetricsCalculator.store_metric_datapoint(
                metric_name='booking_revenue',
                value=float(instance.total_amount)
            )
        
        # Track status changes
        if hasattr(instance, '_state') and not instance._state.adding:
            # Get previous status from database
            try:
                old_instance = sender.objects.get(pk=instance.pk)
                if old_instance.status != instance.status:
                    
                    # Track status change activity
                    UserActivity.objects.create(
                        user=instance.client,
                        activity_type=f'booking_{instance.status}',
                        description=f'Booking status changed to {instance.status}',
                        metadata={
                            'booking_id': str(instance.id),
                            'old_status': old_instance.status,
                            'new_status': instance.status
                        }
                    )
                    
                    # Update status-specific metrics
                    if instance.status == 'confirmed':
                        MetricsCalculator.store_metric_datapoint(
                            metric_name='confirmed_bookings',
                            value=1.0
                        )
                    elif instance.status == 'completed':
                        MetricsCalculator.store_metric_datapoint(
                            metric_name='completed_bookings',
                            value=1.0
                        )
                    elif instance.status == 'cancelled':
                        MetricsCalculator.store_metric_datapoint(
                            metric_name='cancelled_bookings',
                            value=1.0
                        )
                        
                        # Track cancellation activity separately
                        UserActivity.objects.create(
                            user=instance.client,
                            activity_type='booking_cancelled',
                            description=f'Booking cancelled: {instance.service_name}',
                            metadata={
                                'booking_id': str(instance.id),
                                'reason': getattr(instance, 'cancellation_reason', ''),
                                'refund_amount': float(getattr(instance, 'refund_amount', 0))
                            }
                        )
            except sender.DoesNotExist:
                pass
    
    except Exception as e:
        logger.error(f"Error tracking booking activity: {str(e)}")


# Payment Tracking
@receiver(post_save, sender='payments.Payment')
def track_payment_activity(sender, instance, created, **kwargs):
    """Track payment processing."""
    try:
        from .models import UserActivity
        
        if created:
            UserActivity.objects.create(
                user=instance.user,
                activity_type='payment_made',
                description=f'Payment processed: €{instance.amount}',
                metadata={
                    'payment_id': str(instance.id),
                    'amount': float(instance.amount),
                    'payment_method': instance.payment_method.method_type if instance.payment_method else 'unknown',
                    'status': instance.status
                }
            )
        
        # Track successful payments
        if instance.status == 'succeeded':
            MetricsCalculator.store_metric_datapoint(
                metric_name='payment_volume',
                value=1.0
            )
            
            MetricsCalculator.store_metric_datapoint(
                metric_name='payment_revenue',
                value=float(instance.amount)
            )
            
            MetricsCalculator.store_metric_datapoint(
                metric_name='platform_fees',
                value=float(instance.platform_fee or 0)
            )
    
    except Exception as e:
        logger.error(f"Error tracking payment activity: {str(e)}")


# Rating Tracking
@receiver(post_save, sender='ratings.BraiderReview')
def track_rating_activity(sender, instance, created, **kwargs):
    """Track new ratings and reviews."""
    if created:
        try:
            from .models import UserActivity
            
            UserActivity.objects.create(
                user=instance.user,
                activity_type='rating_given',
                description=f'Review given: {instance.overall_rating} stars',
                metadata={
                    'review_id': str(instance.id),
                    'rating_value': instance.overall_rating,
                    'braider_id': str(instance.braider.id),
                    'has_comment': bool(instance.comment)
                }
            )
            
            # Update rating metrics
            MetricsCalculator.store_metric_datapoint(
                metric_name='total_ratings',
                value=1.0
            )
            
            MetricsCalculator.store_metric_datapoint(
                metric_name='average_rating',
                value=float(instance.overall_rating)
            )
        
        except Exception as e:
            logger.error(f"Error tracking rating activity: {str(e)}")


# Chat Message Tracking
@receiver(post_save, sender='chat.Message')
def track_message_activity(sender, instance, created, **kwargs):
    """Track chat messages for engagement metrics."""
    if created:
        try:
            from .models import UserActivity
            
            UserActivity.objects.create(
                user=instance.sender,
                activity_type='message_sent',
                description=f'Message sent in conversation {instance.conversation.id}',
                metadata={
                    'message_id': str(instance.id),
                    'conversation_id': str(instance.conversation.id),
                    'message_type': instance.message_type,
                    'has_attachment': bool(instance.attachment)
                }
            )
            
            # Update messaging metrics
            MetricsCalculator.store_metric_datapoint(
                metric_name='total_messages',
                value=1.0
            )
        
        except Exception as e:
            logger.error(f"Error tracking message activity: {str(e)}")


# System Performance Tracking
def track_api_response_time(endpoint, method, response_time, status_code):
    """Track API response times for performance monitoring."""
    try:
        from .models import SystemPerformance
        
        SystemPerformance.objects.create(
            performance_type='response_time',
            value=Decimal(str(response_time)),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            metadata={
                'response_time_ms': response_time * 1000
            }
        )
        
        # Store as metric
        MetricsCalculator.store_metric_datapoint(
            metric_name='api_response_time',
            value=response_time,
            dimensions={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking API response time: {str(e)}")


def track_error_occurrence(error_type, endpoint, error_details):
    """Track application errors."""
    try:
        from .models import SystemPerformance
        
        SystemPerformance.objects.create(
            performance_type='error_rate',
            value=Decimal('1.0'),
            endpoint=endpoint,
            metadata={
                'error_type': error_type,
                'error_details': str(error_details)
            }
        )
        
        # Store as metric
        MetricsCalculator.store_metric_datapoint(
            metric_name='error_count',
            value=1.0,
            dimensions={
                'error_type': error_type,
                'endpoint': endpoint
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking error occurrence: {str(e)}")


# Auto-create basic metrics on app startup
def create_default_metrics():
    """Create default business metrics if they don't exist."""
    try:
        from .models import MetricCategory, BusinessMetric
        
        # Create default categories
        categories = [
            ('users', 'User Metrics', 'User registration, activity, and engagement'),
            ('bookings', 'Booking Metrics', 'Booking creation, completion, and performance'),
            ('financial', 'Financial Metrics', 'Revenue, payments, and financial performance'),
            ('system', 'System Metrics', 'Performance, errors, and technical metrics'),
        ]
        
        for cat_name, display_name, description in categories:
            category, created = MetricCategory.objects.get_or_create(
                name=cat_name,
                defaults={
                    'display_name': display_name,
                    'description': description
                }
            )
        
        # Create default metrics
        metrics = [
            ('new_user_registrations', 'users', 'New User Registrations', 'counter'),
            ('daily_logins', 'users', 'Daily Logins', 'counter'),
            ('total_bookings', 'bookings', 'Total Bookings', 'counter'),
            ('confirmed_bookings', 'bookings', 'Confirmed Bookings', 'counter'),
            ('completed_bookings', 'bookings', 'Completed Bookings', 'counter'),
            ('cancelled_bookings', 'bookings', 'Cancelled Bookings', 'counter'),
            ('booking_revenue', 'financial', 'Booking Revenue', 'currency'),
            ('payment_volume', 'financial', 'Payment Volume', 'counter'),
            ('payment_revenue', 'financial', 'Payment Revenue', 'currency'),
            ('platform_fees', 'financial', 'Platform Fees', 'currency'),
            ('total_ratings', 'bookings', 'Total Ratings', 'counter'),
            ('average_rating', 'bookings', 'Average Rating', 'gauge'),
            ('total_messages', 'users', 'Total Messages', 'counter'),
            ('api_response_time', 'system', 'API Response Time', 'gauge'),
            ('error_count', 'system', 'Error Count', 'counter'),
        ]
        
        for metric_name, cat_name, display_name, metric_type in metrics:
            try:
                category = MetricCategory.objects.get(name=cat_name)
                metric, created = BusinessMetric.objects.get_or_create(
                    name=metric_name,
                    defaults={
                        'category': category,
                        'display_name': display_name,
                        'metric_type': metric_type,
                        'is_featured': metric_name in ['total_bookings', 'booking_revenue', 'new_user_registrations'],
                    }
                )
                if created:
                    logger.info(f"Created metric: {metric_name}")
            except Exception as e:
                logger.error(f"Error creating metric {metric_name}: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error creating default metrics: {str(e)}")