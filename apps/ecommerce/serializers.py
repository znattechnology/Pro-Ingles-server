"""
Serializers for e-commerce models.
"""

from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from .models import (
    ProductCategory, Brand, Product, ProductImage, ProductAttribute, 
    ProductAttributeValue, ProductVariation, Cart, CartItem, Coupon,
    Order, OrderItem, CouponUsage
)
from apps.core.models import Address
from apps.users.serializers import AddressSerializer


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""
    
    full_path = serializers.ReadOnlyField()
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'parent',
            'is_active', 'sort_order', 'full_path', 'products_count', 'created_at'
        ]
    
    def get_products_count(self, obj):
        """Get number of active products in category."""
        return obj.products.filter(is_active=True).count()


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for brands."""
    
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'website',
            'is_active', 'products_count', 'created_at'
        ]
    
    def get_products_count(self, obj):
        """Get number of active products for brand."""
        return obj.products.filter(is_active=True).count()


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'alt_text', 'image_type', 'sort_order', 
            'is_primary', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """Serializer for product attribute values."""
    
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    
    class Meta:
        model = ProductAttributeValue
        fields = ['id', 'attribute_name', 'value', 'color_code']


class ProductVariationSerializer(serializers.ModelSerializer):
    """Serializer for product variations."""
    
    attributes = ProductAttributeValueSerializer(many=True, read_only=True)
    current_price = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductVariation
        fields = [
            'id', 'sku', 'attributes', 'price', 'sale_price',
            'stock_quantity', 'is_active', 'current_price', 'is_in_stock'
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    is_on_sale = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'category_name',
            'brand_name', 'price', 'sale_price', 'current_price',
            'discount_percentage', 'is_on_sale', 'average_rating',
            'total_reviews', 'primary_image', 'is_featured', 'is_in_stock'
        ]
    
    def get_primary_image(self, obj):
        """Get primary product image."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return self.context['request'].build_absolute_uri(primary_image.image.url)
        
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.image.url)
        
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual product view."""
    
    category = ProductCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variations = ProductVariationSerializer(many=True, read_only=True)
    
    # Computed fields
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    is_on_sale = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'category', 'brand', 'price', 'sale_price', 'current_price',
            'discount_percentage', 'is_on_sale', 'sku', 'stock_quantity',
            'is_in_stock', 'is_low_stock', 'weight', 'dimensions_length',
            'dimensions_width', 'dimensions_height', 'average_rating',
            'total_reviews', 'is_featured', 'is_digital', 'requires_shipping',
            'images', 'variations', 'published_at', 'created_at'
        ]


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating products."""
    
    images_data = ProductImageSerializer(many=True, write_only=True, required=False)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'short_description', 'category',
            'brand', 'price', 'sale_price', 'cost_price', 'sku',
            'stock_quantity', 'low_stock_threshold', 'track_inventory',
            'allow_backorder', 'weight', 'dimensions_length', 'dimensions_width',
            'dimensions_height', 'meta_title', 'meta_description',
            'is_active', 'is_featured', 'is_digital', 'requires_shipping',
            'images_data'
        ]
    
    def validate_sale_price(self, value):
        """Ensure sale price is less than regular price."""
        if value and value >= self.initial_data.get('price', 0):
            raise serializers.ValidationError(
                "Sale price must be less than regular price"
            )
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create product with images."""
        images_data = validated_data.pop('images_data', [])
        product = Product.objects.create(**validated_data)
        
        for image_data in images_data:
            ProductImage.objects.create(product=product, **image_data)
        
        return product


class ProductAdminListSerializer(serializers.ModelSerializer):
    """Admin-specific serializer for product dashboard listing."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    is_on_sale = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    images_urls = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'category', 'category_name',
            'brand', 'brand_name', 'price', 'sale_price', 'cost_price', 'current_price',
            'discount_percentage', 'is_on_sale', 'sku', 'stock_quantity',
            'low_stock_threshold', 'is_active', 'is_featured', 'is_digital',
            'average_rating', 'total_reviews', 'primary_image', 'images_urls',
            'is_in_stock', 'is_low_stock', 'created_at', 'updated_at'
        ]
    
    def get_primary_image(self, obj):
        """Get primary product image URL."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
            return primary_image.image.url
        
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        
        return None
    
    def get_images_urls(self, obj):
        """Get all product image URLs."""
        request = self.context.get('request')
        images = []
        for image in obj.images.all()[:5]:  # Limit to 5 images for performance
            if request:
                images.append(request.build_absolute_uri(image.image.url))
            else:
                images.append(image.image.url)
        return images


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    variation_details = ProductVariationSerializer(source='variation', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'variation', 'quantity', 'product_name',
            'product_image', 'unit_price', 'total_price', 'variation_details',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_product_image(self, obj):
        """Get product primary image."""
        primary_image = obj.product.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            return request.build_absolute_uri(primary_image.image.url)
        return None
    
    def validate_quantity(self, value):
        """Validate quantity against stock."""
        if hasattr(self, 'instance') and self.instance:
            # For updates
            product = self.instance.product
            variation = self.instance.variation
        else:
            # For creation
            product = self.initial_data.get('product')
            variation = self.initial_data.get('variation')
            
            if not product:
                return value
            
            if isinstance(product, str):
                try:
                    product = Product.objects.get(id=product)
                except Product.DoesNotExist:
                    raise serializers.ValidationError("Product not found")
        
        # Check stock availability
        if variation:
            if value > variation.stock_quantity:
                raise serializers.ValidationError(
                    f"Only {variation.stock_quantity} items available"
                )
        elif product.track_inventory and value > product.stock_quantity:
            raise serializers.ValidationError(
                f"Only {product.stock_quantity} items available"
            )
        
        return value


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart."""
    
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'created_at', 'updated_at']


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for coupons."""
    
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'name', 'description', 'discount_type',
            'discount_value', 'usage_limit', 'used_count', 'valid_from',
            'valid_until', 'minimum_amount', 'maximum_discount',
            'first_order_only', 'is_active', 'is_valid'
        ]


class CouponValidateSerializer(serializers.Serializer):
    """Serializer for coupon validation."""
    
    code = serializers.CharField(max_length=50)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate(self, data):
        """Validate coupon code and calculate discount."""
        code = data['code']
        subtotal = data['subtotal']
        user = self.context['request'].user
        
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError({'code': 'Invalid coupon code'})
        
        if not coupon.is_valid:
            raise serializers.ValidationError({'code': 'Coupon is not valid or has expired'})
        
        # Check user usage limit
        if coupon.usage_limit_per_user:
            user_usage = CouponUsage.objects.filter(coupon=coupon, user=user).count()
            if user_usage >= coupon.usage_limit_per_user:
                raise serializers.ValidationError({
                    'code': 'You have already used this coupon the maximum number of times'
                })
        
        # Check first order requirement
        if coupon.first_order_only:
            if Order.objects.filter(user=user).exists():
                raise serializers.ValidationError({
                    'code': 'This coupon is only valid for first-time customers'
                })
        
        # Calculate discount
        discount_amount = coupon.calculate_discount(subtotal)
        
        data['coupon'] = coupon
        data['discount_amount'] = discount_amount
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items."""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'variation', 'product_name', 'product_sku',
            'unit_price', 'quantity', 'total_price'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order listings."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'payment_status', 'payment_status_display', 'total_amount',
            'items_count', 'placed_at', 'created_at'
        ]
    
    def get_items_count(self, obj):
        """Get total number of items in order."""
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual order view."""
    
    items = OrderItemSerializer(many=True, read_only=True)
    billing_address = AddressSerializer(read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    coupon_details = CouponSerializer(source='coupon', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'payment_status', 'payment_status_display', 'billing_address',
            'shipping_address', 'subtotal', 'shipping_cost', 'tax_amount',
            'discount_amount', 'total_amount', 'coupon', 'coupon_code',
            'coupon_details', 'payment_method', 'customer_notes',
            'items', 'placed_at', 'shipped_at', 'delivered_at', 'created_at'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""
    
    billing_address_data = AddressSerializer(write_only=True)
    shipping_address_data = AddressSerializer(write_only=True, required=False)
    coupon_code = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Order
        fields = [
            'billing_address_data', 'shipping_address_data', 'coupon_code',
            'customer_notes'
        ]
    
    def validate(self, data):
        """Validate order data."""
        user = self.context['request'].user
        
        # Check if user has items in cart
        try:
            cart = user.cart
            if not cart.items.exists():
                raise serializers.ValidationError("Cart is empty")
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart not found")
        
        # Validate coupon if provided
        coupon_code = data.get('coupon_code')
        if coupon_code:
            subtotal = cart.subtotal
            coupon_validator = CouponValidateSerializer(
                data={'code': coupon_code, 'subtotal': subtotal},
                context=self.context
            )
            if coupon_validator.is_valid():
                data['coupon'] = coupon_validator.validated_data['coupon']
                data['discount_amount'] = coupon_validator.validated_data['discount_amount']
            else:
                raise serializers.ValidationError({'coupon_code': coupon_validator.errors})
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create order from cart."""
        user = self.context['request'].user
        cart = user.cart
        
        # Create addresses
        billing_address_data = validated_data.pop('billing_address_data')
        shipping_address_data = validated_data.pop('shipping_address_data', None)
        
        billing_address = Address.objects.create(**billing_address_data)
        shipping_address = None
        if shipping_address_data:
            shipping_address = Address.objects.create(**shipping_address_data)
        else:
            shipping_address = billing_address
        
        # Calculate totals
        subtotal = cart.subtotal
        coupon = validated_data.pop('coupon', None)
        discount_amount = validated_data.pop('discount_amount', Decimal('0.00'))
        shipping_cost = Decimal('5.00')  # TODO: Calculate based on shipping method
        tax_amount = Decimal('0.00')  # TODO: Calculate tax
        total_amount = subtotal + shipping_cost + tax_amount - discount_amount
        
        # Create order
        order = Order.objects.create(
            user=user,
            billing_address=billing_address,
            shipping_address=shipping_address,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            coupon=coupon,
            coupon_code=coupon.code if coupon else '',
            **validated_data
        )
        
        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variation=cart_item.variation,
                product_name=cart_item.product.name,
                product_sku=cart_item.variation.sku if cart_item.variation else cart_item.product.sku,
                unit_price=cart_item.unit_price,
                quantity=cart_item.quantity,
                total_price=cart_item.total_price
            )
            
            # Update stock
            if cart_item.variation:
                cart_item.variation.stock_quantity -= cart_item.quantity
                cart_item.variation.save()
            elif cart_item.product.track_inventory:
                cart_item.product.stock_quantity -= cart_item.quantity
                cart_item.product.save()
        
        # Track coupon usage
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=user,
                order=order,
                discount_amount=discount_amount
            )
            coupon.used_count += 1
            coupon.save()
        
        # Clear cart
        cart.items.all().delete()
        
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""
    
    class Meta:
        model = Order
        fields = ['status', 'admin_notes']
    
    def validate_status(self, value):
        """Validate status transitions."""
        order = self.instance
        current_status = order.status
        
        # Define allowed transitions
        allowed_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': ['refunded'],
            'cancelled': [],
            'refunded': [],
        }
        
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        return value