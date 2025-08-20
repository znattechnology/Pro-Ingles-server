"""
Django admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, UserAddress, NotificationSettings
from apps.core.models import Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.
    """
    list_display = [
        'email', 'name', 'role', 'is_active', 'email_verified',
        'created_at', 'last_login_at', 'avatar_preview'
    ]
    list_filter = [
        'role', 'is_active', 'email_verified', 'created_at',
        'is_staff', 'is_superuser'
    ]
    search_fields = ['email', 'name', 'phone']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_login_at',
        'avatar_preview', 'notification_settings_link'
    ]
    
    # Fieldsets for add/change forms
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'email', 'name', 'phone')
        }),
        ('Profile', {
            'fields': ('avatar', 'avatar_preview', 'preferences')
        }),
        ('Role & Status', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Email Verification', {
            'fields': ('email_verified', 'email_verification_token')
        }),
        ('Password Reset', {
            'fields': ('reset_password_token', 'reset_password_expires'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login_at'),
            'classes': ('collapse',)
        }),
        ('Related', {
            'fields': ('notification_settings_link',),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role'),
        }),
        ('Optional Information', {
            'fields': ('phone',),
        }),
    )
    
    def avatar_preview(self, obj):
        """Display avatar thumbnail in admin."""
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        return "No Avatar"
    avatar_preview.short_description = "Avatar"
    
    def notification_settings_link(self, obj):
        """Link to notification settings."""
        if hasattr(obj, 'notification_settings'):
            url = reverse('admin:users_notificationsettings_change', 
                         args=[obj.notification_settings.id])
            return format_html('<a href="{}">View Notification Settings</a>', url)
        return "No settings"
    notification_settings_link.short_description = "Notification Settings"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification_settings')


class AddressInline(admin.StackedInline):
    """
    Inline admin for Address in UserAddress.
    """
    model = Address
    extra = 0
    fields = [
        'street', 'building_number', 'apartment', 'floor',
        'city', 'postal_code', 'district', 'country', 'additional_info'
    ]


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """
    Admin for UserAddress model.
    """
    list_display = ['user', 'address_type', 'is_default', 'city', 'district', 'created_at']
    list_filter = ['address_type', 'is_default', 'created_at']
    search_fields = ['user__name', 'user__email', 'address__city', 'address__district']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User & Type', {
            'fields': ('user', 'address_type', 'is_default')
        }),
        ('Address Details', {
            'fields': ('address',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def city(self, obj):
        return obj.address.city
    city.short_description = "City"
    
    def district(self, obj):
        return obj.address.district
    district.short_description = "District"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Admin for Address model.
    """
    list_display = ['street', 'city', 'postal_code', 'district', 'country']
    list_filter = ['district', 'city', 'country']
    search_fields = ['street', 'city', 'postal_code', 'district']
    readonly_fields = ['id', 'created_at', 'updated_at', 'full_address']
    
    fieldsets = (
        ('Basic Address', {
            'fields': ('street', 'building_number', 'city', 'postal_code', 'district', 'country')
        }),
        ('Additional Details', {
            'fields': ('apartment', 'floor', 'additional_info'),
            'classes': ('collapse',)
        }),
        ('Computed', {
            'fields': ('full_address',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """
    Admin for NotificationSettings model.
    """
    list_display = [
        'user', 'digest_frequency', 'email_bookings', 'email_messages',
        'email_orders', 'email_marketing'
    ]
    list_filter = [
        'digest_frequency', 'email_bookings', 'email_messages',
        'email_orders', 'email_marketing', 'push_bookings'
    ]
    search_fields = ['user__name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Notifications', {
            'fields': (
                'email_bookings', 'email_messages', 'email_ratings',
                'email_orders', 'email_marketing'
            )
        }),
        ('Push Notifications', {
            'fields': (
                'push_bookings', 'push_messages', 'push_ratings', 'push_orders'
            ),
            'classes': ('collapse',)
        }),
        ('Digest & Timing', {
            'fields': ('digest_frequency', 'quiet_hours_start', 'quiet_hours_end', 'timezone')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')