"""
URL configuration for upload API endpoints.
"""

from django.urls import path
from . import upload_views

app_name = 'upload'

urlpatterns = [
    # General upload endpoints
    path('general/', upload_views.GeneralFileUploadView.as_view(), name='general_upload'),
    path('profile/', upload_views.ProfileImageUploadView.as_view(), name='profile_upload'),
    path('batch/', upload_views.BatchUploadView.as_view(), name='batch_upload'),
    
    # Braider-specific uploads
    path('portfolio/', upload_views.PortfolioUploadView.as_view(), name='portfolio_upload'),
    path('service/<uuid:service_id>/', upload_views.ServiceImageUploadView.as_view(), name='service_upload'),
    
    # Upload management
    path('status/', upload_views.upload_status_view, name='upload_status'),
    path('delete/<str:file_path>/', upload_views.delete_uploaded_file_view, name='delete_file'),
]