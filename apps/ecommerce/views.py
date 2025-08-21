"""
Views for e-commerce functionality.
"""

import logging
from decimal import Decimal
from django.db.models import Q, Count, Avg, Min, Max, F
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from .models import (
    ProductCategory, Brand, Product, ProductImage, Cart, CartItem,
    Coupon, Order, OrderItem
)
from .serializers import (
    ProductCategorySerializer, BrandSerializer, ProductListSerializer,
    ProductDetailSerializer, ProductCreateUpdateSerializer, ProductAdminListSerializer,
    ProductImageSerializer, CartSerializer, CartItemSerializer, CouponSerializer, CouponValidateSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer
)
from apps.core.permissions import IsAdminUser
from apps.core.pagination import CustomPagination

logger = logging.getLogger(__name__)


class ProductFilter(django_filters.FilterSet):
    """Advanced filtering for products."""
    
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.ModelMultipleChoiceFilter(
        queryset=ProductCategory.objects.all(),
        field_name='category'
    )
    brand = django_filters.ModelMultipleChoiceFilter(
        queryset=Brand.objects.all(),
        field_name='brand'
    )
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    
    class Meta:
        model = Product
        fields = ['is_featured', 'is_digital']
    
    def filter_in_stock(self, queryset, name, value):
        """Filter products that are in stock."""
        if value:
            return queryset.filter(
                Q(track_inventory=False) |
                Q(track_inventory=True, stock_quantity__gt=0) |
                Q(track_inventory=True, allow_backorder=True)
            )
        return queryset
    
    def filter_on_sale(self, queryset, name, value):
        """Filter products that are on sale."""
        if value:
            return queryset.filter(sale_price__lt=F('price'))
        return queryset


class ProductCategoryListView(generics.ListAPIView):
    """List all product categories."""
    
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = ProductCategory.objects.filter(is_active=True)
    ordering = ['sort_order', 'name']


class BrandListView(generics.ListAPIView):
    """List all brands."""
    
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Brand.objects.filter(is_active=True)
    ordering = ['name']


class ProductListView(generics.ListAPIView):
    """List products with advanced filtering."""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'short_description', 'brand__name']
    ordering_fields = ['name', 'price', 'average_rating', 'created_at']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True
        ).select_related('category', 'brand').prefetch_related('images')


class ProductDetailView(generics.RetrieveAPIView):
    """Retrieve individual product details."""
    
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True
        ).select_related('category', 'brand').prefetch_related(
            'images', 'variations__attributes'
        )


class ProductCreateView(generics.CreateAPIView):
    """Create new product (admin only)."""
    
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAdminUser]
    
    def create(self, request, *args, **kwargs):
        """Create a new product with detailed error logging."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[ProductCreate] Request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"[ProductCreate] Validation errors: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors,
                'message': 'Validation error'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"[ProductCreate] Creation error: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error creating product: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductUpdateView(generics.UpdateAPIView):
    """Update existing product (admin only)."""
    
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return Product.objects.all()
    
    def update(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[ProductUpdate] User: {request.user}")
        logger.info(f"[ProductUpdate] User authenticated: {request.user.is_authenticated}")
        logger.info(f"[ProductUpdate] User role: {getattr(request.user, 'role', None)}")
        logger.info(f"[ProductUpdate] Request data: {request.data}")
        
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"[ProductUpdate] Error: {str(e)}")
            logger.error(f"[ProductUpdate] Error type: {type(e)}")
            raise


class FeaturedProductsView(generics.ListAPIView):
    """List featured products."""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related('category', 'brand').prefetch_related('images')[:12]


class PopularProductsView(generics.ListAPIView):
    """List popular products based on ratings."""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            average_rating__gte=4.0,
            total_reviews__gte=5
        ).select_related('category', 'brand').prefetch_related('images').order_by(
            '-average_rating', '-total_reviews'
        )[:12]


class OnSaleProductsView(generics.ListAPIView):
    """List products currently on sale."""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['discount_percentage', 'sale_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            sale_price__isnull=False,
            sale_price__lt=F('price')
        ).select_related('category', 'brand').prefetch_related('images')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_search_suggestions(request):
    """Get search suggestions for products."""
    query = request.query_params.get('q', '').strip()
    
    if not query or len(query) < 2:
        return Response({'suggestions': []})
    
    # Get product name suggestions
    products = Product.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:10]
    
    # Get brand suggestions
    brands = Brand.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:5]
    
    # Get category suggestions
    categories = ProductCategory.objects.filter(
        name__icontains=query,
        is_active=True
    ).values_list('name', flat=True)[:5]
    
    suggestions = list(set(list(products) + list(brands) + list(categories)))
    
    return Response({
        'suggestions': suggestions[:15]
    })


class CartView(APIView):
    """Manage user's shopping cart."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current user's cart."""
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    def delete(self, request):
        """Clear user's cart."""
        try:
            cart = request.user.cart
            cart.items.all().delete()
            return Response({'message': 'Cart cleared successfully'})
        except Cart.DoesNotExist:
            return Response({'message': 'Cart is already empty'})


