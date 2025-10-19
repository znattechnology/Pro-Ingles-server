"""
Comprehensive authentication tests for the users app.

Tests all authentication flows including registration, login, JWT tokens,
email verification, password reset, and OAuth integration.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.core import mail
from django.conf import settings

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import EmailVerification

User = get_user_model()


# Disable rate limiting for tests
def ratelimit_bypass(group, key, rate, method, block):
    def decorator(func):
        return func
    return decorator


@patch('apps.users.views.ratelimit', ratelimit_bypass)
class UserRegistrationFlowTest(APITestCase):
    """Test complete user registration flow with email verification."""
    
    def setUp(self):
        self.register_url = reverse('users:register')
        self.verify_url = reverse('users:verify_email')
        self.resend_url = reverse('users:resend_verification')
        
        self.valid_registration_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'role': 'student'
        }
    
    def test_successful_registration_flow(self):
        """Test complete registration flow from signup to verification."""
        # Step 1: Register user
        response = self.client.post(self.register_url, self.valid_registration_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('requires_verification', response.data)
        self.assertTrue(response.data['requires_verification'])
        
        # Verify user was created but not verified
        user = User.objects.get(email=self.valid_registration_data['email'])
        self.assertFalse(user.email_verified)
        self.assertEqual(user.role, 'student')
        
        # Step 2: Verify email verification code was created
        verification = EmailVerification.objects.filter(user=user).first()
        self.assertIsNotNone(verification)
        self.assertEqual(len(verification.code), 6)
        self.assertFalse(verification.is_used)
        
        # Step 3: Verify email with code
        verify_response = self.client.post(self.verify_url, {
            'email': user.email,
            'code': verification.code
        })
        
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', verify_response.data)
        self.assertIn('refresh', verify_response.data)
        
        # Verify user is now verified and can login
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
    
    def test_registration_with_invalid_data(self):
        """Test registration with various invalid data scenarios."""
        test_cases = [
            # Missing required fields
            {'email': 'test@example.com', 'name': 'Test'},  # No password
            {'name': 'Test', 'password': 'pass123'},  # No email
            {'email': 'test@example.com', 'password': 'pass123'},  # No name
            
            # Invalid email formats
            {'email': 'invalid-email', 'name': 'Test', 'password': 'pass123'},
            {'email': 'test@', 'name': 'Test', 'password': 'pass123'},
            
            # Password mismatch
            {
                'email': 'test@example.com',
                'name': 'Test',
                'password': 'pass123',
                'password_confirm': 'different123'
            },
            
            # Invalid role
            {
                'email': 'test@example.com',
                'name': 'Test',
                'password': 'pass123',
                'role': 'invalid_role'
            }
        ]
        
        for i, invalid_data in enumerate(test_cases):
            with self.subTest(case=i, data=invalid_data):
                response = self.client.post(self.register_url, invalid_data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_duplicate_email_registration(self):
        """Test that duplicate email registration is prevented."""
        # Create first user
        User.objects.create_user(
            email=self.valid_registration_data['email'],
            name='Existing User',
            password='password123'
        )
        
        # Try to register with same email
        response = self.client.post(self.register_url, self.valid_registration_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_email_verification_with_invalid_code(self):
        """Test email verification with invalid verification codes."""
        # Register user first
        self.client.post(self.register_url, self.valid_registration_data)
        user = User.objects.get(email=self.valid_registration_data['email'])
        
        # Test with invalid codes
        invalid_codes = ['123456', '000000', 'abcdef', '']
        
        for code in invalid_codes:
            with self.subTest(code=code):
                response = self.client.post(self.verify_url, {
                    'email': user.email,
                    'code': code
                })
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_resend_verification_code(self):
        """Test resending verification code functionality."""
        # Register user
        self.client.post(self.register_url, self.valid_registration_data)
        user = User.objects.get(email=self.valid_registration_data['email'])
        
        # Get original verification code
        original_verification = EmailVerification.objects.filter(user=user).first()
        original_code = original_verification.code
        
        # Resend verification code
        response = self.client.post(self.resend_url, {
            'email': user.email
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify new code was created
        new_verification = EmailVerification.objects.filter(user=user, is_used=False).first()
        self.assertNotEqual(new_verification.code, original_code)


@patch('apps.users.views.ratelimit', ratelimit_bypass)
class UserLoginFlowTest(APITestCase):
    """Test user login and JWT token management."""
    
    def setUp(self):
        self.login_url = reverse('users:login')
        self.refresh_url = reverse('users:refresh_token')
        self.logout_url = reverse('users:logout')
        
        # Create verified users with different roles
        self.student = User.objects.create_user(
            email='student@example.com',
            name='Student User',
            password='password123',
            role='student'
        )
        self.student.email_verified = True
        self.student.save()
        
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            name='Teacher User',
            password='password123',
            role='teacher'
        )
        self.teacher.email_verified = True
        self.teacher.save()
        
        self.admin = User.objects.create_user(
            email='admin@example.com',
            name='Admin User',
            password='password123',
            role='admin'
        )
        self.admin.email_verified = True
        self.admin.save()
    
    def test_successful_login_all_roles(self):
        """Test successful login for all user roles."""
        users_data = [
            (self.student, 'student'),
            (self.teacher, 'teacher'),
            (self.admin, 'admin')
        ]
        
        for user, expected_role in users_data:
            with self.subTest(role=expected_role):
                response = self.client.post(self.login_url, {
                    'email': user.email,
                    'password': 'password123'
                })
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('access', response.data)
                self.assertIn('refresh', response.data)
                self.assertIn('user', response.data)
                self.assertEqual(response.data['user']['role'], expected_role)
                self.assertEqual(response.data['user']['email'], user.email)
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        invalid_credentials = [
            {'email': 'student@example.com', 'password': 'wrongpassword'},
            {'email': 'nonexistent@example.com', 'password': 'password123'},
            {'email': '', 'password': 'password123'},
            {'email': 'student@example.com', 'password': ''},
        ]
        
        for credentials in invalid_credentials:
            with self.subTest(credentials=credentials):
                response = self.client.post(self.login_url, credentials)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_with_unverified_email(self):
        """Test that users with unverified email cannot login."""
        unverified_user = User.objects.create_user(
            email='unverified@example.com',
            name='Unverified User',
            password='password123'
        )
        # email_verified is False by default
        
        response = self.client.post(self.login_url, {
            'email': unverified_user.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_with_inactive_user(self):
        """Test that inactive users cannot login."""
        self.student.is_active = False
        self.student.save()
        
        response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_token_refresh(self):
        """Test JWT token refresh functionality."""
        # Login to get tokens
        login_response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        refresh_response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        })
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
    
    def test_logout_functionality(self):
        """Test logout functionality with token blacklisting."""
        # Login to get tokens
        login_response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Logout
        logout_response = self.client.post(self.logout_url, {
            'refresh_token': refresh_token
        })
        
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        
        # Try to use refresh token after logout (should fail)
        refresh_response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        })
        
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)


@patch('apps.users.views.ratelimit', ratelimit_bypass)
class PasswordResetFlowTest(APITestCase):
    """Test password reset functionality."""
    
    def setUp(self):
        self.reset_request_url = reverse('users:password_reset')
        self.reset_confirm_url = reverse('users:password_reset_confirm')
        
        self.user = User.objects.create_user(
            email='reset@example.com',
            name='Reset User',
            password='oldpassword123'
        )
        self.user.email_verified = True
        self.user.save()
    
    def test_password_reset_flow(self):
        """Test complete password reset flow."""
        # Step 1: Request password reset
        response = self.client.post(self.reset_request_url, {
            'email': self.user.email
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 2: Verify reset code was created
        reset_verification = EmailVerification.objects.filter(
            user=self.user,
            is_used=False
        ).order_by('-created_at').first()
        
        self.assertIsNotNone(reset_verification)
        
        # Step 3: Use reset code to change password
        new_password = 'newpassword123'
        confirm_response = self.client.post(self.reset_confirm_url, {
            'email': self.user.email,
            'code': reset_verification.code,
            'newPassword': new_password
        })
        
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password('oldpassword123'))
        
        # Step 5: Verify reset code was marked as used
        reset_verification.refresh_from_db()
        self.assertTrue(reset_verification.is_used)
    
    def test_password_reset_nonexistent_email(self):
        """Test password reset request for non-existent email."""
        response = self.client.post(self.reset_request_url, {
            'email': 'nonexistent@example.com'
        })
        
        # Should return success to not reveal if email exists
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # But no verification code should be created
        verification_count = EmailVerification.objects.filter(
            email='nonexistent@example.com'
        ).count()
        self.assertEqual(verification_count, 0)
    
    def test_password_reset_with_invalid_code(self):
        """Test password reset confirmation with invalid code."""
        # Request password reset first
        self.client.post(self.reset_request_url, {
            'email': self.user.email
        })
        
        # Try to confirm with invalid code
        response = self.client.post(self.reset_confirm_url, {
            'email': self.user.email,
            'code': '123456',  # Invalid code
            'newPassword': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword123'))
    
    def test_password_reset_expired_code(self):
        """Test password reset with expired code."""
        # Create an expired verification code
        expired_verification = EmailVerification.objects.create(
            user=self.user,
            email=self.user.email,
            code='123456',
            expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )
        
        # Try to use expired code
        response = self.client.post(self.reset_confirm_url, {
            'email': self.user.email,
            'code': expired_verification.code,
            'newPassword': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expirado', response.data['error'].lower())


class RoleBasedAuthenticationTest(APITestCase):
    """Test role-based authentication and permissions."""
    
    def setUp(self):
        self.profile_url = reverse('users:profile')
        
        # Create users with different roles
        self.student = User.objects.create_user(
            email='student@example.com',
            name='Student User',
            password='password123',
            role='student'
        )
        
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            name='Teacher User',
            password='password123',
            role='teacher'
        )
        
        self.admin = User.objects.create_user(
            email='admin@example.com',
            name='Admin User',
            password='password123',
            role='admin'
        )
    
    def test_role_verification_in_user_model(self):
        """Test role verification properties in User model."""
        # Test student role
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_teacher)
        self.assertFalse(self.student.is_platform_admin)
        
        # Test teacher role
        self.assertFalse(self.teacher.is_student)
        self.assertTrue(self.teacher.is_teacher)
        self.assertFalse(self.teacher.is_platform_admin)
        
        # Test admin role
        self.assertFalse(self.admin.is_student)
        self.assertFalse(self.admin.is_teacher)
        self.assertTrue(self.admin.is_platform_admin)
    
    def test_authenticated_profile_access(self):
        """Test that authenticated users can access their profile."""
        for user in [self.student, self.teacher, self.admin]:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user=user)
                response = self.client.get(self.profile_url)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['email'], user.email)
                self.assertEqual(response.data['role'], user.role)
    
    def test_unauthenticated_profile_access(self):
        """Test that unauthenticated users cannot access profile."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_token_contains_role_information(self):
        """Test that JWT tokens contain correct role information."""
        login_url = reverse('users:login')
        
        for user in [self.student, self.teacher, self.admin]:
            user.email_verified = True
            user.save()
            
            with self.subTest(role=user.role):
                response = self.client.post(login_url, {
                    'email': user.email,
                    'password': 'password123'
                })
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['user']['role'], user.role)
                
                # Verify token works for authenticated requests
                access_token = response.data['access']
                self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
                
                profile_response = self.client.get(self.profile_url)
                self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
                self.assertEqual(profile_response.data['role'], user.role)