"""
Tests for ecommerce functionality including products, categories, cart, and orders.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta

from .models import (
    ProductCategory, Brand, Product, ProductImage, ProductAttribute, 
    ProductAttributeValue, ProductVariation, Cart, CartItem, Order, 
    OrderItem, Coupon, CouponUsage
)

User = get_user_model()


class ProductCategoryModelTest(TestCase):
    """Test ProductCategory model functionality."""
    
    def setUp(self):
        self.parent_category = ProductCategory.objects.create(
            name='Hair Care',
            slug='hair-care',
            description='Hair care products'
        )
    
    def test_create_category(self):
        """Test creating a product category."""
        category = ProductCategory.objects.create(
            name='Shampoos',
            slug='shampoos',
            description='Hair shampoos',
            parent=self.parent_category
        )
        
        self.assertEqual(category.name, 'Shampoos')
        self.assertEqual(category.parent, self.parent_category)
        self.assertTrue(category.is_active)
    
    def test_category_string_representation(self):
        """Test category string representation."""
        category = ProductCategory.objects.create(
            name='Conditioners',
            slug='conditioners',
            parent=self.parent_category
        )
        
        expected = "Hair Care > Conditioners"
        self.assertEqual(str(category), expected)
    
    def test_category_full_path(self):
        """Test category full path property."""
        subcategory = ProductCategory.objects.create(
            name='Deep Conditioners',
            slug='deep-conditioners',
            parent=self.parent_category
        )
        
        expected = "Hair Care > Deep Conditioners"
        self.assertEqual(subcategory.full_path, expected)
    
    def test_root_category(self):
        """Test root category without parent."""
        self.assertEqual(str(self.parent_category), 'Hair Care')
        self.assertEqual(self.parent_category.full_path, 'Hair Care')


class BrandModelTest(TestCase):
    """Test Brand model functionality."""
    
    def test_create_brand(self):
        """Test creating a brand."""
        brand = Brand.objects.create(
            name='Natural Beauty',
            slug='natural-beauty',
            description='Premium natural hair products',
            website='https://naturalbeauty.com'
        )
        
        self.assertEqual(brand.name, 'Natural Beauty')
        self.assertEqual(brand.slug, 'natural-beauty')
        self.assertTrue(brand.is_active)
    
    def test_brand_string_representation(self):
        """Test brand string representation."""
        brand = Brand.objects.create(
            name='Organic Hair',
            slug='organic-hair'
        )
        
        self.assertEqual(str(brand), 'Organic Hair')


class ProductModelTest(TestCase):
    """Test Product model functionality."""
    
    def setUp(self):
        self.category = ProductCategory.objects.create(
            name='Hair Products',
            slug='hair-products'
        )
        
        self.brand = Brand.objects.create(
            name='Test Brand',
            slug='test-brand'
        )
        
        self.product_data = {
            'name': 'Premium Hair Oil',
            'slug': 'premium-hair-oil',
            'description': 'Nourishing hair oil for all hair types',
            'category': self.category,
            'brand': self.brand,
            'base_price': Decimal('24.99'),
            'stock_quantity': 100,
            'is_active': True
        }
    
    def test_create_product(self):
        """Test creating a product."""
        product = Product.objects.create(**self.product_data)
        
        self.assertEqual(product.name, 'Premium Hair Oil')
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.brand, self.brand)
        self.assertEqual(product.base_price, Decimal('24.99'))
        self.assertEqual(product.stock_quantity, 100)
    
    def test_product_string_representation(self):
        """Test product string representation."""
        product = Product.objects.create(**self.product_data)
        self.assertEqual(str(product), 'Premium Hair Oil')
    
    def test_product_in_stock(self):
        """Test product stock availability."""
        product = Product.objects.create(**self.product_data)
        
        self.assertTrue(product.in_stock)
        
        # Test out of stock
        product.stock_quantity = 0
        product.save()
        self.assertFalse(product.in_stock)
    
    def test_product_final_price(self):
        """Test product final price calculation."""
        product_data = self.product_data.copy()
        product_data['sale_price'] = Decimal('19.99')
        
        product = Product.objects.create(**product_data)
        
        # Should return sale price when available
        self.assertEqual(product.final_price, Decimal('19.99'))
        
        # Should return base price when no sale price
        product.sale_price = None
        product.save()
        self.assertEqual(product.final_price, Decimal('24.99'))


class ProductImageModelTest(TestCase):
    """Test ProductImage model functionality."""
    
    def setUp(self):
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('20.00')
        )
    
    def test_create_product_image(self):
        """Test creating a product image."""
        image = ProductImage.objects.create(
            product=self.product,
            image='products/test_image.jpg',
            alt_text='Test product image',
            is_primary=True
        )
        
        self.assertEqual(image.product, self.product)
        self.assertEqual(image.alt_text, 'Test product image')
        self.assertTrue(image.is_primary)
    
    def test_product_image_string_representation(self):
        """Test product image string representation."""
        image = ProductImage.objects.create(
            product=self.product,
            image='products/test.jpg',
            alt_text='Main image'
        )
        
        expected = "Test Product - Main image"
        self.assertEqual(str(image), expected)


class CartModelTest(TestCase):
    """Test Cart model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='cart@test.com',
            name='Cart User',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('30.00'),
            stock_quantity=10
        )
    
    def test_create_cart(self):
        """Test creating a shopping cart."""
        cart = Cart.objects.create(user=self.user)
        
        self.assertEqual(cart.user, self.user)
        self.assertFalse(cart.is_checked_out)
    
    def test_add_item_to_cart(self):
        """Test adding item to cart."""
        cart = Cart.objects.create(user=self.user)
        
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )
        
        self.assertEqual(cart_item.cart, cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)
    
    def test_cart_total_calculation(self):
        """Test cart total calculation."""
        cart = Cart.objects.create(user=self.user)
        
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
            price=self.product.base_price
        )
        
        # Total should be 2 * 30.00 = 60.00
        self.assertEqual(cart.total_amount, Decimal('60.00'))
    
    def test_cart_string_representation(self):
        """Test cart string representation."""
        cart = Cart.objects.create(user=self.user)
        expected = f"Cart for Cart User (cart@test.com)"
        self.assertEqual(str(cart), expected)


