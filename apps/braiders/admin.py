"""
Django admin configuration for braider models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count

from .models import Braider, BraiderPortfolioImage, Service, ServiceImage


class BraiderPortfolioImageInline(admin.TabularInline):
    """
    Inline admin for portfolio images.
    """
    model = BraiderPortfolioImage
    extra = 0
    fields = ['image', 'image_preview', 'title', 'is_featured', 'order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"


class ServiceInline(admin.TabularInline):
    """
    Inline admin for services.
    """
    model = Service
    extra = 0
    fields = ['name', 'category', 'base_price', 'duration_minutes', 'is_active']
    show_change_link = True


@admin.register(Braider)
class BraiderAdmin(admin.ModelAdmin):
    """
    Admin interface for Braider model.
    """
    list_display = [
        'name', 'contact_email', 'status', 'status_badge', 'average_rating',
        'total_reviews', 'service_count', 'location_display', 'is_featured',
        'created_at', 'approved_at'
    ]
    list_filter = [
        'status', 'is_featured', 'experience_level', 'provides_home_service',
        'has_physical_location', 'created_at', 'approved_at'
    ]
    search_fields = [
        'name', 'contact_email', 'bio', 'user__email', 'address__city',
        'address__district'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'approved_at', 'average_rating',
        'total_reviews', 'profile_image_preview', 'user_link', 'address_link',
        'service_count_display', 'portfolio_count'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'user', 'user_link', 'name', 'contact_email', 'contact_phone'
            )
        }),
        ('Profile', {
            'fields': (
                'bio', 'profile_image', 'profile_image_preview', 
                'years_experience', 'experience_level', 'specialties', 'certifications'
            )
        }),
        ('Location & Services', {
            'fields': (
                'address', 'address_link', 'service_areas', 
                'provides_home_service', 'has_physical_location'
            )
        }),
        ('Status & Approval', {
            'fields': (
                'status', 'status_reason', 'approved_at', 'approved_by'
            )
        }),
        ('Rating & Reviews', {
            'fields': (
                'average_rating', 'total_reviews'
            ),
            'classes': ('collapse',)
        }),
        ('Featured Status', {
            'fields': (
                'is_featured', 'featured_until'
            )
        }),
        ('Business Information', {
            'fields': (
                'availability_schedule', 'pricing_info', 'booking_advance_days',
                'cancellation_policy'
            ),
            'classes': ('collapse',)
        }),
        ('Social Media', {
            'fields': (
                'instagram_handle', 'facebook_url', 'website_url'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'service_count_display', 'portfolio_count'
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
    
    inlines = [ServiceInline, BraiderPortfolioImageInline]
    
    actions = ['approve_braiders', 'reject_braiders', 'suspend_braiders', 'make_featured']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'address', 'approved_by'
        ).annotate(
            service_count=Count('services')
        )
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'suspended': '#fd7e14',
            'inactive': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def service_count(self, obj):
        """Display number of services."""
        return getattr(obj, 'service_count', 0)
    service_count.short_description = "Services"
    
    def profile_image_preview(self, obj):
        """Display profile image preview."""
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 50%;" />',
                obj.profile_image.url
            )
        return "No Image"
    profile_image_preview.short_description = "Profile Image"
    
    def user_link(self, obj):
        """Link to user admin."""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "No User"
    user_link.short_description = "User Account"
    
    def address_link(self, obj):
        """Link to address admin."""
        if obj.address:
            url = reverse('admin:core_address_change', args=[obj.address.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.address))
        return "No Address"
    address_link.short_description = "Address"
    
    def service_count_display(self, obj):
        """Display total services."""
        return obj.services.count()
    service_count_display.short_description = "Total Services"
    
    def portfolio_count(self, obj):
        """Display portfolio image count."""
        return obj.portfolio_images.count()
    portfolio_count.short_description = "Portfolio Images"
    
    # Admin actions
    def approve_braiders(self, request, queryset):
        """Approve selected braiders."""
        updated = queryset.update(status='approved', approved_by=request.user)
        self.message_user(request, f'{updated} braiders have been approved.')
    approve_braiders.short_description = "Approve selected braiders"
    
    def reject_braiders(self, request, queryset):
        """Reject selected braiders."""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} braiders have been rejected.')
    reject_braiders.short_description = "Reject selected braiders"
    
    def suspend_braiders(self, request, queryset):
        """Suspend selected braiders."""
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} braiders have been suspended.')
    suspend_braiders.short_description = "Suspend selected braiders"
    
    def make_featured(self, request, queryset):
        """Make selected braiders featured."""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} braiders are now featured.')
    make_featured.short_description = "Make selected braiders featured"


class ServiceImageInline(admin.TabularInline):
    """
    Inline admin for service images.
    """
    model = ServiceImage
    extra = 0
    fields = ['image', 'image_preview', 'image_type', 'caption', 'order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Service model.
    """
    list_display = [
        'name', 'braider', 'category', 'subcategory', 'base_price',
        'price_display', 'duration_display', 'is_active', 'is_popular',
        'created_at'
    ]
    list_filter = [
        'category', 'difficulty_level', 'is_active', 'is_popular',
        'price_varies', 'duration_varies', 'created_at'
    ]
    search_fields = [
        'name', 'description', 'braider__name', 'tags', 'subcategory'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'price_display', 'duration_display',
        'image_preview'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'braider', 'name', 'description', 'short_description'
            )
        }),
        ('Categorization', {
            'fields': (
                'category', 'subcategory', 'tags'
            )
        }),
        ('Pricing', {
            'fields': (
                'base_price', 'price_varies', 'price_from', 'price_to',
                'price_factors', 'price_display'
            )
        }),
        ('Duration', {
            'fields': (
                'duration_minutes', 'duration_varies', 'min_duration',
                'max_duration', 'duration_display'
            )
        }),
        ('Service Details', {
            'fields': (
                'difficulty_level', 'hair_type_compatibility',
                'required_hair_length'
            )
        }),
        ('Requirements', {
            'fields': (
                'client_preparation', 'braider_provides', 'client_brings'
            ),
            'classes': ('collapse',)
        }),
        ('Care Instructions', {
            'fields': (
                'aftercare_instructions', 'maintenance_schedule',
                'style_duration'
            ),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': (
                'image', 'image_preview'
            )
        }),
        ('Status', {
            'fields': (
                'is_active', 'is_popular'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ServiceImageInline]
    
    actions = ['make_active', 'make_inactive', 'make_popular', 'remove_popular']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('braider')
    
    def image_preview(self, obj):
        """Display service image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Service Image"
    
    # Admin actions
    def make_active(self, request, queryset):
        """Activate selected services."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} services have been activated.')
    make_active.short_description = "Activate selected services"
    
    def make_inactive(self, request, queryset):
        """Deactivate selected services."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} services have been deactivated.')
    make_inactive.short_description = "Deactivate selected services"
    
    def make_popular(self, request, queryset):
        """Mark selected services as popular."""
        updated = queryset.update(is_popular=True)
        self.message_user(request, f'{updated} services are now marked as popular.')
    make_popular.short_description = "Mark as popular"
    
    def remove_popular(self, request, queryset):
        """Remove popular status from selected services."""
        updated = queryset.update(is_popular=False)
        self.message_user(request, f'{updated} services are no longer popular.')
    remove_popular.short_description = "Remove popular status"


@admin.register(BraiderPortfolioImage)
class BraiderPortfolioImageAdmin(admin.ModelAdmin):
    """
    Admin interface for BraiderPortfolioImage model.
    """
    list_display = [
        'braider', 'title', 'image_preview', 'is_featured',
        'order', 'created_at'
    ]
    list_filter = ['is_featured', 'created_at']
    search_fields = ['braider__name', 'title', 'description', 'tags']
    readonly_fields = ['id', 'created_at', 'updated_at', 'image_preview']
    ordering = ['braider', 'order', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'braider', 'title', 'description')
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Settings', {
            'fields': ('tags', 'is_featured', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Image Preview"


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceImage model.
    """
    list_display = [
        'service', 'image_type', 'image_preview', 'caption',
        'order', 'created_at'
    ]
    list_filter = ['image_type', 'created_at']
    search_fields = ['service__name', 'caption']
    readonly_fields = ['id', 'created_at', 'updated_at', 'image_preview']
    ordering = ['service', 'order', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'service', 'image_type', 'caption')
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Settings', {
            'fields': ('order',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Image Preview"