"""
Serializers for user models and authentication.
"""

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from .models import User, UserAddress, NotificationSettings
from apps.core.models import Address


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=False
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'name', 'password', 'password_confirm',
            'phone', 'role'
        ]
        extra_kwargs = {
            'role': {'default': 'customer'}
        }
    
    def validate(self, attrs):
        # Se password_confirm foi fornecido, verificar se as senhas coincidem
        if 'password_confirm' in attrs and attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)  # Remove se existir
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer with additional user data.
    """
    
    def validate(self, attrs):
        # Check for empty credentials first and raise AuthenticationFailed
        email = attrs.get('email', '').strip()
        password = attrs.get('password', '')
        
        if not email or not password:
            raise AuthenticationFailed(
                "Email e senha são obrigatórios."
            )
        
        try:
            # Use parent validate() which handles authentication
            data = super().validate(attrs)
        except Exception:
            # Convert any validation error to AuthenticationFailed for 401 status
            raise AuthenticationFailed(
                "Credenciais inválidas. Verifique seu email e senha."
            )
        
        # Check if email is verified
        user = self.user
        if not user.email_verified:
            raise AuthenticationFailed(
                "Email não verificado. Verifique seu email antes de fazer login."
            )
        
        # Add user data to token response
        data['user'] = {
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'avatar': user.avatar.url if user.avatar else None,
            'email_verified': user.email_verified,
        }
        
        # Update last login
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        
        return data
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to token
        token['user_id'] = str(user.id)
        token['email'] = user.email
        token['role'] = user.role
        token['name'] = user.name
        
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile management.
    """
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'phone', 'avatar', 'avatar_url',
            'role', 'email_verified', 'preferences', 'created_at'
        ]
        read_only_fields = ['id', 'email', 'role', 'email_verified', 'created_at']
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    current_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for Address model.
    """
    
    class Meta:
        model = Address
        fields = [
            'id', 'street', 'city', 'postal_code', 'district', 'country',
            'building_number', 'apartment', 'floor', 'additional_info',
            'full_address'
        ]
        read_only_fields = ['id', 'full_address']


class UserAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for UserAddress model.
    """
    address = AddressSerializer()
    
    class Meta:
        model = UserAddress
        fields = [
            'id', 'address', 'address_type', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        address_data = validated_data.pop('address')
        address = Address.objects.create(**address_data)
        user_address = UserAddress.objects.create(
            address=address,
            user=self.context['request'].user,
            **validated_data
        )
        return user_address


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationSettings model.
    """
    
    class Meta:
        model = NotificationSettings
        fields = [
            'id', 'email_bookings', 'email_messages', 'email_ratings',
            'email_orders', 'email_marketing', 'push_bookings',
            'push_messages', 'push_ratings', 'push_orders',
            'digest_frequency', 'quiet_hours_start', 'quiet_hours_end',
            'timezone'
        ]
        read_only_fields = ['id']


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active user with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """
    token = serializers.CharField()
    new_password = serializers.CharField(
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """
    token = serializers.CharField()


class GoogleOAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication.
    """
    code = serializers.CharField(
        required=False,
        help_text="Authorization code from Google OAuth"
    )
    access_token = serializers.CharField(
        required=False,
        help_text="Access token from Google OAuth"
    )
    id_token = serializers.CharField(
        required=False,
        help_text="ID token from Google OAuth"
    )
    
    def validate(self, attrs):
        """Validate that at least one authentication method is provided."""
        if not any([attrs.get('code'), attrs.get('access_token'), attrs.get('id_token')]):
            raise serializers.ValidationError(
                "Either 'code', 'access_token', or 'id_token' must be provided."
            )
        return attrs


class GoogleOAuthURLSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth URL generation.
    """
    redirect_uri = serializers.URLField(
        required=False,
        help_text="Custom redirect URI (optional)"
    )
    state = serializers.CharField(
        required=False,
        help_text="State parameter for OAuth flow"
    )


class SocialUserInfoSerializer(serializers.Serializer):
    """
    Serializer for social user information from OAuth providers.
    """
    id = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField()
    given_name = serializers.CharField(required=False)
    family_name = serializers.CharField(required=False)
    picture = serializers.URLField(required=False)
    locale = serializers.CharField(required=False)
    verified_email = serializers.BooleanField(required=False)