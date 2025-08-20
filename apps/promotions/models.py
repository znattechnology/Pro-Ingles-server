"""
Models for promotions, campaigns, and discount system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_DOWN
import uuid
import string
import random

from apps.core.models import BaseModel

User = get_user_model()


class Campaign(BaseModel):
    """
    Marketing campaigns that can contain multiple promotions.
    """
    
    CAMPAIGN_TYPES = [
        ('seasonal', 'Seasonal Campaign'),
        ('new_user', 'New User Campaign'),
        ('retention', 'User Retention'),
        ('product_launch', 'Product Launch'),
        ('referral', 'Referral Program'),
        ('loyalty', 'Loyalty Program'),
        ('flash_sale', 'Flash Sale'),
        ('general', 'General Promotion'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Campaign identification
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, default='general')
    
    # Campaign timing
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Campaign targeting
    target_audience = models.JSONField(
        default=dict, 
        help_text="Target audience criteria (user roles, locations, etc.)"
    )
    max_participants = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Maximum number of users who can participate"
    )
    
    # Campaign limits
    total_budget = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Total budget allocated for this campaign"
    )
    current_spend = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Current amount spent on this campaign"
    )
    
    # Analytics
    total_views = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)
    
    # Display settings
    banner_image = models.ImageField(upload_to='campaigns/banners/', null=True, blank=True)
    banner_text = models.CharField(max_length=500, blank=True)
    call_to_action = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['campaign_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
        
        if self.total_budget and self.current_spend > self.total_budget:
            raise ValidationError("Current spend cannot exceed total budget")
    
    @property
    def is_running(self):
        """Check if campaign is currently running."""
        now = timezone.now()
        return (
            self.is_active and 
            self.status == 'active' and
            self.start_date <= now <= self.end_date
        )
    
    @property
    def participation_count(self):
        """Get current number of participants."""
        return self.participants.filter(is_active=True).count()
    
    @property
    def budget_remaining(self):
        """Get remaining budget."""
        if not self.total_budget:
            return None
        return max(Decimal('0.00'), self.total_budget - self.current_spend)
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate."""
        if self.total_clicks == 0:
            return 0
        return round((self.total_conversions / self.total_clicks) * 100, 2)
    
    def can_participate(self, user):
        """Check if user can participate in this campaign."""
        if not self.is_running:
            return False, "Campaign is not active"
        
        # Check if already participating
        if self.participants.filter(user=user, is_active=True).exists():
            return False, "Already participating in this campaign"
        
        # Check max participants
        if self.max_participants and self.participation_count >= self.max_participants:
            return False, "Campaign has reached maximum participants"
        
        # Check target audience criteria
        if not self._matches_target_audience(user):
            return False, "Not in target audience"
        
        return True, "Can participate"
    
    def _matches_target_audience(self, user):
        """Check if user matches target audience criteria."""
        if not self.target_audience:
            return True  # No restrictions
        
        # Check user role
        if 'roles' in self.target_audience:
            if user.role not in self.target_audience['roles']:
                return False
        
        # Check user location (if available)
        if 'locations' in self.target_audience and hasattr(user, 'address'):
            user_location = getattr(user.address, 'city', None)
            if user_location not in self.target_audience['locations']:
                return False
        
        # Check new user criteria
        if 'new_users_only' in self.target_audience:
            days_since_registration = (timezone.now() - user.created_at).days
            max_days = self.target_audience.get('new_user_max_days', 30)
            if days_since_registration > max_days:
                return False
        
        return True
    
    def add_participant(self, user):
        """Add user as campaign participant."""
        can_participate, reason = self.can_participate(user)
        if not can_participate:
            raise ValidationError(reason)
        
        participant, created = CampaignParticipant.objects.get_or_create(
            campaign=self,
            user=user,
            defaults={'is_active': True}
        )
        
        if not created and not participant.is_active:
            participant.is_active = True
            participant.save(update_fields=['is_active'])
        
        return participant


