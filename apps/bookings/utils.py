"""
Utility functions for booking management.
"""

from datetime import datetime, timedelta, time, date
from typing import List, Dict, Tuple
from django.utils import timezone
from django.db.models import Q

from .models import AvailabilitySlot, AvailabilityException, Booking
from apps.braiders.models import Braider


class AvailabilityManager:
    """
    Manage braider availability and booking slots.
    """
    
    def __init__(self, braider: Braider):
        self.braider = braider
    
    def get_available_slots(
        self, 
        start_date: date, 
        end_date: date,
        service_duration: int = 60,
        booking_type: str = 'home'
    ) -> Dict[str, List[Dict]]:
        """
        Get available time slots for a date range.
        
        Args:
            start_date: Start date for availability check
            end_date: End date for availability check  
            service_duration: Duration of service in minutes
            booking_type: Type of booking ('home' or 'salon')
            
        Returns:
            Dict with date strings as keys and list of available slots as values
        """
        available_slots = {}
        current_date = start_date
        
        while current_date <= end_date:
            slots = self._get_slots_for_date(current_date, service_duration, booking_type)
            if slots:
                available_slots[current_date.isoformat()] = slots
            current_date += timedelta(days=1)
        
        return available_slots
    
    def _get_slots_for_date(
        self, 
        date_obj: date, 
        service_duration: int,
        booking_type: str
    ) -> List[Dict]:
        """
        Get available slots for a specific date.
        """
        # Check for availability exceptions first
        try:
            exception = AvailabilityException.objects.get(
                braider=self.braider, 
                date=date_obj
            )
            if exception.exception_type == 'unavailable':
                return []
            elif exception.exception_type in ['limited', 'special']:
                # Use exception times instead of regular availability
                return self._generate_time_slots(
                    exception.start_time, 
                    exception.end_time, 
                    service_duration, 
                    date_obj
                )
        except AvailabilityException.DoesNotExist:
            pass
        
        # Get regular availability slots
        availability_slots = AvailabilitySlot.objects.filter(
            braider=self.braider,
            is_active=True
        )
        
        # Filter by booking type
        if booking_type == 'home':
            availability_slots = availability_slots.filter(is_home_service=True)
        else:
            availability_slots = availability_slots.filter(is_salon_service=True)
        
        all_slots = []
        for slot in availability_slots:
            if slot.is_available_on_date(date_obj):
                # Check advance booking constraints
                if self._is_within_booking_window(date_obj, slot):
                    time_slots = self._generate_time_slots(
                        slot.start_time, 
                        slot.end_time, 
                        service_duration, 
                        date_obj
                    )
                    all_slots.extend(time_slots)
        
        # Remove duplicates and sort
        unique_slots = {}
        for slot in all_slots:
            key = slot['start_time']
            if key not in unique_slots:
                unique_slots[key] = slot
        
        return sorted(unique_slots.values(), key=lambda x: x['start_time'])
    
    def _generate_time_slots(
        self, 
        start_time: time, 
        end_time: time, 
        service_duration: int, 
        date_obj: date
    ) -> List[Dict]:
        """
        Generate individual time slots within a time range.
        """
        slots = []
        current_time = start_time
        slot_duration = timedelta(minutes=30)  # 30-minute slots
        
        while True:
            # Calculate end time for this slot
            slot_start = datetime.combine(date_obj, current_time)
            slot_end = slot_start + timedelta(minutes=service_duration)
            
            # Check if service would end before availability window closes
            if slot_end.time() > end_time:
                break
            
            # Check if slot is not already booked
            if not self._is_slot_booked(date_obj, current_time, service_duration):
                slots.append({
                    'start_time': current_time.strftime('%H:%M'),
                    'end_time': slot_end.time().strftime('%H:%M'),
                    'available': True,
                    'duration': service_duration
                })
            
            # Move to next slot
            next_slot = slot_start + slot_duration
            current_time = next_slot.time()
            
            # Safety check to prevent infinite loop
            if current_time >= end_time:
                break
        
        return slots
    
    def _is_within_booking_window(self, date_obj: date, slot: AvailabilitySlot) -> bool:
        """
        Check if date is within allowed booking window.
        """
        now = timezone.now()
        booking_datetime = datetime.combine(date_obj, slot.start_time)
        
        # Check minimum advance time
        min_advance = now + timedelta(hours=slot.min_advance_hours)
        if booking_datetime < min_advance:
            return False
        
        # Check maximum advance time
        max_advance = now + timedelta(days=slot.max_advance_days)
        if booking_datetime > max_advance:
            return False
        
        return True
    
    def _is_slot_booked(self, date_obj: date, start_time: time, duration: int) -> bool:
        """
        Check if a time slot is already booked.
        """
        booking_start = datetime.combine(date_obj, start_time)
        booking_end = booking_start + timedelta(minutes=duration)
        
        # Find conflicting bookings
        existing_bookings = Booking.objects.filter(
            braider=self.braider,
            booking_date=date_obj,
            status__in=['pending', 'confirmed', 'in_progress']
        )
        
        for booking in existing_bookings:
            existing_start = datetime.combine(booking.booking_date, booking.booking_time)
            existing_end = existing_start + timedelta(minutes=booking.duration_minutes)
            
            # Check for overlap
            if (booking_start < existing_end and booking_end > existing_start):
                return True
        
        return False
    
    def is_slot_available(
        self, 
        date_obj: date, 
        time_obj: time, 
        service_duration: int,
        booking_type: str = 'home'
    ) -> Tuple[bool, str]:
        """
        Check if a specific slot is available.
        
        Returns:
            Tuple of (is_available, reason_if_not)
        """
        # Check if date is in the past
        booking_datetime = datetime.combine(date_obj, time_obj)
        if booking_datetime <= timezone.now():
            return False, "Booking time is in the past"
        
        # Check availability exceptions
        try:
            exception = AvailabilityException.objects.get(
                braider=self.braider, 
                date=date_obj
            )
            if exception.exception_type == 'unavailable':
                return False, f"Braider is unavailable: {exception.reason}"
        except AvailabilityException.DoesNotExist:
            pass
        
        # Check regular availability
        availability_slots = AvailabilitySlot.objects.filter(
            braider=self.braider,
            is_active=True
        )
        
        # Filter by booking type
        if booking_type == 'home':
            availability_slots = availability_slots.filter(is_home_service=True)
        else:
            availability_slots = availability_slots.filter(is_salon_service=True)
        
        # Check if any availability slot covers this time
        slot_available = False
        for slot in availability_slots:
            if (slot.is_available_on_date(date_obj) and 
                slot.start_time <= time_obj and 
                self._is_within_booking_window(date_obj, slot)):
                
                # Check if service would end before slot ends
                service_end = booking_datetime + timedelta(minutes=service_duration)
                if service_end.time() <= slot.end_time:
                    slot_available = True
                    break
        
        if not slot_available:
            return False, "No availability slot covers this time"
        
        # Check for conflicts
        if self._is_slot_booked(date_obj, time_obj, service_duration):
            return False, "Time slot is already booked"
        
        return True, "Available"


