"""
Tests for analytics functionality including metrics, dashboards, and reporting.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta, time, date
import json

from .models import (
    MetricCategory, BusinessMetric, MetricDataPoint, Dashboard, DashboardWidget,
    Report, ReportGeneration, UserActivity, SystemPerformance, Alert, CohortAnalysis
)

User = get_user_model()


class MetricCategoryModelTest(TestCase):
    """Test MetricCategory model functionality."""
    
    def test_create_metric_category(self):
        """Test creating a metric category."""
        category = MetricCategory.objects.create(
            name='revenue',
            display_name='Revenue Metrics',
            description='Financial revenue tracking',
            icon='dollar-sign',
            color='#28a745',
            order=1
        )
        
        self.assertEqual(category.name, 'revenue')
        self.assertEqual(category.display_name, 'Revenue Metrics')
        self.assertEqual(category.color, '#28a745')
        self.assertTrue(category.is_active)
        self.assertEqual(category.order, 1)
    
    def test_category_string_representation(self):
        """Test category string representation."""
        category = MetricCategory.objects.create(
            name='users',
            display_name='User Metrics'
        )
        
        self.assertEqual(str(category), 'User Metrics')
    
    def test_category_ordering(self):
        """Test category ordering by order and name."""
        cat1 = MetricCategory.objects.create(name='zz_last', display_name='Last', order=2)
        cat2 = MetricCategory.objects.create(name='aa_first', display_name='First', order=1)
        cat3 = MetricCategory.objects.create(name='bb_middle', display_name='Middle', order=1)
        
        categories = list(MetricCategory.objects.all())
        
        # Should be ordered by order field first, then by name
        self.assertEqual(categories[0], cat2)  # order=1, name='aa_first'
        self.assertEqual(categories[1], cat3)  # order=1, name='bb_middle'
        self.assertEqual(categories[2], cat1)  # order=2


class BusinessMetricModelTest(TestCase):
    """Test BusinessMetric model functionality."""
    
    def setUp(self):
        self.category = MetricCategory.objects.create(
            name='financial',
            display_name='Financial Metrics'
        )
        
        self.metric_data = {
            'category': self.category,
            'name': 'total_revenue',
            'display_name': 'Total Revenue',
            'description': 'Total revenue generated',
            'metric_type': 'currency',
            'unit': '€',
            'aggregation_type': 'sum',
            'is_featured': True
        }
    
    def test_create_business_metric(self):
        """Test creating a business metric."""
        metric = BusinessMetric.objects.create(**self.metric_data)
        
        self.assertEqual(metric.category, self.category)
        self.assertEqual(metric.name, 'total_revenue')
        self.assertEqual(metric.metric_type, 'currency')
        self.assertEqual(metric.aggregation_type, 'sum')
        self.assertTrue(metric.is_featured)
        self.assertTrue(metric.is_active)
    
    def test_metric_string_representation(self):
        """Test metric string representation."""
        metric = BusinessMetric.objects.create(**self.metric_data)
        self.assertEqual(str(metric), 'Total Revenue')
    
    def test_format_currency_value(self):
        """Test formatting currency values."""
        metric = BusinessMetric.objects.create(
            **self.metric_data,
            metric_type='currency'
        )
        
        formatted = metric.format_value(1234.56)
        self.assertEqual(formatted, '€1,234.56')
    
    def test_format_percentage_value(self):
        """Test formatting percentage values."""
        metric = BusinessMetric.objects.create(
            category=self.category,
            name='conversion_rate',
            display_name='Conversion Rate',
            metric_type='percentage'
        )
        
        formatted = metric.format_value(15.678)
        self.assertEqual(formatted, '15.7%')
    
    def test_format_duration_value(self):
        """Test formatting duration values."""
        metric = BusinessMetric.objects.create(
            category=self.category,
            name='avg_session_time',
            display_name='Average Session Time',
            metric_type='duration'
        )
        
        # Test seconds
        self.assertEqual(metric.format_value(45), '45s')
        
        # Test minutes
        self.assertEqual(metric.format_value(150), '2.5m')
        
        # Test hours
        self.assertEqual(metric.format_value(7200), '2.0h')
    
    def test_custom_format_string(self):
        """Test custom format string."""
        metric = BusinessMetric.objects.create(
            category=self.category,
            name='active_users',
            display_name='Active Users',
            metric_type='counter',
            format_string='{value} users'
        )
        
        formatted = metric.format_value(142)
        self.assertEqual(formatted, '142 users')
    
    def test_metric_with_alerts(self):
        """Test metric with alert thresholds."""
        metric = BusinessMetric.objects.create(
            **self.metric_data,
            has_alerts=True,
            alert_threshold_min=Decimal('1000.00'),
            alert_threshold_max=Decimal('10000.00')
        )
        
        self.assertTrue(metric.has_alerts)
        self.assertEqual(metric.alert_threshold_min, Decimal('1000.00'))
        self.assertEqual(metric.alert_threshold_max, Decimal('10000.00'))


class MetricDataPointModelTest(TestCase):
    """Test MetricDataPoint model functionality."""
    
    def setUp(self):
        self.category = MetricCategory.objects.create(
            name='test_category',
            display_name='Test Category'
        )
        
        self.metric = BusinessMetric.objects.create(
            category=self.category,
            name='test_metric',
            display_name='Test Metric',
            metric_type='counter'
        )
        
        self.timestamp = timezone.now()
    
    def test_create_metric_data_point(self):
        """Test creating a metric data point."""
        data_point = MetricDataPoint.objects.create(
            metric=self.metric,
            value=Decimal('123.45'),
            timestamp=self.timestamp,
            dimensions={'location': 'lisbon', 'source': 'web'}
        )
        
        self.assertEqual(data_point.metric, self.metric)
        self.assertEqual(data_point.value, Decimal('123.45'))
        self.assertEqual(data_point.timestamp, self.timestamp)
        self.assertEqual(data_point.dimensions['location'], 'lisbon')
    
    def test_auto_populate_period_fields(self):
        """Test auto-population of period fields."""
        test_datetime = datetime(2024, 3, 15, 14, 30, 0)  # Friday
        test_datetime = timezone.make_aware(test_datetime)
        
        data_point = MetricDataPoint.objects.create(
            metric=self.metric,
            value=Decimal('100.00'),
            timestamp=test_datetime
        )
        
        self.assertEqual(data_point.date, date(2024, 3, 15))
        self.assertEqual(data_point.hour, 14)
        self.assertEqual(data_point.day_of_week, 4)  # Friday = 4 (Monday = 0)
        self.assertEqual(data_point.month, 3)
        self.assertEqual(data_point.year, 2024)
        self.assertEqual(data_point.week, 11)  # Week 11 of 2024
    
    def test_unique_constraint(self):
        """Test unique constraint on metric, timestamp, and dimensions."""
        dimensions = {'user_type': 'customer'}
        
        # Create first data point
        MetricDataPoint.objects.create(
            metric=self.metric,
            value=Decimal('50.00'),
            timestamp=self.timestamp,
            dimensions=dimensions
        )
        
        # Try to create duplicate - should raise error
        with self.assertRaises(Exception):
            MetricDataPoint.objects.create(
                metric=self.metric,
                value=Decimal('75.00'),
                timestamp=self.timestamp,
                dimensions=dimensions
            )


class DashboardModelTest(TestCase):
    """Test Dashboard model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='dashboard@test.com',
            name='Dashboard User',
            password='testpass'
        )
        
        self.dashboard_data = {
            'name': 'Executive Dashboard',
            'dashboard_type': 'executive',
            'description': 'High-level business metrics',
            'is_public': False,
            'layout_config': {
                'columns': 12,
                'rows': 8,
                'margin': [10, 10]
            },
            'refresh_interval': 60
        }
    
    def test_create_dashboard(self):
        """Test creating a dashboard."""
        dashboard = Dashboard.objects.create(**self.dashboard_data)
        
        self.assertEqual(dashboard.name, 'Executive Dashboard')
        self.assertEqual(dashboard.dashboard_type, 'executive')
        self.assertFalse(dashboard.is_public)
        self.assertEqual(dashboard.refresh_interval, 60)
        self.assertTrue(dashboard.is_active)
    
    def test_dashboard_string_representation(self):
        """Test dashboard string representation."""
        dashboard = Dashboard.objects.create(**self.dashboard_data)
        self.assertEqual(str(dashboard), 'Executive Dashboard')
    
    def test_dashboard_access_control(self):
        """Test dashboard access control."""
        dashboard = Dashboard.objects.create(**self.dashboard_data)
        
        # Add allowed user
        dashboard.allowed_users.add(self.user)
        
        # Set allowed roles
        dashboard.allowed_roles = ['admin', 'manager']
        dashboard.save()
        
        self.assertIn(self.user, dashboard.allowed_users.all())
        self.assertIn('admin', dashboard.allowed_roles)
    
    def test_public_dashboard(self):
        """Test public dashboard creation."""
        public_dashboard = Dashboard.objects.create(
            name='Public Metrics',
            dashboard_type='operational',
            is_public=True
        )
        
        self.assertTrue(public_dashboard.is_public)


