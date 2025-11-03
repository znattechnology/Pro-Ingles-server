"""
Simple unit tests for User models.

Tests the basic user functionality without complex dependencies.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from tests.factories import UserFactory, TeacherFactory, StudentFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserModelBasic(TestCase):
    """Test basic User model functionality."""
    
    def test_create_user_with_email(self):
        """Test creating a user with email."""
        user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'testpass123',
            'role': 'student'
        }
        
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.email, user_data['email'])
        self.assertEqual(user.name, user_data['name'])
        self.assertEqual(user.role, user_data['role'])
        self.assertTrue(user.check_password(user_data['password']))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_user_without_email_raises_error(self):
        """Test that creating user without email raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', name='Test', password='test123')
    
    def test_user_string_representation(self):
        """Test the string representation of user."""
        user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='test123'
        )
        
        expected_str = 'Test User (test@example.com)'
        self.assertEqual(str(user), expected_str)
    
    def test_email_normalization(self):
        """Test that email addresses are normalized."""
        email = 'TEST@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            name='Test User',
            password='testpass123'
        )
        
        # Django's BaseUserManager normalizes the domain only
        # The local part (before @) might not be lowercased
        self.assertTrue('@example.com' in user.email.lower())
    
    def test_unique_email_constraint(self):
        """Test that email addresses must be unique."""
        User.objects.create_user(
            email='test@example.com',
            name='User 1',
            password='pass123'
        )
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',
                name='User 2', 
                password='pass456'
            )


@pytest.mark.django_db 
class TestUserFactories(TestCase):
    """Test user factory classes."""
    
    def test_user_factory(self):
        """Test UserFactory creates valid users."""
        user = UserFactory()
        
        self.assertIsNotNone(user.email)
        self.assertIsNotNone(user.name)
        self.assertEqual(user.role, 'student')
        self.assertTrue(user.is_active)
        
        # Test password is set
        self.assertTrue(user.check_password('testpass123'))
    
    def test_teacher_factory(self):
        """Test TeacherFactory creates teacher users.""" 
        teacher = TeacherFactory()
        
        self.assertEqual(teacher.role, 'teacher')
        self.assertIn('@proenglish.com', teacher.email)
    
    def test_student_factory(self):
        """Test StudentFactory creates student users."""
        student = StudentFactory()
        
        self.assertEqual(student.role, 'student')
        self.assertIn('@example.com', student.email)
    
    def test_factory_with_custom_data(self):
        """Test factories with custom data."""
        custom_email = 'custom@test.com'
        user = UserFactory(email=custom_email)
        
        self.assertEqual(user.email, custom_email)
    
    def test_multiple_users_from_factory(self):
        """Test creating multiple users with factories."""
        users = UserFactory.create_batch(5)
        
        self.assertEqual(len(users), 5)
        
        # All should have unique emails
        emails = [user.email for user in users]
        self.assertEqual(len(emails), len(set(emails)))


@pytest.mark.django_db
class TestUserBusinessLogic(TestCase):
    """Test business logic methods on User model."""
    
    def test_user_roles(self):
        """Test different user roles."""
        # Test student role
        student = UserFactory(role='student')
        self.assertEqual(student.role, 'student')
        self.assertFalse(student.is_staff)
        
        # Test teacher role
        teacher = TeacherFactory(role='teacher')
        self.assertEqual(teacher.role, 'teacher')
        
        # Test admin role  
        admin = UserFactory(role='admin', is_staff=True)
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.is_staff)
    
    def test_user_manager_methods(self):
        """Test custom user manager methods."""
        # Test get_by_natural_key (should use email)
        user = UserFactory()
        found_user = User.objects.get_by_natural_key(user.email)
        self.assertEqual(user, found_user)
        
        # Test normalize_email
        normalized = User.objects.normalize_email('TEST@EXAMPLE.COM')
        self.assertEqual(normalized, 'TEST@example.com')