"""
Analytics service layer for metrics calculation and dashboard data.
"""

from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

from .models import (
    BusinessMetric, MetricDataPoint, Dashboard, DashboardWidget,
    UserActivity, SystemPerformance, Alert, CohortAnalysis
)

User = get_user_model()
logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Service for calculating business metrics."""
    
    @staticmethod
    def calculate_kpi_metrics(start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """Calculate key performance indicators."""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            from apps.bookings.models import Booking
            from apps.payments.models import Payment
            from apps.users.models import User
            from apps.braiders.models import Braider
            
            # User metrics
            total_users = User.objects.count()
            new_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
            active_users = User.objects.filter(
                last_login__date__range=[start_date, end_date]
            ).count()
            
            # Booking metrics
            total_bookings = Booking.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).count()
            
            confirmed_bookings = Booking.objects.filter(
                status='confirmed',
                created_at__date__range=[start_date, end_date]
            ).count()
            
            completed_bookings = Booking.objects.filter(
                status='completed',
                created_at__date__range=[start_date, end_date]
            ).count()
            
            cancelled_bookings = Booking.objects.filter(
                status='cancelled',
                created_at__date__range=[start_date, end_date]
            ).count()
            
            # Financial metrics
            revenue_data = Payment.objects.filter(
                status='succeeded',
                processed_at__date__range=[start_date, end_date]
            ).aggregate(
                total_revenue=Sum('amount'),
                platform_fees=Sum('platform_fee'),
                payment_volume=Count('id')
            )
            
            total_revenue = revenue_data['total_revenue'] or Decimal('0.00')
            platform_fees = revenue_data['platform_fees'] or Decimal('0.00')
            payment_volume = revenue_data['payment_volume'] or 0
            
            # Braider metrics
            total_braiders = Braider.objects.filter(is_active=True).count()
            active_braiders = Braider.objects.filter(
                user__payments_received__processed_at__date__range=[start_date, end_date]
            ).distinct().count()
            
            # Conversion rates
            booking_conversion_rate = (
                (confirmed_bookings / total_bookings * 100) 
                if total_bookings > 0 else 0
            )
            
            completion_rate = (
                (completed_bookings / confirmed_bookings * 100) 
                if confirmed_bookings > 0 else 0
            )
            
            cancellation_rate = (
                (cancelled_bookings / total_bookings * 100) 
                if total_bookings > 0 else 0
            )
            
            # Average values
            avg_booking_value = (
                total_revenue / completed_bookings 
                if completed_bookings > 0 else Decimal('0.00')
            )
            
            avg_revenue_per_user = (
                total_revenue / active_users 
                if active_users > 0 else Decimal('0.00')
            )
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': (end_date - start_date).days + 1
                },
                'users': {
                    'total_users': total_users,
                    'new_users': new_users,
                    'active_users': active_users,
                    'user_growth_rate': (new_users / total_users * 100) if total_users > 0 else 0
                },
                'bookings': {
                    'total_bookings': total_bookings,
                    'confirmed_bookings': confirmed_bookings,
                    'completed_bookings': completed_bookings,
                    'cancelled_bookings': cancelled_bookings,
                    'booking_conversion_rate': round(booking_conversion_rate, 2),
                    'completion_rate': round(completion_rate, 2),
                    'cancellation_rate': round(cancellation_rate, 2)
                },
                'financial': {
                    'total_revenue': float(total_revenue),
                    'platform_fees': float(platform_fees),
                    'payment_volume': payment_volume,
                    'avg_booking_value': float(avg_booking_value),
                    'avg_revenue_per_user': float(avg_revenue_per_user)
                },
                'braiders': {
                    'total_braiders': total_braiders,
                    'active_braiders': active_braiders,
                    'braider_utilization_rate': (
                        (active_braiders / total_braiders * 100) 
                        if total_braiders > 0 else 0
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating KPI metrics: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_financial_metrics(period: str = 'month') -> Dict[str, Any]:
        """Calculate detailed financial metrics."""
        now = timezone.now()
        
        if period == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:
            start_date = now - timedelta(days=30)
            end_date = now
        
        try:
            from apps.payments.models import Payment, Refund
            
            # Revenue breakdown
            payments = Payment.objects.filter(
                status='succeeded',
                processed_at__range=[start_date, end_date]
            )
            
            revenue_breakdown = payments.values('payment_type').annotate(
                total=Sum('amount'),
                count=Count('id'),
                avg_amount=Avg('amount')
            )
            
            # Total metrics
            total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            total_fees = payments.aggregate(Sum('platform_fee'))['platform_fee__sum'] or Decimal('0.00')
            net_revenue = total_revenue - total_fees
            
            # Refunds
            refunds = Refund.objects.filter(
                status='succeeded',
                processed_at__range=[start_date, end_date]
            ).aggregate(
                total_refunds=Sum('amount'),
                refund_count=Count('id')
            )
            
            # Payment methods analysis
            payment_methods = payments.values(
                'payment_method__method_type'
            ).annotate(
                total=Sum('amount'),
                count=Count('id')
            )
            
            # Daily revenue trend
            daily_revenue = []
            current_date = start_date.date()
            while current_date <= end_date.date():
                day_revenue = payments.filter(
                    processed_at__date=current_date
                ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
                
                daily_revenue.append({
                    'date': current_date.isoformat(),
                    'revenue': float(day_revenue)
                })
                current_date += timedelta(days=1)
            
            return {
                'period': period,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'totals': {
                    'gross_revenue': float(total_revenue),
                    'platform_fees': float(total_fees),
                    'net_revenue': float(net_revenue),
                    'total_refunds': float(refunds['total_refunds'] or 0),
                    'refund_count': refunds['refund_count'] or 0,
                    'refund_rate': (
                        float(refunds['total_refunds'] or 0) / float(total_revenue) * 100
                        if total_revenue > 0 else 0
                    )
                },
                'revenue_breakdown': [
                    {
                        'type': item['payment_type'],
                        'total': float(item['total']),
                        'count': item['count'],
                        'avg_amount': float(item['avg_amount'])
                    }
                    for item in revenue_breakdown
                ],
                'payment_methods': [
                    {
                        'method': item['payment_method__method_type'] or 'Unknown',
                        'total': float(item['total']),
                        'count': item['count']
                    }
                    for item in payment_methods
                ],
                'daily_trend': daily_revenue
            }
            
        except Exception as e:
            logger.error(f"Error calculating financial metrics: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_user_behavior_metrics(days: int = 30) -> Dict[str, Any]:
        """Calculate user behavior and engagement metrics."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Activity metrics
            activities = UserActivity.objects.filter(
                timestamp__range=[start_date, end_date]
            )
            
            # Most common activities
            activity_breakdown = activities.values('activity_type').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # User engagement
            active_users = activities.values('user').distinct().count()
            total_sessions = activities.filter(activity_type='login').count()
            
            # Average session metrics
            avg_activities_per_session = (
                activities.count() / total_sessions 
                if total_sessions > 0 else 0
            )
            
            # Peak usage hours
            hourly_activity = activities.extra(
                select={'hour': 'EXTRACT(hour FROM timestamp)'}
            ).values('hour').annotate(
                activity_count=Count('id')
            ).order_by('hour')
            
            # User retention (simplified)
            from apps.users.models import User
            users_created_period = User.objects.filter(
                date_joined__range=[start_date, end_date]
            )
            
            retained_users = users_created_period.filter(
                activities__timestamp__gte=start_date + timedelta(days=7)
            ).distinct().count()
            
            retention_rate = (
                retained_users / users_created_period.count() * 100
                if users_created_period.count() > 0 else 0
            )
            
            return {
                'period_days': days,
                'engagement': {
                    'active_users': active_users,
                    'total_sessions': total_sessions,
                    'avg_activities_per_session': round(avg_activities_per_session, 2),
                    'retention_rate': round(retention_rate, 2)
                },
                'activity_breakdown': [
                    {
                        'activity': item['activity_type'],
                        'count': item['count']
                    }
                    for item in activity_breakdown
                ],
                'hourly_activity': [
                    {
                        'hour': item['hour'],
                        'count': item['activity_count']
                    }
                    for item in hourly_activity
                ]
            }
            
        except Exception as e:
            logger.error(f"Error calculating user behavior metrics: {str(e)}")
            return {}
    
    @staticmethod
    def store_metric_datapoint(metric_name: str, value: float, dimensions: Dict = None, timestamp: datetime = None):
        """Store a metric data point."""
        try:
            metric = BusinessMetric.objects.get(name=metric_name, is_active=True)
            
            MetricDataPoint.objects.create(
                metric=metric,
                value=Decimal(str(value)),
                timestamp=timestamp or timezone.now(),
                dimensions=dimensions or {}
            )
            
        except BusinessMetric.DoesNotExist:
            logger.warning(f"Metric '{metric_name}' not found")
        except Exception as e:
            logger.error(f"Error storing metric datapoint: {str(e)}")