class DashboardWidgetModelTest(TestCase):
    """Test DashboardWidget model functionality."""
    
    def setUp(self):
        self.dashboard = Dashboard.objects.create(
            name='Test Dashboard',
            dashboard_type='custom'
        )
        
        self.category = MetricCategory.objects.create(
            name='widget_test',
            display_name='Widget Test'
        )
        
        self.metric = BusinessMetric.objects.create(
            category=self.category,
            name='widget_metric',
            display_name='Widget Metric',
            metric_type='counter'
        )
        
        self.widget_data = {
            'dashboard': self.dashboard,
            'title': 'Revenue Chart',
            'widget_type': 'chart_line',
            'position_x': 0,
            'position_y': 0,
            'width': 6,
            'height': 4,
            'chart_config': {
                'type': 'line',
                'options': {
                    'responsive': True,
                    'scales': {
                        'y': {'beginAtZero': True}
                    }
                }
            }
        }
    
    def test_create_dashboard_widget(self):
        """Test creating a dashboard widget."""
        widget = DashboardWidget.objects.create(**self.widget_data)
        
        self.assertEqual(widget.dashboard, self.dashboard)
        self.assertEqual(widget.title, 'Revenue Chart')
        self.assertEqual(widget.widget_type, 'chart_line')
        self.assertEqual(widget.width, 6)
        self.assertEqual(widget.height, 4)
        self.assertTrue(widget.is_active)
    
    def test_widget_string_representation(self):
        """Test widget string representation."""
        widget = DashboardWidget.objects.create(**self.widget_data)
        expected = f"Test Dashboard - Revenue Chart"
        self.assertEqual(str(widget), expected)
    
    def test_widget_with_metrics(self):
        """Test widget with associated metrics."""
        widget = DashboardWidget.objects.create(**self.widget_data)
        widget.metrics.add(self.metric)
        
        self.assertIn(self.metric, widget.metrics.all())
    
    def test_widget_positioning(self):
        """Test widget positioning and sizing."""
        widget = DashboardWidget.objects.create(
            dashboard=self.dashboard,
            title='Position Test',
            widget_type='metric_card',
            position_x=2,
            position_y=1,
            width=4,
            height=2
        )
        
        self.assertEqual(widget.position_x, 2)
        self.assertEqual(widget.position_y, 1)
        self.assertEqual(widget.width, 4)
        self.assertEqual(widget.height, 2)


