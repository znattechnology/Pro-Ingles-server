from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
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
from .serializers import (
    LandingPageSettingsSerializer,
    HeroSectionSerializer,
    StatItemSerializer,
    CompanySerializer,
    ServiceItemSerializer,
    PricingTierSerializer,
    FeatureSerializer,
    TestimonialSerializer,
    FAQItemSerializer,
    CallToActionSerializer,
    SeoSettingsSerializer,
    LandingPageDataSerializer
)


# Cache timeout in seconds (15 minutes)
CACHE_TIMEOUT = 60 * 15


class LandingPageSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for landing page settings"""
    queryset = LandingPageSettings.objects.all()
    serializer_class = LandingPageSettingsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        """Allow read access to everyone, write access to staff only"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class HeroSectionViewSet(viewsets.ModelViewSet):
    """ViewSet for hero sections"""
    queryset = HeroSection.objects.all()
    serializer_class = HeroSectionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class StatItemViewSet(viewsets.ModelViewSet):
    """ViewSet for statistics items"""
    queryset = StatItem.objects.all()
    serializer_class = StatItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['section', 'is_active']
    ordering_fields = ['order', 'created_at']
    ordering = ['section', 'order']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class CompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for companies"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'is_active', 'show_in_hero', 'show_in_ticker']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class ServiceItemViewSet(viewsets.ModelViewSet):
    """ViewSet for service items"""
    queryset = ServiceItem.objects.all()
    serializer_class = ServiceItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['is_featured', 'is_active']
    ordering_fields = ['order', 'title', 'created_at']
    ordering = ['order', 'title']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class PricingTierViewSet(viewsets.ModelViewSet):
    """ViewSet for pricing tiers"""
    queryset = PricingTier.objects.all()
    serializer_class = PricingTierSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['is_popular', 'is_active']
    ordering_fields = ['order', 'monthly_price', 'created_at']
    ordering = ['order']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class FeatureViewSet(viewsets.ModelViewSet):
    """ViewSet for features"""
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['is_highlighted', 'is_active']
    ordering_fields = ['order', 'title', 'created_at']
    ordering = ['order']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class TestimonialViewSet(viewsets.ModelViewSet):
    """ViewSet for testimonials"""
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['sector', 'is_featured', 'is_active', 'verified']
    ordering_fields = ['order', 'date_given', 'created_at']
    ordering = ['order', '-date_given']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class FAQItemViewSet(viewsets.ModelViewSet):
    """ViewSet for FAQ items"""
    queryset = FAQItem.objects.all()
    serializer_class = FAQItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'is_featured', 'is_active']
    ordering_fields = ['order', 'category', 'created_at']
    ordering = ['category', 'order']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class CallToActionViewSet(viewsets.ModelViewSet):
    """ViewSet for call to actions"""
    queryset = CallToAction.objects.all()
    serializer_class = CallToActionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['section', 'is_active']
    ordering_fields = ['order', 'section', 'created_at']
    ordering = ['section', 'order']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class SeoSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for SEO settings"""
    queryset = SeoSettings.objects.all()
    serializer_class = SeoSettingsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['page_type']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(CACHE_TIMEOUT)
@vary_on_headers('User-Agent')
def landing_page_data(request):
    """
    Get all landing page data in one optimized request.
    This endpoint is cached and optimized for frontend consumption.
    """
    cache_key = 'landing_page_data_v1'
    
    # Try to get data from cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # If not in cache, generate the data
    serializer = LandingPageDataSerializer(context={'request': request})
    data = serializer.to_representation(None)
    
    # Cache the data
    cache.set(cache_key, data, CACHE_TIMEOUT)
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def clear_cache(request):
    """
    Clear the landing page cache.
    Only accessible by admin users.
    """
    cache_keys = [
        'landing_page_data_v1',
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    # Also clear any view-level caches
    try:
        from django.core.cache.utils import make_template_fragment_key
        # Clear specific template fragments if needed
        pass
    except ImportError:
        pass
    
    return Response({
        'message': 'Cache cleared successfully',
        'cleared_keys': cache_keys
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def landing_page_stats(request):
    """
    Get landing page statistics for analytics.
    """
    stats = {
        'total_companies': Company.objects.filter(is_active=True).count(),
        'total_services': ServiceItem.objects.filter(is_active=True).count(),
        'total_testimonials': Testimonial.objects.filter(is_active=True, verified=True).count(),
        'total_faqs': FAQItem.objects.filter(is_active=True).count(),
        'active_pricing_tiers': PricingTier.objects.filter(is_active=True).count(),
        'featured_testimonials': Testimonial.objects.filter(is_featured=True, is_active=True).count(),
        'sectors': {
            'oil_gas': Company.objects.filter(category='oil_gas', is_active=True).count(),
            'banking': Company.objects.filter(category='banking', is_active=True).count(),
            'telecoms': Company.objects.filter(category='telecoms', is_active=True).count(),
            'technology': Company.objects.filter(category='technology', is_active=True).count(),
        }
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint for the CMS API.
    """
    return Response({
        'status': 'healthy',
        'service': 'ProEnglish CMS API',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat()
    })


# Preview functionality for content management
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def preview_changes(request):
    """
    Preview changes without saving to database.
    Useful for content managers to see how changes will look.
    """
    preview_data = request.data
    model_type = preview_data.get('model_type')
    
    # Map model types to serializers
    serializer_map = {
        'hero': HeroSectionSerializer,
        'pricing': PricingTierSerializer,
        'service': ServiceItemSerializer,
        'testimonial': TestimonialSerializer,
        'feature': FeatureSerializer,
    }
    
    if model_type not in serializer_map:
        return Response({
            'error': 'Invalid model type',
            'valid_types': list(serializer_map.keys())
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer_class = serializer_map[model_type]
    serializer = serializer_class(data=preview_data.get('data', {}), context={'request': request})
    
    if serializer.is_valid():
        # Return the serialized data without saving
        return Response({
            'preview': serializer.validated_data,
            'formatted': serializer.data
        })
    else:
        return Response({
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)