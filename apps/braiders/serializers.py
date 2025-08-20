"""
Serializers for braiders and services.
"""

from rest_framework import serializers
from django.db import transaction

from .models import Braider, BraiderPortfolioImage, Service, ServiceImage
from apps.core.models import Address
from apps.users.serializers import AddressSerializer


class BraiderPortfolioImageSerializer(serializers.ModelSerializer):
    """
    Serializer for braider portfolio images.
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BraiderPortfolioImage
        fields = [
            'id', 'image', 'image_url', 'title', 'description', 
            'tags', 'is_featured', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ServiceImageSerializer(serializers.ModelSerializer):
    """
    Serializer for service images.
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceImage
        fields = [
            'id', 'image', 'image_url', 'image_type', 
            'caption', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ServiceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for service listings.
    """
    braider_name = serializers.CharField(source='braider.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    price_display = serializers.ReadOnlyField()
    duration_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'short_description', 'category', 'subcategory',
            'base_price', 'price_display', 'duration_minutes', 'duration_display',
            'image', 'image_url', 'is_popular', 'braider_name', 'created_at'
        ]
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ServiceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual service view.
    """
    braider_name = serializers.CharField(source='braider.name', read_only=True)
    braider_rating = serializers.DecimalField(
        source='braider.average_rating', 
        max_digits=3, 
        decimal_places=2, 
        read_only=True
    )
    image_url = serializers.SerializerMethodField()
    additional_images = ServiceImageSerializer(many=True, read_only=True)
    price_display = serializers.ReadOnlyField()
    duration_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'short_description', 'category', 
            'subcategory', 'tags', 'base_price', 'price_varies', 'price_from', 
            'price_to', 'price_factors', 'price_display', 'duration_minutes', 
            'duration_varies', 'min_duration', 'max_duration', 'duration_display',
            'difficulty_level', 'hair_type_compatibility', 'required_hair_length',
            'client_preparation', 'braider_provides', 'client_brings',
            'aftercare_instructions', 'maintenance_schedule', 'style_duration',
            'image', 'image_url', 'additional_images', 'is_popular',
            'braider_name', 'braider_rating', 'created_at'
        ]
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ServiceCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating services.
    """
    
    class Meta:
        model = Service
        fields = [
            'name', 'description', 'short_description', 'category', 
            'subcategory', 'tags', 'base_price', 'price_varies', 'price_from', 
            'price_to', 'price_factors', 'duration_minutes', 'duration_varies',
            'min_duration', 'max_duration', 'difficulty_level', 
            'hair_type_compatibility', 'required_hair_length', 'client_preparation',
            'braider_provides', 'client_brings', 'aftercare_instructions',
            'maintenance_schedule', 'style_duration', 'image', 'is_active'
        ]
    
    def validate(self, data):
        """
        Validate service data.
        """
        # Validate price ranges
        if data.get('price_varies'):
            if not data.get('price_from') or not data.get('price_to'):
                raise serializers.ValidationError(
                    "Price range required when price varies"
                )
            if data['price_from'] >= data['price_to']:
                raise serializers.ValidationError(
                    "Price 'from' must be less than price 'to'"
                )
        
        # Validate duration ranges
        if data.get('duration_varies'):
            if not data.get('min_duration') or not data.get('max_duration'):
                raise serializers.ValidationError(
                    "Duration range required when duration varies"
                )
            if data['min_duration'] >= data['max_duration']:
                raise serializers.ValidationError(
                    "Min duration must be less than max duration"
                )
        
        return data


class BraiderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for braider listings.
    """
    profile_image_url = serializers.SerializerMethodField()
    location_display = serializers.ReadOnlyField()
    service_count = serializers.SerializerMethodField()
    featured_portfolio_images = serializers.SerializerMethodField()
    
    class Meta:
        model = Braider
        fields = [
            'id', 'name', 'bio', 'profile_image', 'profile_image_url',
            'location_display', 'average_rating', 'total_reviews',
            'years_experience', 'experience_level', 'specialties',
            'is_featured', 'service_count', 'featured_portfolio_images',
            'provides_home_service', 'has_physical_location', 'created_at'
        ]
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def get_service_count(self, obj):
        return obj.services.filter(is_active=True).count()
    
    def get_featured_portfolio_images(self, obj):
        featured_images = obj.portfolio_images.filter(is_featured=True)[:3]
        return BraiderPortfolioImageSerializer(
            featured_images, 
            many=True, 
            context=self.context
        ).data


class BraiderDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual braider view.
    """
    address = AddressSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    location_display = serializers.ReadOnlyField()
    portfolio_images = BraiderPortfolioImageSerializer(many=True, read_only=True)
    services = ServiceListSerializer(many=True, read_only=True)
    active_services = serializers.SerializerMethodField()
    
    class Meta:
        model = Braider
        fields = [
            'id', 'name', 'contact_email', 'contact_phone', 'bio',
            'address', 'location_display', 'service_areas',
            'provides_home_service', 'has_physical_location',
            'profile_image', 'profile_image_url', 'years_experience',
            'experience_level', 'specialties', 'certifications',
            'average_rating', 'total_reviews', 'availability_schedule',
            'pricing_info', 'booking_advance_days', 'cancellation_policy',
            'instagram_handle', 'facebook_url', 'website_url',
            'portfolio_images', 'services', 'active_services',
            'is_featured', 'created_at'
        ]
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def get_active_services(self, obj):
        active_services = obj.services.filter(is_active=True)
        return ServiceListSerializer(
            active_services, 
            many=True, 
            context=self.context
        ).data


class BraiderRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for braider registration/application.
    """
    address_data = AddressSerializer(write_only=True, required=False)
    
    class Meta:
        model = Braider
        fields = [
            'name', 'contact_email', 'contact_phone', 'bio',
            'address_data', 'service_areas', 'provides_home_service',
            'has_physical_location', 'profile_image', 'years_experience',
            'experience_level', 'specialties', 'certifications',
            'availability_schedule', 'pricing_info', 'booking_advance_days',
            'cancellation_policy', 'instagram_handle', 'facebook_url',
            'website_url'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create braider with address if provided.
        """
        address_data = validated_data.pop('address_data', None)
        user = self.context['request'].user
        
        # Create address if provided
        address = None
        if address_data:
            address = Address.objects.create(**address_data)
        
        # Create braider
        braider = Braider.objects.create(
            user=user,
            address=address,
            **validated_data
        )
        
        return braider


class BraiderUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating braider profile.
    """
    address_data = AddressSerializer(write_only=True, required=False)
    
    class Meta:
        model = Braider
        fields = [
            'name', 'contact_email', 'contact_phone', 'bio',
            'address_data', 'service_areas', 'provides_home_service',
            'has_physical_location', 'profile_image', 'years_experience',
            'experience_level', 'specialties', 'certifications',
            'availability_schedule', 'pricing_info', 'booking_advance_days',
            'cancellation_policy', 'instagram_handle', 'facebook_url',
            'website_url'
        ]
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update braider with address handling.
        """
        address_data = validated_data.pop('address_data', None)
        
        # Update address if provided
        if address_data:
            if instance.address:
                # Update existing address
                for key, value in address_data.items():
                    setattr(instance.address, key, value)
                instance.address.save()
            else:
                # Create new address
                instance.address = Address.objects.create(**address_data)
        
        # Update braider
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        
        return instance


class BraiderApprovalSerializer(serializers.ModelSerializer):
    """
    Serializer for admin approval/rejection of braiders.
    """
    
    class Meta:
        model = Braider
        fields = ['status', 'status_reason']
    
    def validate_status(self, value):
        """
        Validate status transitions.
        """
        if value not in ['approved', 'rejected', 'suspended']:
            raise serializers.ValidationError(
                "Status must be approved, rejected, or suspended"
            )
        return value
    
    def update(self, instance, validated_data):
        """
        Update status and set approved_by if approving.
        """
        status = validated_data.get('status')
        if status == 'approved':
            validated_data['approved_by'] = self.context['request'].user
        
        return super().update(instance, validated_data)