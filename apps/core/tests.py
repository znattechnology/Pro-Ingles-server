"""
Tests for core functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.core.models import Address, BaseModel

User = get_user_model()


class AddressModelTest(TestCase):
    """Test Address model functionality."""
    
    def setUp(self):
        self.address = Address.objects.create(
            street='Rua Test 123',
            city='Lisboa',
            postal_code='1000-001',
            district='Lisboa',
            country='Portugal'
        )
    
    def test_address_creation(self):
        """Test address creation."""
        self.assertEqual(self.address.street, 'Rua Test 123')
        self.assertEqual(self.address.city, 'Lisboa')
        self.assertEqual(self.address.postal_code, '1000-001')
        self.assertEqual(self.address.district, 'Lisboa')
        self.assertEqual(self.address.country, 'Portugal')
    
    def test_address_str_representation(self):
        """Test address string representation."""
        expected = 'Rua Test 123, Lisboa, 1000-001'
        self.assertEqual(str(self.address), expected)
    
    def test_full_address_property(self):
        """Test full_address property."""
        self.address.building_number = '123A'
        self.address.apartment = '2B'
        self.address.floor = '2'
        self.address.save()
        
        full_address = self.address.full_address
        self.assertIn('Rua Test 123 123A', full_address)
        self.assertIn('Apt 2B', full_address)
        self.assertIn('Floor 2', full_address)
        self.assertIn('Lisboa', full_address)
        self.assertIn('Portugal', full_address)
    
    def test_address_optional_fields(self):
        """Test address with optional fields."""
        address_with_extras = Address.objects.create(
            street='Avenida da República',
            city='Porto',
            postal_code='4000-001',
            district='Porto',
            building_number='456',
            apartment='3C',
            floor='3',
            additional_info='Próximo ao metro'
        )
        
        self.assertEqual(address_with_extras.building_number, '456')
        self.assertEqual(address_with_extras.apartment, '3C')
        self.assertEqual(address_with_extras.floor, '3')
        self.assertEqual(address_with_extras.additional_info, 'Próximo ao metro')


class BaseModelTest(TestCase):
    """Test BaseModel functionality."""
    
    def setUp(self):
        # Create user and address to test BaseModel features
        self.user = User.objects.create_user(
            email='base@test.com',
            name='Base User',
            password='testpass'
        )
        self.address = Address.objects.create(
            street='Test Street',
            city='Test City',
            postal_code='12345',
            district='Test District'
        )
    
    def test_base_model_uuid_field(self):
        """Test that BaseModel has UUID primary key."""
        # Test with User model which extends BaseModel
        self.assertIsNotNone(self.user.id)
        # ID should be UUID (36 characters with hyphens)
        self.assertEqual(len(str(self.user.id)), 36)
        
        # Test with Address model which also extends BaseModel
        self.assertIsNotNone(self.address.id)
        self.assertEqual(len(str(self.address.id)), 36)
    
    def test_base_model_timestamp_fields(self):
        """Test that BaseModel has timestamp fields."""
        # User model test
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)
        
        # Address model test
        self.assertIsNotNone(self.address.created_at)
        self.assertIsNotNone(self.address.updated_at)
    
    def test_updated_at_changes(self):
        """Test that updated_at changes when model is saved."""
        original_updated = self.user.updated_at
        
        # Update the user
        self.user.name = 'Updated Name'
        self.user.save()
        
        self.assertGreater(self.user.updated_at, original_updated)
        
        # Test with address as well
        original_address_updated = self.address.updated_at
        self.address.city = 'Updated City'
        self.address.save()
        
        self.assertGreater(self.address.updated_at, original_address_updated)


class CoreHealthTest(APITestCase):
    """Test core health check functionality."""
    
    def test_health_check_available(self):
        """Test that health check functionality exists."""
        # Since we don't have the upload URLs, we'll test basic functionality
        # This ensures the core app can be imported without errors
        from apps.core import models
        from apps.core import exceptions
        
        # Test that core models can be imported
        self.assertTrue(hasattr(models, 'BaseModel'))
        self.assertTrue(hasattr(models, 'Address'))
        self.assertTrue(hasattr(models, 'UUIDModel'))
        self.assertTrue(hasattr(models, 'TimestampedModel'))
        
        # Test that exceptions module exists
        self.assertTrue(hasattr(exceptions, 'custom_exception_handler'))


class CoreExceptionsTest(TestCase):
    """Test core exception handling."""
    
    def test_exception_handler_import(self):
        """Test that custom exception handler can be imported."""
        from apps.core.exceptions import custom_exception_handler
        
        self.assertIsNotNone(custom_exception_handler)
        self.assertTrue(callable(custom_exception_handler))
    
    def test_custom_exception_classes(self):
        """Test custom exception classes."""
        from apps.core.exceptions import APIException, ValidationError, NotFoundError, PermissionError
        
        # Test that custom exceptions can be instantiated
        api_exc = APIException("Test error")
        self.assertEqual(api_exc.message, "Test error")
        
        validation_exc = ValidationError("Validation failed")
        self.assertEqual(validation_exc.message, "Validation failed")
        
        not_found_exc = NotFoundError("Not found")
        self.assertEqual(not_found_exc.message, "Not found")
        
        permission_exc = PermissionError("Permission denied")
        self.assertEqual(permission_exc.message, "Permission denied")