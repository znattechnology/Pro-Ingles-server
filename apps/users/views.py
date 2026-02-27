"""
Views for user authentication and profile management.
"""

import secrets
import uuid
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
from django.db import models
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

# S3 imports for avatar upload
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

from rest_framework.throttling import UserRateThrottle
from apps.cms.views import AdminWritePermissionMixin
from .models import User, UserAddress, NotificationSettings, EmailVerification


# ============================================================
# Custom Permission Classes for Feedback System
# ============================================================

class IsAdminUser(permissions.BasePermission):
    """
    Permission class that checks if the user is an admin.
    More robust than checking request.user.role directly.
    """
    message = "Acesso negado. Privilégios de administrador necessários."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check multiple ways to determine admin status
        return (
            getattr(request.user, 'role', None) == 'admin' or
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'is_superuser', False)
        )


class FeedbackSubmitThrottle(UserRateThrottle):
    """Rate limiting for feedback submissions - 10 per hour per user"""
    rate = '10/hour'


class FeedbackDismissThrottle(UserRateThrottle):
    """Rate limiting for feedback dismissals - 20 per hour per user"""
    rate = '20/hour'
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


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
class UserRegistrationView(generics.CreateAPIView):
    """
    View for user registration with rate limiting (5 registrations per minute per IP).
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
        try:
            verification = EmailVerificationService.create_verification_code(user)
            email_sent = EmailVerificationService.send_verification_email(verification)
            print(f"DEBUG: Email verification created for {user.email}, code: {verification.code}")
            print(f"DEBUG: Email verification sent to {user.email}: {email_sent}")
            if not email_sent:
                print(f"ERROR: Failed to send verification email to {user.email}")
        except Exception as e:
            print(f"ERROR: Exception sending verification email to {user.email}: {e}")
            import traceback
            traceback.print_exc()
            # Continue with registration even if email fails
        
        # Do NOT generate JWT tokens - user must verify email first
        
        return Response({
            'message': 'Utilizador registado com sucesso. Verifique o seu email para ativar a conta.',
            'email': user.email,
            'requires_verification': True
        }, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user):
        """
        Send email verification email.
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}/"
        
        subject = 'Verify your ProEnglish account'
        message = f"""
        Welcome to ProEnglish!
        
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


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user data and rate limiting (10 attempts per minute per IP).
    Sets HttpOnly cookies for cross-domain authentication.
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Get tokens from response data
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            # Cookie settings for cross-domain authentication
            # SameSite=None requires Secure=True (HTTPS)
            is_secure = not settings.DEBUG
            samesite = 'None' if is_secure else 'Lax'

            # Set access token cookie (short-lived)
            if access_token:
                response.set_cookie(
                    key='access_token',
                    value=access_token,
                    max_age=60 * 60,  # 1 hour
                    httponly=True,
                    secure=is_secure,
                    samesite=samesite,
                    path='/',
                )

            # Set refresh token cookie (long-lived)
            if refresh_token:
                response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    max_age=60 * 60 * 24 * 7,  # 7 days
                    httponly=True,
                    secure=is_secure,
                    samesite=samesite,
                    path='/',
                )

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT token refresh view that sets HttpOnly cookies.
    Also supports reading refresh token from cookie if not in request body.
    """

    def post(self, request, *args, **kwargs):
        # If refresh token not in body, try to get from cookie
        if 'refresh' not in request.data and request.COOKIES.get('refresh_token'):
            request._full_data = request.data.copy()
            request._full_data['refresh'] = request.COOKIES.get('refresh_token')

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')

            # Cookie settings for cross-domain authentication
            is_secure = not settings.DEBUG
            samesite = 'None' if is_secure else 'Lax'

            # Set new access token cookie
            if access_token:
                response.set_cookie(
                    key='access_token',
                    value=access_token,
                    max_age=60 * 60,  # 1 hour
                    httponly=True,
                    secure=is_secure,
                    samesite=samesite,
                    path='/',
                )

        return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View for user profile management.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        """Override update to add detailed logging for avatar uploads."""
        print("\n" + "="*80)
        print("📸 USER PROFILE UPDATE REQUEST")
        print("="*80)
        print(f"Method: {request.method}")
        print(f"User: {request.user.email}")
        print(f"Content-Type: {request.content_type}")
        print(f"Request DATA keys: {request.data.keys()}")
        print(f"Request FILES keys: {request.FILES.keys()}")

        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            print(f"\n✅ Avatar file detected:")
            print(f"  - Name: {avatar_file.name}")
            print(f"  - Size: {avatar_file.size} bytes")
            print(f"  - Content-Type: {avatar_file.content_type}")
        else:
            print("\n❌ No avatar file in request.FILES")

        if 'avatar' in request.data:
            print(f"✅ Avatar in request.data: {type(request.data['avatar'])}")

        print("="*80 + "\n")

        return super().update(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def get_avatar_upload_url(request):
    """
    Generate presigned URL for user avatar upload to S3.

    POST /api/v1/users/get-avatar-upload-url/

    Request body:
    {
        "fileName": "profile.jpg",
        "fileType": "image/jpeg"
    }

    Response:
    {
        "message": "URL de upload de avatar gerado com sucesso",
        "data": {
            "uploadUrl": "https://s3.amazonaws.com/...",
            "avatarUrl": "https://cloudfront.net/avatars/..."
        }
    }
    """
    print(f"🖼️ Avatar upload URL request for user: {request.user.email}")

    fileName = request.data.get('fileName')
    fileType = request.data.get('fileType')

    if not fileName or not fileType:
        return Response({
            'message': 'O nome e o tipo do ficheiro são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate image file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if fileType not in allowed_types:
        return Response({
            'message': 'Tipo de arquivo não suportado. Use JPG, PNG ou WebP.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        if not S3_AVAILABLE:
            return Response({
                'error': 'Biblioteca boto3 não instalada'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            return Response({
                'error': 'Configuração S3 incompleta'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # Generate unique filename and S3 key
        file_extension = fileName.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        s3_key = f'avatars/{request.user.id}/{unique_filename}'

        print(f"📁 Generating presigned URL for: {s3_key}")

        # Generate presigned URL for PUT operation
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': fileType,
                'CacheControl': 'max-age=86400'
            },
            ExpiresIn=3600  # 1 hour expiration
        )

        # Generate final avatar URL (using CloudFront if available)
        if getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', ''):
            avatar_url = f"{settings.AWS_CLOUDFRONT_DOMAIN}/avatars/{request.user.id}/{unique_filename}"
        else:
            avatar_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/avatars/{request.user.id}/{unique_filename}"

        print(f"✅ Presigned URL generated successfully")
        print(f"📸 Avatar URL: {avatar_url}")

        return Response({
            'message': 'URL de upload de avatar gerado com sucesso',
            'data': {
                'uploadUrl': upload_url,
                'avatarUrl': avatar_url
            }
        })

    except ClientError as e:
        print(f"❌ S3 Error: {str(e)}")
        return Response({
            'error': f'Erro S3: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return Response({
            'error': f'Erro inesperado: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        return UserAddress.objects.filter(user=self.request.user).order_by('address_type', '-is_default', 'created_at')


class UserAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for managing individual user addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user).order_by('address_type', '-is_default', 'created_at')


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


@method_decorator(ratelimit(key='ip', rate='3/m', method='POST', block=True), name='post')
class PasswordResetRequestView(generics.GenericAPIView):
    """
    View for password reset request with rate limiting (3 requests per minute per IP).
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


@method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='post')
class EmailVerificationView(generics.GenericAPIView):
    """
    View for email verification with 6-digit code and rate limiting (10 attempts per minute per IP).
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
                'message': 'Email verificado com sucesso! Bem-vindo(a) ao ProEnglish!',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'avatar': user.avatar or None,
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

    def get(self, request):
        """Handle GET request for OAuth URL generation."""
        return self._generate_auth_url(request)

    def post(self, request):
        """Handle POST request for OAuth URL generation."""
        return self._generate_auth_url(request)

    def _generate_auth_url(self, request):
        """Generate the OAuth URL."""
        oauth_service = GoogleOAuthService()

        try:
            auth_url = oauth_service.generate_auth_url(
                state=request.data.get('state') or request.query_params.get('state'),
                redirect_uri=request.data.get('redirect_uri') or request.query_params.get('redirect_uri')
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

            # Build response
            response = Response({
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'role': user.role,
                    'avatar': user.avatar if user.avatar else None,
                    'email_verified': user.email_verified,
                    'google_id': user.google_id,
                },
                'tokens': tokens
            })

            # Set HttpOnly cookies for cross-domain authentication
            is_secure = not settings.DEBUG
            samesite = 'None' if is_secure else 'Lax'

            response.set_cookie(
                key='access_token',
                value=tokens['access'],
                max_age=60 * 60,  # 1 hour
                httponly=True,
                secure=is_secure,
                samesite=samesite,
                path='/',
            )

            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                max_age=60 * 60 * 24 * 7,  # 7 days
                httponly=True,
                secure=is_secure,
                samesite=samesite,
                path='/',
            )

            return response

        except Exception as e:
            return Response({
                'error': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(generics.GenericAPIView):
    """
    View for user logout - blacklists the refresh token and clears HttpOnly cookies.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Try to get refresh token from request body or cookie
            refresh_token = request.data.get("refresh_token") or request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Create response and clear HttpOnly cookies
            response = Response({
                'message': 'Logout realizado com sucesso.'
            })

            # Clear cookies with same settings used to set them
            is_secure = not settings.DEBUG
            samesite = 'None' if is_secure else 'Lax'

            response.delete_cookie(
                key='access_token',
                path='/',
                samesite=samesite,
            )
            response.delete_cookie(
                key='refresh_token',
                path='/',
                samesite=samesite,
            )

            return response
        except Exception as e:
            # Still clear cookies even on error
            response = Response({
                'message': 'Logout realizado com sucesso.'
            })
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('refresh_token', path='/')
            return response


class AdminUsersListView(generics.ListAPIView):
    """
    Admin view to list all users with pagination and filtering.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        search = request.query_params.get('search', '')
        role = request.query_params.get('role', '')
        status_filter = request.query_params.get('status', '')  # active, inactive, all
        
        # Base queryset
        queryset = User.objects.all().order_by('-date_joined')
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        if role and role != 'all':
            queryset = queryset.filter(role=role)
        
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Calculate pagination
        total = queryset.count()
        start = (page - 1) * limit
        end = start + limit
        users_page = queryset[start:end]
        
        # Serialize users
        users_data = []
        for user in users_page:
            users_data.append({
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'phone': user.phone or '',
                'role': user.role,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'avatar': user.avatar or None,
            })
        
        # Calculate stats for dashboard
        stats = {
            'total_users': total,
            'active_users': queryset.filter(is_active=True).count(),
            'student_users': queryset.filter(role='student').count(),
            'teacher_users': queryset.filter(role='teacher').count(),
            'admin_users': queryset.filter(role='admin').count(),
            'verified_users': queryset.filter(email_verified=True).count(),
        }
        
        return Response({
            'users': users_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': (total + limit - 1) // limit,
                'has_next': end < total,
                'has_prev': page > 1
            },
            'stats': stats
        })


class AdminUserDetailView(generics.RetrieveAPIView):
    """
    Admin view to get user details by ID.
    """
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get(self, request, *args, **kwargs):
        # Check if user is admin
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = self.get_object()
            
            user_data = {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'phone': user.phone or '',
                'role': user.role,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'avatar': user.avatar or None,
                'google_id': user.google_id if hasattr(user, 'google_id') else None,
            }
            
            return Response({'user': user_data})
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserUpdateView(generics.UpdateAPIView):
    """
    Admin view to update user basic information.
    """
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is admin for all HTTP methods
        if request.user.is_authenticated and request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        # Return 403 for non-admin users instead of 405
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        # This endpoint doesn't support GET, but we want 403 not 405 for non-admins
        return Response({
            'error': 'Method not allowed.'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def patch(self, request, *args, **kwargs):
        
        try:
            user = self.get_object()
            
            # Get update data
            name = request.data.get('name')
            email = request.data.get('email')
            phone = request.data.get('phone')
            
            # Validate required fields
            if not name or not name.strip():
                return Response({
                    'error': 'Name is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not email or not email.strip():
                return Response({
                    'error': 'Email is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if email is already taken by another user
            if email != user.email:
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return Response({
                        'error': 'This email is already registered by another user.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update user data
            user.name = name.strip()
            user.email = email.strip()
            user.phone = phone.strip() if phone else None
            user.save()
            
            # Return updated user data
            user_data = {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'phone': user.phone or '',
                'role': user.role,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'avatar': user.avatar or None,
            }
            
            return Response({
                'message': 'User updated successfully.',
                'user': user_data
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserRoleUpdateView(generics.UpdateAPIView):
    """
    Admin view to update user role.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is admin for all HTTP methods
        if request.user.is_authenticated and request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        # Return 403 for non-admin users instead of 405
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        # This endpoint doesn't support GET, but we want 403 not 405 for non-admins
        return Response({
            'error': 'Method not allowed.'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def patch(self, request, *args, **kwargs):
        
        try:
            user = self.get_object()
            new_role = request.data.get('role')
            
            # Validate role
            valid_roles = ['student', 'teacher', 'admin']
            if not new_role or new_role not in valid_roles:
                return Response({
                    'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prevent admin from changing their own role
            if user.id == request.user.id:
                return Response({
                    'error': 'You cannot change your own role.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update role
            old_role = user.role
            user.role = new_role
            user.save()
            
            return Response({
                'message': f'User role updated from {old_role} to {new_role}.',
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                }
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserToggleStatusView(generics.UpdateAPIView):
    """
    Admin view to toggle user active status.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is admin for all HTTP methods
        if request.user.is_authenticated and request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        # Return 403 for non-admin users instead of 405
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        # This endpoint doesn't support GET, but we want 403 not 405 for non-admins
        return Response({
            'error': 'Method not allowed.'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def patch(self, request, *args, **kwargs):
        
        try:
            user = self.get_object()
            
            # Prevent admin from deactivating themselves
            if user.id == request.user.id:
                return Response({
                    'error': 'You cannot deactivate your own account.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Toggle status
            old_status = user.is_active
            user.is_active = not user.is_active
            user.save()
            
            action = 'activated' if user.is_active else 'deactivated'
            
            return Response({
                'message': f'User {action} successfully.',
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                }
            })
            
        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserDeleteView(generics.DestroyAPIView):
    """
    Admin view to delete user with cascade handling.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is admin for all HTTP methods
        if request.user.is_authenticated and request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        # Return 403 for non-admin users instead of 405
        if request.user.role != 'admin':
            return Response({
                'error': 'Access denied. Admin privileges required.'
            }, status=status.HTTP_403_FORBIDDEN)
        # This endpoint doesn't support GET, but we want 403 not 405 for non-admins
        return Response({
            'error': 'Method not allowed.'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def delete(self, request, *args, **kwargs):

        try:
            user = self.get_object()

            # Prevent admin from deleting themselves
            if user.id == request.user.id:
                return Response({
                    'error': 'You cannot delete your own account.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Store user info for response
            user_info = {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'role': user.role,
            }

            # Delete user (will cascade to related objects)
            user.delete()

            return Response({
                'message': f'User {user_info["name"]} deleted successfully.',
                'user_info': user_info
            })

        except User.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# FEEDBACK VIEWS
# ============================================================================

class FeedbackStatusView(generics.GenericAPIView):
    """
    Check if user should see a feedback prompt.

    GET /api/users/feedback/status/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import UserEngagementMetrics
        from .serializers import FeedbackStatusSerializer

        # Get or create engagement metrics
        metrics, created = UserEngagementMetrics.objects.get_or_create(
            user=request.user
        )

        should_show, trigger = metrics.should_show_feedback_prompt()

        data = {
            'should_show_prompt': should_show,
            'trigger': trigger,
            'last_feedback_at': metrics.last_feedback_at,
            'total_feedbacks_given': metrics.total_feedbacks_given,
            'engagement_summary': {
                'lessons_completed': metrics.total_lessons_completed,
                'courses_completed': metrics.total_courses_completed,
                'ai_sessions': metrics.total_ai_sessions,
                'days_active': metrics.total_days_active,
                'current_streak': metrics.current_streak,
            }
        }

        return Response(FeedbackStatusSerializer(data).data)


class SubmitFeedbackView(generics.CreateAPIView):
    """
    Submit user feedback.

    POST /api/users/feedback/submit/
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [FeedbackSubmitThrottle]

    def post(self, request):
        from .models import UserFeedback, UserEngagementMetrics, FeedbackPromptLog
        from .serializers import SubmitFeedbackSerializer, UserFeedbackSerializer
        from django.utils import timezone

        serializer = SubmitFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create feedback
        feedback = UserFeedback.objects.create(
            user=request.user,
            **serializer.validated_data
        )

        # Update engagement metrics
        metrics, _ = UserEngagementMetrics.objects.get_or_create(
            user=request.user
        )
        metrics.total_feedbacks_given += 1
        metrics.last_feedback_at = timezone.now()
        metrics.save()

        # Log the feedback completion if there was a prompt
        trigger = serializer.validated_data.get('trigger', 'manual')
        if trigger != 'manual':
            FeedbackPromptLog.objects.create(
                user=request.user,
                trigger=trigger,
                status='completed',
                feedback=feedback,
                context_data=serializer.validated_data.get('context_data', {})
            )

        return Response({
            'message': 'Thank you for your feedback!',
            'feedback': UserFeedbackSerializer(feedback).data
        }, status=status.HTTP_201_CREATED)


class DismissFeedbackPromptView(generics.GenericAPIView):
    """
    Dismiss a feedback prompt without submitting feedback.

    POST /api/users/feedback/dismiss/
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [FeedbackDismissThrottle]

    def post(self, request):
        from .models import UserEngagementMetrics, FeedbackPromptLog
        from django.utils import timezone
        import json

        trigger = request.data.get('trigger', 'prompt')
        action = request.data.get('action', 'dismissed')  # 'dismissed' or 'skipped'

        # Validate action
        if action not in ('dismissed', 'skipped'):
            action = 'dismissed'

        # Validate and limit context_data size
        context_data = request.data.get('context_data', {})
        if not isinstance(context_data, dict):
            context_data = {}
        # Limit context_data to 10KB
        try:
            if len(json.dumps(context_data)) > 10240:
                context_data = {'error': 'context_data too large'}
        except (TypeError, ValueError):
            context_data = {}

        # Update last prompt time
        metrics, _ = UserEngagementMetrics.objects.get_or_create(
            user=request.user
        )
        metrics.last_prompt_at = timezone.now()
        metrics.save()

        # Log the dismissal
        FeedbackPromptLog.objects.create(
            user=request.user,
            trigger=trigger,
            status=action,
            context_data=context_data
        )

        return Response({
            'message': 'Feedback prompt dismissed.',
            'next_prompt_available_in': '3 days'
        })


class UserFeedbackListView(generics.ListAPIView):
    """
    List user's own feedback submissions.

    GET /api/users/feedback/my-feedback/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import UserFeedback
        from .serializers import UserFeedbackSerializer

        feedbacks = UserFeedback.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]

        return Response({
            'count': feedbacks.count(),
            'feedbacks': UserFeedbackSerializer(feedbacks, many=True).data
        })


class AdminFeedbackListView(generics.ListAPIView):
    """
    Admin view to list all feedbacks with filters.

    GET /api/users/feedback/admin/list/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import UserFeedback
        from .serializers import UserFeedbackSerializer

        queryset = UserFeedback.objects.all().select_related('user').order_by('-created_at')

        # Apply filters
        feedback_type = request.query_params.get('type')
        if feedback_type:
            queryset = queryset.filter(feedback_type=feedback_type)

        rating = request.query_params.get('rating')
        if rating:
            queryset = queryset.filter(rating=int(rating))

        allow_public = request.query_params.get('allow_public')
        if allow_public:
            queryset = queryset.filter(allow_public=allow_public.lower() == 'true')

        is_reviewed = request.query_params.get('is_reviewed')
        if is_reviewed:
            queryset = queryset.filter(is_reviewed=is_reviewed.lower() == 'true')

        # Pagination
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        total = queryset.count()
        feedbacks = queryset[offset:offset + limit]

        return Response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'feedbacks': UserFeedbackSerializer(feedbacks, many=True).data
        })


class PublicTestimonialsView(generics.ListAPIView):
    """
    Get public testimonials for landing page.

    GET /api/users/feedback/testimonials/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from .models import UserFeedback

        # Get feedbacks that users allowed to be public
        # Ensure rating is not null and comment exists
        feedbacks = UserFeedback.objects.filter(
            allow_public=True,
            rating__gte=4,  # Only good ratings (4 or 5)
            rating__isnull=False,  # Ensure rating exists
            comment__isnull=False
        ).exclude(
            comment=''
        ).select_related('user').order_by('-created_at')[:10]

        # Return anonymized data
        testimonials = []
        for feedback in feedbacks:
            name = getattr(feedback.user, 'name', '') or ''
            name = name.strip()

            # Anonymize name safely: "João Silva" -> "João S."
            if not name:
                anon_name = "Utilizador"
            else:
                parts = name.split()
                if len(parts) > 1:
                    anon_name = f"{parts[0]} {parts[-1][0]}."
                elif len(parts) == 1 and len(parts[0]) > 0:
                    anon_name = f"{parts[0][0]}."
                else:
                    anon_name = "Utilizador"

            # Don't expose internal UUID - use sequential index instead
            testimonials.append({
                'id': len(testimonials) + 1,  # Sequential ID instead of UUID
                'name': anon_name,
                'rating': feedback.rating,
                'comment': feedback.comment,
                'feedback_type': feedback.feedback_type,
                'created_at': feedback.created_at
            })

        return Response({
            'count': len(testimonials),
            'testimonials': testimonials
        })


class AdminFeedbackUpdateView(generics.UpdateAPIView):
    """
    Admin view to update feedback (mark as reviewed, add admin notes).

    PATCH /api/users/feedback/admin/<uuid:id>/

    Note: Admin can only REMOVE allow_public (set to False), not add it.
    Only the user can grant public permission.
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, id):
        from .models import UserFeedback
        from .serializers import UserFeedbackSerializer
        import logging

        logger = logging.getLogger(__name__)

        try:
            feedback = UserFeedback.objects.select_related('user').get(id=id)
        except UserFeedback.DoesNotExist:
            return Response({
                'error': 'Feedback not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        changes = []

        # Update allowed fields
        if 'is_reviewed' in request.data:
            old_value = feedback.is_reviewed
            feedback.is_reviewed = bool(request.data['is_reviewed'])
            if old_value != feedback.is_reviewed:
                changes.append(f"is_reviewed: {old_value} -> {feedback.is_reviewed}")

        if 'admin_notes' in request.data:
            notes = str(request.data['admin_notes'])[:2000]  # Limit to 2000 chars
            if feedback.admin_notes != notes:
                changes.append("admin_notes updated")
                feedback.admin_notes = notes

        # SECURITY: Admin can only REMOVE public permission, not ADD it
        # This protects user privacy - only users can consent to public display
        if 'allow_public' in request.data:
            new_value = bool(request.data['allow_public'])
            if feedback.allow_public and not new_value:
                # Admin is removing public permission - allowed
                feedback.allow_public = False
                changes.append("allow_public: True -> False (removed by admin)")
            elif not feedback.allow_public and new_value:
                # Admin trying to add public permission - NOT allowed
                return Response({
                    'error': 'Não é possível tornar público sem consentimento do utilizador. Apenas o utilizador pode autorizar a publicação do seu feedback.'
                }, status=status.HTTP_403_FORBIDDEN)

        feedback.save()

        # Log admin action for audit
        if changes:
            logger.info(
                f"Admin {request.user.email} updated feedback {id}: {', '.join(changes)}"
            )

        return Response({
            'message': 'Feedback actualizado com sucesso.',
            'feedback': UserFeedbackSerializer(feedback).data
        })


class AdminFeedbackStatsView(generics.GenericAPIView):
    """
    Admin view to get feedback statistics.

    GET /api/users/feedback/admin/stats/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import UserFeedback
        from django.db.models import Avg, Count

        # Get total counts
        total = UserFeedback.objects.count()
        reviewed = UserFeedback.objects.filter(is_reviewed=True).count()
        pending_review = UserFeedback.objects.filter(is_reviewed=False).count()
        public_testimonials = UserFeedback.objects.filter(allow_public=True).count()

        # Get average rating
        avg_rating = UserFeedback.objects.filter(rating__isnull=False).aggregate(
            avg=Avg('rating')
        )['avg'] or 0

        # Get counts by type
        by_type = UserFeedback.objects.values('feedback_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Get counts by rating
        by_rating = UserFeedback.objects.filter(rating__isnull=False).values('rating').annotate(
            count=Count('id')
        ).order_by('rating')

        # Get counts by trigger
        by_trigger = UserFeedback.objects.values('trigger').annotate(
            count=Count('id')
        ).order_by('-count')

        # Recent feedbacks (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_count = UserFeedback.objects.filter(created_at__gte=recent_date).count()

        return Response({
            'total': total,
            'reviewed': reviewed,
            'pending_review': pending_review,
            'public_testimonials': public_testimonials,
            'average_rating': round(avg_rating, 2),
            'recent_count': recent_count,
            'by_type': list(by_type),
            'by_rating': list(by_rating),
            'by_trigger': list(by_trigger),
        })