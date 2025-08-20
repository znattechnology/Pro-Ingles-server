"""
URL configuration for e-commerce app.
"""

from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    # Product categories
    path('categories/', views.ProductCategoryListView.as_view(), name='category-list'),
    
    # Brands
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/featured/', views.FeaturedProductsView.as_view(), name='featured-products'),
    path('products/popular/', views.PopularProductsView.as_view(), name='popular-products'),
    path('products/on-sale/', views.OnSaleProductsView.as_view(), name='on-sale-products'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/<slug:slug>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<uuid:product_id>/recommendations/', views.product_recommendations, name='product-recommendations'),
    
    # Search
    path('search/suggestions/', views.product_search_suggestions, name='search-suggestions'),
    
    # Shopping cart
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartItemView.as_view(), name='cart-add-item'),
    path('cart/items/<uuid:item_id>/', views.CartItemView.as_view(), name='cart-item-detail'),
    
    # Coupons
    path('coupons/validate/', views.validate_coupon, name='validate-coupon'),
    
    # Orders
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<str:order_number>/update/', views.OrderUpdateView.as_view(), name='order-update'),
    
    # User orders
    path('my-orders/', views.MyOrdersView.as_view(), name='my-orders'),
    
    # Admin endpoints
    path('admin/stats/', views.ecommerce_stats, name='ecommerce-stats'),
]