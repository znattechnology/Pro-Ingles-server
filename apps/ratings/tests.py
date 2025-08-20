"""
Tests for ratings and reviews functionality including braider and product reviews.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta

from .models import (
    BraiderReview, ProductReview, ReviewImage, ReviewHelpfulness,
    ReviewResponse, ReviewReport
)
from apps.braiders.models import Braider, Service
from apps.ecommerce.models import Product, ProductCategory, Order, OrderItem
from apps.bookings.models import Booking

User = get_user_model()


class BraiderReviewModelTest(TestCase):
    """Test BraiderReview model functionality."""
    
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
            description='Professional box braids service',
            category='braids',
            base_price=Decimal('100.00'),
            duration_minutes=240
        )
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date(),
            booking_time=timezone.now().time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('100.00'),
            total_price=Decimal('100.00'),
            status='completed'
        )
    
    def test_create_braider_review(self):
        """Test creating a braider review."""
        review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=5,
            quality_rating=5,
            punctuality_rating=4,
            professionalism_rating=5,
            value_rating=4,
            title='Excellent Service',
            review_text='Amazing braiding skills! Very professional and on time.',
            would_recommend=True
        )
        
        self.assertEqual(review.user, self.customer)
        self.assertEqual(review.braider, self.braider)
        self.assertEqual(review.overall_rating, 5)
        self.assertEqual(review.title, 'Excellent Service')
        self.assertTrue(review.would_recommend)
        self.assertEqual(review.status, 'pending')
    
    def test_braider_review_string_representation(self):
        """Test braider review string representation."""
        review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=4,
            title='Good Service'
        )
        
        expected = f"4⭐ review for Test Braiding Studio by Test Customer"
        self.assertEqual(str(review), expected)
    
    def test_braider_review_validation(self):
        """Test braider review validation."""
        # Test rating validation (should be between 1-5)
        with self.assertRaises(ValidationError):
            review = BraiderReview(
                user=self.customer,
                braider=self.braider,
                booking=self.booking,
                overall_rating=6  # Invalid rating
            )
            review.full_clean()
    
    def test_braider_review_approval(self):
        """Test braider review approval process."""
        review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=5,
            title='Great Experience'
        )
        
        # Initially pending
        self.assertEqual(review.status, 'pending')
        
        # Approve review
        review.status = 'approved'
        review.save()
        
        self.assertEqual(review.status, 'approved')


class ProductReviewModelTest(TestCase):
    """Test ProductReview model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Product Customer',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Hair Products',
            slug='hair-products'
        )
        
        self.product = Product.objects.create(
            name='Premium Hair Oil',
            slug='premium-hair-oil',
            category=self.category,
            base_price=Decimal('29.99'),
            stock_quantity=50
        )
        
        self.order = Order.objects.create(
            user=self.customer,
            order_reference='ORD-2024-001',
            total_amount=Decimal('29.99'),
            status='delivered'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=Decimal('29.99')
        )
    
    def test_create_product_review(self):
        """Test creating a product review."""
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            order=self.order,
            rating=4,
            title='Good Quality Oil',
            review_text='This hair oil works well for my hair type. Good value for money.',
            would_recommend=True
        )
        
        self.assertEqual(review.user, self.customer)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.title, 'Good Quality Oil')
        self.assertTrue(review.would_recommend)
    
    def test_product_review_string_representation(self):
        """Test product review string representation."""
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            order=self.order,
            rating=5,
            title='Excellent Product'
        )
        
        expected = f"5⭐ review for Premium Hair Oil by Product Customer"
        self.assertEqual(str(review), expected)
    
    def test_product_review_without_order(self):
        """Test creating product review without order (general review)."""
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=3,
            title='Average Product',
            review_text='It\'s okay, nothing special.'
        )
        
        self.assertIsNone(review.order)
        self.assertEqual(review.rating, 3)


