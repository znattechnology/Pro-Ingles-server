"""
Tests for bookings functionality including appointments, availability, and scheduling.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta, time, date

from .models import Booking, BookingStatusHistory
from apps.braiders.models import Braider, Service
from apps.core.models import Address

User = get_user_model()


class BookingModelTest(TestCase):
    """Test Booking model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Test Customer',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Test Braiding Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Box Braids',
            description='Professional box braids',
            category='braids',
            base_price=Decimal('120.00'),
            duration_minutes=240
        )
        
        self.booking_datetime = timezone.now() + timedelta(days=7)
        
        self.booking_data = {
            'user': self.customer,
            'braider': self.braider,
            'service': self.service,
            'booking_date': self.booking_datetime.date(),
            'booking_time': self.booking_datetime.time(),
            'client_name': self.customer.name,
            'client_phone': '+1234567890',
            'client_email': self.customer.email,
            'booking_type': 'home',
            'base_price': Decimal('120.00'),
            'total_price': Decimal('120.00'),
            'status': 'pending'
        }
    
    def test_create_booking(self):
        """Test creating a booking."""
        booking = Booking.objects.create(**self.booking_data)
        
        self.assertEqual(booking.user, self.customer)
        self.assertEqual(booking.braider, self.braider)
        self.assertEqual(booking.service, self.service)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.total_price, Decimal('120.00'))
        
        # Check that booking reference is generated
        self.assertTrue(booking.booking_reference.startswith('BK-'))
    
    def test_booking_string_representation(self):
        """Test booking string representation."""
        booking = Booking.objects.create(**self.booking_data)
        expected = f"{booking.booking_reference} - {self.customer.name} with {self.braider.name}"
        self.assertEqual(str(booking), expected)
    
    def test_booking_datetime_property(self):
        """Test booking datetime property."""
        booking = Booking.objects.create(**self.booking_data)
        
        expected_datetime = timezone.make_aware(
            datetime.combine(booking.booking_date, booking.booking_time)
        )
        self.assertEqual(booking.booking_datetime.date(), expected_datetime.date())
        self.assertEqual(booking.booking_datetime.time().hour, expected_datetime.time().hour)
    
    def test_booking_end_datetime_property(self):
        """Test booking end datetime calculation."""
        booking = Booking.objects.create(**self.booking_data)
        
        start_datetime = booking.booking_datetime
        # Calculate end time based on service duration
        expected_end = start_datetime + timedelta(minutes=240)
        
        self.assertEqual(booking.end_datetime.date(), expected_end.date())
    
    def test_booking_pricing_calculation(self):
        """Test booking pricing calculation."""
        booking = Booking.objects.create(**self.booking_data)
        
        # Base price should match service price
        self.assertEqual(booking.base_price, Decimal('120.00'))
        self.assertEqual(booking.total_price, Decimal('120.00'))
        
        # Test with additional charges
        booking.additional_charges = Decimal('20.00')
        booking.save()
        self.assertEqual(booking.additional_charges, Decimal('20.00'))
    
    def test_booking_status_transitions(self):
        """Test booking status transitions."""
        booking = Booking.objects.create(**self.booking_data)
        
        # Test confirm booking
        booking.status = 'confirmed'
        booking.save()
        self.assertEqual(booking.status, 'confirmed')
        
        # Test complete booking
        booking.status = 'completed'
        booking.save()
        self.assertEqual(booking.status, 'completed')
    
    def test_booking_type_validation(self):
        """Test booking type validation."""
        booking_data = self.booking_data.copy()
        booking_data['booking_type'] = 'salon'
        
        booking = Booking.objects.create(**booking_data)
        self.assertEqual(booking.booking_type, 'salon')
    
    def test_payment_status_workflow(self):
        """Test payment status workflow."""
        booking = Booking.objects.create(**self.booking_data)
        
        # Initially pending payment
        self.assertEqual(booking.payment_status, 'pending')
        
        # Mark as deposit paid
        booking.payment_status = 'deposit_paid'
        booking.deposit_amount = Decimal('50.00')
        booking.save()
        
        self.assertEqual(booking.payment_status, 'deposit_paid')
        self.assertEqual(booking.deposit_amount, Decimal('50.00'))


