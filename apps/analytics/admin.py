"""
Admin interface for analytics app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    MetricCategory, BusinessMetric, MetricDataPoint, Dashboard,
    DashboardWidget, Report, ReportGeneration, UserActivity,
    SystemPerformance, Alert, CohortAnalysis
)


@admin.register(MetricCategory)
class MetricCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'metrics_count', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['order', 'name']
    
    def metrics_count(self, obj):
        return obj.metrics.filter(is_active=True).count()
    metrics_count.short_description = 'Active Metrics'


class MetricDataPointInline(admin.TabularInline):
    model = MetricDataPoint
    extra = 0
    readonly_fields = ['date', 'hour', 'day_of_week', 'week', 'month', 'year']
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('metric')[:10]


@admin.register(BusinessMetric)
class BusinessMetricAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'category', 'metric_type', 'is_featured', 
        'has_alerts', 'latest_value', 'data_points_count', 'is_active'
    ]
    list_filter = [
        'category', 'metric_type', 'is_featured', 'has_alerts', 
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['latest_value', 'data_points_count']
    inlines = [MetricDataPointInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'display_name', 'description')
        }),
        ('Configuration', {
            'fields': ('metric_type', 'unit', 'aggregation_type', 'format_string')
        }),
        ('Display Options', {
            'fields': ('is_featured', 'is_active')
        }),
        ('Alerts', {
            'fields': ('has_alerts', 'alert_threshold_min', 'alert_threshold_max')
        }),
        ('Statistics', {
            'fields': ('latest_value', 'data_points_count'),
            'classes': ('collapse',)
        })
    )
    
    def latest_value(self, obj):
        latest_point = obj.data_points.first()
        if latest_point:
            return f"{obj.format_value(latest_point.value)} ({latest_point.timestamp.strftime('%Y-%m-%d %H:%M')})"
        return "No data"
    latest_value.short_description = 'Latest Value'
    
    def data_points_count(self, obj):
        return obj.data_points.count()
    data_points_count.short_description = 'Data Points'


@admin.register(MetricDataPoint)
class MetricDataPointAdmin(admin.ModelAdmin):
    list_display = ['metric', 'formatted_value', 'timestamp', 'date']
    list_filter = ['metric', 'date', 'year', 'month']
    search_fields = ['metric__name', 'metric__display_name']
    readonly_fields = ['date', 'hour', 'day_of_week', 'week', 'month', 'year', 'formatted_value']
    ordering = ['-timestamp']
    
    def formatted_value(self, obj):
        return obj.metric.format_value(obj.value)
    formatted_value.short_description = 'Formatted Value'


class DashboardWidgetInline(admin.TabularInline):
    model = DashboardWidget
    extra = 0
    fields = ['title', 'widget_type', 'position_x', 'position_y', 'width', 'height', 'is_active']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'dashboard_type', 'is_public', 'widgets_count', 'is_active', 'created_at']
    list_filter = ['dashboard_type', 'is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['allowed_users']
    inlines = [DashboardWidgetInline]
    
    def widgets_count(self, obj):
        return obj.widgets.filter(is_active=True).count()
    widgets_count.short_description = 'Active Widgets'


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['title', 'dashboard', 'widget_type', 'position_info', 'is_active']
    list_filter = ['dashboard', 'widget_type', 'is_active']
    search_fields = ['title', 'dashboard__name']
    filter_horizontal = ['metrics']
    
    def position_info(self, obj):
        return f"({obj.position_x}, {obj.position_y}) - {obj.width}x{obj.height}"
    position_info.short_description = 'Position & Size'


class ReportGenerationInline(admin.TabularInline):
    model = ReportGeneration
    extra = 0
    readonly_fields = ['status', 'started_at', 'completed_at', 'processing_time', 'file_size', 'download_count']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('generated_by')[:5]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'report_type', 'schedule_type', 'output_format', 
        'last_generated', 'next_scheduled', 'is_active'
    ]
    list_filter = [
        'report_type', 'schedule_type', 'output_format', 
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'description']
    filter_horizontal = ['metrics']
    inlines = [ReportGenerationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'report_type', 'description')
        }),
        ('Content', {
            'fields': ('metrics', 'date_range_start', 'date_range_end', 'filters')
        }),
        ('Scheduling', {
            'fields': (
                'schedule_type', 'schedule_time', 
                'schedule_day_of_week', 'schedule_day_of_month'
            )
        }),
        ('Output', {
            'fields': ('output_format', 'email_recipients')
        }),
        ('Status', {
            'fields': ('is_active', 'last_generated', 'next_scheduled')
        })
    )


@admin.register(ReportGeneration)
class ReportGenerationAdmin(admin.ModelAdmin):
    list_display = [
        'report', 'status', 'generated_by', 'started_at', 
        'completed_at', 'file_size_display', 'download_count'
    ]
    list_filter = ['status', 'report', 'started_at']
    search_fields = ['report__name', 'generated_by__email']
    readonly_fields = [
        'processing_time', 'file_size_display', 'download_link'
    ]
    ordering = ['-created_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = 'File Size'
    
    def download_link(self, obj):
        if obj.file_path and obj.status == 'completed':
            url = reverse('analytics:download-report', args=[obj.id])
            return format_html('<a href="{}" target="_blank">Download</a>', url)
        return "Not available"
    download_link.short_description = 'Download'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'description', 'timestamp', 'session_id']
    list_filter = ['activity_type', 'timestamp', 'user']
    search_fields = ['user__email', 'description', 'session_id']
    readonly_fields = ['timestamp', 'duration']
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SystemPerformance)
class SystemPerformanceAdmin(admin.ModelAdmin):
    list_display = ['performance_type', 'value', 'endpoint', 'status_code', 'timestamp']
    list_filter = ['performance_type', 'status_code', 'timestamp']
    search_fields = ['endpoint', 'method']
    ordering = ['-timestamp']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'alert_type', 'severity_badge', 'status_badge', 
        'metric', 'created_at', 'acknowledged_by'
    ]
    list_filter = [
        'alert_type', 'severity', 'status', 'notification_sent', 
        'created_at', 'acknowledged_at'
    ]
    search_fields = ['title', 'description', 'metric__name']
    readonly_fields = [
        'triggered_value', 'threshold_value', 'acknowledged_at', 
        'resolved_at', 'notification_sent'
    ]
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('title', 'alert_type', 'severity', 'description')
        }),
        ('Metric Details', {
            'fields': ('metric', 'triggered_value', 'threshold_value', 'details')
        }),
        ('Status', {
            'fields': ('status', 'acknowledged_by', 'acknowledged_at', 'resolved_at')
        }),
        ('Notifications', {
            'fields': ('notification_sent', 'notification_channels')
        })
    )
    
    def severity_badge(self, obj):
        colors = {
            'low': '#28a745',
            'medium': '#ffc107', 
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    
    def status_badge(self, obj):
        colors = {
            'active': '#dc3545',
            'acknowledged': '#ffc107',
            'resolved': '#28a745',
            'false_positive': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(CohortAnalysis)
class CohortAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'cohort_period', 'period_number', 'cohort_size', 
        'active_users', 'retention_rate', 'total_revenue'
    ]
    list_filter = ['cohort_period', 'analysis_period']
    ordering = ['cohort_period', 'period_number']
    
    def get_queryset(self, request):
        return super().get_queryset(request)


# Custom Admin Site Configuration
admin.site.site_header = "Tuwi Beauty Analytics"
admin.site.site_title = "Analytics Admin"
admin.site.index_title = "Analytics Management"