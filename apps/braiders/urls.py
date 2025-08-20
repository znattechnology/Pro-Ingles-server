"""
URL configuration for braiders app.
"""

from django.urls import path

from . import views

app_name = 'braiders'

urlpatterns = [
    # Public braider endpoints
    path('', views.BraiderListView.as_view(), name='braider_list'),
    path('<uuid:id>/', views.BraiderDetailView.as_view(), name='braider_detail'),
    path('stats/', views.braider_stats_view, name='braider_stats'),
    path('featured/', views.featured_braiders_view, name='featured_braiders'),
    
    # Braider registration and profile management
    path('register/', views.BraiderRegistrationView.as_view(), name='braider_register'),
    path('profile/', views.BraiderProfileView.as_view(), name='braider_profile'),
    path('dashboard/', views.braider_dashboard_view, name='braider_dashboard'),
    
    # Portfolio management
    path('portfolio/', views.BraiderPortfolioView.as_view(), name='portfolio_list'),
    path('portfolio/<uuid:id>/', views.BraiderPortfolioDetailView.as_view(), name='portfolio_detail'),
    
    # Service management (for braiders)
    path('services/', views.BraiderServiceListCreateView.as_view(), name='braider_services'),
    path('services/<uuid:id>/', views.BraiderServiceDetailView.as_view(), name='braider_service_detail'),
    path('services/<uuid:service_id>/images/', views.ServiceImageView.as_view(), name='service_images'),
    path('services/images/<uuid:id>/', views.ServiceImageDetailView.as_view(), name='service_image_detail'),
    
    # Admin endpoints
    path('admin/approve/<uuid:id>/', views.BraiderApprovalView.as_view(), name='braider_approval'),
]

# Service-specific URLs (public)
service_urlpatterns = [
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/<uuid:id>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('services/popular/', views.popular_services_view, name='popular_services'),
]

urlpatterns += service_urlpatterns