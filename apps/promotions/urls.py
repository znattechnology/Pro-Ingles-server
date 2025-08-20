"""
URL configuration for promotions app.
"""

from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    # Campaigns
    path('campaigns/', views.CampaignListView.as_view(), name='campaign-list'),
    path('campaigns/<slug:slug>/', views.CampaignDetailView.as_view(), name='campaign-detail'),
    path('campaigns/<uuid:campaign_id>/join/', views.join_campaign, name='join-campaign'),
    
    # Promotions
    path('promotions/', views.PromotionListView.as_view(), name='promotion-list'),
    path('promotions/<str:code>/', views.PromotionDetailView.as_view(), name='promotion-detail'),
    
    # Coupon functionality
    path('coupons/validate/', views.validate_coupon, name='validate-coupon'),
    path('coupons/apply/', views.apply_coupon, name='apply-coupon'),
    
    # Active promotions
    path('active/', views.active_promotions, name='active-promotions'),
    
    # User-specific endpoints
    path('my/usage/', views.UserPromotionUsageView.as_view(), name='user-promotion-usage'),
    path('my/campaigns/', views.UserCampaignParticipationView.as_view(), name='user-campaigns'),
    path('my/stats/', views.user_promotion_stats, name='user-promotion-stats'),
]