class ReviewImageModelTest(TestCase):
    """Test ReviewImage model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Image Customer',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('25.00')
        )
        
        self.review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=5,
            title='Great with Photos'
        )
    
    def test_create_review_image(self):
        """Test creating a review image."""
        image = ReviewImage.objects.create(
            review=self.review,
            image='reviews/test_image.jpg',
            caption='Product in use',
            is_verified=True
        )
        
        self.assertEqual(image.review, self.review)
        self.assertEqual(image.caption, 'Product in use')
        self.assertTrue(image.is_verified)
    
    def test_review_image_string_representation(self):
        """Test review image string representation."""
        image = ReviewImage.objects.create(
            review=self.review,
            image='reviews/sample.jpg',
            caption='Sample photo'
        )
        
        expected = f"Image for review: Great with Photos"
        self.assertEqual(str(image), expected)


class ReviewHelpfulnessModelTest(TestCase):
    """Test ReviewHelpfulness model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Review Customer',
            password='testpass'
        )
        
        self.voter = User.objects.create_user(
            email='voter@test.com',
            name='Review Voter',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('30.00')
        )
        
        self.review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=4,
            title='Helpful Review'
        )
    
    def test_create_review_helpfulness(self):
        """Test creating review helpfulness vote."""
        helpfulness = ReviewHelpfulness.objects.create(
            review=self.review,
            user=self.voter,
            is_helpful=True
        )
        
        self.assertEqual(helpfulness.review, self.review)
        self.assertEqual(helpfulness.user, self.voter)
        self.assertTrue(helpfulness.is_helpful)
    
    def test_review_helpfulness_string_representation(self):
        """Test review helpfulness string representation."""
        helpfulness = ReviewHelpfulness.objects.create(
            review=self.review,
            user=self.voter,
            is_helpful=False
        )
        
        expected = f"Review Voter voted 'not helpful' on Helpful Review"
        self.assertEqual(str(helpfulness), expected)


