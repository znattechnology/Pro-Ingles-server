"""
Django admin configuration for e-commerce models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum

from .models import (
    ProductCategory, Brand, Product, ProductImage, ProductAttribute,
    ProductAttributeValue, ProductVariation, Cart, CartItem, Coupon,
    Order, OrderItem, CouponUsage
)


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images."""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'image_type', 'sort_order', 'is_primary']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 150px;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"


class ProductVariationInline(admin.TabularInline):
    """Inline admin for product variations."""
    model = ProductVariation
    extra = 0
    fields = ['sku', 'price', 'sale_price', 'stock_quantity', 'is_active']
    readonly_fields = ['attributes_display']
    
    def attributes_display(self, obj):
        """Display variation attributes."""
        return ', '.join([str(attr) for attr in obj.attributes.all()])
    attributes_display.short_description = "Attributes"


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """Admin interface for ProductCategory model."""
    
    list_display = [
        'name', 'parent', 'products_count', 'is_active', 
        'sort_order', 'created_at'
    ]
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def products_count(self, obj):
        """Display number of products in category."""
        return obj.products.filter(is_active=True).count()
    products_count.short_description = "Active Products"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin interface for Brand model."""
    
    list_display = ['name', 'products_count', 'website', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'logo')
        }),
        ('Contact', {
            'fields': ('website',)
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def products_count(self, obj):
        """Display number of products for brand."""
        return obj.products.filter(is_active=True).count()
    products_count.short_description = "Active Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""
    
    list_display = [
        'name', 'category', 'brand', 'price_display', 'stock_status',
        'average_rating', 'is_featured', 'is_active', 'created_at'
    ]
    list_filter = [
        'category', 'brand', 'is_active', 'is_featured', 'is_digital',
        'track_inventory', 'created_at'
    ]
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'id', 'average_rating', 'total_reviews', 'created_at', 'updated_at',
        'published_at', 'current_price', 'discount_percentage', 'is_on_sale',
        'is_in_stock', 'is_low_stock'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'name', 'slug', 'description', 'short_description'
            )
        }),
        ('Categorization', {
            'fields': ('category', 'brand')
        }),
        ('Pricing', {
            'fields': (
                'price', 'sale_price', 'cost_price', 'current_price',
                'discount_percentage', 'is_on_sale'
            )
        }),
        ('Inventory', {
            'fields': (
                'sku', 'stock_quantity', 'low_stock_threshold',
                'track_inventory', 'allow_backorder', 'is_in_stock', 'is_low_stock'
            )
        }),
        ('Physical Properties', {
            'fields': (
                'weight', 'dimensions_length', 'dimensions_width', 'dimensions_height'
            )
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status & Features', {
            'fields': (
                'is_active', 'is_featured', 'is_digital', 'requires_shipping'
            )
        }),
        ('Reviews & Ratings', {
            'fields': ('average_rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ProductImageInline, ProductVariationInline]
    
    actions = ['make_featured', 'remove_featured', 'activate_products', 'deactivate_products']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'brand')
    
    def price_display(self, obj):
        """Display price with sale indication."""
        if obj.is_on_sale:
            return format_html(
                '<span style="text-decoration: line-through;">€{}</span><br/>'
                '<strong style="color: #e74c3c;">€{}</strong> ({}% off)',
                obj.price, obj.sale_price, obj.discount_percentage
            )
        return f"€{obj.price}"
    price_display.short_description = "Price"
    
    def stock_status(self, obj):
        """Display stock status with color coding."""
        if not obj.track_inventory:
            return format_html('<span style="color: #3498db;">Not Tracked</span>')
        elif obj.stock_quantity == 0:
            if obj.allow_backorder:
                return format_html('<span style="color: #f39c12;">Backorder</span>')
            else:
                return format_html('<span style="color: #e74c3c;">Out of Stock</span>')
        elif obj.is_low_stock:
            return format_html(
                '<span style="color: #f39c12;">Low Stock ({})</span>',
                obj.stock_quantity
            )
        else:
            return format_html(
                '<span style="color: #27ae60;">In Stock ({})</span>',
                obj.stock_quantity
            )
    stock_status.short_description = "Stock Status"
    
    # Admin actions
    def make_featured(self, request, queryset):
        """Mark selected products as featured."""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    make_featured.short_description = "Mark as featured"
    
    def remove_featured(self, request, queryset):
        """Remove featured status from selected products."""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products removed from featured.')
    remove_featured.short_description = "Remove featured status"
    
    def activate_products(self, request, queryset):
        """Activate selected products."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated.')
    activate_products.short_description = "Activate products"
    
    def deactivate_products(self, request, queryset):
        """Deactivate selected products."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    deactivate_products.short_description = "Deactivate products"


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    """Admin interface for ProductAttribute model."""
    
    list_display = ['name', 'slug', 'values_count', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def values_count(self, obj):
        """Display number of values for attribute."""
        return obj.values.count()
    values_count.short_description = "Values Count"


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """Admin interface for ProductAttributeValue model."""
    
    list_display = ['attribute', 'value', 'color_preview', 'created_at']
    list_filter = ['attribute']
    search_fields = ['value', 'attribute__name']
    
    def color_preview(self, obj):
        """Display color preview if color_code is set."""
        if obj.color_code:
            return format_html(
                '<div style="width: 30px; height: 20px; background-color: {}; '
                'border: 1px solid #ccc; display: inline-block;"></div>',
                obj.color_code
            )
        return "N/A"
    color_preview.short_description = "Color"


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items."""
    model = CartItem
    extra = 0
    readonly_fields = ['unit_price', 'total_price']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for Cart model."""
    
    list_display = ['user_email', 'total_items', 'subtotal', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['total_items', 'subtotal']
    
    inlines = [CartItemInline]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """Admin interface for Coupon model."""
    
    list_display = [
        'code', 'name', 'discount_display', 'usage_display',
        'validity_period', 'is_active', 'created_at'
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'name']
    readonly_fields = ['used_count', 'is_valid']
    filter_horizontal = ['allowed_categories', 'allowed_products']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount_value', 'maximum_discount')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_limit_per_user', 'used_count')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'is_valid')
        }),
        ('Conditions', {
            'fields': ('minimum_amount', 'first_order_only')
        }),
        ('Restrictions', {
            'fields': ('allowed_categories', 'allowed_products')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def discount_display(self, obj):
        """Display discount information."""
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        elif obj.discount_type == 'fixed_amount':
            return f"€{obj.discount_value}"
        else:
            return "Free Shipping"
    discount_display.short_description = "Discount"
    
    def usage_display(self, obj):
        """Display usage information."""
        if obj.usage_limit:
            return f"{obj.used_count}/{obj.usage_limit}"
        return f"{obj.used_count}/∞"
    usage_display.short_description = "Usage"
    
    def validity_period(self, obj):
        """Display validity period."""
        return f"{obj.valid_from.strftime('%d/%m/%Y')} - {obj.valid_until.strftime('%d/%m/%Y')}"
    validity_period.short_description = "Valid Period"


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'variation', 'product_name', 'product_sku', 'unit_price', 'total_price']
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model."""
    
    list_display = [
        'order_number', 'user_email', 'status_badge', 'payment_status_badge',
        'total_amount', 'placed_at'
    ]
    list_filter = [
        'status', 'payment_status', 'placed_at', 'shipped_at', 'delivered_at'
    ]
    search_fields = [
        'order_number', 'user__email', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'id', 'order_number', 'user', 'placed_at', 'created_at', 'updated_at',
        'subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount',
        'coupon_code'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': (
                'id', 'order_number', 'user', 'placed_at'
            )
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Addresses', {
            'fields': ('billing_address', 'shipping_address')
        }),
        ('Pricing', {
            'fields': (
                'subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount'
            )
        }),
        ('Coupon', {
            'fields': ('coupon', 'coupon_code')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_intent_id')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('shipped_at', 'delivered_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderItemInline]
    
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'coupon')
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Customer"
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'shipped': '#fd7e14',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
            'refunded': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
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
            'paid': '#28a745',
            'partially_paid': '#17a2b8',
            'refunded': '#6c757d',
            'failed': '#dc3545',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "Payment"
    
    # Admin actions
    def mark_processing(self, request, queryset):
        """Mark selected orders as processing."""
        updated = queryset.filter(status='pending').update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_processing.short_description = "Mark as processing"
    
    def mark_shipped(self, request, queryset):
        """Mark selected orders as shipped."""
        from django.utils import timezone
        updated = queryset.filter(status='processing').update(
            status='shipped',
            shipped_at=timezone.now()
        )
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_shipped.short_description = "Mark as shipped"
    
    def mark_delivered(self, request, queryset):
        """Mark selected orders as delivered."""
        from django.utils import timezone
        updated = queryset.filter(status='shipped').update(
            status='delivered',
            delivered_at=timezone.now()
        )
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_delivered.short_description = "Mark as delivered"


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    """Admin interface for CouponUsage model."""
    
    list_display = ['coupon_code', 'user_email', 'order_number', 'discount_amount', 'created_at']
    list_filter = ['coupon', 'created_at']
    search_fields = ['coupon__code', 'user__email', 'order__order_number']
    readonly_fields = ['coupon', 'user', 'order', 'discount_amount', 'created_at']
    
    def coupon_code(self, obj):
        return obj.coupon.code
    coupon_code.short_description = "Coupon"
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = "Order"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False