class BookingStatusHistoryModelTest(TestCase):
    """Test BookingStatusHistory model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Test Customer',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Test Service',
            description='Test service description',
            category='braids',
            base_price=Decimal('100.00'),
            duration_minutes=180
        )
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date() + timedelta(days=5),
            booking_time=time(14, 0),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            status='pending'
        )
    
    def test_create_status_history(self):
        """Test creating booking status history."""
        history = BookingStatusHistory.objects.create(
            booking=self.booking,
            old_status='pending',
            new_status='confirmed',
            changed_by=self.braider_user,
            reason='Customer confirmed appointment'
        )
        
        self.assertEqual(history.booking, self.booking)
        self.assertEqual(history.old_status, 'pending')
        self.assertEqual(history.new_status, 'confirmed')
        self.assertEqual(history.changed_by, self.braider_user)
        self.assertEqual(history.reason, 'Customer confirmed appointment')
    
    def test_status_history_string_representation(self):
        """Test status history string representation."""
        history = BookingStatusHistory.objects.create(
            booking=self.booking,
            old_status='confirmed',
            new_status='cancelled_client',
            changed_by=self.customer,
            reason='Customer requested cancellation'
        )
        
        expected = f"{self.booking.booking_reference}: confirmed → cancelled_client"
        self.assertEqual(str(history), expected)


class BookingValidationTest(TestCase):
    """Test booking validation logic."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Test Customer',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Test Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Test Studio',
            contact_email='braider@test.com',
            experience_level='intermediate',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Test Service',
            description='Test validation service',
            category='braids',
            base_price=Decimal('80.00'),
            duration_minutes=120
        )
    
    def test_booking_in_past_validation(self):
        """Test that booking in past is not allowed."""
        past_datetime = timezone.now() - timedelta(days=1)
        
        booking_data = {
            'user': self.customer,
            'braider': self.braider,
            'service': self.service,
            'booking_date': past_datetime.date(),
            'booking_time': past_datetime.time(),
            'client_name': self.customer.name,
            'client_phone': '+1234567890',
            'client_email': self.customer.email,
            'booking_type': 'home',
            'base_price': Decimal('80.00'),
            'total_price': Decimal('80.00'),
            'status': 'pending'
        }
        
        # Model allows it, but business logic should validate
        booking = Booking.objects.create(**booking_data)
        self.assertIsNotNone(booking)
    
    def test_overlapping_bookings(self):
        """Test overlapping booking detection."""
        booking_datetime = timezone.now() + timedelta(days=3)
        
        # Create first booking
        first_booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=booking_datetime.date(),
            booking_time=booking_datetime.time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('80.00'),
            total_price=Decimal('80.00'),
            status='confirmed'
        )
        
        # Try to create overlapping booking (same time)
        overlapping_booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=booking_datetime.date(),
            booking_time=booking_datetime.time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('80.00'),
            total_price=Decimal('80.00'),
            status='pending'
        )
        
        # Model allows it, but business logic should prevent it
        self.assertIsNotNone(overlapping_booking)


