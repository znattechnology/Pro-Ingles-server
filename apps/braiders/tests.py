"""
Tests for braiders functionality including braiders, services, and portfolios.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta, time

from .models import Braider, Service, BraiderPortfolioImage, ServiceImage
from apps.core.models import Address

User = get_user_model()


class BraiderModelTest(TestCase):
    """Test Braider model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider_data = {
            'user': self.user,
            'name': 'Test Braiding Studio',
            'contact_email': 'braider@test.com',
            'bio': 'Professional braiding services',
            'experience_level': 'intermediate',
            'years_experience': 3,
            'status': 'approved',
            'provides_home_service': True,
            'has_physical_location': True
        }
    
    def test_create_braider(self):
        """Test creating a braider profile."""
        braider = Braider.objects.create(**self.braider_data)
        
        self.assertEqual(braider.user, self.user)
        self.assertEqual(braider.name, 'Test Braiding Studio')
        self.assertEqual(braider.experience_level, 'intermediate')
        self.assertTrue(braider.provides_home_service)
        self.assertTrue(braider.has_physical_location)
    
    def test_braider_string_representation(self):
        """Test braider string representation."""
        braider = Braider.objects.create(**self.braider_data)
        expected = "Test Braiding Studio"
        self.assertEqual(str(braider), expected)
    
    def test_braider_without_user(self):
        """Test creating braider without user (admin created)."""
        braider_data = self.braider_data.copy()
        del braider_data['user']
        braider_data['name'] = 'Studio Only Braider'
        
        braider = Braider.objects.create(**braider_data)
        self.assertIsNone(braider.user)
        self.assertEqual(str(braider), 'Studio Only Braider')
    
    def test_average_rating_calculation(self):
        """Test average rating calculation."""
        braider = Braider.objects.create(**self.braider_data)
        
        # Initially no rating
        self.assertEqual(braider.average_rating, Decimal('0.00'))
        
        # Test with manual rating (would be calculated from actual reviews)
        braider.average_rating = Decimal('4.5')
        braider.save()
        self.assertEqual(braider.average_rating, Decimal('4.5'))
    
    def test_is_active_property(self):
        """Test braider active status."""
        braider = Braider.objects.create(**self.braider_data)
        
        # Approved braider should be active
        self.assertTrue(braider.is_active)
        
        # Suspended braider should not be active
        braider.status = 'suspended'
        braider.save()
        self.assertFalse(braider.is_active)
    
    def test_location_display_property(self):
        """Test location display property."""
        # Create address
        address = Address.objects.create(
            street='123 Test Street',
            city='Test City',
            district='Test District',
            postal_code='12345'
        )
        
        braider_data = self.braider_data.copy()
        braider_data['address'] = address
        braider = Braider.objects.create(**braider_data)
        
        expected = "Test City, Test District"
        self.assertEqual(braider.location_display, expected)
    
    def test_can_provide_service_at_location(self):
        """Test service location capabilities."""
        braider = Braider.objects.create(**self.braider_data)
        
        # Test home service
        self.assertTrue(braider.can_provide_service_at_location('home'))
        
        # Test salon service
        self.assertTrue(braider.can_provide_service_at_location('salon'))
        
        # Disable home service
        braider.provides_home_service = False
        braider.save()
        self.assertFalse(braider.can_provide_service_at_location('home'))


