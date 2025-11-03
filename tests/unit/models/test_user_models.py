"""
Unit tests for User models.

Tests the core authentication and user management functionality.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from tests.factories import UserFactory, TeacherFactory, StudentFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserModel(TestCase):
    """Test User model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'testpass123',
            'role': 'customer'
        }
    
    def test_create_user_with_email(self):
        """Test creating a user with email."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.name, self.user_data['name'])
        self.assertEqual(user.role, self.user_data['role'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_user_without_email_raises_error(self):
        """Test that creating user without email raises ValueError."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email='', name='Test', password='test123')
        
        self.assertIn('email address', str(context.exception).lower())
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_data = {
            'email': 'admin@example.com',
            'name': 'Admin User',
            'password': 'adminpass123'
        }
        
        user = User.objects.create_superuser(**admin_data)
        
        self.assertEqual(user.email, admin_data['email'])
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_email_normalization(self):
        """Test that email addresses are normalized."""
        email = 'TEST@EXAMPLE.COM'
        user = User.objects.create_user(
            email=email,
            name='Test User',
            password='testpass123'
        )
        
        self.assertEqual(user.email, email.lower())
    
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
    
    def test_user_string_representation(self):
        """Test the string representation of user."""
        user = UserFactory(email='test@example.com', name='Test User')
        
        self.assertEqual(str(user), 'Test User (test@example.com)')
    
    def test_user_roles(self):
        """Test different user roles."""
        # Test customer role
        customer = UserFactory(role='customer')
        self.assertEqual(customer.role, 'customer')
        self.assertFalse(customer.is_staff)
        
        # Test teacher role
        teacher = TeacherFactory(role='teacher')
        self.assertEqual(teacher.role, 'teacher')
        
        # Test admin role  
        admin = UserFactory(role='admin', is_staff=True)
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.is_staff)
    
    def test_phone_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = ['+1234567890', '+351912345678', '912345678']
        
        for phone in valid_phones:
            user = UserFactory(phone=phone)
            self.assertEqual(user.phone, phone)
    
    def test_user_full_clean(self):
        """Test model validation with full_clean."""
        user = UserFactory.build(email='invalid-email')
        
        with self.assertRaises(ValidationError):
            user.full_clean()
    
    def test_user_manager_methods(self):
        """Test custom user manager methods."""
        # Test get_by_natural_key (should use email)
        user = UserFactory()
        found_user = User.objects.get_by_natural_key(user.email)
        self.assertEqual(user, found_user)
        
        # Test normalize_email
        normalized = User.objects.normalize_email('TEST@EXAMPLE.COM')
        self.assertEqual(normalized, 'TEST@example.com')


@pytest.mark.django_db 
class TestUserFactories(TestCase):
    """Test user factory classes."""
    
    def test_user_factory(self):
        """Test UserFactory creates valid users."""
        user = UserFactory()
        
        self.assertIsNotNone(user.email)
        self.assertIsNotNone(user.name)
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.is_active)
    
    def test_teacher_factory(self):
        """Test TeacherFactory creates teacher users.""" 
        teacher = TeacherFactory()
        
        self.assertEqual(teacher.role, 'teacher')
        self.assertIn('@proenglish.com', teacher.email)
    
    def test_student_factory(self):
        """Test StudentFactory creates student users."""
        student = StudentFactory()
        
        self.assertEqual(student.role, 'customer')
        self.assertIn('@example.com', student.email)
    
    def test_factory_password_generation(self):
        """Test that factories set passwords correctly."""
        user = UserFactory()
        
        # Should be able to authenticate with default password
        self.assertTrue(user.check_password('testpass123'))
    
    def test_factory_with_custom_data(self):
        """Test factories with custom data."""
        custom_email = 'custom@test.com'
        user = UserFactory(email=custom_email)
        
        self.assertEqual(user.email, custom_email)


@pytest.mark.django_db
class TestUserBusinessLogic(TestCase):
    """Test business logic methods on User model."""
    
    def test_user_display_name(self):
        """Test user display name logic."""
        # User with name
        user_with_name = UserFactory(name='John Doe')
        self.assertEqual(user_with_name.get_display_name(), 'John Doe')
        
        # User without name should use email prefix
        user_without_name = UserFactory(name='', email='john@example.com')
        expected_display = user_without_name.email.split('@')[0]
        self.assertEqual(user_without_name.get_display_name(), expected_display)
    
    def test_user_is_teacher(self):
        """Test is_teacher property."""
        teacher = TeacherFactory()
        student = StudentFactory()
        
        self.assertTrue(teacher.is_teacher)
        self.assertFalse(student.is_teacher)
    
    def test_user_is_student(self):
        """Test is_student property."""
        teacher = TeacherFactory()
        student = StudentFactory()
        
        self.assertFalse(teacher.is_student)
        self.assertTrue(student.is_student)


@pytest.mark.performance
@pytest.mark.django_db
class TestUserModelPerformance(TestCase):
    """Test performance aspects of User model."""
    
    def test_bulk_user_creation(self):
        """Test creating multiple users efficiently."""
        users_data = [
            {
                'email': f'user{i}@example.com',
                'name': f'User {i}',
                'role': 'customer'
            }
            for i in range(100)
        ]
        
        # This should be efficient and not hit database for each user
        users = [User(**data) for data in users_data]
        created_users = User.objects.bulk_create(users)
        
        self.assertEqual(len(created_users), 100)
    
    def test_user_query_optimization(self):
        """Test that common user queries are optimized."""
        # Create test users
        UserFactory.create_batch(10)
        
        with self.assertNumQueries(1):
            list(User.objects.filter(is_active=True))


@pytest.mark.security
@pytest.mark.django_db
class TestUserSecurity(TestCase):
    """Test security aspects of User model."""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        password = 'mysecretpassword123'
        user = UserFactory()
        user.set_password(password)
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        
        # But check_password should work
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_sensitive_data_not_in_string_representation(self):
        """Test that sensitive data is not exposed in string representation."""
        user = UserFactory(password='secretpassword123')
        user_str = str(user)
        
        # Password should not appear in string representation
        self.assertNotIn('secretpassword123', user_str)
        self.assertNotIn('password', user_str.lower())
    
    def test_user_permissions_default(self):
        """Test default user permissions."""
        user = UserFactory()
        
        # Regular users should not have admin permissions
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)  # But should be active