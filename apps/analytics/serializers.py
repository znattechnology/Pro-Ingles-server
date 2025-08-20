"""
Serializers for analytics system.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import (
    MetricCategory, BusinessMetric, MetricDataPoint, Dashboard,
    DashboardWidget, Report, ReportGeneration, UserActivity,
    SystemPerformance, Alert, CohortAnalysis
)

User = get_user_model()


class MetricCategorySerializer(serializers.ModelSerializer):
    """Serializer for metric categories."""
    
    metrics_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MetricCategory
        fields = [
            'id', 'name', 'display_name', 'description', 'icon', 'color',
            'order', 'is_active', 'metrics_count', 'created_at', 'updated_at'
        ]
    
    def get_metrics_count(self, obj):
        """Count active metrics in category."""
        return obj.metrics.filter(is_active=True).count()


class BusinessMetricSerializer(serializers.ModelSerializer):
    """Serializer for business metrics."""
    
    category_name = serializers.CharField(source='category.display_name', read_only=True)
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    latest_value = serializers.SerializerMethodField()
    data_points_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessMetric
        fields = [
            'id', 'name', 'display_name', 'description', 'category', 'category_name',
            'metric_type', 'metric_type_display', 'unit', 'aggregation_type',
            'is_featured', 'is_active', 'format_string', 'has_alerts',
            'alert_threshold_min', 'alert_threshold_max', 'latest_value',
            'data_points_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['latest_value', 'data_points_count']
    
    def get_latest_value(self, obj):
        """Get latest metric value."""
        latest_point = obj.data_points.first()
        if latest_point:
            return {
                'value': float(latest_point.value),
                'formatted_value': obj.format_value(latest_point.value),
                'timestamp': latest_point.timestamp.isoformat()
            }
        return None
    
    def get_data_points_count(self, obj):
        """Count data points for metric."""
        return obj.data_points.count()


class MetricDataPointSerializer(serializers.ModelSerializer):
    """Serializer for metric data points."""
    
    metric_name = serializers.CharField(source='metric.display_name', read_only=True)
    formatted_value = serializers.SerializerMethodField()
    
    class Meta:
        model = MetricDataPoint
        fields = [
            'id', 'metric', 'metric_name', 'value', 'formatted_value',
            'timestamp', 'dimensions', 'date', 'created_at'
        ]
        read_only_fields = ['date', 'hour', 'day_of_week', 'week', 'month', 'year']
    
    def get_formatted_value(self, obj):
        """Get formatted value using metric's format."""
        return obj.metric.format_value(obj.value)


class DashboardSerializer(serializers.ModelSerializer):
    """Serializer for dashboards."""
    
    dashboard_type_display = serializers.CharField(source='get_dashboard_type_display', read_only=True)
    widgets_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'dashboard_type', 'dashboard_type_display',
            'description', 'is_public', 'layout_config', 'refresh_interval',
            'is_active', 'widgets_count', 'created_at', 'updated_at'
        ]
    
    def get_widgets_count(self, obj):
        """Count active widgets in dashboard."""
        return obj.widgets.filter(is_active=True).count()


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for dashboard widgets."""
    
    dashboard_name = serializers.CharField(source='dashboard.name', read_only=True)
    widget_type_display = serializers.CharField(source='get_widget_type_display', read_only=True)
    metrics_list = serializers.StringRelatedField(source='metrics', many=True, read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'dashboard', 'dashboard_name', 'title', 'widget_type',
            'widget_type_display', 'position_x', 'position_y', 'width', 'height',
            'metrics', 'metrics_list', 'filters', 'chart_config',
            'refresh_interval', 'is_active', 'created_at', 'updated_at'
        ]


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for reports."""
    
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    output_format_display = serializers.CharField(source='get_output_format_display', read_only=True)
    metrics_count = serializers.SerializerMethodField()
    last_generation = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'report_type', 'report_type_display', 'description',
            'date_range_start', 'date_range_end', 'filters', 'schedule_type',
            'schedule_type_display', 'schedule_time', 'schedule_day_of_week',
            'schedule_day_of_month', 'output_format', 'output_format_display',
            'email_recipients', 'is_active', 'last_generated', 'next_scheduled',
            'metrics_count', 'last_generation', 'created_at', 'updated_at'
        ]
    
    def get_metrics_count(self, obj):
        """Count metrics in report."""
        return obj.metrics.count()
    
    def get_last_generation(self, obj):
        """Get info about last generation."""
        last_gen = obj.generations.first()
        if last_gen:
            return {
                'id': str(last_gen.id),
                'status': last_gen.status,
                'completed_at': last_gen.completed_at.isoformat() if last_gen.completed_at else None,
                'file_size': last_gen.file_size
            }
        return None