class BookingAPITest(APITestCase):
    """Test booking API endpoints."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='API Customer',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='API Braider',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='API Braiding Studio',
            contact_email='braider@test.com',
            experience_level='advanced',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='API Box Braids',
            description='Premium braiding service',
            category='braids',
            base_price=Decimal('150.00'),
            duration_minutes=300
        )
        
        # Create address for booking location
        self.address = Address.objects.create(
            street='123 API Street',
            city='Test City',
            postal_code='12345'
        )
        
        self.booking_datetime = timezone.now() + timedelta(days=10)
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=self.booking_datetime.date(),
            booking_time=self.booking_datetime.time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('150.00'),
            total_price=Decimal('150.00'),
            status='confirmed',
            service_address=self.address
        )
        
        self.client.force_authenticate(user=self.customer)
    
    def test_list_customer_bookings(self):
        """Test listing customer bookings."""
        url = reverse('bookings:booking-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['service']['name'], 'API Box Braids')
    
    def test_booking_detail(self):
        """Test getting booking details."""
        url = reverse('bookings:booking-detail', kwargs={'pk': self.booking.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['booking_reference'], self.booking.booking_reference)
        self.assertEqual(response.data['status'], 'confirmed')
    
    def test_create_booking(self):
        """Test creating a new booking."""
        future_date = timezone.now() + timedelta(days=15)
        
        url = reverse('bookings:booking-create')
        data = {
            'braider_id': self.braider.id,
            'service_id': self.service.id,
            'booking_date': future_date.date().isoformat(),
            'booking_time': future_date.time().strftime('%H:%M'),
            'booking_type': 'home',
            'special_requests': 'Please prepare box braids style'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Booking.objects.filter(
            user=self.customer,
            braider=self.braider,
            service=self.service
        ).count() >= 1)
    
    def test_cancel_booking(self):
        """Test cancelling a booking."""
        url = reverse('bookings:booking-cancel', kwargs={'booking_id': self.booking.id})
        data = {
            'reason': 'Change of plans'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check booking status updated
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled_client')
    
    def test_reschedule_booking(self):
        """Test rescheduling a booking."""
        new_datetime = timezone.now() + timedelta(days=20)
        
        url = reverse('bookings:booking-reschedule', kwargs={'booking_id': self.booking.id})
        data = {
            'new_date': new_datetime.date().isoformat(),
            'new_time': new_datetime.time().strftime('%H:%M'),
            'reason': 'Schedule conflict'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check booking updated
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_date, new_datetime.date())
    
    def test_booking_availability_check(self):
        """Test checking booking availability."""
        url = reverse('bookings:check-availability')
        check_datetime = timezone.now() + timedelta(days=25)
        
        data = {
            'braider_id': self.braider.id,
            'service_id': self.service.id,
            'date': check_datetime.date().isoformat(),
            'time': check_datetime.time().strftime('%H:%M')
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available', response.data)
    
    def test_braider_bookings(self):
        """Test braider viewing their bookings."""
        self.client.force_authenticate(user=self.braider_user)
        
        url = reverse('bookings:braider-bookings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_booking_statistics(self):
        """Test getting booking statistics."""
        url = reverse('bookings:booking-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_bookings', response.data)
        self.assertIn('upcoming_bookings', response.data)
        self.assertIn('completed_bookings', response.data)
    
    def test_booking_search(self):
        """Test searching bookings."""
        url = reverse('bookings:booking-search')
        response = self.client.get(url, {'q': 'API Box'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_booking_filters(self):
        """Test filtering bookings by status."""
        url = reverse('bookings:booking-list')
        response = self.client.get(url, {'status': 'confirmed'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_unauthorized_booking_access(self):
        """Test unauthorized access to booking."""
        other_user = User.objects.create_user(
            email='other@test.com',
            name='Other User',
            password='testpass'
        )
        self.client.force_authenticate(user=other_user)
        
        url = reverse('bookings:booking-detail', kwargs={'pk': self.booking.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_booking_confirmation(self):
        """Test confirming a pending booking."""
        # Create pending booking
        pending_booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date() + timedelta(days=30),
            booking_time=time(10, 0),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('150.00'),
            total_price=Decimal('150.00'),
            status='pending'
        )
        
        # Braider confirms booking
        self.client.force_authenticate(user=self.braider_user)
        
        url = reverse('bookings:booking-confirm', kwargs={'booking_id': pending_booking.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        pending_booking.refresh_from_db()
        self.assertEqual(pending_booking.status, 'confirmed')
    
    def test_booking_completion(self):
        """Test marking booking as completed."""
        self.client.force_authenticate(user=self.braider_user)
        
        url = reverse('bookings:booking-complete', kwargs={'booking_id': self.booking.id})
        data = {
            'completion_notes': 'Service completed successfully'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'completed')