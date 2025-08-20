"""
Models for analytics and reporting system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import json

from apps.core.models import BaseModel

User = get_user_model()


class MetricCategory(BaseModel):
    """Categories for organizing metrics."""
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Metric Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name


class BusinessMetric(BaseModel):
    """Core business metrics tracking."""
    
    METRIC_TYPES = [
        ('counter', 'Counter'),
        ('gauge', 'Gauge'),
        ('histogram', 'Histogram'),
        ('percentage', 'Percentage'),
        ('currency', 'Currency'),
        ('duration', 'Duration'),
    ]
    
    AGGREGATION_TYPES = [
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('count', 'Count'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('last', 'Last Value'),
    ]
    
    category = models.ForeignKey(MetricCategory, on_delete=models.CASCADE, related_name='metrics')
    
    # Metric identification
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    
    # Metric configuration
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES, default='counter')
    unit = models.CharField(max_length=20, blank=True, help_text="Unit of measurement (€, %, s, etc.)")
    
    # Calculation settings
    aggregation_type = models.CharField(max_length=20, choices=AGGREGATION_TYPES, default='sum')
    calculation_query = models.TextField(blank=True, help_text="SQL query or calculation logic")
    
    # Display settings
    is_featured = models.BooleanField(default=False, help_text="Show on main dashboard")
    is_active = models.BooleanField(default=True)
    format_string = models.CharField(max_length=50, default='{value}', help_text="Format template for display")
    
    # Alert settings
    has_alerts = models.BooleanField(default=False)
    alert_threshold_min = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    alert_threshold_max = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_featured']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def format_value(self, value):
        """Format metric value for display."""
        try:
            if self.metric_type == 'currency':
                return f"€{value:,.2f}"
            elif self.metric_type == 'percentage':
                return f"{value:.1f}%"
            elif self.metric_type == 'duration':
                # Assume value is in seconds
                if value < 60:
                    return f"{value:.0f}s"
                elif value < 3600:
                    return f"{value/60:.1f}m"
                else:
                    return f"{value/3600:.1f}h"
            else:
                return self.format_string.format(value=value)
        except:
            return str(value)


class MetricDataPoint(BaseModel):
    """Individual metric data points."""
    
    metric = models.ForeignKey(BusinessMetric, on_delete=models.CASCADE, related_name='data_points')
    
    # Value and context
    value = models.DecimalField(max_digits=15, decimal_places=4)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Dimensions for filtering/grouping
    dimensions = models.JSONField(default=dict, help_text="Additional dimensions for filtering")
    
    # Period information
    date = models.DateField()
    hour = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])
    day_of_week = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])
    week = models.PositiveIntegerField()
    month = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric', '-timestamp']),
            models.Index(fields=['metric', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['year', 'month']),
        ]
        unique_together = [['metric', 'timestamp', 'dimensions']]
    
    def save(self, *args, **kwargs):
        """Auto-populate period fields."""
        if not self.date:
            self.date = self.timestamp.date()
        self.hour = self.timestamp.hour
        self.day_of_week = self.timestamp.weekday()
        self.week = self.timestamp.isocalendar()[1]
        self.month = self.timestamp.month
        self.year = self.timestamp.year
        super().save(*args, **kwargs)


class Dashboard(BaseModel):
    """Custom dashboards for different user types."""
    
    DASHBOARD_TYPES = [
        ('executive', 'Executive Dashboard'),
        ('operational', 'Operational Dashboard'),
        ('financial', 'Financial Dashboard'),
        ('user_behavior', 'User Behavior Dashboard'),
        ('braider_performance', 'Braider Performance Dashboard'),
        ('custom', 'Custom Dashboard'),
    ]
    
    name = models.CharField(max_length=100)
    dashboard_type = models.CharField(max_length=20, choices=DASHBOARD_TYPES)
    description = models.TextField(blank=True)
    
    # Access control
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='custom_dashboards')
    allowed_roles = models.JSONField(default=list, help_text="List of allowed user roles")
    
    # Configuration
    layout_config = models.JSONField(default=dict, help_text="Dashboard layout configuration")
    refresh_interval = models.PositiveIntegerField(default=300, help_text="Auto-refresh interval in seconds")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['dashboard_type', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class DashboardWidget(BaseModel):
    """Widgets within dashboards."""
    
    WIDGET_TYPES = [
        ('metric_card', 'Metric Card'),
        ('chart_line', 'Line Chart'),
        ('chart_bar', 'Bar Chart'),
        ('chart_pie', 'Pie Chart'),
        ('chart_area', 'Area Chart'),
        ('table', 'Data Table'),
        ('heatmap', 'Heatmap'),
        ('gauge', 'Gauge'),
        ('progress', 'Progress Bar'),
        ('list', 'List'),
    ]
    
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    
    # Widget identification
    title = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    
    # Layout
    position_x = models.PositiveIntegerField(default=0)
    position_y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=6)
    height = models.PositiveIntegerField(default=4)
    
    # Data configuration
    metrics = models.ManyToManyField(BusinessMetric, related_name='widgets')
    data_query = models.TextField(blank=True, help_text="Custom data query if needed")
    filters = models.JSONField(default=dict, help_text="Filters to apply to data")
    
    # Display configuration
    chart_config = models.JSONField(default=dict, help_text="Chart.js configuration")
    refresh_interval = models.PositiveIntegerField(default=300)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['dashboard', 'position_y', 'position_x']
        indexes = [
            models.Index(fields=['dashboard', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.dashboard.name} - {self.title}"


class Report(BaseModel):
    """Scheduled and generated reports."""
    
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('quarterly', 'Quarterly Report'),
        ('yearly', 'Yearly Report'),
        ('custom', 'Custom Report'),
    ]
    
    REPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    SCHEDULE_TYPES = [
        ('manual', 'Manual'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Content configuration
    metrics = models.ManyToManyField(BusinessMetric, related_name='reports')
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict)
    
    # Scheduling
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES, default='manual')
    schedule_time = models.TimeField(null=True, blank=True)
    schedule_day_of_week = models.PositiveIntegerField(null=True, blank=True)
    schedule_day_of_month = models.PositiveIntegerField(null=True, blank=True)
    
    # Output configuration
    output_format = models.CharField(max_length=10, choices=REPORT_FORMATS, default='pdf')
    email_recipients = models.JSONField(default=list, help_text="Email addresses to send report")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    next_scheduled = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'is_active']),
            models.Index(fields=['next_scheduled']),
        ]
    
    def __str__(self):
        return self.name


class ReportGeneration(BaseModel):
    """Individual report generation instances."""
    
    GENERATION_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='generations')
    
    # Generation details
    status = models.CharField(max_length=20, choices=GENERATION_STATUS, default='pending')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_time = models.DurationField(null=True, blank=True)
    
    # Output
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.report.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class UserActivity(BaseModel):
    """Track user activity for analytics."""
    
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('booking_created', 'Booking Created'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_made', 'Payment Made'),
        ('profile_updated', 'Profile Updated'),
        ('search_performed', 'Search Performed'),
        ('page_view', 'Page View'),
        ('feature_used', 'Feature Used'),
        ('error_occurred', 'Error Occurred'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    
    # Activity details
    description = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, help_text="Additional activity data")
    
    # Context
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timing
    timestamp = models.DateTimeField(default=timezone.now)
    duration = models.DurationField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"


class SystemPerformance(BaseModel):
    """System performance metrics."""
    
    PERFORMANCE_TYPES = [
        ('response_time', 'Response Time'),
        ('error_rate', 'Error Rate'),
        ('throughput', 'Throughput'),
        ('cpu_usage', 'CPU Usage'),
        ('memory_usage', 'Memory Usage'),
        ('db_performance', 'Database Performance'),
        ('cache_hit_rate', 'Cache Hit Rate'),
    ]
    
    performance_type = models.CharField(max_length=30, choices=PERFORMANCE_TYPES)
    
    # Metrics
    value = models.DecimalField(max_digits=15, decimal_places=4)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Context
    endpoint = models.CharField(max_length=200, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['performance_type', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['endpoint', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_performance_type_display()} - {self.value}"


class Alert(BaseModel):
    """System alerts based on metrics."""
    
    ALERT_TYPES = [
        ('metric_threshold', 'Metric Threshold'),
        ('system_error', 'System Error'),
        ('performance_issue', 'Performance Issue'),
        ('business_anomaly', 'Business Anomaly'),
        ('security_concern', 'Security Concern'),
    ]
    
    ALERT_SEVERITY = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    ALERT_STATUS = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    
    # Alert identification
    title = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=ALERT_SEVERITY)
    
    # Content
    description = models.TextField()
    details = models.JSONField(default=dict)
    
    # Related objects
    metric = models.ForeignKey(BusinessMetric, on_delete=models.SET_NULL, null=True, blank=True)
    triggered_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='active')
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notifications
    notification_sent = models.BooleanField(default=False)
    notification_channels = models.JSONField(default=list, help_text="Channels where notification was sent")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['alert_type']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"
    
    def acknowledge(self, user):
        """Acknowledge the alert."""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at'])
    
    def resolve(self):
        """Mark alert as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])


class CohortAnalysis(BaseModel):
    """User cohort analysis data."""
    
    cohort_period = models.DateField(help_text="Period when cohort was created")
    analysis_period = models.DateField(help_text="Period being analyzed")
    
    # Cohort metrics
    cohort_size = models.PositiveIntegerField(help_text="Total users in cohort")
    active_users = models.PositiveIntegerField(help_text="Active users in analysis period")
    retention_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Retention rate percentage")
    
    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    average_revenue_per_user = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Behavioral metrics
    average_bookings = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    average_session_duration = models.DurationField(null=True, blank=True)
    
    # Period information
    period_number = models.PositiveIntegerField(help_text="Period number since cohort creation")
    
    class Meta:
        ordering = ['cohort_period', 'period_number']
        unique_together = [['cohort_period', 'analysis_period']]
        indexes = [
            models.Index(fields=['cohort_period']),
            models.Index(fields=['analysis_period']),
        ]
    
    def __str__(self):
        return f"Cohort {self.cohort_period} - Period {self.period_number}"