class ReportGenerationSerializer(serializers.ModelSerializer):
    """Serializer for report generations."""
    
    report_name = serializers.CharField(source='report.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportGeneration
        fields = [
            'id', 'report', 'report_name', 'status', 'status_display',
            'generated_by', 'generated_by_name', 'started_at', 'completed_at',
            'processing_time', 'file_size', 'download_count', 'error_message',
            'created_at'
        ]


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_email', 'activity_type', 'activity_type_display',
            'description', 'metadata', 'session_id', 'timestamp', 'duration'
        ]


class SystemPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for system performance metrics."""
    
    performance_type_display = serializers.CharField(source='get_performance_type_display', read_only=True)
    
    class Meta:
        model = SystemPerformance
        fields = [
            'id', 'performance_type', 'performance_type_display', 'value',
            'timestamp', 'endpoint', 'method', 'status_code', 'metadata'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for alerts."""
    
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    metric_name = serializers.CharField(source='metric.display_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'title', 'alert_type', 'alert_type_display', 'severity',
            'severity_display', 'description', 'details', 'metric', 'metric_name',
            'triggered_value', 'threshold_value', 'status', 'status_display',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'resolved_at', 'notification_sent', 'created_at', 'updated_at'
        ]


class CohortAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for cohort analysis data."""
    
    class Meta:
        model = CohortAnalysis
        fields = [
            'id', 'cohort_period', 'analysis_period', 'cohort_size',
            'active_users', 'retention_rate', 'total_revenue',
            'average_revenue_per_user', 'average_bookings',
            'average_session_duration', 'period_number', 'created_at'
        ]


class KPIMetricsSerializer(serializers.Serializer):
    """Serializer for KPI metrics data."""
    
    period = serializers.DictField()
    users = serializers.DictField()
    bookings = serializers.DictField()
    financial = serializers.DictField()
    braiders = serializers.DictField()


class FinancialMetricsSerializer(serializers.Serializer):
    """Serializer for financial metrics data."""
    
    period = serializers.CharField()
    date_range = serializers.DictField()
    totals = serializers.DictField()
    revenue_breakdown = serializers.ListField()
    payment_methods = serializers.ListField()
    daily_trend = serializers.ListField()


class UserBehaviorMetricsSerializer(serializers.Serializer):
    """Serializer for user behavior metrics."""
    
    period_days = serializers.IntegerField()
    engagement = serializers.DictField()
    activity_breakdown = serializers.ListField()
    hourly_activity = serializers.ListField()


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard data."""
    
    key_metrics = serializers.DictField(required=False)
    current_period = serializers.DictField(required=False)
    alerts = serializers.ListField(required=False)
    last_updated = serializers.CharField()


class WidgetDataSerializer(serializers.Serializer):
    """Serializer for widget data."""
    
    id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.CharField()
    position = serializers.DictField()
    data = serializers.DictField()
    config = serializers.DictField()


class MetricDataCreateSerializer(serializers.Serializer):
    """Serializer for creating metric data points."""
    
    metric_name = serializers.CharField()
    value = serializers.DecimalField(max_digits=15, decimal_places=4)
    timestamp = serializers.DateTimeField(required=False)
    dimensions = serializers.DictField(required=False, default=dict)
    
    def validate_metric_name(self, value):
        """Validate metric exists and is active."""
        try:
            BusinessMetric.objects.get(name=value, is_active=True)
            return value
        except BusinessMetric.DoesNotExist:
            raise serializers.ValidationError(f"Metric '{value}' not found or inactive.")


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts."""
    
    notes = serializers.CharField(max_length=1000, required=False)


class ReportGenerateSerializer(serializers.Serializer):
    """Serializer for generating reports."""
    
    format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')],
        default='pdf'
    )
    email_recipients = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True
    )
    custom_filters = serializers.DictField(required=False, default=dict)