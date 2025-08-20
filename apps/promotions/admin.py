"""
Admin interface for promotions system.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Campaign, Promotion, CouponCode, CampaignParticipant, PromotionUsage


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin interface for campaigns."""
    
    list_display = [
        'name', 'campaign_type', 'status', 'is_active', 
        'start_date', 'end_date', 'participation_count', 
        'current_spend', 'budget_remaining', 'conversion_rate'
    ]
    list_filter = [
        'campaign_type', 'status', 'is_active', 
        'start_date', 'end_date', 'created_at'
    ]
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'current_spend', 'total_views', 'total_clicks', 
        'total_conversions', 'participation_count', 
        'conversion_rate', 'budget_remaining'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'campaign_type')
        }),
        ('Timing', {
            'fields': ('start_date', 'end_date', 'is_active', 'status')
        }),
        ('Targeting', {
            'fields': ('target_audience', 'max_participants')
        }),
        ('Budget', {
            'fields': ('total_budget', 'current_spend', 'budget_remaining')
        }),
        ('Display', {
            'fields': ('banner_image', 'banner_text', 'call_to_action')
        }),
        ('Analytics', {
            'fields': (
                'total_views', 'total_clicks', 'total_conversions', 
                'participation_count', 'conversion_rate'
            )
        }),
    )
    
    actions = ['activate_campaigns', 'deactivate_campaigns', 'mark_completed']
    
    def activate_campaigns(self, request, queryset):
        """Activate selected campaigns."""
        updated = queryset.update(is_active=True, status='active')
        self.message_user(request, f'{updated} campaigns activated.')
    activate_campaigns.short_description = "Activate selected campaigns"
    
    def deactivate_campaigns(self, request, queryset):
        """Deactivate selected campaigns."""
        updated = queryset.update(is_active=False, status='paused')
        self.message_user(request, f'{updated} campaigns deactivated.')
    deactivate_campaigns.short_description = "Deactivate selected campaigns"
    
    def mark_completed(self, request, queryset):
        """Mark campaigns as completed."""
        updated = queryset.update(status='completed', is_active=False)
        self.message_user(request, f'{updated} campaigns marked as completed.')
    mark_completed.short_description = "Mark as completed"


