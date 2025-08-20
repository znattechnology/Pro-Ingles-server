"""
Views for ratings and reviews system.
"""

from decimal import Decimal
from django.db.models import Q, Count, Avg, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from .models import (
    BraiderReview, ProductReview, ReviewHelpfulness, ReviewResponse,
    ReviewReport
)
from .serializers import (
    BraiderReviewListSerializer, BraiderReviewDetailSerializer,
    BraiderReviewCreateSerializer, ProductReviewListSerializer,
    ProductReviewDetailSerializer, ProductReviewCreateSerializer,
    ReviewHelpfulnessSerializer, ReviewResponseSerializer,
    ReviewResponseCreateSerializer, ReviewReportSerializer,
    ReviewModerationSerializer, ReviewStatsSerializer
)
from apps.braiders.models import Braider
from apps.ecommerce.models import Product
from apps.bookings.models import Booking
from apps.ecommerce.models import Order
from apps.core.permissions import IsAdminUser, IsBraider
from apps.core.pagination import CustomPagination


class BraiderReviewFilter(django_filters.FilterSet):
    """Advanced filtering for braider reviews."""
    
    rating = django_filters.NumberFilter(field_name='overall_rating')
    min_rating = django_filters.NumberFilter(field_name='overall_rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='overall_rating', lookup_expr='lte')
    verified = django_filters.BooleanFilter(field_name='is_verified')
    would_recommend = django_filters.BooleanFilter()
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = BraiderReview
        fields = ['status']


class ProductReviewFilter(django_filters.FilterSet):
    """Advanced filtering for product reviews."""
    
    rating = django_filters.NumberFilter()
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    verified_purchase = django_filters.BooleanFilter(field_name='is_verified_purchase')
    would_recommend = django_filters.BooleanFilter()
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = ProductReview
        fields = ['status']


class BraiderReviewListView(generics.ListAPIView):
    """List reviews for a specific braider."""
    
    serializer_class = BraiderReviewListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BraiderReviewFilter
    ordering_fields = ['created_at', 'overall_rating', 'helpful_count']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        braider_id = self.kwargs['braider_id']
        return BraiderReview.objects.filter(
            braider_id=braider_id,
            status='approved'
        ).select_related('user', 'braider', 'booking__service')


class BraiderReviewDetailView(generics.RetrieveAPIView):
    """Retrieve individual braider review details."""
    
    serializer_class = BraiderReviewDetailSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return BraiderReview.objects.filter(
            status='approved'
        ).select_related(
            'user', 'braider', 'booking__service'
        ).prefetch_related('images', 'response')


class BraiderReviewCreateView(generics.CreateAPIView):
    """Create review for a braider."""
    
    serializer_class = BraiderReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        
        return Response({
            'message': 'Review submitted successfully',
            'review_id': str(review.id),
            'status': review.status
        }, status=status.HTTP_201_CREATED)


class ProductReviewListView(generics.ListAPIView):
    """List reviews for a specific product."""
    
    serializer_class = ProductReviewListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductReviewFilter
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductReview.objects.filter(
            product_id=product_id,
            status='approved'
        ).select_related('user', 'product', 'order')


class ProductReviewDetailView(generics.RetrieveAPIView):
    """Retrieve individual product review details."""
    
    serializer_class = ProductReviewDetailSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return ProductReview.objects.filter(
            status='approved'
        ).select_related(
            'user', 'product', 'order'
        ).prefetch_related('images', 'response')


class ProductReviewCreateView(generics.CreateAPIView):
    """Create review for a product."""
    
    serializer_class = ProductReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        
        return Response({
            'message': 'Review submitted successfully',
            'review_id': str(review.id),
            'status': review.status
        }, status=status.HTTP_201_CREATED)


class MyBraiderReviewsView(generics.ListAPIView):
    """List current user's braider reviews."""
    
    serializer_class = BraiderReviewDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'overall_rating']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return BraiderReview.objects.filter(
            user=self.request.user
        ).select_related('braider', 'booking__service').prefetch_related('images')


