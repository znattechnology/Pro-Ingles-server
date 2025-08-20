"""
Views for user authentication and profile management.
"""

import secrets
from datetime import datetime, timedelta
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from .models import User, UserAddress, NotificationSettings, EmailVerification
from .serializers import (
    UserRegistrationSerializer, CustomTokenObtainPairSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    UserAddressSerializer, NotificationSettingsSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerificationSerializer, GoogleOAuthSerializer,
    GoogleOAuthURLSerializer
)
from .services import GoogleOAuthService
from .email_service import EmailVerificationService


class UserRegistrationView(generics.CreateAPIView):
    """
    View for user registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # User starts with email_verified = False (default)
        # Create and send verification code
        verification = EmailVerificationService.create_verification_code(user)
        EmailVerificationService.send_verification_email(verification)
        
        # Do NOT generate JWT tokens - user must verify email first
        
        return Response({
            'message': 'Usuário registrado com sucesso. Verifique seu email para ativar a conta.',
            'email': user.email,
            'requires_verification': True
        }, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user):
        """
        Send email verification email.
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}/"
        
        subject = 'Verify your Tuwi account'
        message = f"""
        Welcome to Tuwi!
        
        Please click the link below to verify your email address:
        {verification_url}
        
        If you didn't create this account, please ignore this email.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user data.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View for user profile management.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """
    View for password change.
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Password changed successfully.'
        })


class UserAddressListCreateView(generics.ListCreateAPIView):
    """
    View for listing and creating user addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)


class UserAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for managing individual user addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)


class NotificationSettingsView(generics.RetrieveUpdateAPIView):
    """
    View for notification settings management.
    """
    serializer_class = NotificationSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user
        )
        return settings


class PasswordResetRequestView(generics.GenericAPIView):
    """
    View for password reset request.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(
                email=serializer.validated_data['email'],
                is_active=True
            )
            
            # Generate password reset token
            user.reset_password_token = secrets.token_urlsafe(32)
            user.reset_password_expires = timezone.now() + timedelta(hours=24)
            user.save()
            
            # Send password reset email
            self.send_password_reset_email(user)
            
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return Response({
            'message': 'If your email is registered, you will receive password reset instructions.'
        })
    
    def send_password_reset_email(self, user):
        """
        Send password reset email.
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{user.reset_password_token}/"
        
        subject = 'Reset your Tuwi password'
        message = f"""
        Hello {user.name},
        
        You requested to reset your password. Click the link below to create a new password:
        {reset_url}
        
        This link will expire in 24 hours.
        
        If you didn't request this, please ignore this email.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    View for password reset confirmation.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(
                reset_password_token=serializer.validated_data['token'],
                reset_password_expires__gt=timezone.now(),
                is_active=True
            )
            
            # Reset password
            user.set_password(serializer.validated_data['new_password'])
            user.reset_password_token = ''
            user.reset_password_expires = None
            user.save()
            
            return Response({
                'message': 'Password reset successfully.'
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid or expired reset token.'
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationView(generics.GenericAPIView):
    """
    View for email verification with 6-digit code.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({
                'error': 'Email e código são obrigatórios.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the code
        result = EmailVerificationService.verify_code(email, code)
        
        if result['success']:
            # Generate JWT tokens for the user
            from rest_framework_simplejwt.tokens import RefreshToken
            user = result['user']
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            # Send welcome email
            try:
                EmailVerificationService.send_welcome_email(user)
            except Exception as e:
                # Don't fail the verification if welcome email fails
                print(f"Failed to send welcome email: {e}")
            
            return Response({
                'message': 'Email verificado com sucesso! Bem-vindo(a) ao Tuwi!',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'avatar': user.avatar.url if user.avatar else None,
                    'email_verified': user.email_verified,
                },
                'access': str(access),
                'refresh': str(refresh),
            })
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_verification_email(request):
    """
    Resend email verification code.
    """
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email é obrigatório.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Resend verification code
    result = EmailVerificationService.resend_verification_code(email)
    
    if result['success']:
        return Response({
            'message': 'Novo código enviado para seu email!'
        })
    else:
        return Response({
            'error': result['error']
        }, status=status.HTTP_400_BAD_REQUEST)


class GoogleOAuthURLView(generics.GenericAPIView):
    """
    Generate Google OAuth authorization URL.
    """
    serializer_class = GoogleOAuthURLSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        oauth_service = GoogleOAuthService()
        
        try:
            auth_url = oauth_service.generate_auth_url(
                state=serializer.validated_data.get('state'),
                redirect_uri=serializer.validated_data.get('redirect_uri')
            )
            
            return Response({
                'auth_url': auth_url
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to generate OAuth URL: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class GoogleOAuthLoginView(generics.GenericAPIView):
    """
    Authenticate user with Google OAuth.
    """
    serializer_class = GoogleOAuthSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        oauth_service = GoogleOAuthService()
        
        try:
            # Authenticate user using OAuth service
            user, tokens = oauth_service.authenticate_user(**serializer.validated_data)
            
            # Update last login
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])
            
            # Return user data and tokens
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'avatar': user.avatar.url if user.avatar else None,
                    'email_verified': user.email_verified,
                    'google_id': user.google_id,
                },
                'tokens': tokens
            })
            
        except Exception as e:
            return Response({
                'error': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)