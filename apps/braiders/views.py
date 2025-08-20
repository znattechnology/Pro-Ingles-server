"""
Views for braiders and services.
"""

from django.db.models import Q, Avg, Count, Sum, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from .models import Braider, BraiderPortfolioImage, Service, ServiceImage
from .serializers import (
    BraiderListSerializer, BraiderDetailSerializer, BraiderRegistrationSerializer,
    BraiderUpdateSerializer, BraiderApprovalSerializer, BraiderPortfolioImageSerializer,
    ServiceListSerializer, ServiceDetailSerializer, ServiceCreateUpdateSerializer,
    ServiceImageSerializer
)
from apps.core.permissions import (
    IsBraiderOrReadOnly, IsBraider, IsAdminUser, IsOwnerOrReadOnly
)
from apps.core.pagination import CustomPagination


class BraiderFilter(django_filters.FilterSet):
    """
    Advanced filtering for braiders.
    """
    location = django_filters.CharFilter(method='filter_by_location')
    district = django_filters.CharFilter(field_name='address__district', lookup_expr='iexact')
    city = django_filters.CharFilter(field_name='address__city', lookup_expr='iexact')
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='lte')
    experience_level = django_filters.ChoiceFilter(choices=Braider.EXPERIENCE_LEVELS)
    min_experience = django_filters.NumberFilter(field_name='years_experience', lookup_expr='gte')
    specialties = django_filters.CharFilter(method='filter_by_specialties')
    service_type = django_filters.CharFilter(method='filter_by_service_type')
    provides_home_service = django_filters.BooleanFilter()
    has_physical_location = django_filters.BooleanFilter()
    is_featured = django_filters.BooleanFilter()
    
    class Meta:
        model = Braider
        fields = []
    
    def filter_by_location(self, queryset, name, value):
        """Filter by location (city or district)."""
        return queryset.filter(
            Q(address__city__icontains=value) |
            Q(address__district__icontains=value) |
            Q(service_areas__icontains=value)
        )
    
    def filter_by_specialties(self, queryset, name, value):
        """Filter by specialties (JSON array field)."""
        return queryset.filter(specialties__icontains=value)
    
    def filter_by_service_type(self, queryset, name, value):
        """Filter braiders who offer specific service category."""
        return queryset.filter(
            services__category=value,
            services__is_active=True
        ).distinct()


class ServiceFilter(django_filters.FilterSet):
    """
    Advanced filtering for services.
    """
    category = django_filters.ChoiceFilter(choices=Service.CATEGORY_CHOICES)
    subcategory = django_filters.CharFilter(lookup_expr='icontains')
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')
    max_duration = django_filters.NumberFilter(field_name='duration_minutes', lookup_expr='lte')
    difficulty_level = django_filters.ChoiceFilter(choices=Service.DIFFICULTY_LEVELS)
    hair_type = django_filters.CharFilter(method='filter_by_hair_type')
    braider_location = django_filters.CharFilter(method='filter_by_braider_location')
    braider_rating = django_filters.NumberFilter(
        field_name='braider__average_rating', 
        lookup_expr='gte'
    )
    tags = django_filters.CharFilter(method='filter_by_tags')
    is_popular = django_filters.BooleanFilter()
    
    class Meta:
        model = Service
        fields = []
    
    def filter_by_hair_type(self, queryset, name, value):
        """Filter services compatible with hair type."""
        return queryset.filter(
            Q(hair_type_compatibility__icontains=value) |
            Q(hair_type_compatibility__len=0)  # No restrictions
        )
    
    def filter_by_braider_location(self, queryset, name, value):
        """Filter by braider location."""
        return queryset.filter(
            Q(braider__address__city__icontains=value) |
            Q(braider__address__district__icontains=value)
        )
    
    def filter_by_tags(self, queryset, name, value):
        """Filter by service tags."""
        return queryset.filter(tags__icontains=value)