class MyProductReviewsView(generics.ListAPIView):
    """List current user's product reviews."""
    
    serializer_class = ProductReviewDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return ProductReview.objects.filter(
            user=self.request.user
        ).select_related('product', 'order').prefetch_related('images')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reviewable_bookings(request):
    """Get bookings that can be reviewed."""
    bookings = Booking.objects.filter(
        user=request.user,
        status='completed'
    ).exclude(
        review__isnull=False  # Exclude bookings that already have reviews
    ).select_related('braider', 'service').order_by('-completed_at')
    
    reviewable = []
    for booking in bookings:
        reviewable.append({
            'booking_id': str(booking.id),
            'braider_id': str(booking.braider.id),
            'braider_name': booking.braider.name,
            'service_name': booking.service.name,
            'booking_date': booking.booking_date.isoformat(),
            'completed_at': booking.completed_at.isoformat() if booking.completed_at else None
        })
    
    return Response({'reviewable_bookings': reviewable})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reviewable_products(request):
    """Get products from delivered orders that can be reviewed."""
    from apps.ecommerce.models import OrderItem
    
    # Get delivered orders
    delivered_orders = Order.objects.filter(
        user=request.user,
        status='delivered'
    )
    
    reviewable = []
    for order in delivered_orders:
        for item in order.items.all():
            # Check if product was already reviewed for this order
            if not ProductReview.objects.filter(
                user=request.user,
                product=item.product,
                order=order
            ).exists():
                reviewable.append({
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'product_id': str(item.product.id),
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None
                })
    
    return Response({'reviewable_products': reviewable})


