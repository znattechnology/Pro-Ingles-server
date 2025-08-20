"""
URL configuration for payments app.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment Methods
    path('methods/', views.PaymentMethodListView.as_view(), name='method-list'),
    path('methods/<uuid:pk>/', views.PaymentMethodDetailView.as_view(), name='method-detail'),
    
    # Payment Accounts
    path('accounts/', views.PaymentAccountListView.as_view(), name='account-list'),
    path('accounts/<uuid:pk>/', views.PaymentAccountDetailView.as_view(), name='account-detail'),
    
    # Payments
    path('', views.PaymentListView.as_view(), name='payment-list'),
    path('create/', views.PaymentCreateView.as_view(), name='payment-create'),
    path('<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    
    # Payment Intents
    path('intents/', views.PaymentIntentListView.as_view(), name='intent-list'),
    path('intents/<str:intent_id>/confirm/', views.confirm_payment_intent, name='intent-confirm'),
    
    # Refunds
    path('refunds/', views.RefundListView.as_view(), name='refund-list'),
    path('<uuid:payment_id>/refunds/', views.RefundCreateView.as_view(), name='refund-create'),
    
    # Wallet
    path('wallet/', views.WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),
    
    # Stripe Connect
    path('stripe/connect/', views.create_stripe_connect_account, name='stripe-connect'),
    
    # Statistics
    path('stats/', views.payment_stats, name='payment-stats'),
    
    # Webhooks
    path('webhooks/stripe/', views.stripe_webhook, name='stripe-webhook'),
]