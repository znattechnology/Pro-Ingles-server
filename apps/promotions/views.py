"""
Views for promotions and campaigns API.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from decimal import Decimal

from .models import Campaign, Promotion, CouponCode, CampaignParticipant, PromotionUsage
from .serializers import (
    CampaignListSerializer, CampaignDetailSerializer,
    PromotionListSerializer, PromotionDetailSerializer,
    CouponValidationSerializer, CouponApplicationSerializer,
    DiscountCalculationSerializer, ActivePromotionsSerializer,
    PromotionUsageSerializer, CampaignParticipantSerializer
)
from apps.core.pagination import CustomPagination


class CampaignFilter(django_filters.FilterSet):
    """Filter for campaigns."""
    
    campaign_type = django_filters.ChoiceFilter(choices=Campaign.CAMPAIGN_TYPES)
    status = django_filters.ChoiceFilter(choices=Campaign.STATUS_CHOICES)
    is_running = django_filters.BooleanFilter(method='filter_is_running')
    
    class Meta:
        model = Campaign
        fields = ['campaign_type', 'status', 'is_active']
    
    def filter_is_running(self, queryset, name, value):
        """Filter campaigns that are currently running."""
        now = timezone.now()
        if value:
            return queryset.filter(
                is_active=True,
                status='active',
                start_date__lte=now,
                end_date__gte=now
            )
        return queryset


class CampaignListView(generics.ListAPIView):
    """List active campaigns."""
    
    serializer_class = CampaignListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CampaignFilter
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Campaign.objects.filter(
            is_active=True,
            status='active'
        ).order_by('-created_at')


class CampaignDetailView(generics.RetrieveAPIView):
    """Get campaign details."""
    
    serializer_class = CampaignDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Campaign.objects.filter(is_active=True, status='active')
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when campaign is viewed."""
        instance = self.get_object()
        instance.total_views += 1
        instance.save(update_fields=['total_views'])
        
        # Track user view if authenticated
        if request.user.is_authenticated:
            participant, created = CampaignParticipant.objects.get_or_create(
                campaign=instance,
                user=request.user,
                defaults={'is_active': True}
            )
            participant.total_views += 1
            participant.save(update_fields=['total_views'])
        
        return super().retrieve(request, *args, **kwargs)


class PromotionFilter(django_filters.FilterSet):
    """Filter for promotions."""
    
    promotion_type = django_filters.ChoiceFilter(choices=Promotion.PROMOTION_TYPES)
    applies_to = django_filters.ChoiceFilter(choices=Promotion.APPLIES_TO)
    campaign = django_filters.ModelChoiceFilter(queryset=Campaign.objects.all())
    min_discount = django_filters.NumberFilter(method='filter_min_discount')
    
    class Meta:
        model = Promotion
        fields = ['promotion_type', 'applies_to', 'is_active', 'is_stackable']
    
    def filter_min_discount(self, queryset, name, value):
        """Filter by minimum discount percentage."""
        return queryset.filter(discount_percentage__gte=value)


class PromotionListView(generics.ListAPIView):
    """List active promotions."""
    
    serializer_class = PromotionListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PromotionFilter
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Promotion.objects.filter(
            is_active=True,
            campaign__is_active=True,
            campaign__status='active'
        ).select_related('campaign').order_by('-created_at')