class ReviewResponseModelTest(TestCase):
    """Test ReviewResponse model functionality."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='customer@test.com',
            name='Review Customer',
            password='testpass'
        )
        
        self.braider_user = User.objects.create_user(
            email='braider@test.com',
            name='Braider User',
            password='testpass'
        )
        
        self.braider = Braider.objects.create(
            user=self.braider_user,
            name='Response Studio',
            contact_email='braider@test.com',
            experience_level='advanced',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='Test Service',
            description='Test service for reviews',
            category='braids',
            base_price=Decimal('75.00'),
            duration_minutes=180
        )
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date(),
            booking_time=timezone.now().time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('75.00'),
            total_price=Decimal('75.00'),
            status='completed'
        )
        
        self.review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=4,
            title='Good Service'
        )
    
    def test_create_review_response(self):
        """Test creating a review response."""
        response = ReviewResponse.objects.create(
            review=self.review,
            responder=self.braider_user,
            response_text='Thank you for your feedback! We appreciate your business.',
            is_public=True
        )
        
        self.assertEqual(response.review, self.review)
        self.assertEqual(response.responder, self.braider_user)
        self.assertTrue(response.is_public)
    
    def test_review_response_string_representation(self):
        """Test review response string representation."""
        response = ReviewResponse.objects.create(
            review=self.review,
            responder=self.braider_user,
            response_text='Thanks for the review!'
        )
        
        expected = f"Response to 'Good Service' by Braider User"
        self.assertEqual(str(response), expected)


class ReviewReportModelTest(TestCase):
    """Test ReviewReport model functionality."""
    
    def setUp(self):
        self.reviewer = User.objects.create_user(
            email='reviewer@test.com',
            name='Reviewer',
            password='testpass'
        )
        
        self.reporter = User.objects.create_user(
            email='reporter@test.com',
            name='Reporter',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('35.00')
        )
        
        self.review = ProductReview.objects.create(
            user=self.reviewer,
            product=self.product,
            rating=1,
            title='Suspicious Review',
            review_text='This might be inappropriate content'
        )
    
    def test_create_review_report(self):
        """Test creating a review report."""
        report = ReviewReport.objects.create(
            review=self.review,
            reported_by=self.reporter,
            reason='inappropriate',
            description='Contains inappropriate language',
            status='pending'
        )
        
        self.assertEqual(report.review, self.review)
        self.assertEqual(report.reported_by, self.reporter)
        self.assertEqual(report.reason, 'inappropriate')
        self.assertEqual(report.status, 'pending')
    
    def test_review_report_string_representation(self):
        """Test review report string representation."""
        report = ReviewReport.objects.create(
            review=self.review,
            reported_by=self.reporter,
            reason='spam',
            description='Looks like spam content'
        )
        
        expected = f"Report: 'Suspicious Review' - spam (pending)"
        self.assertEqual(str(report), expected)


class RatingsAPITest(APITestCase):
    """Test ratings and reviews API endpoints."""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            email='api@test.com',
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
            experience_level='expert',
            status='approved'
        )
        
        self.service = Service.objects.create(
            braider=self.braider,
            name='API Service',
            description='API test service',
            category='braids',
            base_price=Decimal('90.00'),
            duration_minutes=240
        )
        
        self.booking = Booking.objects.create(
            user=self.customer,
            braider=self.braider,
            service=self.service,
            booking_date=timezone.now().date(),
            booking_time=timezone.now().time(),
            client_name=self.customer.name,
            client_phone='+1234567890',
            client_email=self.customer.email,
            booking_type='home',
            base_price=Decimal('90.00'),
            total_price=Decimal('90.00'),
            status='completed'
        )
        
        self.category = ProductCategory.objects.create(
            name='API Category',
            slug='api-category'
        )
        
        self.product = Product.objects.create(
            name='API Product',
            slug='api-product',
            category=self.category,
            base_price=Decimal('40.00')
        )
        
        self.client.force_authenticate(user=self.customer)
    
    def test_create_braider_review(self):
        """Test creating braider review via API."""
        url = reverse('ratings:braider-review-create')
        data = {
            'braider_id': self.braider.id,
            'booking_id': self.booking.id,
            'overall_rating': 5,
            'quality_rating': 5,
            'punctuality_rating': 4,
            'professionalism_rating': 5,
            'value_rating': 4,
            'title': 'Excellent API Service',
            'review_text': 'Amazing braiding skills via API test!',
            'would_recommend': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check review was created
        review = BraiderReview.objects.get(id=response.data['id'])
        self.assertEqual(review.overall_rating, 5)
        self.assertEqual(review.title, 'Excellent API Service')
    
    def test_create_product_review(self):
        """Test creating product review via API."""
        url = reverse('ratings:product-review-create')
        data = {
            'product_id': self.product.id,
            'rating': 4,
            'title': 'Good API Product',
            'review_text': 'This product works well for API testing.',
            'would_recommend': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check review was created
        review = ProductReview.objects.get(id=response.data['id'])
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.title, 'Good API Product')
    
    def test_list_braider_reviews(self):
        """Test listing braider reviews."""
        # Create review first
        review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=5,
            title='API Test Review',
            status='approved'
        )
        
        url = reverse('ratings:braider-reviews', kwargs={'braider_id': self.braider.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Test Review')
    
    def test_list_product_reviews(self):
        """Test listing product reviews."""
        # Create review first
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=4,
            title='API Product Review',
            status='approved'
        )
        
        url = reverse('ratings:product-reviews', kwargs={'product_id': self.product.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Product Review')
    
    def test_review_helpfulness_vote(self):
        """Test voting on review helpfulness."""
        # Create review first
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=5,
            title='Helpful Review',
            status='approved'
        )
        
        # Create another user to vote
        voter = User.objects.create_user(
            email='voter@test.com',
            name='Voter',
            password='testpass'
        )
        self.client.force_authenticate(user=voter)
        
        url = reverse('ratings:review-helpful', kwargs={'review_id': review.id})
        data = {'is_helpful': True}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check vote was recorded
        helpfulness = ReviewHelpfulness.objects.get(review=review, user=voter)
        self.assertTrue(helpfulness.is_helpful)
    
    def test_review_response(self):
        """Test braider responding to review."""
        # Create review first
        review = BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=4,
            title='Good Service',
            status='approved'
        )
        
        # Braider responds
        self.client.force_authenticate(user=self.braider_user)
        
        url = reverse('ratings:review-response', kwargs={'review_id': review.id})
        data = {
            'response_text': 'Thank you for the feedback!',
            'is_public': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response was created
        review_response = ReviewResponse.objects.get(review=review)
        self.assertEqual(review_response.response_text, 'Thank you for the feedback!')
    
    def test_report_review(self):
        """Test reporting a review."""
        # Create review to report
        review = ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=1,
            title='Suspicious Review',
            review_text='This might be spam',
            status='approved'
        )
        
        # Another user reports the review
        reporter = User.objects.create_user(
            email='reporter@test.com',
            name='Reporter',
            password='testpass'
        )
        self.client.force_authenticate(user=reporter)
        
        url = reverse('ratings:report-review', kwargs={'review_id': review.id})
        data = {
            'reason': 'spam',
            'description': 'This looks like spam content'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check report was created
        report = ReviewReport.objects.get(review=review)
        self.assertEqual(report.reason, 'spam')
    
    def test_review_statistics(self):
        """Test getting review statistics."""
        url = reverse('ratings:review-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_reviews', response.data)
        self.assertIn('average_rating', response.data)
    
    def test_user_reviews(self):
        """Test getting user's own reviews."""
        # Create user reviews
        BraiderReview.objects.create(
            user=self.customer,
            braider=self.braider,
            booking=self.booking,
            overall_rating=5,
            title='My Braider Review'
        )
        
        ProductReview.objects.create(
            user=self.customer,
            product=self.product,
            rating=4,
            title='My Product Review'
        )
        
        url = reverse('ratings:user-reviews')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('braider_reviews', response.data)
        self.assertIn('product_reviews', response.data)
    
    def test_unauthorized_review_creation(self):
        """Test unauthorized review creation."""
        self.client.force_authenticate(user=None)
        
        url = reverse('ratings:product-review-create')
        data = {
            'product_id': self.product.id,
            'rating': 3,
            'title': 'Unauthorized Review'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)