class CartItemView(APIView):
    """Manage cart items."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Add item to cart."""
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        serializer = CartItemSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Check if item already exists in cart
        product = serializer.validated_data['product']
        variation = serializer.validated_data.get('variation')
        quantity = serializer.validated_data['quantity']
        
        try:
            cart_item = CartItem.objects.get(
                cart=cart,
                product=product,
                variation=variation
            )
            # Update quantity
            cart_item.quantity += quantity
            cart_item.save()
            
            serializer = CartItemSerializer(cart_item, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except CartItem.DoesNotExist:
            # Create new cart item
            cart_item = serializer.save(cart=cart)
            return Response(
                CartItemSerializer(cart_item, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
    
    def put(self, request, item_id):
        """Update cart item quantity."""
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartItemSerializer(
            cart_item,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    def delete(self, request, item_id):
        """Remove item from cart."""
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__user=request.user
            )
            cart_item.delete()
            return Response({'message': 'Item removed from cart'})
            
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def validate_coupon(request):
    """Validate coupon code and calculate discount."""
    serializer = CouponValidateSerializer(
        data=request.data,
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    
    coupon = serializer.validated_data['coupon']
    discount_amount = serializer.validated_data['discount_amount']
    
    return Response({
        'valid': True,
        'coupon': CouponSerializer(coupon).data,
        'discount_amount': discount_amount,
        'message': f'Coupon applied! You save €{discount_amount}'
    })


class OrderFilter(django_filters.FilterSet):
    """Filtering for orders."""
    
    status = django_filters.MultipleChoiceFilter(choices=Order.STATUS_CHOICES)
    payment_status = django_filters.MultipleChoiceFilter(choices=Order.PAYMENT_STATUS_CHOICES)
    placed_from = django_filters.DateTimeFilter(field_name='placed_at', lookup_expr='gte')
    placed_to = django_filters.DateTimeFilter(field_name='placed_at', lookup_expr='lte')
    min_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_total = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    
    class Meta:
        model = Order
        fields = []


class OrderListView(generics.ListAPIView):
    """List all orders (admin only)."""
    
    serializer_class = OrderListSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['order_number', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['placed_at', 'total_amount']
    ordering = ['-placed_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Order.objects.select_related('user').all()


class MyOrdersView(generics.ListAPIView):
    """List current user's orders."""
    
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ['placed_at', 'total_amount']
    ordering = ['-placed_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    """Retrieve individual order details."""
    
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.select_related(
                'user', 'billing_address', 'shipping_address', 'coupon'
            ).prefetch_related('items__product')
        else:
            return Order.objects.filter(user=user).select_related(
                'billing_address', 'shipping_address', 'coupon'
            ).prefetch_related('items__product')


class OrderCreateView(generics.CreateAPIView):
    """Create new order from cart."""
    
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        return Response({
            'message': 'Order created successfully',
            'order_number': order.order_number,
            'total_amount': order.total_amount,
            'order_id': str(order.id)
        }, status=status.HTTP_201_CREATED)


class OrderUpdateView(generics.UpdateAPIView):
    """Update order status (admin only)."""
    
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'order_number'
    
    def get_queryset(self):
        return Order.objects.all()
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        return Response({
            'message': f'Order status updated to {order.get_status_display()}',
            'order_number': order.order_number,
            'status': order.status
        })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def ecommerce_stats(request):
    """Get e-commerce statistics for admin dashboard."""
    from django.db.models import Sum, Avg, Count
    from django.utils import timezone
    
    today = timezone.now().date()
    this_month = today.replace(day=1)
    
    stats = {
        # Products
        'total_products': Product.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'inactive_products': Product.objects.filter(is_active=False).count(),
        'featured_products': Product.objects.filter(is_active=True, is_featured=True).count(),
        'low_stock_products': Product.objects.filter(
            track_inventory=True,
            stock_quantity__lte=F('low_stock_threshold'),
            stock_quantity__gt=0
        ).count(),
        'out_of_stock_products': Product.objects.filter(
            track_inventory=True,
            stock_quantity=0
        ).count(),
        
        # Product values
        'total_product_value': Product.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum(F('price') * F('stock_quantity'))
        )['total'] or 0,
        'average_product_price': Product.objects.filter(
            is_active=True
        ).aggregate(avg=Avg('price'))['avg'] or 0,
        
        # Orders
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'processing_orders': Order.objects.filter(status='processing').count(),
        'shipped_orders': Order.objects.filter(status='shipped').count(),
        'delivered_orders': Order.objects.filter(status='delivered').count(),
        
        # Revenue
        'total_revenue': Order.objects.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'monthly_revenue': Order.objects.filter(
            payment_status='paid',
            placed_at__gte=this_month
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'average_order_value': Order.objects.filter(
            payment_status='paid'
        ).aggregate(avg=Avg('total_amount'))['avg'] or 0,
        
        # Analytics
        'orders_by_status': Order.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count'),
        'top_selling_products': Product.objects.annotate(
            orders_count=Count('orderitem')
        ).order_by('-orders_count')[:10].values('name', 'orders_count'),
        'recent_orders': Order.objects.select_related('user').order_by(
            '-created_at'
        )[:5].values(
            'id', 'order_number', 'user__email', 'status', 'total_amount', 'created_at'
        ),
        
        # Customers
        'total_customers': get_user_model().objects.filter(
            orders__isnull=False
        ).distinct().count(),
        'active_carts': Cart.objects.filter(
            items__isnull=False
        ).distinct().count(),
    }
    
    return Response(stats)


# ============================================================================
# ADMIN VIEWS FOR DASHBOARD
# ============================================================================

class ProductAdminListView(generics.ListAPIView):
    """Admin-specific product listing for dashboard."""
    
    serializer_class = ProductAdminListSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'short_description', 'sku', 'brand__name']
    ordering_fields = ['name', 'price', 'stock_quantity', 'created_at', 'average_rating']
    ordering = ['-created_at']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        """Return all products (active and inactive) for admin."""
        return Product.objects.select_related('category', 'brand').prefetch_related('images')


class ProductAdminDetailView(generics.RetrieveAPIView):
    """Admin-specific product detail view."""
    
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Product.objects.select_related('category', 'brand').prefetch_related(
            'images', 'variations__attributes'
        )


class ProductToggleStatusView(generics.UpdateAPIView):
    """Toggle product active status."""
    
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    def patch(self, request, id):
        try:
            product = Product.objects.get(id=id)
            product.is_active = not product.is_active
            product.save(update_fields=['is_active'])
            
            return Response({
                'success': True, 
                'is_active': product.is_active,
                'message': f'Product {"activated" if product.is_active else "deactivated"} successfully'
            })
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ProductBulkOperationsView(generics.GenericAPIView):
    """Bulk operations for products."""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        action = request.data.get('action')
        product_ids = request.data.get('product_ids', [])
        
        if not action or not product_ids:
            return Response({
                'success': False,
                'error': 'Action and product_ids are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if action == 'bulk_activate':
                updated = Product.objects.filter(id__in=product_ids).update(is_active=True)
                message = f'{updated} products activated successfully'
                
            elif action == 'bulk_deactivate':
                updated = Product.objects.filter(id__in=product_ids).update(is_active=False)
                message = f'{updated} products deactivated successfully'
                
            elif action == 'bulk_delete':
                deleted = Product.objects.filter(id__in=product_ids).delete()
                message = f'{deleted[0]} products deleted successfully'
                
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action. Use: bulk_activate, bulk_deactivate, or bulk_delete'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductCategoriesAdminView(generics.ListCreateAPIView):
    """Admin endpoint for product categories - list and create."""
    
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminUser]
    pagination_class = None  # No pagination for dropdown
    
    def get_queryset(self):
        return ProductCategory.objects.filter(is_active=True).order_by('sort_order', 'name')


class ProductCategoryAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin endpoint for individual category operations."""
    
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    def get_queryset(self):
        return ProductCategory.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete category by marking as inactive."""
        category = self.get_object()
        
        # Check if category has products
        if category.products.filter(is_active=True).exists():
            return Response({
                'success': False,
                'error': 'Cannot delete category with active products. Move products to another category first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Soft delete
        category.is_active = False
        category.save()
        
        return Response({
            'success': True,
            'message': 'Category deleted successfully'
        })


class ProductCategoryToggleStatusView(generics.UpdateAPIView):
    """Toggle category active status."""
    
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    def patch(self, request, id):
        try:
            category = ProductCategory.objects.get(id=id)
            category.is_active = not category.is_active
            category.save(update_fields=['is_active'])
            
            return Response({
                'success': True, 
                'is_active': category.is_active,
                'message': f'Category {"activated" if category.is_active else "deactivated"} successfully'
            })
        except ProductCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_recommendations(request, product_id):
    """Get product recommendations based on category and price range."""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)
    
    # Get related products from same category
    price_min = product.current_price * Decimal('0.7')  # -30%
    price_max = product.current_price * Decimal('1.3')  # +30%
    
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        price__gte=price_min,
        price__lte=price_max
    ).exclude(id=product.id).select_related('category', 'brand').prefetch_related('images')[:8]
    
    serializer = ProductListSerializer(
        related_products, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'recommendations': serializer.data
    })


# ============================================================================
# PRODUCT IMAGE MANAGEMENT VIEWS
# ============================================================================

class ProductImageListView(generics.ListAPIView):
    """List all images for a specific product."""
    
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductImage.objects.filter(product_id=product_id).order_by('sort_order', 'created_at')


class ProductImageDeleteView(generics.DestroyAPIView):
    """Delete a specific product image."""
    
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductImage.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        image = self.get_object()
        product_id = image.product_id
        
        # Delete the physical file
        if image.image:
            try:
                image.image.delete(save=False)
            except Exception as e:
                logger.warning(f"Could not delete image file: {str(e)}")
        
        # Delete the database record
        image.delete()
        
        return Response({
            'success': True,
            'message': 'Imagem deletada com sucesso',
            'product_id': str(product_id)
        }, status=status.HTTP_200_OK)


class ProductImageUpdateView(generics.UpdateAPIView):
    """Update product image metadata (alt_text, is_primary, sort_order)."""
    
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ProductImage.objects.all()
    
    def update(self, request, *args, **kwargs):
        # If setting as primary, unset other primary images for this product
        if request.data.get('is_primary') is True:
            image = self.get_object()
            ProductImage.objects.filter(
                product=image.product, 
                is_primary=True
            ).exclude(id=image.id).update(is_primary=False)
        
        return super().update(request, *args, **kwargs)