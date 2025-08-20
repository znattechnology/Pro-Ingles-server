"""
URL configuration for users app.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh-token/', TokenRefreshView.as_view(), name='refresh_token'),
    
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.PasswordChangeView.as_view(), name='change_password'),
    
    # Addresses
    path('addresses/', views.UserAddressListCreateView.as_view(), name='address_list'),
    path('addresses/<uuid:pk>/', views.UserAddressDetailView.as_view(), name='address_detail'),
    
    # Notification settings
    path('notification-settings/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    
    # Password reset
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Email verification
    path('verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    
    # Google OAuth
    path('oauth/google/url/', views.GoogleOAuthURLView.as_view(), name='google_oauth_url'),
    path('oauth/google/login/', views.GoogleOAuthLoginView.as_view(), name='google_oauth_login'),
]