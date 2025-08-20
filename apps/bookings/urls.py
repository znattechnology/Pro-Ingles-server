"""
URL configuration for booking app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'bookings'

urlpatterns = [
    # Booking management
    path('bookings/', views.BookingListView.as_view(), name='booking-list'),
    path('bookings/create/', views.BookingCreateView.as_view(), name='booking-create'),
    path('bookings/<uuid:id>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/<uuid:id>/update/', views.BookingUpdateView.as_view(), name='booking-update'),
    path('bookings/<uuid:id>/status/', views.BookingStatusUpdateView.as_view(), name='booking-status-update'),
    
    # User-specific booking views
    path('my-bookings/', views.MyBookingsView.as_view(), name='my-bookings'),
    
    # Braider-specific booking views
    path('braider/bookings/', views.BraiderBookingsView.as_view(), name='braider-bookings'),
    
    # Booking actions
    path('bookings/<uuid:booking_id>/cancel/', views.cancel_booking, name='cancel-booking'),
    path('bookings/<uuid:booking_id>/confirm/', views.confirm_booking, name='confirm-booking'),
    
    # Availability management (braider only)
    path('availability/slots/', views.AvailabilitySlotListCreateView.as_view(), name='availability-slots'),
    path('availability/slots/<uuid:id>/', views.AvailabilitySlotDetailView.as_view(), name='availability-slot-detail'),
    path('availability/exceptions/', views.AvailabilityExceptionListCreateView.as_view(), name='availability-exceptions'),
    path('availability/exceptions/<uuid:id>/', views.AvailabilityExceptionDetailView.as_view(), name='availability-exception-detail'),
    
    # Public availability checking
    path('availability/check/', views.check_availability, name='check-availability'),
    path('braiders/<uuid:braider_id>/availability/', views.braider_availability, name='braider-availability'),
    path('braiders/<uuid:braider_id>/next-slots/', views.next_available_slots, name='next-available-slots'),
    
    # Admin statistics
    path('admin/booking-stats/', views.booking_stats, name='booking-stats'),
]