class PromotionDetailView(generics.RetrieveAPIView):
    """Get promotion details."""
    
    serializer_class = PromotionDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'code'
    
    def get_queryset(self):
        return Promotion.objects.filter(
            is_active=True,
            campaign__is_active=True,
            campaign__status='active'
        ).select_related('campaign')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_coupon(request):
    """
    Validate a coupon code without applying it.
    """
    serializer = CouponValidationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    code = serializer.validated_data['code']
    order_amount = serializer.validated_data.get('order_amount')
    
    try:
        # Try to find promotion by code
        promotion = Promotion.objects.get(
            code=code,
            is_active=True,
            campaign__is_active=True,
            campaign__status='active'
        )
        
        # Check if user can use promotion
        if request.user.is_authenticated:
            can_use, reason = promotion.can_be_used(request.user, order_amount)
        else:
            can_use, reason = True, "Valid promotion"
        
        if can_use:
            discount_amount = Decimal('0.00')
            if order_amount:
                discount_amount = promotion.calculate_discount(order_amount)
            
            return Response({
                'valid': True,
                'promotion': PromotionDetailSerializer(
                    promotion, 
                    context={'request': request}
                ).data,
                'estimated_discount': float(discount_amount)
            })
        else:
            return Response({
                'valid': False,
                'error': reason
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Promotion.DoesNotExist:
        # Try to find coupon code
        try:
            coupon = CouponCode.objects.get(code=code)
            if request.user.is_authenticated:
                can_use, reason = coupon.can_be_used_by(request.user)
            else:
                can_use, reason = coupon.is_valid, "Valid coupon" if coupon.is_valid else "Invalid coupon"
            
            if can_use:
                discount_amount = Decimal('0.00')
                if order_amount:
                    discount_amount = coupon.promotion.calculate_discount(order_amount)
                
                return Response({
                    'valid': True,
                    'promotion': PromotionDetailSerializer(
                        coupon.promotion,
                        context={'request': request}
                    ).data,
                    'estimated_discount': float(discount_amount)
                })
            else:
                return Response({
                    'valid': False,
                    'error': reason
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except CouponCode.DoesNotExist:
            return Response({
                'valid': False,
                'error': 'Invalid coupon code'
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def apply_coupon(request):
    """
    Apply a coupon code and calculate final discount.
    """
    serializer = CouponApplicationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    code = serializer.validated_data['code']
    order_amount = serializer.validated_data['order_amount']
    order_items = serializer.validated_data.get('order_items', [])
    
    try:
        # Try to find promotion by code
        promotion = Promotion.objects.get(
            code=code,
            is_active=True,
            campaign__is_active=True,
            campaign__status='active'
        )
        
        can_use, reason = promotion.can_be_used(request.user, order_amount)
        if not can_use:
            return Response({
                'error': reason
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate discount
        discount_amount = promotion.calculate_discount(order_amount, order_items)
        final_amount = max(Decimal('0.00'), order_amount - discount_amount)
        
        # Add user to campaign if not already participating
        try:
            promotion.campaign.add_participant(request.user)
        except:
            pass  # User might already be participating
        
        return Response({
            'success': True,
            'discount_amount': float(discount_amount),
            'final_amount': float(final_amount),
            'promotion': {
                'id': str(promotion.id),
                'name': promotion.name,
                'code': promotion.code,
                'type': promotion.promotion_type
            }
        })
    
    except Promotion.DoesNotExist:
        # Try coupon code
        try:
            coupon = CouponCode.objects.get(code=code)
            can_use, reason = coupon.can_be_used_by(request.user)
            
            if not can_use:
                return Response({
                    'error': reason
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate discount
            discount_amount = coupon.promotion.calculate_discount(order_amount, order_items)
            final_amount = max(Decimal('0.00'), order_amount - discount_amount)
            
            return Response({
                'success': True,
                'discount_amount': float(discount_amount),
                'final_amount': float(final_amount),
                'promotion': {
                    'id': str(coupon.promotion.id),
                    'name': coupon.promotion.name,
                    'code': coupon.code,
                    'type': coupon.promotion.promotion_type
                },
                'coupon_id': str(coupon.id)
            })
            
        except CouponCode.DoesNotExist:
            return Response({
                'error': 'Invalid coupon code'
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def active_promotions(request):
    """
    Get all active promotions and campaigns.
    """
    # Get running campaigns
    campaigns = Campaign.objects.filter(
        is_active=True,
        status='active',
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).order_by('-created_at')[:10]
    
    # Get active promotions
    promotions = Promotion.objects.filter(
        is_active=True,
        campaign__is_active=True,
        campaign__status='active'
    ).select_related('campaign').order_by('-created_at')[:20]
    
    # Count eligible promotions for authenticated user
    user_eligible_count = 0
    if request.user.is_authenticated:
        for promotion in promotions:
            can_use, _ = promotion.can_be_used(request.user)
            if can_use:
                user_eligible_count += 1
    
    return Response({
        'campaigns': CampaignListSerializer(campaigns, many=True).data,
        'promotions': PromotionListSerializer(promotions, many=True).data,
        'user_eligible_count': user_eligible_count
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_campaign(request, campaign_id):
    """
    Join a campaign as a participant.
    """
    try:
        campaign = get_object_or_404(Campaign, id=campaign_id)
        
        can_participate, reason = campaign.can_participate(request.user)
        if not can_participate:
            return Response({
                'error': reason
            }, status=status.HTTP_400_BAD_REQUEST)
        
        participant = campaign.add_participant(request.user)
        
        return Response({
            'success': True,
            'message': f'Successfully joined {campaign.name}',
            'participant_id': str(participant.id)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class UserPromotionUsageView(generics.ListAPIView):
    """
    List user's promotion usage history.
    """
    serializer_class = PromotionUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return PromotionUsage.objects.filter(
            user=self.request.user
        ).select_related('promotion', 'promotion__campaign').order_by('-created_at')


class UserCampaignParticipationView(generics.ListAPIView):
    """
    List user's campaign participations.
    """
    serializer_class = CampaignParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return CampaignParticipant.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related('campaign').order_by('-joined_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_promotion_stats(request):
    """
    Get user's promotion usage statistics.
    """
    user = request.user
    
    total_usages = PromotionUsage.objects.filter(user=user).count()
    total_savings = PromotionUsage.objects.filter(user=user).aggregate(
        total=models.Sum('discount_amount')
    )['total'] or Decimal('0.00')
    
    active_participations = CampaignParticipant.objects.filter(
        user=user,
        is_active=True
    ).count()
    
    # Get favorite promotion types
    favorite_types = PromotionUsage.objects.filter(user=user).values(
        'promotion__promotion_type'
    ).annotate(
        count=models.Count('id')
    ).order_by('-count')[:3]
    
    return Response({
        'total_promotions_used': total_usages,
        'total_savings': float(total_savings),
        'active_campaign_participations': active_participations,
        'favorite_promotion_types': list(favorite_types)
    })