"""
Views for booking management.
"""

from datetime import datetime, timedelta, date
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.utils import timezone

from .models import Booking, AvailabilitySlot, AvailabilityException
from .serializers import (
    BookingListSerializer, BookingDetailSerializer, BookingCreateSerializer,
    BookingUpdateSerializer, BookingStatusUpdateSerializer,
    AvailabilitySlotSerializer, AvailabilityExceptionSerializer,
    AvailabilityCheckSerializer, BraiderAvailabilitySerializer
)
from .utils import AvailabilityManager, get_braider_next_available_slots, check_booking_conflicts
from apps.braiders.models import Braider, Service
from apps.core.permissions import CanManageBooking, IsBraider, IsAdminUser
from apps.core.pagination import CustomPagination


class BookingFilter(django_filters.FilterSet):
    """
    Advanced filtering for bookings.
    """
    status = django_filters.MultipleChoiceFilter(choices=Booking.STATUS_CHOICES)
    booking_type = django_filters.ChoiceFilter(choices=Booking.BOOKING_TYPES)
    payment_status = django_filters.MultipleChoiceFilter(choices=Booking.PAYMENT_STATUS_CHOICES)
    
    # Date filters
    booking_date = django_filters.DateFilter()
    booking_date_from = django_filters.DateFilter(field_name='booking_date', lookup_expr='gte')
    booking_date_to = django_filters.DateFilter(field_name='booking_date', lookup_expr='lte')
    created_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Price filters
    min_price = django_filters.NumberFilter(field_name='total_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='total_price', lookup_expr='lte')
    
    # Service filters
    service_category = django_filters.CharFilter(field_name='service__category')
    braider_name = django_filters.CharFilter(field_name='braider__name', lookup_expr='icontains')
    
    # Client filters
    client_name = django_filters.CharFilter(lookup_expr='icontains')
    client_email = django_filters.CharFilter(lookup_expr='icontains')
    
    # Special filters
    is_past_due = django_filters.BooleanFilter(method='filter_past_due')
    upcoming = django_filters.BooleanFilter(method='filter_upcoming')
    
    class Meta:
        model = Booking
        fields = []
    
    def filter_past_due(self, queryset, name, value):
        """Filter bookings that are past due."""
        now = timezone.now()
        if value:
            return queryset.filter(
                booking_date__lt=now.date()
            ).exclude(
                status__in=['completed', 'cancelled_client', 'cancelled_braider']
            )
        return queryset
    
    def filter_upcoming(self, queryset, name, value):
        """Filter upcoming bookings."""
        now = timezone.now()
        if value:
            return queryset.filter(
                booking_date__gte=now.date(),
                status__in=['pending', 'confirmed']
            )
        return queryset


class BookingListView(generics.ListAPIView):
    """
    List bookings with filtering (admin view).
    """
    serializer_class = BookingListSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookingFilter
    search_fields = [
        'booking_reference', 'client_name', 'client_email', 'client_phone',
        'braider__name', 'service__name'
    ]
    ordering_fields = ['booking_date', 'booking_time', 'created_at', 'total_price']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Booking.objects.select_related(
            'braider', 'service', 'user'
        ).all()


class BookingDetailView(generics.RetrieveAPIView):
    """
    Retrieve individual booking details.
    """
    serializer_class = BookingDetailSerializer
    permission_classes = [CanManageBooking]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Booking.objects.select_related(
            'braider', 'service', 'service_address', 'user'
        ).prefetch_related('status_history__changed_by')


class BookingCreateView(generics.CreateAPIView):
    """
    Create new booking.
    """
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        
        return Response({
            'message': 'Booking created successfully',
            'booking_id': str(booking.id),
            'booking_reference': booking.booking_reference,
            'status': booking.status
        }, status=status.HTTP_201_CREATED)


class BookingUpdateView(generics.UpdateAPIView):
    """
    Update existing booking.
    """
    serializer_class = BookingUpdateSerializer
    permission_classes = [CanManageBooking]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Booking.objects.all()
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        
        return Response({
            'message': 'Booking updated successfully',
            'booking_id': str(booking.id),
            'booking_reference': booking.booking_reference
        })


class BookingStatusUpdateView(generics.UpdateAPIView):
    """
    Update booking status.
    """
    serializer_class = BookingStatusUpdateSerializer
    permission_classes = [CanManageBooking]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Booking.objects.all()
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        
        return Response({
            'message': f'Booking status updated to {booking.get_status_display()}',
            'booking_id': str(booking.id),
            'status': booking.status
        })


class MyBookingsView(generics.ListAPIView):
    """
    List current user's bookings.
    """
    serializer_class = BookingListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BookingFilter
    ordering_fields = ['booking_date', 'booking_time', 'created_at']
    ordering = ['-booking_date', '-booking_time']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).select_related('braider', 'service')