class ReportModelTest(TestCase):
    """Test Report model functionality."""
    
    def setUp(self):
        self.category = MetricCategory.objects.create(
            name='report_test',
            display_name='Report Test'
        )
        
        self.metric = BusinessMetric.objects.create(
            category=self.category,
            name='report_metric',
            display_name='Report Metric',
            metric_type='currency'
        )
        
        self.report_data = {
            'name': 'Monthly Revenue Report',
            'report_type': 'monthly',
            'description': 'Monthly financial performance report',
            'schedule_type': 'monthly',
            'schedule_time': time(9, 0),
            'schedule_day_of_month': 1,
            'output_format': 'pdf',
            'email_recipients': ['admin@tuwi.com', 'finance@tuwi.com']
        }
    
    def test_create_report(self):
        """Test creating a report."""
        report = Report.objects.create(**self.report_data)
        
        self.assertEqual(report.name, 'Monthly Revenue Report')
        self.assertEqual(report.report_type, 'monthly')
        self.assertEqual(report.schedule_type, 'monthly')
        self.assertEqual(report.output_format, 'pdf')
        self.assertTrue(report.is_active)
    
    def test_report_string_representation(self):
        """Test report string representation."""
        report = Report.objects.create(**self.report_data)
        self.assertEqual(str(report), 'Monthly Revenue Report')
    
    def test_report_with_metrics(self):
        """Test report with associated metrics."""
        report = Report.objects.create(**self.report_data)
        report.metrics.add(self.metric)
        
        self.assertIn(self.metric, report.metrics.all())
    
    def test_manual_report(self):
        """Test manual report creation."""
        manual_report = Report.objects.create(
            name='Ad-hoc Analysis',
            report_type='custom',
            schedule_type='manual',
            date_range_start=date(2024, 1, 1),
            date_range_end=date(2024, 1, 31),
            output_format='excel'
        )
        
        self.assertEqual(manual_report.schedule_type, 'manual')
        self.assertEqual(manual_report.date_range_start, date(2024, 1, 1))
        self.assertEqual(manual_report.output_format, 'excel')
    
    def test_weekly_scheduled_report(self):
        """Test weekly scheduled report."""
        weekly_report = Report.objects.create(
            name='Weekly Performance',
            report_type='weekly',
            schedule_type='weekly',
            schedule_time=time(8, 30),
            schedule_day_of_week=1,  # Monday
            output_format='csv'
        )
        
        self.assertEqual(weekly_report.schedule_day_of_week, 1)
        self.assertEqual(weekly_report.schedule_time, time(8, 30))