class ReviewHelpfulnessView(APIView):
    """Manage review helpfulness votes."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, review_type, review_id):
        """Vote on review helpfulness."""
        # Validate review type
        if review_type not in ['braider', 'product']:
            return Response(
                {'error': 'Invalid review type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the review
        if review_type == 'braider':
            try:
                review = BraiderReview.objects.get(id=review_id, status='approved')
            except BraiderReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                review = ProductReview.objects.get(id=review_id, status='approved')
            except ProductReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Prevent self-voting
        if review.user == request.user:
            return Response(
                {'error': 'You cannot vote on your own review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update vote
        serializer = ReviewHelpfulnessSerializer(
            data=request.data,
            context={
                'request': request,
                'review_id': review_id,
                'review_type': review_type
            }
        )
        serializer.is_valid(raise_exception=True)
        helpfulness = serializer.save()
        
        return Response({
            'message': f'Voted {helpfulness.vote} successfully',
            'vote': helpfulness.vote
        })


class ReviewResponseView(generics.CreateAPIView):
    """Create response to a review."""
    
    serializer_class = ReviewResponseCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, review_type, review_id):
        """Create response to review."""
        # Validate review type
        if review_type not in ['braider', 'product']:
            return Response(
                {'error': 'Invalid review type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the review and validate permissions
        if review_type == 'braider':
            try:
                review = BraiderReview.objects.get(id=review_id, status='approved')
                # Only braider or admin can respond
                if not (request.user.is_staff or 
                       (hasattr(request.user, 'braider_profile') and 
                        request.user.braider_profile == review.braider)):
                    return Response(
                        {'error': 'Permission denied'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except BraiderReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                review = ProductReview.objects.get(id=review_id, status='approved')
                # Only admin can respond to product reviews
                if not request.user.is_staff:
                    return Response(
                        {'error': 'Permission denied'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except ProductReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Check if response already exists
        if hasattr(review, 'response'):
            return Response(
                {'error': 'Response already exists for this review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create response
        serializer = self.get_serializer(
            data=request.data,
            context={
                'request': request,
                'review_id': review_id,
                'review_type': review_type
            }
        )
        serializer.is_valid(raise_exception=True)
        response = serializer.save()
        
        return Response({
            'message': 'Response created successfully',
            'response_id': str(response.id)
        }, status=status.HTTP_201_CREATED)


class ReviewReportView(generics.CreateAPIView):
    """Report a review as inappropriate."""
    
    serializer_class = ReviewReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, review_type, review_id):
        """Report review."""
        # Validate review type
        if review_type not in ['braider', 'product']:
            return Response(
                {'error': 'Invalid review type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the review
        if review_type == 'braider':
            try:
                review = BraiderReview.objects.get(id=review_id, status='approved')
            except BraiderReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                review = ProductReview.objects.get(id=review_id, status='approved')
            except ProductReview.DoesNotExist:
                return Response(
                    {'error': 'Review not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Prevent self-reporting
        if review.user == request.user:
            return Response(
                {'error': 'You cannot report your own review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create report
        serializer = self.get_serializer(
            data=request.data,
            context={
                'request': request,
                'review_id': review_id,
                'review_type': review_type
            }
        )
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        
        return Response({
            'message': 'Review reported successfully',
            'report_id': str(report.id)
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def braider_review_stats(request, braider_id):
    """Get review statistics for a braider."""
    braider = get_object_or_404(Braider, id=braider_id)
    
    reviews = BraiderReview.objects.filter(braider=braider, status='approved')
    
    if not reviews.exists():
        return Response({
            'total_reviews': 0,
            'average_rating': 0,
            'rating_distribution': {},
            'verified_reviews': 0,
            'recent_reviews': 0,
            'recommendation_rate': 0
        })
    
    # Calculate statistics
    stats = reviews.aggregate(
        total_reviews=Count('id'),
        average_rating=Avg('overall_rating'),
        quality_rating=Avg('quality_rating'),
        professionalism_rating=Avg('professionalism_rating'),
        communication_rating=Avg('communication_rating'),
        value_rating=Avg('value_rating'),
        verified_reviews=Count('id', filter=Q(is_verified=True)),
        would_recommend=Count('id', filter=Q(would_recommend=True))
    )
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[str(i)] = reviews.filter(overall_rating=i).count()
    
    # Recent reviews (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reviews = reviews.filter(created_at__gte=thirty_days_ago).count()
    
    # Recommendation rate
    recommendation_rate = (stats['would_recommend'] / stats['total_reviews']) * 100 if stats['total_reviews'] > 0 else 0
    
    response_data = {
        'total_reviews': stats['total_reviews'],
        'average_rating': round(stats['average_rating'], 2),
        'quality_rating': round(stats['quality_rating'], 2),
        'professionalism_rating': round(stats['professionalism_rating'], 2),
        'communication_rating': round(stats['communication_rating'], 2),
        'value_rating': round(stats['value_rating'], 2),
        'rating_distribution': rating_distribution,
        'verified_reviews': stats['verified_reviews'],
        'recent_reviews': recent_reviews,
        'recommendation_rate': round(recommendation_rate, 2)
    }
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_review_stats(request, product_id):
    """Get review statistics for a product."""
    product = get_object_or_404(Product, id=product_id)
    
    reviews = ProductReview.objects.filter(product=product, status='approved')
    
    if not reviews.exists():
        return Response({
            'total_reviews': 0,
            'average_rating': 0,
            'rating_distribution': {},
            'verified_reviews': 0,
            'recent_reviews': 0,
            'recommendation_rate': 0
        })
    
    # Calculate statistics
    stats = reviews.aggregate(
        total_reviews=Count('id'),
        average_rating=Avg('rating'),
        quality_rating=Avg('quality_rating'),
        value_rating=Avg('value_rating'),
        verified_reviews=Count('id', filter=Q(is_verified_purchase=True)),
        would_recommend=Count('id', filter=Q(would_recommend=True))
    )
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[str(i)] = reviews.filter(rating=i).count()
    
    # Recent reviews (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reviews = reviews.filter(created_at__gte=thirty_days_ago).count()
    
    # Recommendation rate
    recommendation_rate = (stats['would_recommend'] / stats['total_reviews']) * 100 if stats['total_reviews'] > 0 else 0
    
    response_data = {
        'total_reviews': stats['total_reviews'],
        'average_rating': round(stats['average_rating'], 2),
        'quality_rating': round(stats['quality_rating'], 2),
        'value_rating': round(stats['value_rating'], 2),
        'rating_distribution': rating_distribution,
        'verified_reviews': stats['verified_reviews'],
        'recent_reviews': recent_reviews,
        'recommendation_rate': round(recommendation_rate, 2)
    }
    
    return Response(response_data)


# Admin views for moderation
class PendingReviewsView(generics.ListAPIView):
    """List reviews pending moderation (admin only)."""
    
    permission_classes = [IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering = ['created_at']
    pagination_class = CustomPagination
    
    def get_serializer_class(self):
        review_type = self.request.query_params.get('type', 'braider')
        return BraiderReviewDetailSerializer if review_type == 'braider' else ProductReviewDetailSerializer
    
    def get_queryset(self):
        review_type = self.request.query_params.get('type', 'braider')
        
        if review_type == 'braider':
            return BraiderReview.objects.filter(
                status='pending'
            ).select_related('user', 'braider', 'booking__service')
        else:
            return ProductReview.objects.filter(
                status='pending'
            ).select_related('user', 'product', 'order')


class ReviewModerationView(generics.UpdateAPIView):
    """Moderate review status (admin only)."""
    
    serializer_class = ReviewModerationSerializer
    permission_classes = [IsAdminUser]
    
    def get_object(self):
        review_type = self.kwargs['review_type']
        review_id = self.kwargs['review_id']
        
        if review_type == 'braider':
            return get_object_or_404(BraiderReview, id=review_id)
        else:
            return get_object_or_404(ProductReview, id=review_id)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        
        return Response({
            'message': f'Review status updated to {review.status}',
            'review_id': str(review.id),
            'status': review.status
        })