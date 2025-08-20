"""
E-commerce models for product catalog, shopping cart, and orders.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.core.models import BaseModel, Address

User = get_user_model()


class ProductCategory(BaseModel):
    """Product categories for organizing items."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name='children'
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    @property
    def full_path(self):
        """Get full category path."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Brand(BaseModel):
    """Product brands."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(BaseModel):
    """Products available for purchase."""
    
    # Basic information
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    # Categorization
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Inventory
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Physical attributes
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # kg
    dimensions_length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # cm
    dimensions_width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # cm  
    dimensions_height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)  # cm
    
    # SEO and meta
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    
    # Status and visibility
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    
    # Ratings and reviews
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Timestamps
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def current_price(self):
        """Get the current selling price."""
        return self.sale_price if self.sale_price else self.price
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale."""
        if self.sale_price and self.sale_price < self.price:
            return round(((self.price - self.sale_price) / self.price) * 100, 1)
        return 0
    
    @property
    def is_on_sale(self):
        """Check if product is on sale."""
        return self.sale_price and self.sale_price < self.price
    
    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorder
    
    @property
    def is_low_stock(self):
        """Check if product has low stock."""
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold
    
    def save(self, *args, **kwargs):
        # Set published_at when product becomes active
        if self.is_active and not self.published_at:
            self.published_at = timezone.now()
        elif not self.is_active:
            self.published_at = None
        
        super().save(*args, **kwargs)


class ProductImage(BaseModel):
    """Product images with ordering and types."""
    
    IMAGE_TYPES = [
        ('main', 'Main Image'),
        ('gallery', 'Gallery Image'),
        ('detail', 'Detail Image'),
        ('lifestyle', 'Lifestyle Image'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='gallery')
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'image_type']),
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.get_image_type_display()}"


class ProductAttribute(BaseModel):
    """Product attributes for variations (size, color, etc.)."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'slug']
    
    def __str__(self):
        return self.name


class ProductAttributeValue(BaseModel):
    """Values for product attributes."""
    
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    color_code = models.CharField(max_length=7, blank=True)  # For color attributes
    
    class Meta:
        ordering = ['value']
        unique_together = ['attribute', 'value']
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariation(BaseModel):
    """Product variations with different attributes and pricing."""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    sku = models.CharField(max_length=100, unique=True)
    attributes = models.ManyToManyField(ProductAttributeValue, related_name='variations')
    
    # Pricing (overrides product price if set)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        attributes_str = ', '.join([str(attr) for attr in self.attributes.all()])
        return f"{self.product.name} ({attributes_str})"
    
    @property
    def current_price(self):
        """Get current price for this variation."""
        if self.sale_price:
            return self.sale_price
        elif self.price:
            return self.price
        return self.product.current_price
    
    @property
    def is_in_stock(self):
        """Check if variation is in stock."""
        return self.stock_quantity > 0


class Cart(BaseModel):
    """Shopping cart for users."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    
    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        """Calculate cart subtotal."""
        return sum(item.total_price for item in self.items.all())


class CartItem(BaseModel):
    """Items in shopping cart."""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        unique_together = ['cart', 'product', 'variation']
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]
    
    def __str__(self):
        if self.variation:
            return f"{self.product.name} ({self.variation}) x{self.quantity}"
        return f"{self.product.name} x{self.quantity}"
    
    @property
    def unit_price(self):
        """Get unit price for this item."""
        if self.variation:
            return self.variation.current_price
        return self.product.current_price
    
    @property
    def total_price(self):
        """Calculate total price for this cart item."""
        return self.unit_price * self.quantity


class Coupon(BaseModel):
    """Discount coupons."""
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Discount details
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    usage_limit_per_user = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    
    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    
    # Conditions
    minimum_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    maximum_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Restrictions
    allowed_categories = models.ManyToManyField(ProductCategory, blank=True)
    allowed_products = models.ManyToManyField(Product, blank=True)
    first_order_only = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['valid_from', 'valid_until']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid."""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (not self.usage_limit or self.used_count < self.usage_limit)
        )
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount for given subtotal."""
        if not self.is_valid:
            return Decimal('0.00')
        
        if self.minimum_amount and subtotal < self.minimum_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'percentage':
            discount = subtotal * (self.discount_value / 100)
        elif self.discount_type == 'fixed_amount':
            discount = self.discount_value
        else:  # free_shipping
            return Decimal('0.00')  # Handled separately
        
        # Apply maximum discount limit
        if self.maximum_discount:
            discount = min(discount, self.maximum_discount)
        
        return min(discount, subtotal)


class Order(BaseModel):
    """Customer orders."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Addresses
    billing_address = models.ForeignKey(
        Address, 
        on_delete=models.PROTECT, 
        related_name='billing_orders'
    )
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.PROTECT, 
        related_name='shipping_orders',
        blank=True,
        null=True
    )
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Coupon
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, blank=True, null=True)
    coupon_code = models.CharField(max_length=50, blank=True)  # Store code even if coupon is deleted
    
    # Payment details
    payment_method = models.CharField(max_length=50, blank=True)
    payment_intent_id = models.CharField(max_length=200, blank=True)
    
    # Order notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    placed_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['placed_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)
    
    def _generate_order_number(self):
        """Generate unique order number."""
        import uuid
        return str(uuid.uuid4()).replace('-', '').upper()[:12]


class OrderItem(BaseModel):
    """Items in an order."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE, blank=True, null=True)
    
    # Item details at time of purchase
    product_name = models.CharField(max_length=200)  # Store in case product is deleted
    product_sku = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'product']),
        ]
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity} (Order {self.order.order_number})"


class CouponUsage(BaseModel):
    """Track coupon usage by users."""
    
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['coupon', 'order']
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email} (Order {self.order.order_number})"