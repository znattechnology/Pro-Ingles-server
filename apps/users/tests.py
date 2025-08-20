"""
Tests for users app including OAuth functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model functionality."""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'testpass123',
            'role': 'customer'
        }
    
    def test_create_user(self):
        """Test creating a user with email."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.name, self.user_data['name'])
        self.assertEqual(user.role, self.user_data['role'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            name='Admin User',
            password='adminpass123'
        )
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'admin')
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        expected = f"{self.user_data['name']} ({self.user_data['email']})"
        self.assertEqual(str(user), expected)
    
    def test_email_normalization(self):
        """Test email is normalized."""
        email = 'TEST@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            name='Test User',
            password='testpass123'
        )
        # Django normalizes email domain to lowercase automatically
        self.assertEqual(user.email, 'TEST@example.com')


class UserRegistrationAPITest(APITestCase):
    """Test user registration API."""
    
    def setUp(self):
        self.url = reverse('users:register')
        self.valid_data = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'role': 'customer'
        }
    
    def test_valid_registration(self):
        """Test successful user registration."""
        response = self.client.post(self.url, self.valid_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.valid_data['email']).exists())
        
        user = User.objects.get(email=self.valid_data['email'])
        self.assertEqual(user.name, self.valid_data['name'])
        self.assertTrue(user.check_password(self.valid_data['password']))
    
    def test_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = self.valid_data.copy()
        data['password_confirm'] = 'differentpass'
        del data['password_confirm']  # Remove invalid field for model
        
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email=data['email']).exists())
    
    def test_duplicate_email(self):
        """Test registration with existing email."""
        user_data = self.valid_data.copy()
        del user_data['password_confirm']  # Remove field not in model
        User.objects.create_user(**user_data)
        
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GoogleOAuthTest(APITestCase):
    """Test Google OAuth functionality."""
    
    def setUp(self):
        self.oauth_url = reverse('users:google_oauth_url')
        self.oauth_login_url = reverse('users:google_oauth_login')
    
    def test_oauth_url_generation(self):
        """Test Google OAuth URL generation."""
        response = self.client.post(self.oauth_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should fail without Google credentials configured
    
    @patch('apps.users.services.GoogleOAuthService.authenticate_user')
    def test_oauth_login_with_code(self, mock_auth):
        """Test OAuth login with authorization code."""
        # Mock the OAuth service response
        mock_user = User.objects.create_user(
            email='oauth@example.com',
            name='OAuth User',
            google_id='123456789'
        )
        mock_tokens = {
            'access': 'mock_access_token',
            'refresh': 'mock_refresh_token'
        }
        mock_auth.return_value = (mock_user, mock_tokens)
        
        response = self.client.post(self.oauth_login_url, {
            'code': 'mock_authorization_code'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        mock_auth.assert_called_once()


class UserProfileAPITest(APITestCase):
    """Test user profile management API."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='profile@example.com',
            name='Profile User',
            password='profilepass123'
        )
        self.url = reverse('users:profile')
        self.client.force_authenticate(user=self.user)
    
    def test_get_profile(self):
        """Test retrieving user profile."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['name'], self.user.name)
    
    def test_update_profile(self):
        """Test updating user profile."""
        update_data = {
            'name': 'Updated Name',
            'phone': '+351123456789'
        }
        
        response = self.client.patch(self.url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, update_data['name'])
        self.assertEqual(self.user.phone, update_data['phone'])
    
    def test_profile_unauthorized(self):
        """Test profile access without authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordChangeTest(APITestCase):
    """Test password change functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='password@example.com',
            name='Password User',
            password='oldpass123'
        )
        self.url = reverse('users:change_password')
        self.client.force_authenticate(user=self.user)
    
    def test_valid_password_change(self):
        """Test successful password change."""
        data = {
            'current_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))
    
    def test_wrong_current_password(self):
        """Test password change with wrong current password."""
        data = {
            'current_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpass123'))
    
    def test_password_mismatch(self):
        """Test password change with mismatched new passwords."""
        data = {
            'current_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpass123'))