class ReportGenerationModelTest(TestCase):
    """Test ReportGeneration model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='reports@test.com',
            name='Reports User',
            password='testpass'
        )
        
        self.report = Report.objects.create(
            name='Test Report',
            report_type='daily',
            output_format='pdf'
        )
    
    def test_create_report_generation(self):
        """Test creating a report generation."""
        generation = ReportGeneration.objects.create(
            report=self.report,
            generated_by=self.user,
            status='completed',
            started_at=timezone.now() - timedelta(minutes=5),
            completed_at=timezone.now(),
            file_path='/reports/test_report_2024_01_15.pdf',
            file_size=1024000
        )
        
        self.assertEqual(generation.report, self.report)
        self.assertEqual(generation.generated_by, self.user)
        self.assertEqual(generation.status, 'completed')
        self.assertEqual(generation.file_size, 1024000)
    
    def test_generation_string_representation(self):
        """Test generation string representation."""
        generation = ReportGeneration.objects.create(
            report=self.report,
            status='pending'
        )
        
        expected = f"Test Report - {generation.created_at.strftime('%Y-%m-%d %H:%M')}"
        self.assertEqual(str(generation), expected)
    
    def test_failed_generation(self):
        """Test failed report generation."""
        generation = ReportGeneration.objects.create(
            report=self.report,
            status='failed',
            error_message='Database connection timeout'
        )
        
        self.assertEqual(generation.status, 'failed')
        self.assertEqual(generation.error_message, 'Database connection timeout')


class UserActivityModelTest(TestCase):
    """Test UserActivity model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='activity@test.com',
            name='Activity User',
            password='testpass'
        )
    
    def test_create_user_activity(self):
        """Test creating user activity record."""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='User logged in',
            session_id='session_123',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            metadata={'browser': 'chrome', 'device': 'desktop'}
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.description, 'User logged in')
        self.assertEqual(activity.session_id, 'session_123')
        self.assertEqual(activity.metadata['browser'], 'chrome')
    
    def test_activity_string_representation(self):
        """Test activity string representation."""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='booking_created',
            description='Created new booking'
        )
        
        expected = f"{self.user.email} - Booking Created"
        self.assertEqual(str(activity), expected)
    
    def test_activity_with_duration(self):
        """Test activity with duration tracking."""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='page_view',
            description='Viewed braiders listing page',
            duration=timedelta(minutes=3, seconds=45)
        )
        
        self.assertEqual(activity.duration, timedelta(minutes=3, seconds=45))


