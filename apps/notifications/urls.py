"""
URL configuration for notifications app.
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Templates
    path('templates/', views.NotificationTemplateListView.as_view(), name='template-list'),
    path('templates/<uuid:pk>/', views.NotificationTemplateDetailView.as_view(), name='template-detail'),
    
    # Channels
    path('channels/', views.NotificationChannelListView.as_view(), name='channel-list'),
    path('channels/<uuid:pk>/', views.NotificationChannelDetailView.as_view(), name='channel-detail'),
    
    # User Preferences
    path('preferences/', views.UserNotificationPreferenceView.as_view(), name='preferences'),
    
    # Categories
    path('categories/', views.NotificationCategoryListView.as_view(), name='category-list'),
    
    # Notifications
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('create/', views.NotificationCreateView.as_view(), name='notification-create'),
    path('<uuid:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('<uuid:notification_id>/read/', views.mark_notification_read, name='notification-read'),
    path('<uuid:notification_id>/click/', views.notification_clicked, name='notification-click'),
    path('<uuid:notification_id>/analytics/', views.notification_analytics, name='notification-analytics'),
    
    # Bulk operations
    path('bulk/create/', views.bulk_create_notifications, name='bulk-create'),
    path('bulk/read/', views.mark_all_notifications_read, name='bulk-read'),
    
    # Batches
    path('batches/', views.NotificationBatchListView.as_view(), name='batch-list'),
    path('batches/<uuid:pk>/', views.NotificationBatchDetailView.as_view(), name='batch-detail'),
    
    # Analytics and stats
    path('stats/', views.notification_stats, name='stats'),
    path('dashboard/', views.dashboard_data, name='dashboard'),
]