class DashboardService:
    """Service for dashboard data and management."""
    
    @staticmethod
    def get_executive_dashboard_data() -> Dict[str, Any]:
        """Get data for executive dashboard."""
        try:
            # Get current period metrics
            current_metrics = MetricsCalculator.calculate_kpi_metrics()
            
            # Get previous period for comparison
            now = timezone.now().date()
            days_in_period = 30
            previous_start = now - timedelta(days=days_in_period * 2)
            previous_end = now - timedelta(days=days_in_period)
            
            previous_metrics = MetricsCalculator.calculate_kpi_metrics(
                previous_start, previous_end
            )
            
            # Calculate growth rates
            def calculate_growth(current, previous):
                if previous == 0:
                    return 100 if current > 0 else 0
                return ((current - previous) / previous) * 100
            
            # Key metrics with growth
            key_metrics = {
                'total_revenue': {
                    'current': current_metrics['financial']['total_revenue'],
                    'previous': previous_metrics['financial']['total_revenue'],
                    'growth': calculate_growth(
                        current_metrics['financial']['total_revenue'],
                        previous_metrics['financial']['total_revenue']
                    )
                },
                'total_bookings': {
                    'current': current_metrics['bookings']['total_bookings'],
                    'previous': previous_metrics['bookings']['total_bookings'],
                    'growth': calculate_growth(
                        current_metrics['bookings']['total_bookings'],
                        previous_metrics['bookings']['total_bookings']
                    )
                },
                'active_users': {
                    'current': current_metrics['users']['active_users'],
                    'previous': previous_metrics['users']['active_users'],
                    'growth': calculate_growth(
                        current_metrics['users']['active_users'],
                        previous_metrics['users']['active_users']
                    )
                },
                'active_braiders': {
                    'current': current_metrics['braiders']['active_braiders'],
                    'previous': previous_metrics['braiders']['active_braiders'],
                    'growth': calculate_growth(
                        current_metrics['braiders']['active_braiders'],
                        previous_metrics['braiders']['active_braiders']
                    )
                }
            }
            
            # Recent alerts
            recent_alerts = Alert.objects.filter(
                status='active',
                severity__in=['high', 'critical']
            ).order_by('-created_at')[:5]
            
            return {
                'key_metrics': key_metrics,
                'current_period': current_metrics,
                'alerts': [
                    {
                        'id': str(alert.id),
                        'title': alert.title,
                        'severity': alert.severity,
                        'created_at': alert.created_at.isoformat()
                    }
                    for alert in recent_alerts
                ],
                'last_updated': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting executive dashboard data: {str(e)}")
            return {}
    
    @staticmethod
    def get_financial_dashboard_data() -> Dict[str, Any]:
        """Get data for financial dashboard."""
        try:
            # Current month metrics
            monthly_metrics = MetricsCalculator.calculate_financial_metrics('month')
            
            # Year-to-date metrics
            yearly_metrics = MetricsCalculator.calculate_financial_metrics('year')
            
            # Revenue trends (last 12 months)
            revenue_trends = []
            current_date = timezone.now().replace(day=1)
            
            for i in range(12):
                month_start = current_date.replace(month=current_date.month - i)
                if month_start.month > current_date.month:
                    month_start = month_start.replace(year=current_date.year - 1)
                
                month_end = month_start.replace(day=28) + timedelta(days=4)
                month_end = month_end - timedelta(days=month_end.day)
                
                from apps.payments.models import Payment
                month_revenue = Payment.objects.filter(
                    status='succeeded',
                    processed_at__range=[month_start, month_end]
                ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
                
                revenue_trends.append({
                    'month': month_start.strftime('%Y-%m'),
                    'revenue': float(month_revenue)
                })
            
            revenue_trends.reverse()
            
            return {
                'monthly': monthly_metrics,
                'yearly': yearly_metrics,
                'revenue_trends': revenue_trends,
                'last_updated': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting financial dashboard data: {str(e)}")
            return {}
    
    @staticmethod
    def get_dashboard_widgets(dashboard_id: str) -> List[Dict[str, Any]]:
        """Get widgets for a specific dashboard."""
        try:
            dashboard = Dashboard.objects.get(id=dashboard_id, is_active=True)
            widgets = DashboardWidget.objects.filter(
                dashboard=dashboard,
                is_active=True
            ).order_by('position_y', 'position_x')
            
            widget_data = []
            for widget in widgets:
                # Get widget data based on type
                data = DashboardService._get_widget_data(widget)
                
                widget_data.append({
                    'id': str(widget.id),
                    'title': widget.title,
                    'type': widget.widget_type,
                    'position': {
                        'x': widget.position_x,
                        'y': widget.position_y,
                        'width': widget.width,
                        'height': widget.height
                    },
                    'data': data,
                    'config': widget.chart_config
                })
            
            return widget_data
            
        except Dashboard.DoesNotExist:
            logger.warning(f"Dashboard {dashboard_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting dashboard widgets: {str(e)}")
            return []
    
    @staticmethod
    def _get_widget_data(widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget."""
        try:
            if widget.widget_type == 'metric_card':
                # Get latest value for metric
                metric = widget.metrics.first()
                if metric:
                    latest_point = metric.data_points.first()
                    return {
                        'value': float(latest_point.value) if latest_point else 0,
                        'formatted_value': metric.format_value(latest_point.value) if latest_point else '0'
                    }
            
            elif widget.widget_type in ['chart_line', 'chart_bar', 'chart_area']:
                # Get time series data
                metric = widget.metrics.first()
                if metric:
                    # Get last 30 data points
                    data_points = metric.data_points.order_by('-timestamp')[:30]
                    return {
                        'labels': [point.timestamp.strftime('%Y-%m-%d') for point in reversed(data_points)],
                        'datasets': [{
                            'label': metric.display_name,
                            'data': [float(point.value) for point in reversed(data_points)]
                        }]
                    }
            
            # Add more widget types as needed
            return {}
            
        except Exception as e:
            logger.error(f"Error getting widget data: {str(e)}")
            return {}


class AlertService:
    """Service for managing alerts and notifications."""
    
    @staticmethod
    def check_metric_thresholds():
        """Check all metrics against their alert thresholds."""
        metrics_with_alerts = BusinessMetric.objects.filter(
            has_alerts=True,
            is_active=True
        )
        
        alerts_created = 0
        
        for metric in metrics_with_alerts:
            try:
                # Get latest data point
                latest_point = metric.data_points.first()
                if not latest_point:
                    continue
                
                value = latest_point.value
                alert_triggered = False
                alert_message = ""
                
                # Check thresholds
                if metric.alert_threshold_min and value < metric.alert_threshold_min:
                    alert_triggered = True
                    alert_message = f"Value {value} is below minimum threshold {metric.alert_threshold_min}"
                
                elif metric.alert_threshold_max and value > metric.alert_threshold_max:
                    alert_triggered = True
                    alert_message = f"Value {value} exceeds maximum threshold {metric.alert_threshold_max}"
                
                if alert_triggered:
                    # Check if alert already exists
                    existing_alert = Alert.objects.filter(
                        metric=metric,
                        status='active',
                        created_at__gte=timezone.now() - timedelta(hours=1)
                    ).first()
                    
                    if not existing_alert:
                        # Create new alert
                        alert = Alert.objects.create(
                            title=f"Metric Alert: {metric.display_name}",
                            alert_type='metric_threshold',
                            severity='high' if metric.alert_threshold_max and value > metric.alert_threshold_max else 'medium',
                            description=alert_message,
                            metric=metric,
                            triggered_value=value,
                            threshold_value=metric.alert_threshold_min or metric.alert_threshold_max,
                            details={
                                'metric_name': metric.name,
                                'current_value': float(value),
                                'timestamp': latest_point.timestamp.isoformat()
                            }
                        )
                        
                        # Send notification
                        AlertService._send_alert_notification(alert)
                        alerts_created += 1
                
            except Exception as e:
                logger.error(f"Error checking alert for metric {metric.name}: {str(e)}")
        
        logger.info(f"Created {alerts_created} new alerts")
        return alerts_created
    
    @staticmethod
    def _send_alert_notification(alert: Alert):
        """Send notification for an alert."""
        try:
            from apps.notifications.integrations import notify_system
            
            # Get admin users (you might want to have a specific alert recipients list)
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            
            for user in admin_users:
                notify_system(
                    user=user,
                    title=f"🚨 {alert.title}",
                    message=alert.description,
                    priority=4 if alert.severity == 'critical' else 3
                )
            
            alert.notification_sent = True
            alert.notification_channels = ['in_app']
            alert.save(update_fields=['notification_sent', 'notification_channels'])
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}")