"""
Tests for promotions system.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta

from .models import Campaign, Promotion, CouponCode, CampaignParticipant, PromotionUsage

User = get_user_model()


class CampaignModelTest(TestCase):
    """Test Campaign model functionality."""
    
    def setUp(self):
        self.campaign_data = {
            'name': 'Test Campaign',
            'slug': 'test-campaign',
            'campaign_type': 'seasonal',
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(days=30),
            'is_active': True,
            'status': 'active'
        }
    
    def test_create_campaign(self):
        """Test creating a campaign."""
        campaign = Campaign.objects.create(**self.campaign_data)
        
        self.assertEqual(campaign.name, self.campaign_data['name'])
        self.assertEqual(campaign.campaign_type, self.campaign_data['campaign_type'])
        self.assertTrue(campaign.is_active)
        self.assertEqual(str(campaign), self.campaign_data['name'])
    
    def test_campaign_is_running(self):
        """Test campaign is_running property."""
        campaign = Campaign.objects.create(**self.campaign_data)
        self.assertTrue(campaign.is_running)
        
        # Test past campaign
        campaign.end_date = timezone.now() - timedelta(days=1)
        campaign.save()
        self.assertFalse(campaign.is_running)
    
    def test_campaign_participation_count(self):
        """Test campaign participation count."""
        campaign = Campaign.objects.create(**self.campaign_data)
        user1 = User.objects.create_user(email='user1@test.com', name='User 1', password='pass')
        user2 = User.objects.create_user(email='user2@test.com', name='User 2', password='pass')
        
        self.assertEqual(campaign.participation_count, 0)
        
        CampaignParticipant.objects.create(campaign=campaign, user=user1)
        CampaignParticipant.objects.create(campaign=campaign, user=user2)
        
        self.assertEqual(campaign.participation_count, 2)
    
    def test_can_participate(self):
        """Test campaign participation eligibility."""
        campaign = Campaign.objects.create(**self.campaign_data)
        user = User.objects.create_user(email='test@test.com', name='Test User', password='pass')
        
        can_participate, reason = campaign.can_participate(user)
        self.assertTrue(can_participate)
        
        # Test max participants limit
        campaign.max_participants = 1
        campaign.save()
        
        # Add a participant
        CampaignParticipant.objects.create(campaign=campaign, user=user)
        
        user2 = User.objects.create_user(email='test2@test.com', name='Test User 2', password='pass')
        can_participate, reason = campaign.can_participate(user2)
        self.assertFalse(can_participate)
        self.assertIn('maximum participants', reason)


class PromotionModelTest(TestCase):
    """Test Promotion model functionality."""
    
    def setUp(self):
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            slug='test-campaign',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            status='active'
        )
        
        self.user = User.objects.create_user(
            email='test@test.com',
            name='Test User',
            password='testpass'
        )
    
    def test_create_percentage_promotion(self):
        """Test creating a percentage discount promotion."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='10% Off',
            code='TEST10',
            promotion_type='percentage',
            discount_percentage=Decimal('10.00'),
            is_active=True
        )
        
        self.assertEqual(promotion.name, '10% Off')
        self.assertEqual(promotion.code, 'TEST10')
        self.assertEqual(promotion.discount_percentage, Decimal('10.00'))
    
    def test_create_fixed_amount_promotion(self):
        """Test creating a fixed amount discount promotion."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='€5 Off',
            code='SAVE5',
            promotion_type='fixed_amount',
            discount_amount=Decimal('5.00'),
            is_active=True
        )
        
        self.assertEqual(promotion.discount_amount, Decimal('5.00'))
    
    def test_calculate_percentage_discount(self):
        """Test percentage discount calculation."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='20% Off',
            code='TEST20',
            promotion_type='percentage',
            discount_percentage=Decimal('20.00'),
            is_active=True
        )
        
        order_amount = Decimal('100.00')
        discount = promotion.calculate_discount(order_amount)
        self.assertEqual(discount, Decimal('20.00'))
    
    def test_calculate_fixed_discount(self):
        """Test fixed amount discount calculation."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='€10 Off',
            code='SAVE10',
            promotion_type='fixed_amount',
            discount_amount=Decimal('10.00'),
            is_active=True
        )
        
        order_amount = Decimal('50.00')
        discount = promotion.calculate_discount(order_amount)
        self.assertEqual(discount, Decimal('10.00'))
        
        # Test discount doesn't exceed order amount
        small_order = Decimal('5.00')
        discount = promotion.calculate_discount(small_order)
        self.assertEqual(discount, Decimal('5.00'))
    
    def test_max_discount_amount(self):
        """Test maximum discount amount for percentage promotions."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='50% Off (Max €20)',
            code='MAX20',
            promotion_type='percentage',
            discount_percentage=Decimal('50.00'),
            max_discount_amount=Decimal('20.00'),
            is_active=True
        )
        
        # Large order should be capped at max discount
        large_order = Decimal('100.00')
        discount = promotion.calculate_discount(large_order)
        self.assertEqual(discount, Decimal('20.00'))
        
        # Small order should get percentage discount
        small_order = Decimal('20.00')
        discount = promotion.calculate_discount(small_order)
        self.assertEqual(discount, Decimal('10.00'))
    
    def test_can_be_used(self):
        """Test promotion usage validation."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='Test Promotion',
            code='TEST',
            promotion_type='percentage',
            discount_percentage=Decimal('10.00'),
            minimum_order_amount=Decimal('20.00'),
            is_active=True
        )
        
        # Test minimum order amount
        can_use, reason = promotion.can_be_used(self.user, Decimal('10.00'))
        self.assertFalse(can_use)
        self.assertIn('Minimum order amount', reason)
        
        can_use, reason = promotion.can_be_used(self.user, Decimal('25.00'))
        self.assertTrue(can_use)
    
    def test_usage_limits(self):
        """Test promotion usage limits."""
        promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='Limited Promotion',
            code='LIMITED',
            promotion_type='percentage',
            discount_percentage=Decimal('15.00'),
            usage_limit_per_user=1,
            total_usage_limit=2,
            is_active=True
        )
        
        # First use should work
        can_use, reason = promotion.can_be_used(self.user)
        self.assertTrue(can_use)
        
        # Create usage record
        PromotionUsage.objects.create(
            promotion=promotion,
            user=self.user,
            order_amount=Decimal('50.00'),
            discount_amount=Decimal('7.50')
        )
        promotion.current_usage_count = 1
        promotion.save()
        
        # Second use by same user should fail
        can_use, reason = promotion.can_be_used(self.user)
        self.assertFalse(can_use)
        self.assertIn('Personal usage limit', reason)


class CouponCodeModelTest(TestCase):
    """Test CouponCode model functionality."""
    
    def setUp(self):
        self.campaign = Campaign.objects.create(
            name='Test Campaign',
            slug='test-campaign',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            status='active'
        )
        
        self.promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='Test Promotion',
            code='TESTPROMO',
            promotion_type='percentage',
            discount_percentage=Decimal('15.00'),
            is_active=True
        )
        
        self.user = User.objects.create_user(
            email='test@test.com',
            name='Test User',
            password='testpass'
        )
    
    def test_create_coupon_code(self):
        """Test creating a coupon code."""
        coupon = CouponCode.objects.create(
            promotion=self.promotion,
            code='UNIQUE123'
        )
        
        self.assertEqual(coupon.code, 'UNIQUE123')
        self.assertFalse(coupon.is_used)
        self.assertTrue(coupon.is_valid)
    
    def test_coupon_expiration(self):
        """Test coupon expiration."""
        expired_coupon = CouponCode.objects.create(
            promotion=self.promotion,
            code='EXPIRED',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(expired_coupon.is_expired)
        self.assertFalse(expired_coupon.is_valid)
    
    def test_use_coupon(self):
        """Test using a coupon code."""
        coupon = CouponCode.objects.create(
            promotion=self.promotion,
            code='USEME'
        )
        
        self.assertTrue(coupon.is_valid)
        
        coupon.use(self.user)
        
        self.assertTrue(coupon.is_used)
        self.assertEqual(coupon.used_by, self.user)
        self.assertIsNotNone(coupon.used_at)
        self.assertFalse(coupon.is_valid)
    
    def test_assigned_coupon(self):
        """Test assigned coupon usage."""
        coupon = CouponCode.objects.create(
            promotion=self.promotion,
            code='ASSIGNED',
            assigned_to=self.user
        )
        
        other_user = User.objects.create_user(
            email='other@test.com',
            name='Other User',
            password='testpass'
        )
        
        # Assigned user should be able to use it
        can_use, reason = coupon.can_be_used_by(self.user)
        self.assertTrue(can_use)
        
        # Other user should not be able to use it
        can_use, reason = coupon.can_be_used_by(other_user)
        self.assertFalse(can_use)
        self.assertIn('assigned to another user', reason)


class PromotionsAPITest(APITestCase):
    """Test promotions API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        
        self.campaign = Campaign.objects.create(
            name='API Test Campaign',
            slug='api-test-campaign',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            status='active'
        )
        
        self.promotion = Promotion.objects.create(
            campaign=self.campaign,
            name='API Test Promotion',
            code='APITEST',
            promotion_type='percentage',
            discount_percentage=Decimal('20.00'),
            is_active=True
        )
    
    def test_list_campaigns(self):
        """Test listing active campaigns."""
        url = reverse('promotions:campaign-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], self.campaign.name)
    
    def test_campaign_detail(self):
        """Test getting campaign details."""
        url = reverse('promotions:campaign-detail', kwargs={'slug': self.campaign.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.campaign.name)
    
    def test_list_promotions(self):
        """Test listing active promotions."""
        url = reverse('promotions:promotion-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['code'], self.promotion.code)
    
    def test_validate_coupon(self):
        """Test coupon validation endpoint."""
        url = reverse('promotions:validate-coupon')
        data = {
            'code': self.promotion.code,
            'order_amount': '100.00'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['estimated_discount'], 20.0)
    
    def test_validate_invalid_coupon(self):
        """Test validation with invalid coupon code."""
        url = reverse('promotions:validate-coupon')
        data = {
            'code': 'INVALID',
            'order_amount': '100.00'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['valid'])
    
    def test_apply_coupon(self):
        """Test applying a coupon code."""
        self.client.force_authenticate(user=self.user)
        url = reverse('promotions:apply-coupon')
        data = {
            'code': self.promotion.code,
            'order_amount': '50.00'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['discount_amount'], 10.0)  # 20% of 50
        self.assertEqual(response.data['final_amount'], 40.0)
    
    def test_join_campaign(self):
        """Test joining a campaign."""
        self.client.force_authenticate(user=self.user)
        url = reverse('promotions:join-campaign', kwargs={'campaign_id': self.campaign.id})
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify participation was created
        self.assertTrue(
            CampaignParticipant.objects.filter(
                campaign=self.campaign,
                user=self.user
            ).exists()
        )
    
    def test_active_promotions(self):
        """Test getting active promotions."""
        url = reverse('promotions:active-promotions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['campaigns']), 1)
        self.assertEqual(len(response.data['promotions']), 1)
        self.assertEqual(response.data['user_eligible_count'], 0)  # Not authenticated
    
    def test_user_promotion_stats(self):
        """Test getting user promotion statistics."""
        self.client.force_authenticate(user=self.user)
        
        # Create some usage history
        PromotionUsage.objects.create(
            promotion=self.promotion,
            user=self.user,
            order_amount=Decimal('100.00'),
            discount_amount=Decimal('20.00')
        )
        
        url = reverse('promotions:user-promotion-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_promotions_used'], 1)
        self.assertEqual(response.data['total_savings'], 20.0)