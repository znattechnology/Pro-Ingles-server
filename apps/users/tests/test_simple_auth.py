"""
Simplified authentication tests without rate limiting.

These tests focus on core authentication functionality
without being affected by rate limiting decorators.
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import EmailVerification

User = get_user_model()


@override_settings(
    RATELIMIT_ENABLE=False,  # Disable rate limiting
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}},  # Disable cache
)
class SimpleAuthenticationTest(APITestCase):
    """Simple authentication tests without rate limiting interference."""
    
    def setUp(self):
        self.login_url = reverse('users:login')
        self.profile_url = reverse('users:profile')
        
        # Create test users
        self.student = User.objects.create_user(
            email='student@test.com',
            name='Test Student',
            password='password123',
            role='student'
        )
        self.student.email_verified = True
        self.student.save()
        
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            name='Test Teacher',
            password='password123',
            role='teacher'
        )
        self.teacher.email_verified = True
        self.teacher.save()
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            name='Test Admin',
            password='password123',
            role='admin'
        )
        self.admin.email_verified = True
        self.admin.save()
    
    def test_student_login_success(self):
        """Test successful student login."""
        response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['role'], 'student')
    
    def test_teacher_login_success(self):
        """Test successful teacher login."""
        response = self.client.post(self.login_url, {
            'email': self.teacher.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['role'], 'teacher')
    
    def test_admin_login_success(self):
        """Test successful admin login."""
        response = self.client.post(self.login_url, {
            'email': self.admin.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['role'], 'admin')
    
    def test_invalid_login_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_unverified_email_login_denied(self):
        """Test that unverified email users cannot login."""
        unverified_user = User.objects.create_user(
            email='unverified@test.com',
            name='Unverified User',
            password='password123',
            role='student'
        )
        # email_verified is False by default
        
        response = self.client.post(self.login_url, {
            'email': unverified_user.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_inactive_user_login_denied(self):
        """Test that inactive users cannot login."""
        self.student.is_active = False
        self.student.save()
        
        response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_access_with_jwt(self):
        """Test profile access using JWT token."""
        # Login to get token
        login_response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        access_token = login_response.data['access']
        
        # Use token to access profile
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_response = self.client.get(self.profile_url)
        
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['email'], self.student.email)
        self.assertEqual(profile_response.data['role'], 'student')
    
    def test_course_api_integration_security(self):
        """Test that course API security works with user authentication."""
        # Login as student
        login_response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Student should be able to access student endpoints
        student_response = self.client.get('/api/v1/student/video-courses/')
        self.assertEqual(student_response.status_code, status.HTTP_200_OK)
        
        # Student should NOT be able to access teacher endpoints
        teacher_response = self.client.get('/api/v1/teacher/video-courses/')
        self.assertEqual(teacher_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Login as teacher
        teacher_login_response = self.client.post(self.login_url, {
            'email': self.teacher.email,
            'password': 'password123'
        })
        teacher_access_token = teacher_login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_access_token}')
        
        # Teacher should be able to access teacher endpoints
        teacher_response = self.client.get('/api/v1/teacher/video-courses/')
        self.assertEqual(teacher_response.status_code, status.HTTP_200_OK)
    
    def test_user_role_properties(self):
        """Test user model role properties."""
        # Test student
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_teacher)
        self.assertFalse(self.student.is_platform_admin)
        
        # Test teacher
        self.assertFalse(self.teacher.is_student)
        self.assertTrue(self.teacher.is_teacher)
        self.assertFalse(self.teacher.is_platform_admin)
        
        # Test admin
        self.assertFalse(self.admin.is_student)
        self.assertFalse(self.admin.is_teacher)
        self.assertTrue(self.admin.is_platform_admin)
    
    def test_jwt_token_refresh(self):
        """Test JWT token refresh functionality."""
        # Login to get tokens
        login_response = self.client.post(self.login_url, {
            'email': self.student.email,
            'password': 'password123'
        })
        
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        refresh_url = reverse('users:refresh_token')
        refresh_response = self.client.post(refresh_url, {
            'refresh': refresh_token
        })
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}},
)
class AdminPermissionsSimpleTest(APITestCase):
    """Simple admin permissions test."""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            name='Test Admin',
            password='password123',
            role='admin'
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            name='Test Student',
            password='password123',
            role='student'
        )
        
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            name='Test Teacher',
            password='password123',
            role='teacher'
        )
    
    def test_admin_can_access_user_management(self):
        """Test that admin can access user management endpoints."""
        self.client.force_authenticate(user=self.admin)
        
        admin_users_url = reverse('users:admin_users_list')
        response = self.client.get(admin_users_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('stats', response.data)
    
    def test_non_admin_cannot_access_admin_endpoints(self):
        """Test that non-admin users cannot access admin endpoints."""
        admin_users_url = reverse('users:admin_users_list')
        
        # Test with student
        self.client.force_authenticate(user=self.student)
        response = self.client.get(admin_users_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test with teacher
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(admin_users_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_cannot_modify_own_critical_data(self):
        """Test that admin cannot modify critical aspects of their own account."""
        self.client.force_authenticate(user=self.admin)
        
        # Admin cannot change own role
        role_update_url = reverse('users:admin_user_role_update', kwargs={'id': self.admin.id})
        response = self.client.patch(role_update_url, {'role': 'student'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Admin cannot deactivate themselves
        status_toggle_url = reverse('users:admin_user_toggle_status', kwargs={'id': self.admin.id})
        response = self.client.patch(status_toggle_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)