class ServiceModelTest(TestCase):
    """Test Service model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.user,
            name='Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service_data = {
            'braider': self.braider,
            'name': 'Box Braids',
            'description': 'Professional box braids styling',
            'category': 'braids',
            'base_price': Decimal('80.00'),
            'duration_minutes': 240,
            'is_active': True
        }
    
    def test_create_service(self):
        """Test creating a service."""
        service = Service.objects.create(**self.service_data)
        
        self.assertEqual(service.braider, self.braider)
        self.assertEqual(service.name, 'Box Braids')
        self.assertEqual(service.base_price, Decimal('80.00'))
        self.assertEqual(service.duration_minutes, 240)
        self.assertTrue(service.is_active)
    
    def test_service_string_representation(self):
        """Test service string representation."""
        service = Service.objects.create(**self.service_data)
        expected = f"Test Studio - Box Braids"
        self.assertEqual(str(service), expected)
    
    def test_service_price_display(self):
        """Test service price display property."""
        service = Service.objects.create(**self.service_data)
        expected = "€80.00"
        self.assertEqual(service.price_display, expected)
        
        # Test with price range
        service.price_varies = True
        service.price_from = Decimal('60.00')
        service.price_to = Decimal('100.00')
        service.save()
        
        expected = "€60.00 - €100.00"
        self.assertEqual(service.price_display, expected)
    
    def test_service_duration_display(self):
        """Test service duration display property."""
        service = Service.objects.create(**self.service_data)
        expected = "4h00"
        self.assertEqual(service.duration_display, expected)
        
        # Test with minutes only
        service.duration_minutes = 90
        service.save()
        expected = "1h30"
        self.assertEqual(service.duration_display, expected)
        
        # Test with minutes only (less than hour)
        service.duration_minutes = 45
        service.save()
        expected = "45min"
        self.assertEqual(service.duration_display, expected)
    
    def test_service_categories(self):
        """Test different service categories."""
        categories = ['braids', 'twists', 'locs', 'protective']
        
        for category in categories:
            service_data = self.service_data.copy()
            service_data['name'] = f'Test {category} Service'
            service_data['category'] = category
            
            service = Service.objects.create(**service_data)
            self.assertEqual(service.category, category)
    
    def test_hair_type_compatibility(self):
        """Test hair type compatibility checking."""
        service = Service.objects.create(**self.service_data)
        
        # No restrictions - should work for all
        self.assertTrue(service.is_suitable_for_hair_type('4c'))
        
        # Add restrictions
        service.hair_type_compatibility = ['4a', '4b', '4c']
        service.save()
        
        self.assertTrue(service.is_suitable_for_hair_type('4c'))
        self.assertFalse(service.is_suitable_for_hair_type('2a'))


class BraiderPortfolioImageModelTest(TestCase):
    """Test BraiderPortfolioImage model functionality."""
    
    def setUp(self):
        self.braider_user = User.objects.create_user(
            email='portfolio@test.com',
            name='Portfolio Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Portfolio Studio',
            contact_email='portfolio@test.com',
            experience_level='advanced',
            status='approved'
        )
    
    def test_create_portfolio_image(self):
        """Test creating a portfolio image."""
        image = BraiderPortfolioImage.objects.create(
            braider=self.braider,
            image='portfolio/test_image.jpg',
            title='Beautiful Braids',
            description='Professional box braids with extensions',
            is_featured=True,
            order=1
        )
        
        self.assertEqual(image.braider, self.braider)
        self.assertEqual(image.title, 'Beautiful Braids')
        self.assertTrue(image.is_featured)
        self.assertEqual(image.order, 1)
    
    def test_portfolio_image_string_representation(self):
        """Test portfolio image string representation."""
        image = BraiderPortfolioImage.objects.create(
            braider=self.braider,
            image='portfolio/sample.jpg',
            title='Sample Work'
        )
        
        expected = f"Portfolio Studio - Sample Work"
        self.assertEqual(str(image), expected)


class ServiceImageModelTest(TestCase):
    """Test ServiceImage model functionality."""
    
    def setUp(self):
        self.braider_user = User.objects.create_user(
            email='serviceimage@test.com',
            name='Service Image Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Service Image Studio',
            contact_email='serviceimage@test.com',
            experience_level='expert',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Cornrow Braids',
            description='Traditional cornrow braiding',
            category='braids',
            base_price=Decimal('80.00'),
            duration_minutes=180
        )
    
    def test_create_service_image(self):
        """Test creating a service image."""
        image = ServiceImage.objects.create(
            service=self.service,
            image='services/test_image.jpg',
            image_type='after',
            caption='Beautiful cornrows completed',
            order=1
        )
        
        self.assertEqual(image.service, self.service)
        self.assertEqual(image.image_type, 'after')
        self.assertEqual(image.caption, 'Beautiful cornrows completed')
        self.assertEqual(image.order, 1)
    
    def test_service_image_string_representation(self):
        """Test service image string representation."""
        image = ServiceImage.objects.create(
            service=self.service,
            image='services/before.jpg',
            image_type='before',
            caption='Before styling'
        )
        
        expected = f"Cornrow Braids - Before"
        self.assertEqual(str(image), expected)


class BraidersAPITest(APITestCase):
    """Test braiders API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.user,
            name='API Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='API Test Service',
            description='API test service',
            category='braids',
            base_price=Decimal('60.00'),
            duration_minutes=180
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_braiders(self):
        """Test listing braiders."""
        url = reverse('braiders:braider-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Test Studio')
    
    def test_braider_detail(self):
        """Test getting braider details."""
        url = reverse('braiders:braider-detail', kwargs={'pk': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'API Test Studio')
        self.assertEqual(response.data['experience_level'], 'intermediate')
    
    def test_braider_services(self):
        """Test listing braider services."""
        url = reverse('braiders:braider-services', kwargs={'braider_id': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Test Service')
    
    def test_service_detail(self):
        """Test getting service details."""
        url = reverse('braiders:service-detail', kwargs={'pk': self.service.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'API Test Service')
        self.assertEqual(float(response.data['base_price']), 60.00)
    
    def test_braider_portfolio(self):
        """Test getting braider portfolio."""
        # Create portfolio image
        BraiderPortfolioImage.objects.create(
            braider=self.braider,
            image='portfolio/test.jpg',
            title='Test Portfolio'
        )
        
        url = reverse('braiders:braider-portfolio', kwargs={'braider_id': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Portfolio')
    
    def test_search_braiders(self):
        """Test searching braiders."""
        url = reverse('braiders:braider-search')
        response = self.client.get(url, {'q': 'API Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_braider_stats(self):
        """Test getting braider statistics."""
        url = reverse('braiders:braider-stats', kwargs={'braider_id': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_services', response.data)
        self.assertIn('average_rating', response.data)
        self.assertIn('total_bookings', response.data)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to braider endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('braiders:braider-detail', kwargs={'pk': self.braider.id})
        response = self.client.get(url)
        
        # Public endpoints should still work
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_braider_dashboard(self):
        """Test braider dashboard functionality."""
        url = reverse('braiders:braider-dashboard', kwargs={'braider_id': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('braider_info', response.data)
        self.assertIn('summary_metrics', response.data)
        self.assertIn('recent_activity', response.data)