class SystemPerformanceModelTest(TestCase):
    """Test SystemPerformance model functionality."""
    
    def test_create_performance_metric(self):
        """Test creating system performance metric."""
        performance = SystemPerformance.objects.create(
            performance_type='response_time',
            value=Decimal('245.50'),
            endpoint='/api/v1/braiders/',
            method='GET',
            status_code=200,
            metadata={'server': 'web-01', 'load': 'high'}
        )
        
        self.assertEqual(performance.performance_type, 'response_time')
        self.assertEqual(performance.value, Decimal('245.50'))
        self.assertEqual(performance.endpoint, '/api/v1/braiders/')
        self.assertEqual(performance.method, 'GET')
        self.assertEqual(performance.status_code, 200)
    
    def test_performance_string_representation(self):
        """Test performance metric string representation."""
        performance = SystemPerformance.objects.create(
            performance_type='cpu_usage',
            value=Decimal('78.5')
        )
        
        expected = f"CPU Usage - 78.5"
        self.assertEqual(str(performance), expected)
    
    def test_database_performance_metric(self):
        """Test database performance tracking."""
        db_performance = SystemPerformance.objects.create(
            performance_type='db_performance',
            value=Decimal('15.2'),
            metadata={
                'query_type': 'SELECT',
                'table': 'braiders',
                'execution_plan': 'index_scan'
            }
        )
        
        self.assertEqual(db_performance.performance_type, 'db_performance')
        self.assertEqual(db_performance.metadata['query_type'], 'SELECT')