class OrderModelTest(TestCase):
    """Test Order model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='order@test.com',
            name='Order User',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            base_price=Decimal('25.00')
        )
    
    def test_create_order(self):
        """Test creating an order."""
        order = Order.objects.create(
            user=self.user,
            order_reference='ORD-2024-001',
            total_amount=Decimal('75.00'),
            status='pending'
        )
        
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.order_reference, 'ORD-2024-001')
        self.assertEqual(order.status, 'pending')
    
    def test_order_with_items(self):
        """Test order with order items."""
        order = Order.objects.create(
            user=self.user,
            order_reference='ORD-2024-002',
            total_amount=Decimal('50.00'),
            status='confirmed'
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=Decimal('25.00')
        )
        
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.total_price, Decimal('50.00'))
    
    def test_order_string_representation(self):
        """Test order string representation."""
        order = Order.objects.create(
            user=self.user,
            order_reference='ORD-2024-003',
            total_amount=Decimal('100.00')
        )
        
        expected = "ORD-2024-003 - Order User (order@test.com)"
        self.assertEqual(str(order), expected)


class CouponModelTest(TestCase):
    """Test Coupon model functionality."""
    
    def test_create_coupon(self):
        """Test creating a coupon."""
        coupon = Coupon.objects.create(
            code='SAVE20',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            minimum_order_amount=Decimal('50.00'),
            usage_limit=100,
            is_active=True
        )
        
        self.assertEqual(coupon.code, 'SAVE20')
        self.assertEqual(coupon.discount_type, 'percentage')
        self.assertEqual(coupon.discount_value, Decimal('20.00'))
        self.assertTrue(coupon.is_active)
    
    def test_coupon_percentage_discount(self):
        """Test percentage discount calculation."""
        coupon = Coupon.objects.create(
            code='PERCENT10',
            discount_type='percentage',
            discount_value=Decimal('10.00')
        )
        
        order_amount = Decimal('100.00')
        discount = coupon.calculate_discount(order_amount)
        self.assertEqual(discount, Decimal('10.00'))
    
    def test_coupon_fixed_discount(self):
        """Test fixed amount discount calculation."""
        coupon = Coupon.objects.create(
            code='FIXED15',
            discount_type='fixed',
            discount_value=Decimal('15.00')
        )
        
        order_amount = Decimal('100.00')
        discount = coupon.calculate_discount(order_amount)
        self.assertEqual(discount, Decimal('15.00'))
    
    def test_coupon_string_representation(self):
        """Test coupon string representation."""
        coupon = Coupon.objects.create(
            code='TEST50',
            discount_type='percentage',
            discount_value=Decimal('50.00')
        )
        
        self.assertEqual(str(coupon), 'TEST50 - 50% off')


class EcommerceAPITest(APITestCase):
    """Test ecommerce API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@test.com',
            name='API User',
            password='testpass'
        )
        
        self.category = ProductCategory.objects.create(
            name='API Category',
            slug='api-category'
        )
        
        self.brand = Brand.objects.create(
            name='API Brand',
            slug='api-brand'
        )
        
        self.product = Product.objects.create(
            name='API Product',
            slug='api-product',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('40.00'),
            stock_quantity=20
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_products(self):
        """Test listing products."""
        url = reverse('ecommerce:product-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Product')
    
    def test_product_detail(self):
        """Test getting product details."""
        url = reverse('ecommerce:product-detail', kwargs={'slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'API Product')
        self.assertEqual(float(response.data['base_price']), 40.00)
    
    def test_list_categories(self):
        """Test listing product categories."""
        url = reverse('ecommerce:category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Category')
    
    def test_add_to_cart(self):
        """Test adding product to cart."""
        url = reverse('ecommerce:add-to-cart')
        data = {
            'product_id': self.product.id,
            'quantity': 2
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
    
    def test_view_cart(self):
        """Test viewing cart contents."""
        # Create cart with item
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
            price=self.product.base_price
        )
        
        url = reverse('ecommerce:cart-detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['product']['name'], 'API Product')
    
    def test_apply_coupon(self):
        """Test applying coupon to cart."""
        # Create coupon
        coupon = Coupon.objects.create(
            code='API20',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            is_active=True
        )
        
        # Create cart
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
            price=self.product.base_price
        )
        
        url = reverse('ecommerce:apply-coupon')
        data = {'coupon_code': 'API20'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_create_order(self):
        """Test creating an order."""
        # Create cart with items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
            price=self.product.base_price
        )
        
        url = reverse('ecommerce:create-order')
        data = {
            'shipping_address': {
                'street': '123 Test St',
                'city': 'Test City',
                'postal_code': '12345',
                'country': 'Test Country'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Order.objects.filter(user=self.user).exists())
    
    def test_list_user_orders(self):
        """Test listing user orders."""
        # Create an order
        Order.objects.create(
            user=self.user,
            order_reference='TEST-001',
            total_amount=Decimal('40.00'),
            status='confirmed'
        )
        
        url = reverse('ecommerce:order-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['order_reference'], 'TEST-001')
    
    def test_search_products(self):
        """Test searching products."""
        url = reverse('ecommerce:product-search')
        response = self.client.get(url, {'q': 'API Product'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_products_by_category(self):
        """Test filtering products by category."""
        url = reverse('ecommerce:product-list')
        response = self.client.get(url, {'category': self.category.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_unauthorized_cart_access(self):
        """Test unauthorized access to cart."""
        self.client.force_authenticate(user=None)
        
        url = reverse('ecommerce:cart-detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)