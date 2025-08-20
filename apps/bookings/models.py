"""
Booking models for the Tuwi platform.

Comprehensive appointment scheduling system with availability management.
"""

import uuid
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from apps.core.models import BaseModel, Address
from apps.users.models import User
from apps.braiders.models import Braider, Service


class AvailabilitySlot(BaseModel):
    """
    Define braider's availability slots.
    
    Improvements over original schema:
    - Recurring availability patterns
    - Exception handling (holidays, breaks)
    - Flexible time slots
    """
    
    RECURRENCE_TYPES = [
        ('once', 'One-time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    braider = models.ForeignKey(
        Braider,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    
    # Date range for this availability
    start_date = models.DateField(
        help_text="Start date for this availability pattern"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date (null for indefinite)"
    )
    
    # Time range
    start_time = models.TimeField(
        help_text="Start time for availability"
    )
    end_time = models.TimeField(
        help_text="End time for availability"
    )
    
    # Recurrence pattern
    recurrence_type = models.CharField(
        max_length=20,
        choices=RECURRENCE_TYPES,
        default='weekly',
        help_text="How often this availability repeats"
    )
    
    # Days of week (for weekly recurrence)
    days_of_week = models.JSONField(
        default=list,
        blank=True,
        help_text="Days of week (0=Monday, 6=Sunday) for weekly recurrence"
    )
    
    # Location where this availability applies
    is_home_service = models.BooleanField(
        default=True,
        help_text="Whether this slot is for home service"
    )
    is_salon_service = models.BooleanField(
        default=False,
        help_text="Whether this slot is for salon service"
    )
    
    # Booking constraints
    min_advance_hours = models.PositiveIntegerField(
        default=24,
        help_text="Minimum hours in advance for booking"
    )
    max_advance_days = models.PositiveIntegerField(
        default=90,
        help_text="Maximum days in advance for booking"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this availability slot is active"
    )
    
    class Meta:
        verbose_name = 'Availability Slot'
        verbose_name_plural = 'Availability Slots'
        db_table = 'availability_slots'
        indexes = [
            models.Index(fields=['braider', 'start_date', 'end_date']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.braider.name} - {self.start_time}-{self.end_time} ({self.get_recurrence_type_display()})"
    
    def clean(self):
        """Validate availability slot."""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")
        
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date")
        
        if not self.is_home_service and not self.is_salon_service:
            raise ValidationError("At least one service type must be selected")
    
    def is_available_on_date(self, date):
        """Check if this slot is available on given date."""
        if not self.is_active:
            return False
            
        if date < self.start_date:
            return False
            
        if self.end_date and date > self.end_date:
            return False
        
        if self.recurrence_type == 'once':
            return date == self.start_date
        elif self.recurrence_type == 'weekly':
            return date.weekday() in self.days_of_week
        elif self.recurrence_type == 'daily':
            return True
        elif self.recurrence_type == 'monthly':
            return date.day == self.start_date.day
        
        return False


class AvailabilityException(BaseModel):
    """
    Handle exceptions to regular availability (holidays, breaks, etc.).
    """
    
    EXCEPTION_TYPES = [
        ('unavailable', 'Unavailable'),
        ('limited', 'Limited Hours'),
        ('special', 'Special Hours'),
    ]
    
    braider = models.ForeignKey(
        Braider,
        on_delete=models.CASCADE,
        related_name='availability_exceptions'
    )
    
    date = models.DateField(
        help_text="Date for this exception"
    )
    exception_type = models.CharField(
        max_length=20,
        choices=EXCEPTION_TYPES,
        help_text="Type of exception"
    )
    
    # For limited/special hours
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Special start time (for limited/special hours)"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Special end time (for limited/special hours)"
    )
    
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for exception (holiday, personal, etc.)"
    )
    
    class Meta:
        verbose_name = 'Availability Exception'
        verbose_name_plural = 'Availability Exceptions'
        db_table = 'availability_exceptions'
        unique_together = ['braider', 'date']
        indexes = [
            models.Index(fields=['braider', 'date']),
            models.Index(fields=['exception_type']),
        ]
    
    def __str__(self):
        return f"{self.braider.name} - {self.date} ({self.get_exception_type_display()})"


class Booking(BaseModel):
    """
    Main booking model with comprehensive workflow.
    
    Improvements over original schema:
    - Better status management
    - Enhanced client information handling
    - Automatic pricing calculations
    - Conflict prevention
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled_client', 'Cancelled by Client'),
        ('cancelled_braider', 'Cancelled by Braider'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    BOOKING_TYPES = [
        ('home', 'Home Service (Domicílio)'),
        ('salon', 'Salon Service (Estabelecimento)'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('deposit_paid', 'Deposit Paid'),
        ('paid', 'Fully Paid'),
        ('refund_pending', 'Refund Pending'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Payment Cancelled'),
    ]
    
    # Core booking information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings_as_client',
        help_text="Client who made the booking"
    )
    braider = models.ForeignKey(
        Braider,
        on_delete=models.CASCADE,
        related_name='received_bookings',
        help_text="Braider providing the service"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='bookings',
        help_text="Service being booked"
    )
    
    # Date and time
    booking_date = models.DateField(
        help_text="Date of the appointment"
    )
    booking_time = models.TimeField(
        help_text="Start time of the appointment"
    )
    estimated_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Estimated end time (calculated from service duration)"
    )
    actual_start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual start time of service"
    )
    actual_end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual end time of service"
    )
    
    # Booking type and location
    booking_type = models.CharField(
        max_length=20,
        choices=BOOKING_TYPES,
        help_text="Type of booking (home or salon service)"
    )
    service_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
        help_text="Address for home service (if applicable)"
    )
    
    # Client information (stored for booking record)
    client_name = models.CharField(
        max_length=255,
        help_text="Client's full name"
    )
    client_phone = models.CharField(
        max_length=20,
        help_text="Client's contact phone"
    )
    client_email = models.EmailField(
        help_text="Client's contact email"
    )
    
    # Special requirements
    special_requests = models.TextField(
        blank=True,
        help_text="Any special requests from the client"
    )
    hair_type = models.CharField(
        max_length=10,
        blank=True,
        help_text="Client's hair type (e.g., 4C)"
    )
    hair_length = models.CharField(
        max_length=50,
        blank=True,
        help_text="Client's current hair length"
    )
    preferred_products = models.JSONField(
        default=list,
        blank=True,
        help_text="Client's preferred products or allergies"
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Base service price at booking time"
    )
    additional_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="Additional charges (travel, materials, etc.)"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="Discount applied"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total price for the booking"
    )
    
    # Payment information
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Payment status"
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method used"
    )
    payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe payment intent ID"
    )
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Deposit amount (if applicable)"
    )
    
    # Status and workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Booking status"
    )
    
    # Confirmation
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the booking was confirmed"
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_bookings',
        help_text="Who confirmed the booking"
    )
    
    # Cancellation
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the booking was cancelled"
    )
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_bookings',
        help_text="Who cancelled the booking"
    )
    
    # Completion
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the service was completed"
    )
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes about service completion"
    )
    
    # Internal tracking
    booking_reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Unique booking reference for clients"
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes for admin/braider"
    )
    
    # Reminder and notification tracking
    reminder_sent = models.BooleanField(
        default=False,
        help_text="Whether reminder was sent to client"
    )
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When reminder was sent"
    )
    
    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['user', 'booking_date']),
            models.Index(fields=['braider', 'booking_date']),
            models.Index(fields=['service', 'booking_date']),
            models.Index(fields=['status']),
            models.Index(fields=['booking_date', 'booking_time']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['booking_reference']),
        ]
        # Prevent double bookings for same braider at same time
        constraints = [
            models.UniqueConstraint(
                fields=['braider', 'booking_date', 'booking_time'],
                condition=Q(status__in=['pending', 'confirmed', 'in_progress']),
                name='unique_braider_booking_slot'
            )
        ]
    
    def __str__(self):
        return f"{self.booking_reference} - {self.client_name} with {self.braider.name}"
    
    def save(self, *args, **kwargs):
        # Generate booking reference if not set
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        
        # Calculate estimated end time
        if not self.estimated_end_time and self.service:
            start_datetime = datetime.combine(
                self.booking_date, 
                self.booking_time
            )
            end_datetime = start_datetime + timedelta(
                minutes=self.service.duration_minutes
            )
            self.estimated_end_time = end_datetime.time()
        
        # Calculate total price if not set
        if not self.total_price:
            self.calculate_total_price()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate booking data."""
        errors = {}
        
        # Check if booking is in the past
        booking_datetime = datetime.combine(self.booking_date, self.booking_time)
        if booking_datetime <= timezone.now():
            errors['booking_date'] = "Booking cannot be in the past"
        
        # Check if braider offers the service
        if self.service and self.braider and self.service.braider != self.braider:
            errors['service'] = "Selected service is not offered by this braider"
        
        # Check if braider supports the booking type
        if self.booking_type == 'home' and not self.braider.provides_home_service:
            errors['booking_type'] = "Braider doesn't provide home service"
        elif self.booking_type == 'salon' and not self.braider.has_physical_location:
            errors['booking_type'] = "Braider doesn't have a physical location"
        
        # Check for conflicts with existing bookings
        if self.braider and self.booking_date and self.booking_time:
            conflicts = self.check_conflicts()
            if conflicts.exists():
                errors['booking_time'] = "This time slot is already booked"
        
        if errors:
            raise ValidationError(errors)
    
    def generate_booking_reference(self):
        """Generate unique booking reference."""
        import random
        import string
        
        while True:
            reference = ''.join(random.choices(
                string.ascii_uppercase + string.digits, 
                k=8
            ))
            if not Booking.objects.filter(booking_reference=reference).exists():
                return reference
    
    def calculate_total_price(self):
        """Calculate total booking price."""
        if not self.base_price:
            self.base_price = self.service.base_price if self.service else Decimal('0.00')
        
        total = self.base_price + self.additional_charges - self.discount_amount
        self.total_price = max(total, Decimal('0.00'))
    
    def check_conflicts(self):
        """Check for booking conflicts."""
        if not all([self.braider, self.booking_date, self.booking_time]):
            return Booking.objects.none()
        
        # Calculate time range for this booking
        start_datetime = datetime.combine(self.booking_date, self.booking_time)
        end_datetime = start_datetime + timedelta(minutes=self.service.duration_minutes)
        
        # Find overlapping bookings
        conflicts = Booking.objects.filter(
            braider=self.braider,
            booking_date=self.booking_date,
            status__in=['pending', 'confirmed', 'in_progress']
        ).exclude(pk=self.pk if self.pk else None)
        
        # Check for time overlaps
        overlapping = []
        for booking in conflicts:
            booking_start = datetime.combine(booking.booking_date, booking.booking_time)
            booking_end = booking_start + timedelta(minutes=booking.service.duration_minutes)
            
            # Check if times overlap
            if (start_datetime < booking_end and end_datetime > booking_start):
                overlapping.append(booking.pk)
        
        return conflicts.filter(pk__in=overlapping)
    
    def can_be_cancelled(self):
        """Check if booking can be cancelled."""
        if self.status in ['completed', 'cancelled_client', 'cancelled_braider']:
            return False
        
        # Check if cancellation is within allowed timeframe
        booking_datetime = datetime.combine(self.booking_date, self.booking_time)
        time_until_booking = booking_datetime - timezone.now()
        
        # Allow cancellation if more than 24 hours in advance
        return time_until_booking.total_seconds() > 24 * 3600
    
    def can_be_rescheduled(self):
        """Check if booking can be rescheduled."""
        return self.status in ['pending', 'confirmed'] and self.can_be_cancelled()
    
    @property
    def is_past_due(self):
        """Check if booking is past its scheduled time."""
        booking_datetime = datetime.combine(self.booking_date, self.booking_time)
        return booking_datetime < timezone.now()
    
    @property
    def duration_minutes(self):
        """Get booking duration in minutes."""
        return self.service.duration_minutes if self.service else 0
    
    @property
    def booking_datetime(self):
        """Get booking date and time as datetime object."""
        return datetime.combine(self.booking_date, self.booking_time)
    
    def get_status_display_color(self):
        """Get color for status display."""
        colors = {
            'pending': '#ffc107',
            'confirmed': '#17a2b8',
            'in_progress': '#fd7e14',
            'completed': '#28a745',
            'cancelled_client': '#dc3545',
            'cancelled_braider': '#dc3545',
            'no_show': '#6c757d',
            'rescheduled': '#6f42c1',
        }
        return colors.get(self.status, '#6c757d')


class BookingStatusHistory(BaseModel):
    """
    Track booking status changes for audit trail.
    """
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="Previous status"
    )
    new_status = models.CharField(
        max_length=20,
        help_text="New status"
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who changed the status"
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for status change"
    )
    automatic = models.BooleanField(
        default=False,
        help_text="Whether change was automatic"
    )
    
    class Meta:
        verbose_name = 'Booking Status History'
        verbose_name_plural = 'Booking Status History'
        db_table = 'booking_status_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking', 'created_at']),
            models.Index(fields=['new_status']),
        ]
    
    def __str__(self):
        return f"{self.booking.booking_reference}: {self.old_status} → {self.new_status}"