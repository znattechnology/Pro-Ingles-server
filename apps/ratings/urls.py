"""
URL configuration for ratings and reviews app.
"""

from django.urls import path
from . import views

app_name = 'ratings'

urlpatterns = [
    # Braider reviews
    path('braiders/<uuid:braider_id>/reviews/', views.BraiderReviewListView.as_view(), name='braider-reviews'),
    path('braiders/<uuid:braider_id>/reviews/stats/', views.braider_review_stats, name='braider-review-stats'),
    path('braider-reviews/create/', views.BraiderReviewCreateView.as_view(), name='braider-review-create'),
    path('braider-reviews/<uuid:pk>/', views.BraiderReviewDetailView.as_view(), name='braider-review-detail'),
    
    # Product reviews
    path('products/<uuid:product_id>/reviews/', views.ProductReviewListView.as_view(), name='product-reviews'),
    path('products/<uuid:product_id>/reviews/stats/', views.product_review_stats, name='product-review-stats'),
    path('product-reviews/create/', views.ProductReviewCreateView.as_view(), name='product-review-create'),
    path('product-reviews/<uuid:pk>/', views.ProductReviewDetailView.as_view(), name='product-review-detail'),
    
    # User's own reviews
    path('my-reviews/braiders/', views.MyBraiderReviewsView.as_view(), name='my-braider-reviews'),
    path('my-reviews/products/', views.MyProductReviewsView.as_view(), name='my-product-reviews'),
    
    # Reviewable items
    path('reviewable/bookings/', views.reviewable_bookings, name='reviewable-bookings'),
    path('reviewable/products/', views.reviewable_products, name='reviewable-products'),
    
    # Review interactions
    path('reviews/<str:review_type>/<uuid:review_id>/helpful/', views.ReviewHelpfulnessView.as_view(), name='review-helpfulness'),
    path('reviews/<str:review_type>/<uuid:review_id>/response/', views.ReviewResponseView.as_view(), name='review-response'),
    path('reviews/<str:review_type>/<uuid:review_id>/report/', views.ReviewReportView.as_view(), name='review-report'),
    
    # Admin moderation
    path('admin/pending-reviews/', views.PendingReviewsView.as_view(), name='pending-reviews'),
    path('admin/moderate/<str:review_type>/<uuid:review_id>/', views.ReviewModerationView.as_view(), name='review-moderation'),
]