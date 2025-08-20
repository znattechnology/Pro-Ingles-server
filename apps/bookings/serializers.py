"""
Serializers for booking models.
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Booking, AvailabilitySlot, AvailabilityException, BookingStatusHistory
from .utils import AvailabilityManager, check_booking_conflicts
from apps.core.models import Address
from apps.users.serializers import AddressSerializer
from apps.braiders.serializers import BraiderListSerializer, ServiceListSerializer


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    """
    Serializer for availability slots.
    """
    
    class Meta:
        model = AvailabilitySlot
        fields = [
            'id', 'start_date', 'end_date', 'start_time', 'end_time',
            'recurrence_type', 'days_of_week', 'is_home_service',
            'is_salon_service', 'min_advance_hours', 'max_advance_days',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Validate availability slot data."""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError({
                'end_time': 'End time must be after start time'
            })
        
        if data.get('end_date') and data['start_date'] > data['end_date']:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date'
            })
        
        if not data['is_home_service'] and not data['is_salon_service']:
            raise serializers.ValidationError(
                'At least one service type must be selected'
            )
        
        if data['recurrence_type'] == 'weekly' and not data.get('days_of_week'):
            raise serializers.ValidationError({
                'days_of_week': 'Days of week required for weekly recurrence'
            })
        
        return data


