"""
Django admin configuration for booking models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from django.utils import timezone

from .models import Booking, AvailabilitySlot, AvailabilityException, BookingStatusHistory


class BookingStatusHistoryInline(admin.TabularInline):
    """
    Inline admin for booking status history.
    """
    model = BookingStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'reason', 'automatic', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Admin interface for Booking model.
    """
    list_display = [
        'booking_reference', 'client_name', 'braider', 'service_name',
        'booking_datetime', 'status_badge', 'booking_type', 'total_price',
        'payment_status_badge', 'created_at'
    ]
    list_filter = [
        'status', 'booking_type', 'payment_status', 'booking_date',
        'created_at', 'service__category'
    ]
    search_fields = [
        'booking_reference', 'client_name', 'client_email', 'client_phone',
        'braider__name', 'service__name'
    ]
    readonly_fields = [
        'id', 'booking_reference', 'created_at', 'updated_at',
        'booking_datetime_display', 'duration_display', 'user_link',
        'braider_link', 'service_link', 'address_link', 'conflicts_check',
        'status_color', 'can_cancel_display', 'is_past_due'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'booking_reference', 'user', 'user_link'
            )
        }),
        ('Service Details', {
            'fields': (
                'braider', 'braider_link', 'service', 'service_link'
            )
        }),
        ('Booking Details', {
            'fields': (
                'booking_date', 'booking_time', 'booking_datetime_display',
                'estimated_end_time', 'duration_display', 'booking_type',
                'service_address', 'address_link', 'conflicts_check'
            )
        }),
        ('Client Information', {
            'fields': (
                'client_name', 'client_phone', 'client_email'
            )
        }),
        ('Service Requirements', {
            'fields': (
                'special_requests', 'hair_type', 'hair_length', 'preferred_products'
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': (
                'base_price', 'additional_charges', 'discount_amount', 'total_price'
            )
        }),
        ('Payment', {
            'fields': (
                'payment_status', 'payment_method', 'payment_intent_id', 'deposit_amount'
            )
        }),
        ('Status & Workflow', {
            'fields': (
                'status', 'status_color', 'confirmed_at', 'completed_at',
                'cancelled_at', 'cancellation_reason', 'can_cancel_display',
                'is_past_due'
            )
        }),
        ('Service Execution', {
            'fields': (
                'actual_start_time', 'actual_end_time', 'completion_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Internal', {
            'fields': (
                'internal_notes', 'reminder_sent', 'reminder_sent_at'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [BookingStatusHistoryInline]
    
    actions = [
        'confirm_bookings', 'cancel_bookings', 'mark_completed',
        'send_reminders'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'braider', 'service', 'service_address'
        )
    
    def service_name(self, obj):
        """Display service name."""
        return obj.service.name
    service_name.short_description = "Service"
    
    def booking_datetime(self, obj):
        """Display booking date and time."""
        return f"{obj.booking_date} {obj.booking_time}"
    booking_datetime.short_description = "Date & Time"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        color = obj.get_status_display_color()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def payment_status_badge(self, obj):
        """Display payment status with color coding."""
        colors = {
            'pending': '#ffc107',
            'deposit_paid': '#17a2b8',
            'paid': '#28a745',
            'refund_pending': '#fd7e14',
            'refunded': '#6c757d',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "Payment"
    
    def booking_datetime_display(self, obj):
        """Display formatted booking datetime."""
        return f"{obj.booking_date.strftime('%d/%m/%Y')} at {obj.booking_time.strftime('%H:%M')}"
    booking_datetime_display.short_description = "Booking DateTime"
    
    def duration_display(self, obj):
        """Display service duration."""
        minutes = obj.duration_minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h{mins:02d}"
        return f"{mins}min"
    duration_display.short_description = "Duration"
    
    def user_link(self, obj):
        """Link to user admin."""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "No User"
    user_link.short_description = "User Account"
    
    def braider_link(self, obj):
        """Link to braider admin."""
        url = reverse('admin:braiders_braider_change', args=[obj.braider.id])
        return format_html('<a href="{}">{}</a>', url, obj.braider.name)
    braider_link.short_description = "Braider Profile"
    
    def service_link(self, obj):
        """Link to service admin."""
        url = reverse('admin:braiders_service_change', args=[obj.service.id])
        return format_html('<a href="{}">{}</a>', url, obj.service.name)
    service_link.short_description = "Service Details"
    
    def address_link(self, obj):
        """Link to address admin."""
        if obj.service_address:
            url = reverse('admin:core_address_change', args=[obj.service_address.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.service_address))
        return "No Address"
    address_link.short_description = "Service Address"
    
    def conflicts_check(self, obj):
        """Check for booking conflicts."""
        if obj.status in ['completed', 'cancelled_client', 'cancelled_braider']:
            return "N/A"
        
        from .utils import check_booking_conflicts
        conflicts = check_booking_conflicts(
            obj.braider, obj.booking_date, obj.booking_time,
            obj.duration_minutes, str(obj.id)
        )
        
        if conflicts:
            conflict_refs = [c.booking_reference for c in conflicts]
            return format_html(
                '<span style="color: red;">⚠️ Conflicts: {}</span>',
                ', '.join(conflict_refs)
            )
        return format_html('<span style="color: green;">✅ No conflicts</span>')
    conflicts_check.short_description = "Conflicts"
    
    def status_color(self, obj):
        """Display status color."""
        color = obj.get_status_display_color()
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; '
            'border-radius: 3px; display: inline-block;"></div> {}',
            color, color
        )
    status_color.short_description = "Status Color"
    
    def can_cancel_display(self, obj):
        """Display if booking can be cancelled."""
        if obj.can_be_cancelled():
            return format_html('<span style="color: green;">✅ Yes</span>')
        return format_html('<span style="color: red;">❌ No</span>')
    can_cancel_display.short_description = "Can Cancel"
    
    # Admin actions
    def confirm_bookings(self, request, queryset):
        """Confirm selected bookings."""
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            confirmed_at=timezone.now()
        )
        self.message_user(request, f'{updated} bookings have been confirmed.')
    confirm_bookings.short_description = "Confirm selected bookings"
    
    def cancel_bookings(self, request, queryset):
        """Cancel selected bookings."""
        updated = queryset.filter(
            status__in=['pending', 'confirmed']
        ).update(
            status='cancelled_braider',
            cancelled_at=timezone.now(),
            cancellation_reason='Cancelled by admin'
        )
        self.message_user(request, f'{updated} bookings have been cancelled.')
    cancel_bookings.short_description = "Cancel selected bookings"
    
    def mark_completed(self, request, queryset):
        """Mark selected bookings as completed."""
        updated = queryset.filter(status='in_progress').update(
            status='completed',
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} bookings have been marked as completed.')
    mark_completed.short_description = "Mark as completed"
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected bookings."""
        # This would integrate with notification system
        count = queryset.filter(
            reminder_sent=False,
            status='confirmed'
        ).count()
        self.message_user(request, f'Reminders would be sent for {count} bookings.')
    send_reminders.short_description = "Send reminders"


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    """
    Admin interface for AvailabilitySlot model.
    """
    list_display = [
        'braider', 'start_date', 'end_date', 'time_range',
        'recurrence_type', 'service_types', 'is_active', 'created_at'
    ]
    list_filter = [
        'recurrence_type', 'is_home_service', 'is_salon_service',
        'is_active', 'created_at'
    ]
    search_fields = ['braider__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'braider')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Time Range', {
            'fields': ('start_time', 'end_time')
        }),
        ('Recurrence', {
            'fields': ('recurrence_type', 'days_of_week')
        }),
        ('Service Types', {
            'fields': ('is_home_service', 'is_salon_service')
        }),
        ('Booking Constraints', {
            'fields': ('min_advance_hours', 'max_advance_days')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('braider')
    
    def time_range(self, obj):
        """Display time range."""
        return f"{obj.start_time} - {obj.end_time}"
    time_range.short_description = "Time Range"
    
    def service_types(self, obj):
        """Display service types."""
        types = []
        if obj.is_home_service:
            types.append("Home")
        if obj.is_salon_service:
            types.append("Salon")
        return ", ".join(types) if types else "None"
    service_types.short_description = "Service Types"


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    """
    Admin interface for AvailabilityException model.
    """
    list_display = [
        'braider', 'date', 'exception_type', 'time_range',
        'reason', 'created_at'
    ]
    list_filter = ['exception_type', 'date', 'created_at']
    search_fields = ['braider__name', 'reason']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'braider', 'date', 'exception_type')
        }),
        ('Time Details', {
            'fields': ('start_time', 'end_time')
        }),
        ('Details', {
            'fields': ('reason',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('braider')
    
    def time_range(self, obj):
        """Display time range for limited/special hours."""
        if obj.start_time and obj.end_time:
            return f"{obj.start_time} - {obj.end_time}"
        return "All day"
    time_range.short_description = "Time Range"


@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for BookingStatusHistory model.
    """
    list_display = [
        'booking_reference', 'status_transition', 'changed_by',
        'automatic', 'created_at'
    ]
    list_filter = ['automatic', 'new_status', 'created_at']
    search_fields = ['booking__booking_reference', 'reason']
    readonly_fields = [
        'id', 'booking', 'old_status', 'new_status', 'changed_by',
        'reason', 'automatic', 'created_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('id', 'booking')
        }),
        ('Status Change', {
            'fields': ('old_status', 'new_status', 'reason')
        }),
        ('Change Details', {
            'fields': ('changed_by', 'automatic', 'created_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'booking', 'changed_by'
        )
    
    def booking_reference(self, obj):
        """Display booking reference."""
        return obj.booking.booking_reference
    booking_reference.short_description = "Booking Reference"
    
    def status_transition(self, obj):
        """Display status transition."""
        if obj.old_status:
            return f"{obj.old_status} → {obj.new_status}"
        return f"Created as {obj.new_status}"
    status_transition.short_description = "Status Transition"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False