class Promotion(BaseModel):
    """
    Individual promotions that belong to campaigns.
    """
    
    PROMOTION_TYPES = [
        ('percentage', 'Percentage Discount'),
        ('fixed_amount', 'Fixed Amount Discount'),
        ('free_shipping', 'Free Shipping'),
        ('buy_x_get_y', 'Buy X Get Y'),
        ('first_booking', 'First Booking Discount'),
        ('loyalty_points', 'Loyalty Points Multiplier'),
        ('referral_bonus', 'Referral Bonus'),
    ]
    
    APPLIES_TO = [
        ('all', 'All Services'),
        ('category', 'Service Category'),
        ('service', 'Specific Service'),
        ('braider', 'Specific Braider'),
        ('order_total', 'Order Total'),
    ]
    
    # Promotion identification
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='promotions'
    )
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Promotion code users can enter"
    )
    description = models.TextField()
    
    # Promotion configuration
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES)
    applies_to = models.CharField(max_length=20, choices=APPLIES_TO, default='all')
    
    # Discount values
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount amount for percentage discounts"
    )
    
    # Conditions
    minimum_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum order amount to qualify"
    )
    maximum_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum order amount to qualify"
    )
    
    # Usage limits
    usage_limit_per_user = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Maximum uses per user"
    )
    total_usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Maximum total uses across all users"
    )
    current_usage_count = models.PositiveIntegerField(default=0)
    
    # Targeting
    target_services = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of service IDs this promotion applies to"
    )
    target_categories = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of service categories this promotion applies to"
    )
    target_braiders = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of braider IDs this promotion applies to"
    )
    
    # Buy X Get Y configuration
    buy_quantity = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Quantity to buy for Buy X Get Y promotions"
    )
    get_quantity = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Quantity to get free for Buy X Get Y promotions"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_stackable = models.BooleanField(
        default=False,
        help_text="Can be combined with other promotions"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['promotion_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['campaign', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        # Validate promotion type specific fields
        if self.promotion_type == 'percentage' and not self.discount_percentage:
            raise ValidationError("Percentage discount requires discount_percentage")
        
        if self.promotion_type == 'fixed_amount' and not self.discount_amount:
            raise ValidationError("Fixed amount discount requires discount_amount")
        
        if self.promotion_type == 'buy_x_get_y':
            if not self.buy_quantity or not self.get_quantity:
                raise ValidationError("Buy X Get Y requires both buy_quantity and get_quantity")
        
        # Validate order amount ranges
        if (self.minimum_order_amount and self.maximum_order_amount and 
            self.minimum_order_amount >= self.maximum_order_amount):
            raise ValidationError("Maximum order amount must be greater than minimum")
    
    @classmethod
    def generate_unique_code(cls, length=8):
        """Generate a unique promotion code."""
        characters = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(characters, k=length))
            if not cls.objects.filter(code=code).exists():
                return code
    
    def can_be_used(self, user, order_amount=None):
        """Check if promotion can be used by user."""
        # Check if promotion and campaign are active
        if not self.is_active or not self.campaign.is_running:
            return False, "Promotion is not active"
        
        # Check campaign participation
        can_participate, reason = self.campaign.can_participate(user)
        if not can_participate and reason != "Already participating in this campaign":
            return False, reason
        
        # Check usage limits
        if self.total_usage_limit and self.current_usage_count >= self.total_usage_limit:
            return False, "Promotion usage limit reached"
        
        if self.usage_limit_per_user:
            user_usage = self.usages.filter(user=user).count()
            if user_usage >= self.usage_limit_per_user:
                return False, "Personal usage limit reached"
        
        # Check order amount conditions
        if order_amount:
            if self.minimum_order_amount and order_amount < self.minimum_order_amount:
                return False, f"Minimum order amount is €{self.minimum_order_amount}"
            
            if self.maximum_order_amount and order_amount > self.maximum_order_amount:
                return False, f"Maximum order amount is €{self.maximum_order_amount}"
        
        return True, "Can be used"
    
    def calculate_discount(self, order_amount, items=None):
        """
        Calculate discount amount for given order.
        
        Args:
            order_amount: Total order amount
            items: List of order items (for item-specific promotions)
        
        Returns:
            Decimal: Discount amount
        """
        if self.promotion_type == 'percentage':
            discount = order_amount * (self.discount_percentage / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        
        elif self.promotion_type == 'fixed_amount':
            return min(self.discount_amount, order_amount)
        
        elif self.promotion_type == 'free_shipping':
            # This would need to be calculated based on shipping costs
            # For now, return a standard shipping amount
            return Decimal('5.00')  # Standard shipping cost
        
        elif self.promotion_type == 'buy_x_get_y' and items:
            # Calculate discount based on eligible items
            eligible_items = self._get_eligible_items(items)
            if len(eligible_items) >= self.buy_quantity:
                # Find cheapest items to give free
                sorted_items = sorted(eligible_items, key=lambda x: x.get('price', 0))
                free_items_count = min(
                    self.get_quantity,
                    len(eligible_items) - self.buy_quantity
                )
                discount = sum(
                    Decimal(str(item.get('price', 0))) 
                    for item in sorted_items[:free_items_count]
                )
                return discount
        
        return Decimal('0.00')
    
    def _get_eligible_items(self, items):
        """Get items eligible for this promotion."""
        if self.applies_to == 'all':
            return items
        
        eligible = []
        for item in items:
            if self.applies_to == 'service' and item.get('service_id') in self.target_services:
                eligible.append(item)
            elif self.applies_to == 'category' and item.get('category') in self.target_categories:
                eligible.append(item)
            elif self.applies_to == 'braider' and item.get('braider_id') in self.target_braiders:
                eligible.append(item)
        
        return eligible


class CouponCode(BaseModel):
    """
    Individual coupon codes that can be generated for promotions.
    """
    
    promotion = models.ForeignKey(
        Promotion, 
        on_delete=models.CASCADE, 
        related_name='coupon_codes'
    )
    code = models.CharField(max_length=50, unique=True)
    
    # Usage tracking
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_coupons'
    )
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment (for personalized coupons)
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_coupons'
    )
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['promotion', 'is_used']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Coupon {self.code} for {self.promotion.name}"
    
    @property
    def is_expired(self):
        """Check if coupon is expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if coupon is valid for use."""
        return not self.is_used and not self.is_expired
    
    def can_be_used_by(self, user):
        """Check if coupon can be used by specific user."""
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        if self.assigned_to and self.assigned_to != user:
            return False, "Coupon is assigned to another user"
        
        return self.promotion.can_be_used(user)
    
    def use(self, user):
        """Mark coupon as used."""
        if not self.is_valid:
            raise ValidationError("Cannot use invalid coupon")
        
        if self.assigned_to and self.assigned_to != user:
            raise ValidationError("Coupon is assigned to another user")
        
        self.is_used = True
        self.used_by = user
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_by', 'used_at'])