def get_braider_next_available_slots(
    braider: Braider, 
    service_duration: int = 60,
    booking_type: str = 'home',
    days_ahead: int = 14
) -> List[Dict]:
    """
    Get the next available slots for a braider.
    
    Args:
        braider: Braider instance
        service_duration: Duration in minutes
        booking_type: 'home' or 'salon'
        days_ahead: Number of days to look ahead
        
    Returns:
        List of next available slots
    """
    manager = AvailabilityManager(braider)
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=days_ahead)
    
    all_slots = manager.get_available_slots(
        start_date, end_date, service_duration, booking_type
    )
    
    # Flatten and limit to next 10 slots
    next_slots = []
    for date_str, slots in all_slots.items():
        for slot in slots:
            next_slots.append({
                'date': date_str,
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'duration': slot['duration']
            })
            if len(next_slots) >= 10:
                break
        if len(next_slots) >= 10:
            break
    
    return next_slots


def check_booking_conflicts(
    braider: Braider,
    booking_date: date,
    booking_time: time,
    service_duration: int,
    exclude_booking_id: str = None
) -> List[Booking]:
    """
    Check for booking conflicts for a specific time slot.
    
    Args:
        braider: Braider instance
        booking_date: Date of booking
        booking_time: Time of booking
        service_duration: Duration in minutes
        exclude_booking_id: Booking ID to exclude (for updates)
        
    Returns:
        List of conflicting bookings
    """
    booking_start = datetime.combine(booking_date, booking_time)
    booking_end = booking_start + timedelta(minutes=service_duration)
    
    # Get existing bookings for that day
    existing_bookings = Booking.objects.filter(
        braider=braider,
        booking_date=booking_date,
        status__in=['pending', 'confirmed', 'in_progress']
    )
    
    if exclude_booking_id:
        existing_bookings = existing_bookings.exclude(id=exclude_booking_id)
    
    conflicts = []
    for booking in existing_bookings:
        existing_start = datetime.combine(booking.booking_date, booking.booking_time)
        existing_end = existing_start + timedelta(minutes=booking.duration_minutes)
        
        # Check for overlap
        if booking_start < existing_end and booking_end > existing_start:
            conflicts.append(booking)
    
    return conflicts