class AlertModelTest(TestCase):
    """Test Alert model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='alerts@test.com',
            name='Alerts Admin',
            password='testpass'
        )
        
        self.category = MetricCategory.objects.create(
            name='performance',
            display_name='Performance'
        )
        
        self.metric = BusinessMetric.objects.create(
            category=self.category,
            name='response_time',
            display_name='Response Time',
            metric_type='duration',
            has_alerts=True,
            alert_threshold_max=Decimal('500.00')
        )
    
    def test_create_alert(self):
        """Test creating an alert."""
        alert = Alert.objects.create(
            title='High Response Time Detected',
            alert_type='metric_threshold',
            severity='high',
            description='Response time exceeded 500ms threshold',
            metric=self.metric,
            triggered_value=Decimal('750.00'),
            threshold_value=Decimal('500.00'),
            details={
                'endpoint': '/api/v1/bookings/',
                'duration': '750ms',
                'threshold': '500ms'
            }
        )
        
        self.assertEqual(alert.title, 'High Response Time Detected')
        self.assertEqual(alert.alert_type, 'metric_threshold')
        self.assertEqual(alert.severity, 'high')
        self.assertEqual(alert.status, 'active')
        self.assertEqual(alert.metric, self.metric)
        self.assertEqual(alert.triggered_value, Decimal('750.00'))
    
    def test_alert_string_representation(self):
        """Test alert string representation."""
        alert = Alert.objects.create(
            title='System Error Alert',
            alert_type='system_error',
            severity='critical',
            description='Database connection failed'
        )
        
        expected = "System Error Alert (Critical)"
        self.assertEqual(str(alert), expected)
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        alert = Alert.objects.create(
            title='Test Alert',
            alert_type='performance_issue',
            severity='medium',
            description='Test alert for acknowledgment'
        )
        
        self.assertEqual(alert.status, 'active')
        self.assertIsNone(alert.acknowledged_by)
        
        alert.acknowledge(self.user)
        
        self.assertEqual(alert.status, 'acknowledged')
        self.assertEqual(alert.acknowledged_by, self.user)
        self.assertIsNotNone(alert.acknowledged_at)
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        alert = Alert.objects.create(
            title='Resolvable Alert',
            alert_type='business_anomaly',
            severity='low',
            description='Test alert for resolution'
        )
        
        alert.resolve()
        
        self.assertEqual(alert.status, 'resolved')
        self.assertIsNotNone(alert.resolved_at)
    
    def test_critical_security_alert(self):
        """Test critical security alert."""
        security_alert = Alert.objects.create(
            title='Multiple Failed Login Attempts',
            alert_type='security_concern',
            severity='critical',
            description='Potential brute force attack detected',
            details={
                'ip_address': '192.168.1.100',
                'failed_attempts': 10,
                'time_window': '5 minutes'
            },
            notification_sent=True,
            notification_channels=['email', 'slack', 'sms']
        )
        
        self.assertEqual(security_alert.severity, 'critical')
        self.assertTrue(security_alert.notification_sent)
        self.assertIn('email', security_alert.notification_channels)


class CohortAnalysisModelTest(TestCase):
    """Test CohortAnalysis model functionality."""
    
    def test_create_cohort_analysis(self):
        """Test creating cohort analysis data."""
        cohort = CohortAnalysis.objects.create(
            cohort_period=date(2024, 1, 1),
            analysis_period=date(2024, 2, 1),
            cohort_size=100,
            active_users=85,
            retention_rate=Decimal('85.00'),
            total_revenue=Decimal('12500.00'),
            average_revenue_per_user=Decimal('147.06'),
            average_bookings=Decimal('2.3'),
            average_session_duration=timedelta(minutes=15, seconds=30),
            period_number=1
        )
        
        self.assertEqual(cohort.cohort_period, date(2024, 1, 1))
        self.assertEqual(cohort.analysis_period, date(2024, 2, 1))
        self.assertEqual(cohort.cohort_size, 100)
        self.assertEqual(cohort.active_users, 85)
        self.assertEqual(cohort.retention_rate, Decimal('85.00'))
        self.assertEqual(cohort.period_number, 1)
    
    def test_cohort_string_representation(self):
        """Test cohort analysis string representation."""
        cohort = CohortAnalysis.objects.create(
            cohort_period=date(2024, 1, 1),
            analysis_period=date(2024, 3, 1),
            cohort_size=50,
            active_users=30,
            retention_rate=Decimal('60.00'),
            period_number=2
        )
        
        expected = "Cohort 2024-01-01 - Period 2"
        self.assertEqual(str(cohort), expected)
    
    def test_cohort_revenue_metrics(self):
        """Test cohort revenue calculations."""
        cohort = CohortAnalysis.objects.create(
            cohort_period=date(2024, 1, 1),
            analysis_period=date(2024, 1, 1),
            cohort_size=200,
            active_users=200,
            retention_rate=Decimal('100.00'),
            total_revenue=Decimal('25000.00'),
            average_revenue_per_user=Decimal('125.00'),
            period_number=0
        )
        
        # Verify ARPU calculation makes sense
        calculated_arpu = cohort.total_revenue / cohort.active_users
        self.assertEqual(calculated_arpu, cohort.average_revenue_per_user)


class AnalyticsIntegrationTest(TestCase):
    """Test analytics system integration scenarios."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='integration@test.com',
            name='Integration User',
            password='testpass'
        )
        
        # Create metric category and metrics
        self.category = MetricCategory.objects.create(
            name='integration_test',
            display_name='Integration Test'
        )
        
        self.revenue_metric = BusinessMetric.objects.create(
            category=self.category,
            name='daily_revenue',
            display_name='Daily Revenue',
            metric_type='currency',
            has_alerts=True,
            alert_threshold_min=Decimal('1000.00')
        )
        
        self.user_metric = BusinessMetric.objects.create(
            category=self.category,
            name='active_users',
            display_name='Active Users',
            metric_type='counter'
        )
    
    def test_metric_data_collection_and_alerting(self):
        """Test metric data collection with alert generation."""
        # Record normal metric value
        normal_data = MetricDataPoint.objects.create(
            metric=self.revenue_metric,
            value=Decimal('1500.00'),
            timestamp=timezone.now() - timedelta(hours=2)
        )
        
        # Record low value that should trigger alert
        low_data = MetricDataPoint.objects.create(
            metric=self.revenue_metric,
            value=Decimal('500.00'),
            timestamp=timezone.now()
        )
        
        # Simulate alert generation (would be done by background task)
        if low_data.value < self.revenue_metric.alert_threshold_min:
            alert = Alert.objects.create(
                title=f'Low {self.revenue_metric.display_name}',
                alert_type='metric_threshold',
                severity='medium',
                description=f'Revenue dropped below €{self.revenue_metric.alert_threshold_min}',
                metric=self.revenue_metric,
                triggered_value=low_data.value,
                threshold_value=self.revenue_metric.alert_threshold_min
            )
        
        # Verify alert was created
        alerts = Alert.objects.filter(metric=self.revenue_metric)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().severity, 'medium')
    
    def test_dashboard_with_widgets_and_metrics(self):
        """Test complete dashboard setup with widgets and metrics."""
        # Create dashboard
        dashboard = Dashboard.objects.create(
            name='Business Overview',
            dashboard_type='executive',
            is_public=True
        )
        
        # Create revenue widget
        revenue_widget = DashboardWidget.objects.create(
            dashboard=dashboard,
            title='Daily Revenue',
            widget_type='metric_card',
            position_x=0,
            position_y=0,
            width=6,
            height=3
        )
        revenue_widget.metrics.add(self.revenue_metric)
        
        # Create users widget
        users_widget = DashboardWidget.objects.create(
            dashboard=dashboard,
            title='Active Users Trend',
            widget_type='chart_line',
            position_x=6,
            position_y=0,
            width=6,
            height=3,
            chart_config={
                'type': 'line',
                'options': {'responsive': True}
            }
        )
        users_widget.metrics.add(self.user_metric)
        
        # Verify dashboard setup
        self.assertEqual(dashboard.widgets.count(), 2)
        self.assertIn(self.revenue_metric, revenue_widget.metrics.all())
        self.assertIn(self.user_metric, users_widget.metrics.all())
    
    def test_report_generation_workflow(self):
        """Test complete report generation workflow."""
        # Create report
        report = Report.objects.create(
            name='Weekly Business Report',
            report_type='weekly',
            schedule_type='weekly',
            schedule_time=time(9, 0),
            output_format='pdf'
        )
        report.metrics.add(self.revenue_metric, self.user_metric)
        
        # Add some metric data
        for i in range(7):
            date_offset = timezone.now() - timedelta(days=i)
            MetricDataPoint.objects.create(
                metric=self.revenue_metric,
                value=Decimal(f'{1000 + i * 100}.00'),
                timestamp=date_offset
            )
            MetricDataPoint.objects.create(
                metric=self.user_metric,
                value=Decimal(f'{50 + i * 5}'),
                timestamp=date_offset
            )
        
        # Simulate report generation
        generation = ReportGeneration.objects.create(
            report=report,
            generated_by=self.user,
            status='processing',
            started_at=timezone.now()
        )
        
        # Simulate completion
        generation.status = 'completed'
        generation.completed_at = timezone.now()
        generation.file_path = f'/reports/weekly_report_{timezone.now().strftime("%Y%m%d")}.pdf'
        generation.file_size = 512000
        generation.save()
        
        # Verify report generation
        self.assertEqual(generation.status, 'completed')
        self.assertIsNotNone(generation.file_path)
        self.assertEqual(generation.file_size, 512000)


