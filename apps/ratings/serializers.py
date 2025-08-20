"""
Serializers for ratings and reviews system.
"""

from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    BraiderReview, ProductReview, ReviewImage, ReviewHelpfulness,
    ReviewResponse, ReviewReport
)
from apps.bookings.models import Booking
from apps.ecommerce.models import Order
from apps.braiders.models import Braider
from apps.ecommerce.models import Product

User = get_user_model()


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images."""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption', 'image_type', 'sort_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class BraiderReviewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for braider review listings."""
    
    user_name = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='booking.service.name', read_only=True)
    helpful_ratio = serializers.ReadOnlyField()
    images_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BraiderReview
        fields = [
            'id', 'user_name', 'overall_rating', 'title', 'comment',
            'service_name', 'would_recommend', 'helpful_count',
            'not_helpful_count', 'helpful_ratio', 'is_verified',
            'images_count', 'created_at'
        ]
    
    def get_user_name(self, obj):
        """Get user name or anonymize if needed."""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name[0]}."
        return "Anonymous User"
    
    def get_images_count(self, obj):
        """Get count of images attached to review."""
        return obj.images.count()


class BraiderReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual braider review view."""
    
    user_name = serializers.SerializerMethodField()
    braider_name = serializers.CharField(source='braider.name', read_only=True)
    service_name = serializers.CharField(source='booking.service.name', read_only=True)
    booking_date = serializers.DateField(source='booking.booking_date', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = serializers.SerializerMethodField()
    helpful_ratio = serializers.ReadOnlyField()
    average_detailed_rating = serializers.ReadOnlyField()
    
    class Meta:
        model = BraiderReview
        fields = [
            'id', 'user_name', 'braider_name', 'service_name', 'booking_date',
            'overall_rating', 'quality_rating', 'professionalism_rating',
            'communication_rating', 'value_rating', 'average_detailed_rating',
            'title', 'comment', 'would_recommend', 'helpful_count',
            'not_helpful_count', 'helpful_ratio', 'is_verified', 'status',
            'images', 'response', 'created_at'
        ]
    
    def get_user_name(self, obj):
        """Get user name or anonymize if needed."""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name[0]}."
        return "Anonymous User"
    
    def get_response(self, obj):
        """Get braider's response if exists."""
        if hasattr(obj, 'response'):
            return {
                'response_text': obj.response.response_text,
                'created_at': obj.response.created_at,
                'is_official': obj.response.is_official
            }
        return None


class BraiderReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating braider reviews."""
    
    images_data = ReviewImageSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = BraiderReview
        fields = [
            'booking', 'overall_rating', 'quality_rating', 'professionalism_rating',
            'communication_rating', 'value_rating', 'title', 'comment',
            'would_recommend', 'images_data'
        ]
    
    def validate_booking(self, value):
        """Validate that booking belongs to user and is completed."""
        user = self.context['request'].user
        
        if value.user != user:
            raise serializers.ValidationError("You can only review your own bookings")
        
        if value.status != 'completed':
            raise serializers.ValidationError("You can only review completed bookings")
        
        # Check if review already exists
        if hasattr(value, 'review'):
            raise serializers.ValidationError("You have already reviewed this booking")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create review with images."""
        images_data = validated_data.pop('images_data', [])
        user = self.context['request'].user
        
        # Create review
        review = BraiderReview.objects.create(
            user=user,
            braider=validated_data['booking'].braider,
            **validated_data
        )
        
        # Create images
        for image_data in images_data:
            ReviewImage.objects.create(braider_review=review, **image_data)
        
        return review


class ProductReviewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product review listings."""
    
    user_name = serializers.SerializerMethodField()
    helpful_ratio = serializers.ReadOnlyField()
    images_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'user_name', 'rating', 'title', 'comment',
            'would_recommend', 'helpful_count', 'not_helpful_count',
            'helpful_ratio', 'is_verified_purchase', 'images_count',
            'created_at'
        ]
    
    def get_user_name(self, obj):
        """Get user name or anonymize if needed."""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name[0]}."
        return "Anonymous User"
    
    def get_images_count(self, obj):
        """Get count of images attached to review."""
        return obj.images.count()


class ProductReviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual product review view."""
    
    user_name = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    order_date = serializers.DateTimeField(source='order.placed_at', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = serializers.SerializerMethodField()
    helpful_ratio = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'user_name', 'product_name', 'order_date', 'rating',
            'quality_rating', 'value_rating', 'title', 'comment',
            'would_recommend', 'helpful_count', 'not_helpful_count',
            'helpful_ratio', 'is_verified_purchase', 'status', 'images',
            'response', 'created_at'
        ]
    
    def get_user_name(self, obj):
        """Get user name or anonymize if needed."""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name[0]}."
        return "Anonymous User"
    
    def get_response(self, obj):
        """Get official response if exists."""
        if hasattr(obj, 'response'):
            return {
                'response_text': obj.response.response_text,
                'created_at': obj.response.created_at,
                'is_official': obj.response.is_official
            }
        return None


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating product reviews."""
    
    images_data = ReviewImageSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = ProductReview
        fields = [
            'product', 'order', 'rating', 'quality_rating', 'value_rating',
            'title', 'comment', 'would_recommend', 'images_data'
        ]
    
    def validate(self, data):
        """Validate that user purchased the product and order is delivered."""
        user = self.context['request'].user
        product = data['product']
        order = data['order']
        
        # Check if order belongs to user
        if order.user != user:
            raise serializers.ValidationError({"order": "You can only review your own orders"})
        
        # Check if order is delivered
        if order.status != 'delivered':
            raise serializers.ValidationError({"order": "You can only review delivered orders"})
        
        # Check if product was in the order
        if not order.items.filter(product=product).exists():
            raise serializers.ValidationError({"product": "Product was not in this order"})
        
        # Check if review already exists
        if ProductReview.objects.filter(user=user, product=product, order=order).exists():
            raise serializers.ValidationError("You have already reviewed this product for this order")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create review with images."""
        images_data = validated_data.pop('images_data', [])
        user = self.context['request'].user
        
        # Create review
        review = ProductReview.objects.create(user=user, **validated_data)
        
        # Create images
        for image_data in images_data:
            ReviewImage.objects.create(product_review=review, **image_data)
        
        return review