class AvailabilityExceptionSerializer(serializers.ModelSerializer):
    """
    Serializer for availability exceptions.
    """
    
    class Meta:
        model = AvailabilityException
        fields = [
            'id', 'date', 'exception_type', 'start_time', 'end_time',
            'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Validate availability exception data."""
        if data['exception_type'] in ['limited', 'special']:
            if not data.get('start_time') or not data.get('end_time'):
                raise serializers.ValidationError(
                    'Start and end time required for limited/special hours'
                )
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
        
        return data


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for booking status history.
    """
    changed_by_name = serializers.CharField(source='changed_by.name', read_only=True)
    
    class Meta:
        model = BookingStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'changed_by_name',
            'reason', 'automatic', 'created_at'
        ]


class BookingListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for booking listings.
    """
    braider_name = serializers.CharField(source='braider.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    booking_datetime = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'braider_name', 'service_name',
            'service_category', 'booking_date', 'booking_time', 'booking_datetime',
            'booking_type', 'status', 'status_display', 'total_price',
            'payment_status', 'client_name', 'duration_display', 'created_at'
        ]
    
    def get_booking_datetime(self, obj):
        """Get formatted booking datetime."""
        return datetime.combine(obj.booking_date, obj.booking_time).isoformat()
    
    def get_duration_display(self, obj):
        """Get formatted duration."""
        minutes = obj.duration_minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h{mins:02d}"
        return f"{mins}min"


class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual booking view.
    """
    braider = BraiderListSerializer(read_only=True)
    service = ServiceListSerializer(read_only=True)
    service_address = AddressSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.CharField(source='get_status_display_color', read_only=True)
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    booking_datetime = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_reschedule = serializers.SerializerMethodField()
    is_past_due = serializers.ReadOnlyField()
    duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'braider', 'service', 'booking_date',
            'booking_time', 'booking_datetime', 'estimated_end_time',
            'actual_start_time', 'actual_end_time', 'booking_type',
            'service_address', 'client_name', 'client_phone', 'client_email',
            'special_requests', 'hair_type', 'hair_length', 'preferred_products',
            'base_price', 'additional_charges', 'discount_amount', 'total_price',
            'payment_status', 'payment_method', 'deposit_amount', 'status',
            'status_display', 'status_color', 'confirmed_at', 'completed_at',
            'cancelled_at', 'cancellation_reason', 'completion_notes',
            'internal_notes', 'reminder_sent', 'reminder_sent_at',
            'status_history', 'can_cancel', 'can_reschedule', 'is_past_due',
            'duration_display', 'created_at'
        ]
    
    def get_booking_datetime(self, obj):
        """Get formatted booking datetime."""
        return datetime.combine(obj.booking_date, obj.booking_time).isoformat()
    
    def get_can_cancel(self, obj):
        """Check if booking can be cancelled."""
        return obj.can_be_cancelled()
    
    def get_can_reschedule(self, obj):
        """Check if booking can be rescheduled."""
        return obj.can_be_rescheduled()
    
    def get_duration_display(self, obj):
        """Get formatted duration."""
        minutes = obj.duration_minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h{mins:02d}"
        return f"{mins}min"


class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating bookings.
    """
    service_address_data = AddressSerializer(write_only=True, required=False)
    
    class Meta:
        model = Booking
        fields = [
            'braider', 'service', 'booking_date', 'booking_time',
            'booking_type', 'service_address_data', 'client_name',
            'client_phone', 'client_email', 'special_requests',
            'hair_type', 'hair_length', 'preferred_products'
        ]
    
    def validate(self, data):
        """Validate booking data."""
        braider = data['braider']
        service = data['service']
        booking_date = data['booking_date']
        booking_time = data['booking_time']
        booking_type = data['booking_type']
        
        # Check if service belongs to braider
        if service.braider != braider:
            raise serializers.ValidationError({
                'service': 'Selected service is not offered by this braider'
            })
        
        # Check if booking is in the future
        booking_datetime = datetime.combine(booking_date, booking_time)
        if booking_datetime <= timezone.now():
            raise serializers.ValidationError({
                'booking_date': 'Booking cannot be in the past'
            })
        
        # Check if braider supports the booking type
        if booking_type == 'home' and not braider.provides_home_service:
            raise serializers.ValidationError({
                'booking_type': 'Braider does not provide home service'
            })
        elif booking_type == 'salon' and not braider.has_physical_location:
            raise serializers.ValidationError({
                'booking_type': 'Braider does not have a physical location'
            })
        
        # Check for conflicts
        conflicts = check_booking_conflicts(
            braider, booking_date, booking_time, service.duration_minutes
        )
        if conflicts:
            raise serializers.ValidationError({
                'booking_time': 'This time slot is already booked'
            })
        
        # Check availability using AvailabilityManager
        manager = AvailabilityManager(braider)
        is_available, reason = manager.is_slot_available(
            booking_date, booking_time, service.duration_minutes, booking_type
        )
        if not is_available:
            raise serializers.ValidationError({
                'booking_time': reason
            })
        
        # Validate address for home service
        if booking_type == 'home' and not data.get('service_address_data'):
            raise serializers.ValidationError({
                'service_address_data': 'Address required for home service'
            })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create booking with address handling."""
        service_address_data = validated_data.pop('service_address_data', None)
        user = self.context['request'].user
        
        # Create address for home service
        service_address = None
        if service_address_data:
            service_address = Address.objects.create(**service_address_data)
        
        # Create booking
        booking = Booking.objects.create(
            user=user,
            service_address=service_address,
            base_price=validated_data['service'].base_price,
            **validated_data
        )
        
        return booking


class BookingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating bookings.
    """
    service_address_data = AddressSerializer(write_only=True, required=False)
    
    class Meta:
        model = Booking
        fields = [
            'booking_date', 'booking_time', 'booking_type',
            'service_address_data', 'special_requests', 'hair_type',
            'hair_length', 'preferred_products'
        ]
    
    def validate(self, data):
        """Validate booking update data."""
        booking = self.instance
        
        # Only allow updates for certain statuses
        if booking.status not in ['pending', 'confirmed']:
            raise serializers.ValidationError(
                'Booking cannot be modified in current status'
            )
        
        # If changing date/time, validate availability
        if 'booking_date' in data or 'booking_time' in data:
            booking_date = data.get('booking_date', booking.booking_date)
            booking_time = data.get('booking_time', booking.booking_time)
            booking_type = data.get('booking_type', booking.booking_type)
            
            # Check if new time is in the future
            booking_datetime = datetime.combine(booking_date, booking_time)
            if booking_datetime <= timezone.now():
                raise serializers.ValidationError({
                    'booking_date': 'Booking cannot be in the past'
                })
            
            # Check for conflicts (excluding current booking)
            conflicts = check_booking_conflicts(
                booking.braider, booking_date, booking_time,
                booking.service.duration_minutes, str(booking.id)
            )
            if conflicts:
                raise serializers.ValidationError({
                    'booking_time': 'This time slot is already booked'
                })
            
            # Check availability
            manager = AvailabilityManager(booking.braider)
            is_available, reason = manager.is_slot_available(
                booking_date, booking_time, booking.service.duration_minutes, booking_type
            )
            if not is_available:
                raise serializers.ValidationError({
                    'booking_time': reason
                })
        
        return data
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update booking with address handling."""
        service_address_data = validated_data.pop('service_address_data', None)
        
        # Update address if provided
        if service_address_data:
            if instance.service_address:
                # Update existing address
                for key, value in service_address_data.items():
                    setattr(instance.service_address, key, value)
                instance.service_address.save()
            else:
                # Create new address
                instance.service_address = Address.objects.create(**service_address_data)
        
        # Update booking
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        
        return instance


class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating booking status.
    """
    reason = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Booking
        fields = ['status', 'reason']
    
    def validate_status(self, value):
        """Validate status transitions."""
        booking = self.instance
        current_status = booking.status
        
        # Define allowed transitions
        allowed_transitions = {
            'pending': ['confirmed', 'cancelled_client', 'cancelled_braider'],
            'confirmed': ['in_progress', 'cancelled_client', 'cancelled_braider', 'no_show'],
            'in_progress': ['completed', 'cancelled_braider'],
            'completed': [],  # No transitions allowed
            'cancelled_client': [],
            'cancelled_braider': [],
            'no_show': [],
            'rescheduled': ['pending'],
        }
        
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        return value
    
    def update(self, instance, validated_data):
        """Update booking status and create history record."""
        reason = validated_data.pop('reason', '')
        old_status = instance.status
        new_status = validated_data['status']
        
        # Update booking
        instance.status = new_status
        instance.save()
        
        # Create status history record
        BookingStatusHistory.objects.create(
            booking=instance,
            old_status=old_status,
            new_status=new_status,
            changed_by=self.context['request'].user,
            reason=reason,
            automatic=False
        )
        
        return instance


class AvailabilityCheckSerializer(serializers.Serializer):
    """
    Serializer for checking availability.
    """
    braider_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    booking_date = serializers.DateField()
    booking_time = serializers.TimeField()
    booking_type = serializers.ChoiceField(choices=['home', 'salon'])
    
    def validate(self, data):
        """Validate availability check data."""
        from apps.braiders.models import Braider, Service
        
        try:
            braider = Braider.objects.get(id=data['braider_id'])
        except Braider.DoesNotExist:
            raise serializers.ValidationError({'braider_id': 'Braider not found'})
        
        try:
            service = Service.objects.get(id=data['service_id'])
        except Service.DoesNotExist:
            raise serializers.ValidationError({'service_id': 'Service not found'})
        
        if service.braider != braider:
            raise serializers.ValidationError({
                'service_id': 'Service does not belong to this braider'
            })
        
        data['braider'] = braider
        data['service'] = service
        return data


class BraiderAvailabilitySerializer(serializers.Serializer):
    """
    Serializer for braider availability response.
    """
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    service_duration = serializers.IntegerField(default=60)
    booking_type = serializers.ChoiceField(choices=['home', 'salon'], default='home')