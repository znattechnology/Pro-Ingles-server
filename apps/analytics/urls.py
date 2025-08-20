"""
URL configuration for analytics app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'analytics'

# API Routes
urlpatterns = [
    # Metric Categories
    path('categories/', views.MetricCategoryListView.as_view(), name='category-list'),
    path('categories/<uuid:pk>/', views.MetricCategoryDetailView.as_view(), name='category-detail'),
    
    # Business Metrics
    path('metrics/', views.BusinessMetricListView.as_view(), name='metric-list'),
    path('metrics/<uuid:pk>/', views.BusinessMetricDetailView.as_view(), name='metric-detail'),
    
    # Metric Data Points
    path('metrics/<uuid:metric_id>/data/', views.MetricDataPointListView.as_view(), name='metric-data-list'),
    path('metric-data/', views.MetricDataPointListView.as_view(), name='all-metric-data'),
    path('metric-data/store/', views.store_metric_data, name='store-metric-data'),
    
    # Dashboards
    path('dashboards/', views.DashboardListView.as_view(), name='dashboard-list'),
    path('dashboards/<uuid:pk>/', views.DashboardDetailView.as_view(), name='dashboard-detail'),
    path('dashboards/<uuid:dashboard_id>/widgets/', views.dashboard_widgets, name='dashboard-widgets'),
    
    # Reports
    path('reports/', views.ReportListView.as_view(), name='report-list'),
    path('reports/<uuid:pk>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('reports/<uuid:report_id>/generate/', views.generate_report_view, name='generate-report'),
    path('reports/<uuid:report_id>/generations/', views.ReportGenerationListView.as_view(), name='report-generations'),
    
    # Report Downloads
    path('report-generations/<uuid:generation_id>/download/', views.download_report, name='download-report'),
    path('executive-summary/export/', views.export_executive_summary, name='export-executive-summary'),
    
    # Alerts
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/<uuid:pk>/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<uuid:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge-alert'),
    path('alerts/<uuid:alert_id>/resolve/', views.resolve_alert, name='resolve-alert'),
    
    # Analytics API Endpoints
    path('kpi-metrics/', views.kpi_metrics, name='kpi-metrics'),
    path('financial-metrics/', views.financial_metrics, name='financial-metrics'),
    path('user-behavior-metrics/', views.user_behavior_metrics, name='user-behavior-metrics'),
    
    # Dashboard Data
    path('executive-dashboard/', views.executive_dashboard, name='executive-dashboard'),
    path('financial-dashboard/', views.financial_dashboard, name='financial-dashboard'),
    
    # Real-time Metrics
    path('real-time-metrics/', views.real_time_metrics, name='real-time-metrics'),
    
    # User Activity Tracking
    path('activity/track/', views.track_user_activity, name='track-activity'),
    path('analytics-summary/', views.analytics_summary, name='analytics-summary'),
]