class BraiderBookingsView(generics.ListAPIView):
    """
    List bookings for authenticated braider.
    """
    serializer_class = BookingListSerializer
    permission_classes = [IsBraider]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookingFilter
    search_fields = ['client_name', 'client_email', 'booking_reference']
    ordering_fields = ['booking_date', 'booking_time', 'created_at']
    ordering = ['booking_date', 'booking_time']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        braider = get_object_or_404(Braider, user=self.request.user)
        return Booking.objects.filter(
            braider=braider
        ).select_related('service', 'user')


class AvailabilitySlotListCreateView(generics.ListCreateAPIView):
    """
    Manage braider availability slots.
    """
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsBraider]
    
    def get_queryset(self):
        braider = get_object_or_404(Braider, user=self.request.user)
        return AvailabilitySlot.objects.filter(braider=braider)
    
    def perform_create(self, serializer):
        braider = get_object_or_404(Braider, user=self.request.user)
        serializer.save(braider=braider)


class AvailabilitySlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual availability slots.
    """
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsBraider]
    lookup_field = 'id'
    
    def get_queryset(self):
        braider = get_object_or_404(Braider, user=self.request.user)
        return AvailabilitySlot.objects.filter(braider=braider)


class AvailabilityExceptionListCreateView(generics.ListCreateAPIView):
    """
    Manage braider availability exceptions.
    """
    serializer_class = AvailabilityExceptionSerializer
    permission_classes = [IsBraider]
    
    def get_queryset(self):
        braider = get_object_or_404(Braider, user=self.request.user)
        return AvailabilityException.objects.filter(braider=braider)
    
    def perform_create(self, serializer):
        braider = get_object_or_404(Braider, user=self.request.user)
        serializer.save(braider=braider)


class AvailabilityExceptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual availability exceptions.
    """
    serializer_class = AvailabilityExceptionSerializer
    permission_classes = [IsBraider]
    lookup_field = 'id'
    
    def get_queryset(self):
        braider = get_object_or_404(Braider, user=self.request.user)
        return AvailabilityException.objects.filter(braider=braider)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_availability(request):
    """
    Check availability for a specific slot.
    """
    serializer = AvailabilityCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    braider = data['braider']
    service = data['service']
    booking_date = data['booking_date']
    booking_time = data['booking_time']
    booking_type = data['booking_type']
    
    # Check availability
    manager = AvailabilityManager(braider)
    is_available, reason = manager.is_slot_available(
        booking_date, booking_time, service.duration_minutes, booking_type
    )
    
    return Response({
        'available': is_available,
        'reason': reason,
        'slot_details': {
            'date': booking_date.isoformat(),
            'time': booking_time.strftime('%H:%M'),
            'duration': service.duration_minutes,
            'service_name': service.name,
            'braider_name': braider.name
        }
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def braider_availability(request, braider_id):
    """
    Get braider availability for a date range.
    """
    braider = get_object_or_404(Braider, id=braider_id, status='approved')
    
    serializer = BraiderAvailabilitySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    start_date = data['start_date']
    end_date = data['end_date']
    service_duration = data['service_duration']
    booking_type = data['booking_type']
    
    # Get availability
    manager = AvailabilityManager(braider)
    availability = manager.get_available_slots(
        start_date, end_date, service_duration, booking_type
    )
    
    return Response({
        'braider_id': str(braider.id),
        'braider_name': braider.name,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'service_duration': service_duration,
        'booking_type': booking_type,
        'availability': availability
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def next_available_slots(request, braider_id):
    """
    Get next available slots for a braider.
    """
    braider = get_object_or_404(Braider, id=braider_id, status='approved')
    
    service_duration = int(request.query_params.get('duration', 60))
    booking_type = request.query_params.get('type', 'home')
    days_ahead = int(request.query_params.get('days', 14))
    
    next_slots = get_braider_next_available_slots(
        braider, service_duration, booking_type, days_ahead
    )
    
    return Response({
        'braider_id': str(braider.id),
        'braider_name': braider.name,
        'service_duration': service_duration,
        'booking_type': booking_type,
        'next_available_slots': next_slots
    })


@api_view(['POST'])
@permission_classes([CanManageBooking])
def cancel_booking(request, booking_id):
    """
    Cancel a booking.
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if booking can be cancelled
    if not booking.can_be_cancelled():
        return Response({
            'error': 'Booking cannot be cancelled at this time'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    reason = request.data.get('reason', '')
    
    # Determine who is cancelling
    if request.user == booking.user:
        new_status = 'cancelled_client'
    elif hasattr(request.user, 'braider_profile') and request.user.braider_profile == booking.braider:
        new_status = 'cancelled_braider'
    else:
        new_status = 'cancelled_braider'  # Admin cancellation
    
    # Update booking status
    serializer = BookingStatusUpdateSerializer(
        booking, 
        data={'status': new_status, 'reason': reason},
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    updated_booking = serializer.save()
    
    return Response({
        'message': 'Booking cancelled successfully',
        'booking_id': str(updated_booking.id),
        'status': updated_booking.status,
        'cancelled_at': updated_booking.cancelled_at
    })


@api_view(['POST'])
@permission_classes([IsBraider])
def confirm_booking(request, booking_id):
    """
    Confirm a booking (braider only).
    """
    booking = get_object_or_404(Booking, id=booking_id)
    braider = get_object_or_404(Braider, user=request.user)
    
    # Check if booking belongs to braider
    if booking.braider != braider:
        return Response({
            'error': 'You can only confirm your own bookings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if booking can be confirmed
    if booking.status != 'pending':
        return Response({
            'error': 'Booking is not in pending status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Confirm booking
    serializer = BookingStatusUpdateSerializer(
        booking,
        data={'status': 'confirmed', 'reason': 'Confirmed by braider'},
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    updated_booking = serializer.save()
    
    return Response({
        'message': 'Booking confirmed successfully',
        'booking_id': str(updated_booking.id),
        'status': updated_booking.status,
        'confirmed_at': updated_booking.confirmed_at
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def booking_stats(request):
    """
    Get booking statistics for admin dashboard.
    """
    from django.db.models import Sum, Avg
    
    today = timezone.now().date()
    
    stats = {
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'confirmed_bookings': Booking.objects.filter(status='confirmed').count(),
        'completed_bookings': Booking.objects.filter(status='completed').count(),
        'cancelled_bookings': Booking.objects.filter(
            status__in=['cancelled_client', 'cancelled_braider']
        ).count(),
        'today_bookings': Booking.objects.filter(booking_date=today).count(),
        'upcoming_bookings': Booking.objects.filter(
            booking_date__gt=today,
            status__in=['pending', 'confirmed']
        ).count(),
        'total_revenue': Booking.objects.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'average_booking_value': Booking.objects.filter(
            status='completed'
        ).aggregate(avg=Avg('total_price'))['avg'] or 0,
        'bookings_by_status': Booking.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count'),
        'bookings_by_type': Booking.objects.values('booking_type').annotate(
            count=Count('id')
        ),
        'recent_bookings': Booking.objects.select_related(
            'braider', 'service'
        ).order_by('-created_at')[:5].values(
            'id', 'booking_reference', 'client_name', 
            'braider__name', 'service__name', 'status'
        )
    }
    
    return Response(stats)