class ReviewHelpfulnessSerializer(serializers.ModelSerializer):
    """Serializer for review helpfulness votes."""
    
    class Meta:
        model = ReviewHelpfulness
        fields = ['vote']
    
    def create(self, validated_data):
        """Create or update helpfulness vote."""
        user = self.context['request'].user
        review_id = self.context['review_id']
        review_type = self.context['review_type']
        
        # Determine which review field to use
        if review_type == 'braider':
            filter_kwargs = {'user': user, 'braider_review_id': review_id}
            create_kwargs = {'user': user, 'braider_review_id': review_id, **validated_data}
        else:
            filter_kwargs = {'user': user, 'product_review_id': review_id}
            create_kwargs = {'user': user, 'product_review_id': review_id, **validated_data}
        
        # Update existing vote or create new one
        helpfulness, created = ReviewHelpfulness.objects.update_or_create(
            defaults=validated_data,
            **filter_kwargs
        )
        
        return helpfulness


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Serializer for review responses."""
    
    responder_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewResponse
        fields = [
            'id', 'response_text', 'responder_name', 'is_official', 'created_at'
        ]
        read_only_fields = ['id', 'responder_name', 'is_official', 'created_at']
    
    def get_responder_name(self, obj):
        """Get responder name."""
        if obj.responder.first_name and obj.responder.last_name:
            return f"{obj.responder.first_name} {obj.responder.last_name}"
        return obj.responder.email


class ReviewResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating review responses."""
    
    class Meta:
        model = ReviewResponse
        fields = ['response_text']
    
    def create(self, validated_data):
        """Create response to review."""
        user = self.context['request'].user
        review_id = self.context['review_id']
        review_type = self.context['review_type']
        
        # Determine which review field to use
        if review_type == 'braider':
            create_kwargs = {'braider_review_id': review_id}
        else:
            create_kwargs = {'product_review_id': review_id}
        
        # Create response
        response = ReviewResponse.objects.create(
            responder=user,
            is_official=True,
            **create_kwargs,
            **validated_data
        )
        
        return response


class ReviewReportSerializer(serializers.ModelSerializer):
    """Serializer for reporting reviews."""
    
    class Meta:
        model = ReviewReport
        fields = ['reason', 'description']
    
    def create(self, validated_data):
        """Create report for review."""
        user = self.context['request'].user
        review_id = self.context['review_id']
        review_type = self.context['review_type']
        
        # Check if user already reported this review
        if review_type == 'braider':
            filter_kwargs = {'reporter': user, 'braider_review_id': review_id}
            create_kwargs = {'reporter': user, 'braider_review_id': review_id}
        else:
            filter_kwargs = {'reporter': user, 'product_review_id': review_id}
            create_kwargs = {'reporter': user, 'product_review_id': review_id}
        
        if ReviewReport.objects.filter(**filter_kwargs).exists():
            raise serializers.ValidationError("You have already reported this review")
        
        # Create report
        report = ReviewReport.objects.create(**create_kwargs, **validated_data)
        
        return report


class ReviewModerationSerializer(serializers.ModelSerializer):
    """Serializer for moderating reviews (admin only)."""
    
    class Meta:
        model = BraiderReview  # Can be used for both review types
        fields = ['status', 'moderation_notes']
    
    def update(self, instance, validated_data):
        """Update review moderation status."""
        user = self.context['request'].user
        
        # Set moderation fields
        instance.moderated_by = user
        instance.moderated_at = timezone.now()
        
        # Update other fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        instance.save()
        return instance


class ReviewStatsSerializer(serializers.Serializer):
    """Serializer for review statistics."""
    
    total_reviews = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    rating_distribution = serializers.DictField()
    verified_reviews = serializers.IntegerField()
    recent_reviews = serializers.IntegerField()
    
    # For braider reviews
    quality_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    professionalism_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    communication_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    value_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    recommendation_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)