class CouponCodeInline(admin.TabularInline):
    """Inline admin for coupon codes."""
    model = CouponCode
    extra = 0
    readonly_fields = ['is_used', 'used_by', 'used_at']
    fields = ['code', 'assigned_to', 'expires_at', 'is_used', 'used_by', 'used_at']


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    """Admin interface for promotions."""
    
    list_display = [
        'name', 'code', 'campaign', 'promotion_type', 
        'discount_display', 'current_usage_count', 
        'usage_limit_display', 'is_active'
    ]
    list_filter = [
        'promotion_type', 'applies_to', 'is_active', 
        'is_stackable', 'campaign__campaign_type', 'created_at'
    ]
    search_fields = ['name', 'code', 'description', 'campaign__name']
    readonly_fields = ['current_usage_count']
    inlines = [CouponCodeInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('campaign', 'name', 'code', 'description')
        }),
        ('Promotion Configuration', {
            'fields': ('promotion_type', 'applies_to', 'is_active', 'is_stackable')
        }),
        ('Discount Settings', {
            'fields': (
                'discount_percentage', 'discount_amount', 'max_discount_amount'
            )
        }),
        ('Conditions', {
            'fields': ('minimum_order_amount', 'maximum_order_amount')
        }),
        ('Usage Limits', {
            'fields': (
                'usage_limit_per_user', 'total_usage_limit', 'current_usage_count'
            )
        }),
        ('Targeting', {
            'fields': ('target_services', 'target_categories', 'target_braiders')
        }),
        ('Buy X Get Y', {
            'fields': ('buy_quantity', 'get_quantity'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generate_coupon_codes', 'activate_promotions', 'deactivate_promotions']
    
    def discount_display(self, obj):
        """Display discount in a readable format."""
        if obj.promotion_type == 'percentage':
            return f"{obj.discount_percentage}%"
        elif obj.promotion_type == 'fixed_amount':
            return f"€{obj.discount_amount}"
        elif obj.promotion_type == 'free_shipping':
            return "Free Shipping"
        elif obj.promotion_type == 'buy_x_get_y':
            return f"Buy {obj.buy_quantity} Get {obj.get_quantity}"
        return "-"
    discount_display.short_description = "Discount"
    
    def usage_limit_display(self, obj):
        """Display usage limits."""
        total = obj.total_usage_limit or "∞"
        per_user = obj.usage_limit_per_user or "∞"
        return f"{obj.current_usage_count}/{total} (max {per_user}/user)"
    usage_limit_display.short_description = "Usage (Current/Total)"
    
    def generate_coupon_codes(self, request, queryset):
        """Generate coupon codes for selected promotions."""
        from django.shortcuts import render
        from django import forms
        
        class CouponGenerationForm(forms.Form):
            quantity = forms.IntegerField(min_value=1, max_value=1000, initial=10)
            expires_days = forms.IntegerField(
                min_value=1, max_value=365, initial=30,
                help_text="Days until expiration"
            )
        
        if 'apply' in request.POST:
            form = CouponGenerationForm(request.POST)
            if form.is_valid():
                quantity = form.cleaned_data['quantity']
                expires_days = form.cleaned_data['expires_days']
                expires_at = timezone.now() + timezone.timedelta(days=expires_days)
                
                created_count = 0
                for promotion in queryset:
                    for _ in range(quantity):
                        code = Promotion.generate_unique_code()
                        CouponCode.objects.create(
                            promotion=promotion,
                            code=code,
                            expires_at=expires_at
                        )
                        created_count += 1
                
                self.message_user(
                    request, 
                    f'Generated {created_count} coupon codes for {queryset.count()} promotions.'
                )
                return
        else:
            form = CouponGenerationForm()
        
        return render(
            request, 
            'admin/promotions/generate_coupons.html',
            {'form': form, 'promotions': queryset}
        )
    generate_coupon_codes.short_description = "Generate coupon codes"
    
    def activate_promotions(self, request, queryset):
        """Activate selected promotions."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotions activated.')
    activate_promotions.short_description = "Activate selected promotions"
    
    def deactivate_promotions(self, request, queryset):
        """Deactivate selected promotions."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotions deactivated.')
    deactivate_promotions.short_description = "Deactivate selected promotions"


@admin.register(CouponCode)
class CouponCodeAdmin(admin.ModelAdmin):
    """Admin interface for coupon codes."""
    
    list_display = [
        'code', 'promotion', 'assigned_to', 'is_used', 
        'used_by', 'used_at', 'expires_at', 'is_valid'
    ]
    list_filter = [
        'is_used', 'promotion__campaign', 'promotion__promotion_type',
        'expires_at', 'created_at'
    ]
    search_fields = ['code', 'promotion__name', 'assigned_to__email', 'used_by__email']
    readonly_fields = ['is_used', 'used_by', 'used_at', 'is_valid', 'is_expired']
    
    def is_valid(self, obj):
        """Display if coupon is valid."""
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = "Valid"


@admin.register(CampaignParticipant)
class CampaignParticipantAdmin(admin.ModelAdmin):
    """Admin interface for campaign participants."""
    
    list_display = [
        'user', 'campaign', 'joined_at', 'is_active',
        'total_views', 'total_clicks', 'total_conversions',
        'total_discount_received'
    ]
    list_filter = [
        'is_active', 'campaign__campaign_type', 'campaign',
        'joined_at'
    ]
    search_fields = ['user__email', 'user__name', 'campaign__name']
    readonly_fields = [
        'total_views', 'total_clicks', 'total_conversions',
        'total_discount_received'
    ]


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    """Admin interface for promotion usage tracking."""
    
    list_display = [
        'user', 'promotion', 'order_amount', 'discount_amount',
        'booking', 'created_at'
    ]
    list_filter = [
        'promotion__campaign', 'promotion__promotion_type',
        'created_at'
    ]
    search_fields = [
        'user__email', 'user__name', 'promotion__name', 
        'promotion__code', 'booking__booking_reference'
    ]
    readonly_fields = ['user_agent', 'ip_address']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'user', 'promotion', 'promotion__campaign', 'booking'
        )