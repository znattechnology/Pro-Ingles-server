"""
Services for user authentication and OAuth.
"""

import requests
import secrets
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

User = get_user_model()
logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Service for Google OAuth authentication."""
    
    def __init__(self):
        self.config = settings.OAUTH2_SETTINGS.get('GOOGLE', {})
        self.client_id = self.config.get('CLIENT_ID')
        self.client_secret = self.config.get('CLIENT_SECRET')
        self.redirect_uri = self.config.get('REDIRECT_URI')
        self.scope = ' '.join(self.config.get('SCOPE', []))
        self.auth_uri = self.config.get('AUTH_URI')
        self.token_uri = self.config.get('TOKEN_URI')
        self.user_info_uri = self.config.get('USER_INFO_URI')
    
    def generate_auth_url(self, state: str = None, redirect_uri: str = None) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for security
            redirect_uri: Optional custom redirect URI
            
        Returns:
            Authorization URL
        """
        if not self.client_id:
            raise ValidationError("Google OAuth client ID not configured")
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'scope': self.scope,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        if state:
            params['state'] = state
        else:
            params['state'] = secrets.token_urlsafe(32)
        
        return f"{self.auth_uri}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in the authorization request
            
        Returns:
            Token response from Google
        """
        if not self.client_secret:
            raise ValidationError("Google OAuth client secret not configured")
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri or self.redirect_uri,
        }
        
        try:
            response = requests.post(self.token_uri, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise ValidationError("Failed to exchange authorization code for tokens")
    
    def get_user_info_from_token(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            User information from Google
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.user_info_uri, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting user info from token: {str(e)}")
            raise ValidationError("Failed to get user information from Google")
    
    def verify_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """
        Verify and decode Google ID token.
        
        Args:
            id_token_str: Google ID token
            
        Returns:
            Decoded token payload
        """
        try:
            # Verify the token
            id_info = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                self.client_id
            )
            
            # Verify the issuer
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValidationError('Invalid token issuer')
            
            return id_info
        except Exception as e:
            logger.error(f"Error verifying ID token: {str(e)}")
            raise ValidationError("Invalid ID token")
    
    def authenticate_user(self, **kwargs) -> Tuple[User, Dict[str, str]]:
        """
        Authenticate user with Google OAuth.
        
        Args:
            **kwargs: Can contain 'code', 'access_token', or 'id_token'
            
        Returns:
            Tuple of (user, tokens) where tokens contains 'access' and 'refresh'
        """
        user_info = None
        
        # Try different authentication methods
        if 'code' in kwargs:
            # Exchange code for tokens and get user info
            token_response = self.exchange_code_for_tokens(kwargs['code'])
            access_token = token_response.get('access_token')
            if access_token:
                user_info = self.get_user_info_from_token(access_token)
            
            # Also try to get info from ID token if present
            if not user_info and 'id_token' in token_response:
                user_info = self.verify_id_token(token_response['id_token'])
        
        elif 'access_token' in kwargs:
            # Get user info directly from access token
            user_info = self.get_user_info_from_token(kwargs['access_token'])
        
        elif 'id_token' in kwargs:
            # Verify and decode ID token
            user_info = self.verify_id_token(kwargs['id_token'])
        
        if not user_info:
            raise ValidationError("Could not retrieve user information from Google")
        
        # Extract user data
        google_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name', '')
        given_name = user_info.get('given_name', '')
        family_name = user_info.get('family_name', '')
        picture = user_info.get('picture')
        verified_email = user_info.get('verified_email', False)
        
        if not email:
            raise ValidationError("Email not provided by Google")
        
        # Find or create user
        user = self._get_or_create_user(
            google_id=google_id,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            picture=picture,
            verified_email=verified_email
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        tokens = {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
        
        return user, tokens
    
    def _get_or_create_user(self, **user_data) -> User:
        """
        Get existing user or create new one from Google data.
        
        Args:
            **user_data: User information from Google
            
        Returns:
            User instance
        """
        email = user_data['email']
        google_id = user_data['google_id']
        
        # Try to find existing user by email
        try:
            user = User.objects.get(email=email)
            
            # Update user with Google data if needed
            if not user.google_id and google_id:
                user.google_id = google_id
            
            if not user.name and user_data.get('name'):
                user.name = user_data['name']
            
            if user_data.get('verified_email') and not user.email_verified:
                user.email_verified = True
            
            if user_data.get('picture') and not user.avatar:
                # TODO: Download and save avatar from Google
                pass
            
            user.save()
            logger.info(f"Updated existing user {user.email} with Google OAuth data")
            
        except User.DoesNotExist:
            # Create new user
            user_data_clean = {
                'email': email,
                'name': user_data.get('name', ''),
                'google_id': google_id,
                'email_verified': user_data.get('verified_email', False),
                'role': 'customer',  # Default role
                'is_active': True,
            }
            
            # Create user without password (OAuth only)
            user = User.objects.create(**user_data_clean)
            logger.info(f"Created new user {user.email} via Google OAuth")
        
        return user


class UserService:
    """Service for general user operations."""
    
    @staticmethod
    def create_user_tokens(user: User) -> Dict[str, str]:
        """
        Create JWT tokens for user.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with access and refresh tokens
        """
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    
    @staticmethod
    def get_user_profile_data(user: User) -> Dict[str, Any]:
        """
        Get complete user profile data.
        
        Args:
            user: User instance
            
        Returns:
            User profile dictionary
        """
        return {
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'phone': user.phone,
            'role': user.role,
            'avatar': user.avatar.url if user.avatar else None,
            'email_verified': user.email_verified,
            'google_id': user.google_id,
            'preferences': user.preferences,
            'created_at': user.created_at,
            'last_login_at': user.last_login_at,
        }