class BraiderListView(generics.ListAPIView):
    """
    List all approved braiders with filtering and search.
    """
    serializer_class = BraiderListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BraiderFilter
    search_fields = ['name', 'bio', 'specialties', 'address__city', 'address__district']
    ordering_fields = ['name', 'average_rating', 'total_reviews', 'years_experience', 'created_at']
    ordering = ['-is_featured', '-average_rating', '-total_reviews']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Braider.objects.filter(
            status='approved'
        ).select_related('address').prefetch_related('portfolio_images', 'services')


class BraiderDetailView(generics.RetrieveAPIView):
    """
    Retrieve individual braider details.
    """
    serializer_class = BraiderDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Braider.objects.filter(
            status='approved'
        ).select_related('address').prefetch_related(
            'portfolio_images', 'services__additional_images'
        )


class BraiderRegistrationView(generics.CreateAPIView):
    """
    Register as a braider (create braider profile).
    """
    serializer_class = BraiderRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Check if user already has a braider profile
        if hasattr(request.user, 'braider_profile'):
            return Response({
                'error': 'User already has a braider profile'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        braider = serializer.save()
        
        return Response({
            'message': 'Braider registration submitted successfully. Your profile is pending approval.',
            'braider_id': str(braider.id),
            'status': braider.status
        }, status=status.HTTP_201_CREATED)


class BraiderProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update own braider profile.
    """
    serializer_class = BraiderDetailSerializer
    permission_classes = [IsBraider]
    
    def get_object(self):
        return get_object_or_404(Braider, user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BraiderUpdateSerializer
        return BraiderDetailSerializer


class BraiderApprovalView(generics.UpdateAPIView):
    """
    Admin view to approve/reject braider applications.
    """
    queryset = Braider.objects.all()
    serializer_class = BraiderApprovalSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': f'Braider {instance.name} has been {instance.status}',
            'braider_id': str(instance.id),
            'status': instance.status
        })


class ServiceListView(generics.ListAPIView):
    """
    List all active services with filtering and search.
    """
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ServiceFilter
    search_fields = ['name', 'description', 'short_description', 'tags', 'braider__name']
    ordering_fields = ['name', 'base_price', 'duration_minutes', 'created_at', 'braider__average_rating']
    ordering = ['-is_popular', 'base_price']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Service.objects.filter(
            is_active=True,
            braider__status='approved'
        ).select_related('braider').prefetch_related('additional_images')


class ServiceDetailView(generics.RetrieveAPIView):
    """
    Retrieve individual service details.
    """
    serializer_class = ServiceDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Service.objects.filter(
            is_active=True,
            braider__status='approved'
        ).select_related('braider').prefetch_related('additional_images')


class BraiderServiceListCreateView(generics.ListCreateAPIView):
    """
    List and create services for authenticated braider.
    """
    permission_classes = [IsBraider]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Service.objects.filter(
            braider__user=self.request.user
        ).prefetch_related('additional_images')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceCreateUpdateSerializer
        return ServiceListSerializer
    
    def perform_create(self, serializer):
        braider = get_object_or_404(Braider, user=self.request.user)
        serializer.save(braider=braider)


class BraiderServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete own services.
    """
    permission_classes = [IsBraider]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Service.objects.filter(
            braider__user=self.request.user
        ).prefetch_related('additional_images')
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ServiceCreateUpdateSerializer
        return ServiceDetailSerializer


class BraiderPortfolioView(generics.ListCreateAPIView):
    """
    Manage braider portfolio images.
    """
    serializer_class = BraiderPortfolioImageSerializer
    permission_classes = [IsBraider]
    
    def get_queryset(self):
        return BraiderPortfolioImage.objects.filter(
            braider__user=self.request.user
        ).order_by('order', '-created_at')
    
    def perform_create(self, serializer):
        braider = get_object_or_404(Braider, user=self.request.user)
        serializer.save(braider=braider)


class BraiderPortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual portfolio images.
    """
    serializer_class = BraiderPortfolioImageSerializer
    permission_classes = [IsBraider]
    lookup_field = 'id'
    
    def get_queryset(self):
        return BraiderPortfolioImage.objects.filter(
            braider__user=self.request.user
        )


class ServiceImageView(generics.ListCreateAPIView):
    """
    Manage service images.
    """
    serializer_class = ServiceImageSerializer
    permission_classes = [IsBraider]
    
    def get_queryset(self):
        service_id = self.kwargs.get('service_id')
        return ServiceImage.objects.filter(
            service_id=service_id,
            service__braider__user=self.request.user
        ).order_by('order', '-created_at')
    
    def perform_create(self, serializer):
        service_id = self.kwargs.get('service_id')
        service = get_object_or_404(
            Service, 
            id=service_id, 
            braider__user=self.request.user
        )
        serializer.save(service=service)


class ServiceImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual service images.
    """
    serializer_class = ServiceImageSerializer
    permission_classes = [IsBraider]
    lookup_field = 'id'
    
    def get_queryset(self):
        return ServiceImage.objects.filter(
            service__braider__user=self.request.user
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def braider_stats_view(request):
    """
    Get platform statistics about braiders.
    """
    stats = {
        'total_braiders': Braider.objects.filter(status='approved').count(),
        'total_services': Service.objects.filter(
            is_active=True, 
            braider__status='approved'
        ).count(),
        'featured_braiders': Braider.objects.filter(
            status='approved', 
            is_featured=True
        ).count(),
        'average_rating': Braider.objects.filter(
            status='approved',
            total_reviews__gt=0
        ).aggregate(avg_rating=Avg('average_rating'))['avg_rating'] or 0,
        'service_categories': Service.objects.filter(
            is_active=True,
            braider__status='approved'
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def featured_braiders_view(request):
    """
    Get featured braiders for homepage.
    """
    featured_braiders = Braider.objects.filter(
        status='approved',
        is_featured=True
    ).select_related('address').prefetch_related('portfolio_images')[:6]
    
    serializer = BraiderListSerializer(
        featured_braiders, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def popular_services_view(request):
    """
    Get popular services for homepage.
    """
    popular_services = Service.objects.filter(
        is_active=True,
        braider__status='approved',
        is_popular=True
    ).select_related('braider')[:8]
    
    serializer = ServiceListSerializer(
        popular_services, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsBraider])
def braider_dashboard_view(request):
    """
    Unified dashboard for braiders with comprehensive metrics and data.
    """
    try:
        braider = get_object_or_404(Braider, user=request.user)
    except Braider.DoesNotExist:
        return Response({
            'error': 'Braider profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get date ranges for metrics
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    last_year = today - timedelta(days=365)
    
    # Import related models
    from apps.bookings.models import Booking
    from apps.payments.models import Payment
    from apps.ratings.models import Review
    from apps.chat.models import ChatMessage
    from apps.notifications.models import Notification
    
    # === BOOKING METRICS ===
    bookings_total = Booking.objects.filter(braider=braider).count()
    bookings_today = Booking.objects.filter(
        braider=braider, created_at__date=today
    ).count()
    bookings_this_week = Booking.objects.filter(
        braider=braider, created_at__date__gte=last_week
    ).count()
    bookings_this_month = Booking.objects.filter(
        braider=braider, created_at__date__gte=last_month
    ).count()
    
    # Booking status breakdown
    booking_status_stats = Booking.objects.filter(braider=braider).values('status').annotate(
        count=Count('id')
    )
    
    # Upcoming bookings
    upcoming_bookings = Booking.objects.filter(
        braider=braider,
        status__in=['confirmed', 'rescheduled'],
        booking_date__gte=today
    ).order_by('booking_date', 'start_time')[:10]
    
    # Recent bookings
    recent_bookings = Booking.objects.filter(
        braider=braider
    ).order_by('-created_at')[:10]
    
    # === REVENUE METRICS ===
    payments = Payment.objects.filter(booking__braider=braider, status='completed')
    
    revenue_total = payments.aggregate(total=Sum('amount'))['total'] or 0
    revenue_today = payments.filter(
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    revenue_this_week = payments.filter(
        created_at__date__gte=last_week
    ).aggregate(total=Sum('amount'))['total'] or 0
    revenue_this_month = payments.filter(
        created_at__date__gte=last_month
    ).aggregate(total=Sum('amount'))['total'] or 0
    revenue_this_year = payments.filter(
        created_at__date__gte=last_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Average booking value
    avg_booking_value = payments.aggregate(avg=Avg('amount'))['avg'] or 0
    
    # Revenue trend (last 30 days)
    revenue_trend = []
    for i in range(30):
        date = today - timedelta(days=i)
        daily_revenue = payments.filter(
            created_at__date=date
        ).aggregate(total=Sum('amount'))['total'] or 0
        revenue_trend.append({
            'date': date.isoformat(),
            'revenue': float(daily_revenue)
        })
    revenue_trend.reverse()
    
    # === RATING AND REVIEW METRICS ===
    reviews = Review.objects.filter(braider=braider)
    reviews_total = reviews.count()
    reviews_this_month = reviews.filter(created_at__date__gte=last_month).count()
    
    rating_distribution = reviews.values('rating').annotate(
        count=Count('id')
    ).order_by('-rating')
    
    recent_reviews = reviews.order_by('-created_at')[:5]
    
    # === SERVICE METRICS ===
    services = braider.services.filter(is_active=True)
    services_total = services.count()
    
    # Most popular services
    popular_services = services.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:5]
    
    # Service category breakdown
    service_categories = services.values('category').annotate(
        count=Count('id')
    )
    
    # === CHAT AND CUSTOMER METRICS ===
    # Messages received
    messages_total = ChatMessage.objects.filter(
        conversation__participants=braider.user,
        sender__role='customer'
    ).count()
    
    messages_this_week = ChatMessage.objects.filter(
        conversation__participants=braider.user,
        sender__role='customer',
        created_at__date__gte=last_week
    ).count()
    
    # Unique customers
    unique_customers = Booking.objects.filter(
        braider=braider
    ).values('customer').distinct().count()
    
    # === AVAILABILITY AND SCHEDULE ===
    from apps.braiders.models import BraiderAvailability
    
    # Current availability status
    current_availability = BraiderAvailability.objects.filter(
        braider=braider,
        day_of_week=now.weekday(),
        is_available=True
    ).exists()
    
    # === PERFORMANCE METRICS ===
    # Completion rate
    completed_bookings = Booking.objects.filter(
        braider=braider, status='completed'
    ).count()
    completion_rate = (completed_bookings / bookings_total * 100) if bookings_total > 0 else 0
    
    # Cancellation rate
    cancelled_bookings = Booking.objects.filter(
        braider=braider, status='cancelled'
    ).count()
    cancellation_rate = (cancelled_bookings / bookings_total * 100) if bookings_total > 0 else 0
    
    # Response time (if chat messages exist)
    avg_response_time = None  # This would need more complex calculation
    
    # === NOTIFICATIONS ===
    unread_notifications = Notification.objects.filter(
        user=braider.user,
        is_read=False
    ).count()
    
    recent_notifications = Notification.objects.filter(
        user=braider.user
    ).order_by('-created_at')[:5]
    
    # === PROFILE COMPLETION ===
    profile_completion = calculate_profile_completion(braider)
    
    # === BUILD RESPONSE ===
    dashboard_data = {
        'braider_info': {
            'id': str(braider.id),
            'name': braider.name,
            'email': braider.user.email,
            'status': braider.status,
            'is_featured': braider.is_featured,
            'average_rating': float(braider.average_rating) if braider.average_rating else 0,
            'total_reviews': braider.total_reviews,
            'years_experience': braider.years_experience,
            'profile_completion': profile_completion,
            'current_availability': current_availability,
        },
        
        'summary_metrics': {
            'total_bookings': bookings_total,
            'total_revenue': float(revenue_total),
            'total_reviews': reviews_total,
            'total_services': services_total,
            'unique_customers': unique_customers,
            'completion_rate': round(completion_rate, 1),
            'cancellation_rate': round(cancellation_rate, 1),
            'average_booking_value': float(avg_booking_value),
            'unread_notifications': unread_notifications,
        },
        
        'time_based_metrics': {
            'today': {
                'bookings': bookings_today,
                'revenue': float(revenue_today),
            },
            'this_week': {
                'bookings': bookings_this_week,
                'revenue': float(revenue_this_week),
                'messages': messages_this_week,
            },
            'this_month': {
                'bookings': bookings_this_month,
                'revenue': float(revenue_this_month),
                'reviews': reviews_this_month,
            },
            'this_year': {
                'revenue': float(revenue_this_year),
            }
        },
        
        'charts_data': {
            'revenue_trend': revenue_trend,
            'booking_status_distribution': list(booking_status_stats),
            'rating_distribution': list(rating_distribution),
            'service_categories': list(service_categories),
        },
        
        'recent_activity': {
            'upcoming_bookings': [
                {
                    'id': str(booking.id),
                    'customer_name': booking.customer.name,
                    'service_name': booking.service.name if booking.service else 'N/A',
                    'booking_date': booking.booking_date.isoformat(),
                    'start_time': booking.start_time.strftime('%H:%M'),
                    'status': booking.status,
                    'total_price': float(booking.total_price) if booking.total_price else 0,
                } for booking in upcoming_bookings
            ],
            'recent_bookings': [
                {
                    'id': str(booking.id),
                    'customer_name': booking.customer.name,
                    'service_name': booking.service.name if booking.service else 'N/A',
                    'created_at': booking.created_at.isoformat(),
                    'status': booking.status,
                    'total_price': float(booking.total_price) if booking.total_price else 0,
                } for booking in recent_bookings
            ],
            'recent_reviews': [
                {
                    'id': str(review.id),
                    'customer_name': review.customer.name,
                    'rating': review.rating,
                    'comment': review.comment[:100] + '...' if len(review.comment) > 100 else review.comment,
                    'created_at': review.created_at.isoformat(),
                } for review in recent_reviews
            ],
            'recent_notifications': [
                {
                    'id': str(notification.id),
                    'title': notification.title,
                    'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
                    'notification_type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                } for notification in recent_notifications
            ]
        },
        
        'services_performance': [
            {
                'id': str(service.id),
                'name': service.name,
                'category': service.category,
                'base_price': float(service.base_price),
                'is_active': service.is_active,
                'booking_count': service.booking_count,
            } for service in popular_services
        ],
        
        'quick_actions': {
            'can_create_service': services_total < 50,  # Limit services
            'can_update_availability': True,
            'has_pending_bookings': upcoming_bookings.count() > 0,
            'needs_profile_update': profile_completion < 80,
        }
    }
    
    return Response(dashboard_data)


def calculate_profile_completion(braider):
    """Calculate braider profile completion percentage."""
    total_fields = 10
    completed_fields = 0
    
    # Required fields
    if braider.name: completed_fields += 1
    if braider.bio: completed_fields += 1
    if braider.phone: completed_fields += 1
    if braider.address: completed_fields += 1
    if braider.years_experience: completed_fields += 1
    if braider.specialties: completed_fields += 1
    if braider.portfolio_images.exists(): completed_fields += 1
    if braider.services.exists(): completed_fields += 1
    if braider.profile_image: completed_fields += 1
    if braider.service_areas: completed_fields += 1
    
    return round((completed_fields / total_fields) * 100)