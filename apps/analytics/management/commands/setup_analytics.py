"""
Management command to initialize analytics system with default metrics and dashboards.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.analytics.models import (
    MetricCategory, BusinessMetric, Dashboard, DashboardWidget
)


class Command(BaseCommand):
    help = 'Initialize analytics system with default metrics and dashboards'
    
    def handle(self, *args, **options):
        """Set up default analytics configuration."""
        try:
            with transaction.atomic():
                self.stdout.write('Setting up analytics system...')
                
                # Create default metric categories
                categories_created = self.create_default_categories()
                self.stdout.write(f'Created {categories_created} metric categories')
                
                # Create default metrics
                metrics_created = self.create_default_metrics()
                self.stdout.write(f'Created {metrics_created} business metrics')
                
                # Create default dashboards
                dashboards_created = self.create_default_dashboards()
                self.stdout.write(f'Created {dashboards_created} dashboards')
                
                self.stdout.write(
                    self.style.SUCCESS('Analytics system setup completed successfully!')
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up analytics system: {str(e)}')
            )
    
    def create_default_categories(self):
        """Create default metric categories."""
        categories = [
            {
                'name': 'users',
                'display_name': 'User Metrics',
                'description': 'User registration, activity, and engagement metrics',
                'icon': 'fas fa-users',
                'color': '#3498db',
                'order': 1
            },
            {
                'name': 'bookings',
                'display_name': 'Booking Metrics',
                'description': 'Booking creation, completion, and performance metrics',
                'icon': 'fas fa-calendar-check',
                'color': '#2ecc71',
                'order': 2
            },
            {
                'name': 'financial',
                'display_name': 'Financial Metrics',
                'description': 'Revenue, payments, and financial performance metrics',
                'icon': 'fas fa-euro-sign',
                'color': '#f39c12',
                'order': 3
            },
            {
                'name': 'braiders',
                'display_name': 'Braider Metrics',
                'description': 'Braider performance and activity metrics',
                'icon': 'fas fa-user-tie',
                'color': '#9b59b6',
                'order': 4
            },
            {
                'name': 'system',
                'display_name': 'System Metrics',
                'description': 'Performance, errors, and technical metrics',
                'icon': 'fas fa-server',
                'color': '#34495e',
                'order': 5
            }
        ]
        
        created_count = 0
        for cat_data in categories:
            category, created = MetricCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  - Created category: {category.display_name}')
        
        return created_count
    
    def create_default_metrics(self):
        """Create default business metrics."""
        # Get categories
        users_cat = MetricCategory.objects.get(name='users')
        bookings_cat = MetricCategory.objects.get(name='bookings')
        financial_cat = MetricCategory.objects.get(name='financial')
        braiders_cat = MetricCategory.objects.get(name='braiders')
        system_cat = MetricCategory.objects.get(name='system')
        
        metrics = [
            # User metrics
            {
                'name': 'new_user_registrations',
                'display_name': 'New User Registrations',
                'category': users_cat,
                'metric_type': 'counter',
                'unit': 'users',
                'description': 'Number of new users registered',
                'is_featured': True,
                'aggregation_type': 'sum'
            },
            {
                'name': 'daily_logins',
                'display_name': 'Daily Logins',
                'category': users_cat,
                'metric_type': 'counter',
                'unit': 'logins',
                'description': 'Number of user logins per day',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'active_users',
                'display_name': 'Active Users',
                'category': users_cat,
                'metric_type': 'gauge',
                'unit': 'users',
                'description': 'Number of active users',
                'is_featured': True,
                'aggregation_type': 'last'
            },
            
            # Booking metrics
            {
                'name': 'total_bookings',
                'display_name': 'Total Bookings',
                'category': bookings_cat,
                'metric_type': 'counter',
                'unit': 'bookings',
                'description': 'Total number of bookings created',
                'is_featured': True,
                'aggregation_type': 'sum'
            },
            {
                'name': 'confirmed_bookings',
                'display_name': 'Confirmed Bookings',
                'category': bookings_cat,
                'metric_type': 'counter',
                'unit': 'bookings',
                'description': 'Number of confirmed bookings',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'completed_bookings',
                'display_name': 'Completed Bookings',
                'category': bookings_cat,
                'metric_type': 'counter',
                'unit': 'bookings',
                'description': 'Number of completed bookings',
                'is_featured': True,
                'aggregation_type': 'sum'
            },
            {
                'name': 'cancelled_bookings',
                'display_name': 'Cancelled Bookings',
                'category': bookings_cat,
                'metric_type': 'counter',
                'unit': 'bookings',
                'description': 'Number of cancelled bookings',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'booking_conversion_rate',
                'display_name': 'Booking Conversion Rate',
                'category': bookings_cat,
                'metric_type': 'percentage',
                'unit': '%',
                'description': 'Percentage of bookings that get confirmed',
                'is_featured': True,
                'aggregation_type': 'avg'
            },
            
            # Financial metrics
            {
                'name': 'booking_revenue',
                'display_name': 'Booking Revenue',
                'category': financial_cat,
                'metric_type': 'currency',
                'unit': '€',
                'description': 'Total revenue from bookings',
                'is_featured': True,
                'aggregation_type': 'sum'
            },
            {
                'name': 'payment_volume',
                'display_name': 'Payment Volume',
                'category': financial_cat,
                'metric_type': 'counter',
                'unit': 'payments',
                'description': 'Number of successful payments',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'payment_revenue',
                'display_name': 'Payment Revenue',
                'category': financial_cat,
                'metric_type': 'currency',
                'unit': '€',
                'description': 'Total revenue from payments',
                'is_featured': True,
                'aggregation_type': 'sum'
            },
            {
                'name': 'platform_fees',
                'display_name': 'Platform Fees',
                'category': financial_cat,
                'metric_type': 'currency',
                'unit': '€',
                'description': 'Total platform fees collected',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'average_booking_value',
                'display_name': 'Average Booking Value',
                'category': financial_cat,
                'metric_type': 'currency',
                'unit': '€',
                'description': 'Average value per booking',
                'is_featured': True,
                'aggregation_type': 'avg'
            },
            
            # Braider metrics
            {
                'name': 'active_braiders',
                'display_name': 'Active Braiders',
                'category': braiders_cat,
                'metric_type': 'gauge',
                'unit': 'braiders',
                'description': 'Number of active braiders',
                'is_featured': True,
                'aggregation_type': 'last'
            },
            {
                'name': 'total_ratings',
                'display_name': 'Total Ratings',
                'category': braiders_cat,
                'metric_type': 'counter',
                'unit': 'ratings',
                'description': 'Total number of ratings given',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'average_rating',
                'display_name': 'Average Rating',
                'category': braiders_cat,
                'metric_type': 'gauge',
                'unit': 'stars',
                'description': 'Average rating across all braiders',
                'is_featured': True,
                'aggregation_type': 'avg'
            },
            
            # System metrics
            {
                'name': 'total_messages',
                'display_name': 'Total Messages',
                'category': system_cat,
                'metric_type': 'counter',
                'unit': 'messages',
                'description': 'Total chat messages sent',
                'is_featured': False,
                'aggregation_type': 'sum'
            },
            {
                'name': 'api_response_time',
                'display_name': 'API Response Time',
                'category': system_cat,
                'metric_type': 'duration',
                'unit': 'ms',
                'description': 'Average API response time',
                'is_featured': False,
                'aggregation_type': 'avg',
                'has_alerts': True,
                'alert_threshold_max': 1000  # Alert if response time > 1 second
            },
            {
                'name': 'error_count',
                'display_name': 'Error Count',
                'category': system_cat,
                'metric_type': 'counter',
                'unit': 'errors',
                'description': 'Number of application errors',
                'is_featured': False,
                'aggregation_type': 'sum',
                'has_alerts': True,
                'alert_threshold_max': 10  # Alert if more than 10 errors per hour
            }
        ]
        
        created_count = 0
        for metric_data in metrics:
            metric, created = BusinessMetric.objects.get_or_create(
                name=metric_data['name'],
                defaults=metric_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  - Created metric: {metric.display_name}')
        
        return created_count
    
    def create_default_dashboards(self):
        """Create default dashboards."""
        dashboards = [
            {
                'name': 'Executive Dashboard',
                'dashboard_type': 'executive',
                'description': 'High-level KPIs and business metrics for executives',
                'is_public': True,
                'refresh_interval': 300,
                'layout_config': {
                    'grid_cols': 12,
                    'grid_rows': 8,
                    'widgets': []
                }
            },
            {
                'name': 'Financial Dashboard',
                'dashboard_type': 'financial',
                'description': 'Revenue, payments, and financial performance metrics',
                'is_public': False,
                'refresh_interval': 300,
                'layout_config': {
                    'grid_cols': 12,
                    'grid_rows': 8,
                    'widgets': []
                }
            },
            {
                'name': 'Operations Dashboard',
                'dashboard_type': 'operational',
                'description': 'Day-to-day operations and booking metrics',
                'is_public': False,
                'refresh_interval': 180,
                'layout_config': {
                    'grid_cols': 12,
                    'grid_rows': 8,
                    'widgets': []
                }
            },
            {
                'name': 'User Behavior Dashboard',
                'dashboard_type': 'user_behavior',
                'description': 'User engagement and behavior analytics',
                'is_public': False,
                'refresh_interval': 600,
                'layout_config': {
                    'grid_cols': 12,
                    'grid_rows': 8,
                    'widgets': []
                }
            }
        ]
        
        created_count = 0
        for dashboard_data in dashboards:
            dashboard, created = Dashboard.objects.get_or_create(
                name=dashboard_data['name'],
                defaults=dashboard_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  - Created dashboard: {dashboard.name}')
                
                # Create some default widgets for the executive dashboard
                if dashboard.dashboard_type == 'executive':
                    self.create_executive_dashboard_widgets(dashboard)
        
        return created_count
    
    def create_executive_dashboard_widgets(self, dashboard):
        """Create default widgets for executive dashboard."""
        # Get featured metrics
        featured_metrics = BusinessMetric.objects.filter(is_featured=True)
        
        widgets = [
            {
                'title': 'New Users',
                'widget_type': 'metric_card',
                'position_x': 0,
                'position_y': 0,
                'width': 3,
                'height': 2,
                'metrics': ['new_user_registrations']
            },
            {
                'title': 'Total Bookings',
                'widget_type': 'metric_card',
                'position_x': 3,
                'position_y': 0,
                'width': 3,
                'height': 2,
                'metrics': ['total_bookings']
            },
            {
                'title': 'Revenue',
                'widget_type': 'metric_card',
                'position_x': 6,
                'position_y': 0,
                'width': 3,
                'height': 2,
                'metrics': ['booking_revenue']
            },
            {
                'title': 'Active Braiders',
                'widget_type': 'metric_card',
                'position_x': 9,
                'position_y': 0,
                'width': 3,
                'height': 2,
                'metrics': ['active_braiders']
            },
            {
                'title': 'Revenue Trend',
                'widget_type': 'chart_line',
                'position_x': 0,
                'position_y': 2,
                'width': 6,
                'height': 3,
                'metrics': ['booking_revenue'],
                'chart_config': {
                    'type': 'line',
                    'options': {
                        'responsive': True,
                        'scales': {
                            'y': {
                                'beginAtZero': True
                            }
                        }
                    }
                }
            },
            {
                'title': 'Booking Status',
                'widget_type': 'chart_pie',
                'position_x': 6,
                'position_y': 2,
                'width': 6,
                'height': 3,
                'metrics': ['completed_bookings', 'cancelled_bookings'],
                'chart_config': {
                    'type': 'pie',
                    'options': {
                        'responsive': True
                    }
                }
            }
        ]
        
        for widget_data in widgets:
            metric_names = widget_data.pop('metrics', [])
            widget = DashboardWidget.objects.create(
                dashboard=dashboard,
                **widget_data
            )
            
            # Add metrics to widget
            for metric_name in metric_names:
                try:
                    metric = BusinessMetric.objects.get(name=metric_name)
                    widget.metrics.add(metric)
                except BusinessMetric.DoesNotExist:
                    pass
            
            self.stdout.write(f'    - Created widget: {widget.title}')