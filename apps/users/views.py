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
    View for password reset request - now using 6-digit codes like email verification.
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
            
            # Create password reset code using EmailVerificationService
            from .models import EmailVerification
            
            # Invalidate any existing password reset codes for this user
            EmailVerification.objects.filter(
                user=user,
                email=user.email,
                is_used=False,
                code__isnull=False
            ).update(is_used=True)
            
            # Generate new 6-digit code
            code = EmailVerificationService.generate_verification_code()
            expires_at = timezone.now() + timedelta(minutes=30)  # 30 minutes expiry
            
            # Create verification record for password reset
            verification = EmailVerification.objects.create(
                user=user,
                code=code,
                email=user.email,
                expires_at=expires_at
            )
            
            # Send password reset email with code
            EmailVerificationService.send_password_reset_email(verification)
            
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return Response({
            'message': 'Se o email estiver cadastrado, você receberá um código de verificação para redefinir sua senha.'
        })


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    View for password reset confirmation using 6-digit code.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('newPassword')
        
        if not email or not code or not new_password:
            return Response({
                'error': 'Email, código e nova senha são obrigatórios.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the code manually without marking as used
        try:
            from .models import EmailVerification
            
            # Find the verification record
            verification = EmailVerification.objects.filter(
                email=email,
                code=code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not verification:
                return Response({
                    'error': 'Código inválido ou não encontrado'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if code is expired
            if verification.is_expired():
                return Response({
                    'error': 'Código expirado. Solicite um novo código.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check max attempts
            if verification.attempts >= verification.max_attempts:
                return Response({
                    'error': 'Muitas tentativas. Solicite um novo código.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = verification.user
            
            # Reset password
            user.set_password(new_password)
            user.save()
            
            # Mark the verification code as used
            verification.is_used = True
            verification.save()
            
            return Response({
                'message': 'Senha alterada com sucesso.'
            })
            
        except Exception as e:
            print(f"Error in password reset confirm: {e}")
            return Response({
                'error': 'Erro ao alterar a senha. Tente novamente.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class LogoutView(generics.GenericAPIView):
    """
    View for user logout - blacklists the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Logout realizado com sucesso.'
            })
        except Exception as e:
            return Response({
                'message': 'Logout realizado com sucesso.'
            })  # Always return success for logout