class CampaignParticipant(BaseModel):
    """
    Track users who participate in campaigns.
    """
    
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='participants'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='campaign_participations'
    )
    
    # Participation details
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Analytics
    total_views = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)
    total_discount_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    class Meta:
        unique_together = ['campaign', 'user']
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['campaign', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} in {self.campaign.name}"


class PromotionUsage(BaseModel):
    """
    Track individual uses of promotions.
    """
    
    promotion = models.ForeignKey(
        Promotion, 
        on_delete=models.CASCADE, 
        related_name='usages'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='promotion_usages'
    )
    
    # Usage details
    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Related objects
    booking = models.ForeignKey(
        'bookings.Booking', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='promotion_usages'
    )
    coupon_code = models.ForeignKey(
        CouponCode, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='usages'
    )
    
    # Analytics
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['promotion', 'user']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['booking']),
        ]
    
    def __str__(self):
        return f"{self.user.email} used {self.promotion.code} - €{self.discount_amount} discount"
    
    def save(self, *args, **kwargs):
        # Update promotion usage count
        if not self.pk:  # Only on creation
            self.promotion.current_usage_count = models.F('current_usage_count') + 1
            self.promotion.save(update_fields=['current_usage_count'])
            
            # Update campaign spend
            self.promotion.campaign.current_spend = models.F('current_spend') + self.discount_amount
            self.promotion.campaign.save(update_fields=['current_spend'])
        
        super().save(*args, **kwargs)