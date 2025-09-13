from rest_framework import serializers
from django.utils import timezone
from .models import (
    LandingPageSettings,
    HeroSection,
    StatItem,
    Company,
    ServiceItem,
    PricingTier,
    Feature,
    Testimonial,
    FAQItem,
    CallToAction,
    SeoSettings
)


class LandingPageSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingPageSettings
        fields = '__all__'


class HeroSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroSection
        fields = '__all__'


class StatItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatItem
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = '__all__'
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class ServiceItemSerializer(serializers.ModelSerializer):
    target_companies = CompanySerializer(many=True, read_only=True)
    service_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceItem
        fields = '__all__'
    
    def get_service_image_url(self, obj):
        if obj.service_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.service_image.url)
            return obj.service_image.url
        return None


class PricingTierSerializer(serializers.ModelSerializer):
    formatted_monthly_price = serializers.SerializerMethodField()
    formatted_yearly_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PricingTier
        fields = '__all__'
    
    def get_formatted_monthly_price(self, obj):
        """Format price according to Angola currency standards"""
        if obj.monthly_price == 0:
            return "Gratuito"
        return f"{obj.monthly_price:,.0f} {obj.currency}"
    
    def get_formatted_yearly_price(self, obj):
        """Format price according to Angola currency standards"""
        if obj.yearly_price == 0:
            return "Gratuito"
        return f"{obj.yearly_price:,.0f} {obj.currency}"


class FeatureSerializer(serializers.ModelSerializer):
    background_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Feature
        fields = '__all__'
    
    def get_background_image_url(self, obj):
        if obj.background_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.background_image.url)
            return obj.background_image.url
        return None


class TestimonialSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Testimonial
        fields = '__all__'
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_company_name(self, obj):
        return obj.company.name if obj.company else ""


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = '__all__'


class CallToActionSerializer(serializers.ModelSerializer):
    background_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CallToAction
        fields = '__all__'
    
    def get_background_image_url(self, obj):
        if obj.background_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.background_image.url)
            return obj.background_image.url
        return None


class SeoSettingsSerializer(serializers.ModelSerializer):
    og_image_url = serializers.SerializerMethodField()
    twitter_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SeoSettings
        fields = '__all__'
    
    def get_og_image_url(self, obj):
        if obj.og_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.og_image.url)
            return obj.og_image.url
        return None
    
    def get_twitter_image_url(self, obj):
        if obj.twitter_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.twitter_image.url)
            return obj.twitter_image.url
        return None


# Landing Page Complete Data Serializer
class LandingPageDataSerializer(serializers.Serializer):
    """Serializer that returns all landing page data in one response"""
    
    settings = LandingPageSettingsSerializer()
    hero = HeroSectionSerializer()
    hero_stats = StatItemSerializer(many=True)
    companies = CompanySerializer(many=True)
    services = ServiceItemSerializer(many=True)
    pricing_tiers = PricingTierSerializer(many=True)
    features = FeatureSerializer(many=True)
    testimonials = TestimonialSerializer(many=True)
    faqs = FAQItemSerializer(many=True)
    ctas = CallToActionSerializer(many=True)
    seo = SeoSettingsSerializer()
    
    def to_representation(self, instance):
        """Custom representation to format data for frontend consumption"""
        
        # Get active hero section
        try:
            hero = HeroSection.objects.filter(is_active=True).first()
        except HeroSection.DoesNotExist:
            hero = None
        
        # Get hero stats
        hero_stats = StatItem.objects.filter(section='hero', is_active=True).order_by('order')
        
        # Get active companies for different sections
        hero_companies = Company.objects.filter(show_in_hero=True, is_active=True).order_by('order')
        ticker_companies = Company.objects.filter(show_in_ticker=True, is_active=True).order_by('order')
        
        # Get active services
        services = ServiceItem.objects.filter(is_active=True).order_by('order')
        
        # Get active pricing tiers
        pricing_tiers = PricingTier.objects.filter(is_active=True).order_by('order')
        
        # Get active features
        features = Feature.objects.filter(is_active=True).order_by('order')
        
        # Get active testimonials
        testimonials = Testimonial.objects.filter(is_active=True).order_by('order')
        
        # Get active FAQs
        faqs = FAQItem.objects.filter(is_active=True).order_by('category', 'order')
        
        # Get active CTAs
        ctas = CallToAction.objects.filter(is_active=True).order_by('section', 'order')
        
        # Get settings
        try:
            settings = LandingPageSettings.objects.filter(is_active=True).first()
        except LandingPageSettings.DoesNotExist:
            settings = None
        
        # Get SEO settings for home page
        try:
            seo = SeoSettings.objects.get(page_type='home')
        except SeoSettings.DoesNotExist:
            seo = None
        
        # Serialize data with context
        context = self.context
        
        return {
            'settings': LandingPageSettingsSerializer(settings, context=context).data if settings else None,
            'hero': HeroSectionSerializer(hero, context=context).data if hero else None,
            'hero_stats': StatItemSerializer(hero_stats, many=True, context=context).data,
            'hero_companies': CompanySerializer(hero_companies, many=True, context=context).data,
            'ticker_companies': CompanySerializer(ticker_companies, many=True, context=context).data,
            'services': ServiceItemSerializer(services, many=True, context=context).data,
            'pricing_tiers': PricingTierSerializer(pricing_tiers, many=True, context=context).data,
            'features': FeatureSerializer(features, many=True, context=context).data,
            'testimonials': TestimonialSerializer(testimonials, many=True, context=context).data,
            'faqs': FAQItemSerializer(faqs, many=True, context=context).data,
            'ctas': CallToActionSerializer(ctas, many=True, context=context).data,
            'seo': SeoSettingsSerializer(seo, context=context).data if seo else None,
            'last_updated': max([
                settings.updated_at if settings else timezone.now(),
                hero.updated_at if hero else timezone.now(),
            ])
        }