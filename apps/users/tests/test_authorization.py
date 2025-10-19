"""
Authorization and permission tests for the users app.

Tests role-based access control, permissions, and integration
with course APIs to ensure security measures are working properly.
"""

from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# Disable rate limiting for tests
def ratelimit_bypass(group, key, rate, method, block):
    def decorator(func):
        return func
    return decorator


class AdminPermissionsTest(APITestCase):
    """Test admin-specific permissions and endpoints."""
    
    def setUp(self):
        # Create users with different roles
        self.admin = User.objects.create_user(
            email='admin@example.com',
            name='Admin User',
            password='password123',
            role='admin'
        )
        
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            name='Teacher User',
            password='password123',
            role='teacher'
        )
        
        self.student = User.objects.create_user(
            email='student@example.com',
            name='Student User',
            password='password123',
            role='student'
        )
        
        # Admin endpoints
        self.admin_users_url = reverse('users:admin_users_list')
        self.admin_user_detail_url = reverse('users:admin_user_detail', kwargs={'id': self.student.id})
        self.admin_user_update_url = reverse('users:admin_user_update', kwargs={'id': self.student.id})
        self.admin_role_update_url = reverse('users:admin_user_role_update', kwargs={'id': self.student.id})
        self.admin_status_toggle_url = reverse('users:admin_user_toggle_status', kwargs={'id': self.student.id})
        self.admin_user_delete_url = reverse('users:admin_user_delete', kwargs={'id': self.student.id})
    
    def test_admin_can_access_user_management(self):
        """Test that admin can access all user management endpoints."""
        self.client.force_authenticate(user=self.admin)
        
        # Test user list
        response = self.client.get(self.admin_users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('stats', response.data)
        
        # Test user detail
        response = self.client.get(self.admin_user_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        
        # Test user update
        response = self.client.patch(self.admin_user_update_url, {
            'name': 'Updated Student Name',
            'email': self.student.email
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test role update
        response = self.client.patch(self.admin_role_update_url, {
            'role': 'teacher'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test status toggle
        response = self.client.patch(self.admin_status_toggle_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_teacher_cannot_access_admin_endpoints(self):
        """Test that teachers cannot access admin endpoints."""
        self.client.force_authenticate(user=self.teacher)
        
        admin_endpoints = [
            self.admin_users_url,
            self.admin_user_detail_url,
            self.admin_user_update_url,
            self.admin_role_update_url,
            self.admin_status_toggle_url,
        ]
        
        for url in admin_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_student_cannot_access_admin_endpoints(self):
        """Test that students cannot access admin endpoints."""
        self.client.force_authenticate(user=self.student)
        
        admin_endpoints = [
            self.admin_users_url,
            self.admin_user_detail_url,
            self.admin_user_update_url,
            self.admin_role_update_url,
            self.admin_status_toggle_url,
        ]
        
        for url in admin_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_cannot_modify_own_role(self):
        """Test that admin cannot change their own role."""
        self.client.force_authenticate(user=self.admin)
        
        admin_role_update_url = reverse('users:admin_user_role_update', kwargs={'id': self.admin.id})
        response = self.client.patch(admin_role_update_url, {
            'role': 'student'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot change your own role', response.data['error'])
    
    def test_admin_cannot_deactivate_themselves(self):
        """Test that admin cannot deactivate their own account."""
        self.client.force_authenticate(user=self.admin)
        
        admin_status_toggle_url = reverse('users:admin_user_toggle_status', kwargs={'id': self.admin.id})
        response = self.client.patch(admin_status_toggle_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot deactivate your own account', response.data['error'])
    
    def test_admin_cannot_delete_themselves(self):
        """Test that admin cannot delete their own account."""
        self.client.force_authenticate(user=self.admin)
        
        admin_delete_url = reverse('users:admin_user_delete', kwargs={'id': self.admin.id})
        response = self.client.delete(admin_delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot delete your own account', response.data['error'])
    
    def test_admin_user_statistics(self):
        """Test admin user statistics functionality."""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(self.admin_users_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = response.data['stats']
        
        # Verify statistics structure
        expected_stats = [
            'total_users', 'active_users', 'student_users', 
            'teacher_users', 'admin_users', 'verified_users'
        ]
        
        for stat in expected_stats:
            self.assertIn(stat, stats)
            self.assertIsInstance(stats[stat], int)
        
        # Verify counts are correct
        self.assertEqual(stats['total_users'], 3)  # admin, teacher, student
        self.assertEqual(stats['admin_users'], 1)
        self.assertEqual(stats['teacher_users'], 1)
        self.assertEqual(stats['student_users'], 1)


class UserProfilePermissionsTest(APITestCase):
    """Test user profile access and modification permissions."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            name='User One',
            password='password123',
            role='student'
        )
        
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            name='User Two',
            password='password123',
            role='teacher'
        )
        
        self.profile_url = reverse('users:profile')
        self.password_change_url = reverse('users:change_password')
    
    def test_user_can_access_own_profile(self):
        """Test that users can access their own profile."""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user1.email)
        self.assertEqual(response.data['name'], self.user1.name)
    
    def test_user_can_update_own_profile(self):
        """Test that users can update their own profile."""
        self.client.force_authenticate(user=self.user1)
        
        update_data = {
            'name': 'Updated Name',
            'phone': '+351123456789'
        }
        
        response = self.client.patch(self.profile_url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.name, update_data['name'])
        self.assertEqual(self.user1.phone, update_data['phone'])
    
    def test_user_can_change_own_password(self):
        """Test that users can change their own password."""
        self.client.force_authenticate(user=self.user1)
        
        password_data = {
            'current_password': 'password123',
            'new_password': 'newpassword456',
            'new_password_confirm': 'newpassword456'
        }
        
        response = self.client.post(self.password_change_url, password_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password('newpassword456'))
    
    def test_user_cannot_change_password_with_wrong_current(self):
        """Test that password change fails with wrong current password."""
        self.client.force_authenticate(user=self.user1)
        
        password_data = {
            'current_password': 'wrongpassword',
            'new_password': 'newpassword456',
            'new_password_confirm': 'newpassword456'
        }
        
        response = self.client.post(self.password_change_url, password_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password('password123'))  # Unchanged
    
    def test_profile_access_requires_authentication(self):
        """Test that profile access requires authentication."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserAddressPermissionsTest(APITestCase):
    """Test user address management permissions."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            name='User One',
            password='password123'
        )
        
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            name='User Two',
            password='password123'
        )
        
        self.address_list_url = reverse('users:address_list')
    
    def test_user_can_manage_own_addresses(self):
        """Test that users can create and list their own addresses."""
        self.client.force_authenticate(user=self.user1)
        
        # Test listing addresses (initially empty)
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_address_access_requires_authentication(self):
        """Test that address access requires authentication."""
        response = self.client.get(self.address_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CourseAPIIntegrationSecurityTest(APITestCase):
    """Test integration between user authentication and course API security."""
    
    def setUp(self):
        # Create users
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
        
        # Course API URLs
        self.teacher_courses_url = '/api/v1/teacher/video-courses/'
        self.student_courses_url = '/api/v1/student/video-courses/'
    
    def test_student_cannot_access_teacher_endpoints(self):
        """Test that students cannot access teacher-only endpoints."""
        self.client.force_authenticate(user=self.student)
        
        teacher_endpoints = [
            '/api/v1/teacher/video-courses/',
            '/api/v1/teacher/practice-courses/',
        ]
        
        for url in teacher_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Should be 403 (Forbidden) due to role restriction
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_teacher_can_access_teacher_endpoints(self):
        """Test that teachers can access teacher endpoints."""
        self.client.force_authenticate(user=self.teacher)
        
        response = self.client.get(self.teacher_courses_url)
        # Should be 200 (OK) - teacher has proper access
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthenticated_cannot_access_protected_endpoints(self):
        """Test that unauthenticated users cannot access protected endpoints."""
        protected_endpoints = [
            '/api/v1/teacher/video-courses/',
            '/api/v1/teacher/practice-courses/',
        ]
        
        for url in protected_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Should be 401 (Unauthorized) due to missing authentication
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_student_can_access_student_endpoints(self):
        """Test that students can access student endpoints."""
        self.client.force_authenticate(user=self.student)
        
        response = self.client.get(self.student_courses_url)
        # Should be 200 (OK) - students can view published courses
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_jwt_token_authentication_with_course_apis(self):
        """Test that JWT token authentication works with course APIs."""
        # Generate JWT token for teacher
        refresh = RefreshToken.for_user(self.teacher)
        access_token = str(refresh.access_token)
        
        # Use token to authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.get(self.teacher_courses_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_invalid_jwt_token_rejection(self):
        """Test that invalid JWT tokens are properly rejected."""
        # Use invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_here')
        
        response = self.client.get(self.teacher_courses_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_jwt_token_rejection(self):
        """Test that expired JWT tokens are properly rejected."""
        # Create token and simulate expiration by manipulating time
        from freezegun import freeze_time
        from datetime import datetime, timedelta
        
        # Generate token
        with freeze_time(datetime.now() - timedelta(days=1)):
            refresh = RefreshToken.for_user(self.teacher)
            access_token = str(refresh.access_token)
        
        # Try to use expired token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.get(self.teacher_courses_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserModelPermissionsTest(TestCase):
    """Test User model permissions and role-based properties."""
    
    def setUp(self):
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
    
    def test_role_properties(self):
        """Test role-based properties work correctly."""
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
    
    def test_username_email_consistency(self):
        """Test that username is always set to email."""
        user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        # Username should be set to email automatically
        self.assertEqual(user.username, user.email)
        
        # Test updating email updates username
        user.email = 'newemail@example.com'
        user.save()
        
        self.assertEqual(user.username, 'newemail@example.com')
    
    def test_user_string_representation(self):
        """Test user string representation."""
        expected = f"{self.student.name} ({self.student.email})"
        self.assertEqual(str(self.student), expected)
    
    def test_get_full_name_and_short_name(self):
        """Test name getter methods."""
        user = User.objects.create_user(
            email='fullname@example.com',
            name='John Doe Smith',
            password='password123'
        )
        
        self.assertEqual(user.get_full_name(), 'John Doe Smith')
        self.assertEqual(user.get_short_name(), 'John')
        
        # Test with user having no name
        user_no_name = User.objects.create_user(
            email='noname@example.com',
            name='',
            password='password123'
        )
        
        self.assertEqual(user_no_name.get_short_name(), 'noname@example.com')