class AnalyticsAPITest(APITestCase):
    """Test analytics API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        
        self.category = MetricCategory.objects.create(
            name='api_test',
            display_name='API Test'
        )
        
        self.metric = BusinessMetric.objects.create(
            category=self.category,
            name='api_metric',
            display_name='API Metric',
            metric_type='counter',
            is_featured=True
        )
        
        # Add some data points
        for i in range(5):
            MetricDataPoint.objects.create(
                metric=self.metric,
                value=Decimal(f'{100 + i * 10}'),
                timestamp=timezone.now() - timedelta(days=i)
            )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_metrics(self):
        """Test listing business metrics."""
        url = reverse('analytics:metrics-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'api_metric')
    
    def test_metric_data_points(self):
        """Test getting metric data points."""
        url = reverse('analytics:metric-data', kwargs={'metric_id': self.metric.id})
        response = self.client.get(url, {'days': 7})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data_points']), 5)
    
    def test_dashboard_list(self):
        """Test listing dashboards."""
        Dashboard.objects.create(
            name='API Test Dashboard',
            dashboard_type='custom',
            is_public=True
        )
        
        url = reverse('analytics:dashboards-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_user_activity_tracking(self):
        """Test user activity tracking."""
        url = reverse('analytics:track-activity')
        data = {
            'activity_type': 'page_view',
            'description': 'Viewed braiders listing',
            'metadata': {'page': '/braiders', 'source': 'web'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify activity was recorded
        activity = UserActivity.objects.filter(user=self.user).first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.activity_type, 'page_view')
    
    def test_alerts_list(self):
        """Test listing alerts."""
        Alert.objects.create(
            title='Test Alert',
            alert_type='system_error',
            severity='medium',
            description='Test alert for API'
        )
        
        url = reverse('analytics:alerts-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to analytics endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('analytics:metrics-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)