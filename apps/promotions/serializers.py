"""
Serializers for promotions system.
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from .models import Campaign, Promotion, CouponCode, CampaignParticipant, PromotionUsage


class CampaignListSerializer(serializers.ModelSerializer):
    """Serializer for campaign list view."""
    
    participation_count = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'slug', 'description', 'campaign_type',
            'start_date', 'end_date', 'is_active', 'status',
            'banner_image', 'banner_text', 'call_to_action',
            'participation_count', 'conversion_rate', 'is_running'
        ]


class CampaignDetailSerializer(serializers.ModelSerializer):
    """Serializer for campaign detail view."""
    
    participation_count = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    budget_remaining = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    promotions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'slug', 'description', 'campaign_type',
            'start_date', 'end_date', 'is_active', 'status',
            'target_audience', 'max_participants', 'total_budget',
            'current_spend', 'budget_remaining', 'banner_image',
            'banner_text', 'call_to_action', 'total_views',
            'total_clicks', 'total_conversions', 'participation_count',
            'conversion_rate', 'is_running', 'promotions_count'
        ]
    
    def get_promotions_count(self, obj):
        return obj.promotions.filter(is_active=True).count()


class PromotionListSerializer(serializers.ModelSerializer):
    """Serializer for promotion list view."""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    usage_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'code', 'description', 'campaign_name',
            'promotion_type', 'applies_to', 'discount_percentage',
            'discount_amount', 'current_usage_count', 'total_usage_limit',
            'usage_percentage', 'is_active'
        ]
    
    def get_usage_percentage(self, obj):
        if not obj.total_usage_limit:
            return 0
        return round((obj.current_usage_count / obj.total_usage_limit) * 100, 1)


class PromotionDetailSerializer(serializers.ModelSerializer):
    """Serializer for promotion detail view."""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    usage_percentage = serializers.SerializerMethodField()
    can_be_used = serializers.SerializerMethodField()
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'code', 'description', 'campaign_name',
            'promotion_type', 'applies_to', 'discount_percentage',
            'discount_amount', 'max_discount_amount', 'minimum_order_amount',
            'maximum_order_amount', 'usage_limit_per_user', 'total_usage_limit',
            'current_usage_count', 'usage_percentage', 'target_services',
            'target_categories', 'target_braiders', 'buy_quantity',
            'get_quantity', 'is_active', 'is_stackable', 'can_be_used'
        ]
    
    def get_usage_percentage(self, obj):
        if not obj.total_usage_limit:
            return 0
        return round((obj.current_usage_count / obj.total_usage_limit) * 100, 1)
    
    def get_can_be_used(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_use, reason = obj.can_be_used(request.user)
            return {'can_use': can_use, 'reason': reason}
        return {'can_use': False, 'reason': 'Authentication required'}


class CouponValidationSerializer(serializers.Serializer):
    """Serializer for coupon validation."""
    
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False
    )


class CouponApplicationSerializer(serializers.Serializer):
    """Serializer for applying coupons."""
    
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_items = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class DiscountCalculationSerializer(serializers.Serializer):
    """Serializer for discount calculation response."""
    
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    promotion_name = serializers.CharField()
    promotion_code = serializers.CharField()
    promotion_type = serializers.CharField()


class ActivePromotionsSerializer(serializers.Serializer):
    """Serializer for active promotions response."""
    
    campaigns = CampaignListSerializer(many=True)
    promotions = PromotionListSerializer(many=True)
    user_eligible_count = serializers.IntegerField()


class PromotionUsageSerializer(serializers.ModelSerializer):
    """Serializer for promotion usage tracking."""
    
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    campaign_name = serializers.CharField(source='promotion.campaign.name', read_only=True)
    
    class Meta:
        model = PromotionUsage
        fields = [
            'id', 'promotion_name', 'promotion_code', 'campaign_name',
            'order_amount', 'discount_amount', 'created_at'
        ]


class CampaignParticipantSerializer(serializers.ModelSerializer):
    """Serializer for campaign participation."""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = CampaignParticipant
        fields = [
            'id', 'campaign_name', 'joined_at', 'is_active',
            'total_views', 'total_clicks', 'total_conversions',
            'total_discount_received'
        ]