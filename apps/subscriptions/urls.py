"""
Subscription URLs - URL routing para sistema de assinaturas

URL patterns para endpoints da API de assinaturas.
Maps client project routes to Django views.
"""

from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # ========================================================================
    # PUBLIC ENDPOINTS - Disponível sem autenticação
    # ========================================================================
    
    # Lista pública de planos (para landing page)
    path(
        'plans/', 
        views.PublicSubscriptionPlansListView.as_view(), 
        name='public-plans-list'
    ),
    
    # ========================================================================
    # USER ENDPOINTS - Requer autenticação de usuário
    # ========================================================================
    
    # Assinatura atual do usuário
    path(
        'my-subscription/', 
        views.UserSubscriptionView.as_view(), 
        name='user-subscription'
    ),
    
    # Upgrade/downgrade de plano
    path(
        'upgrade/', 
        views.upgrade_subscription, 
        name='upgrade-subscription'
    ),
    
    # Aplicar código promocional (validação)
    path(
        'apply-promo-code/', 
        views.apply_promo_code, 
        name='apply-promo-code'
    ),
    
    # Cancelar assinatura
    path(
        'cancel/', 
        views.cancel_subscription, 
        name='cancel-subscription'
    ),
    
    # ========================================================================
    # ADMIN ENDPOINTS - Requer permissões de admin
    # ========================================================================
    
    # Gerenciamento de planos
    path(
        'admin/plans/', 
        views.AdminSubscriptionPlansListView.as_view(), 
        name='admin-plans-list'
    ),
    path(
        'admin/plans/<uuid:pk>/', 
        views.AdminSubscriptionPlanDetailView.as_view(), 
        name='admin-plan-detail'
    ),
    
    # Gerenciamento de assinantes
    path(
        'admin/subscriptions/', 
        views.AdminUserSubscriptionsListView.as_view(), 
        name='admin-subscriptions-list'
    ),
    
    # Estatísticas para dashboard admin
    path(
        'admin/stats/', 
        views.admin_subscription_stats, 
        name='admin-subscription-stats'
    ),
    
    # Gerenciamento de códigos promocionais
    path(
        'admin/promo-codes/', 
        views.AdminPromotionalCodesListView.as_view(), 
        name='admin-promo-codes-list'
    ),
    path(
        'admin/promo-codes/<uuid:pk>/', 
        views.AdminPromotionalCodeDetailView.as_view(), 
        name='admin-promo-code-detail'
    ),
    
    # Histórico de uso de códigos promocionais
    path(
        'admin/promo-code-usage/', 
        views.AdminPromoCodeUsageListView.as_view(), 
        name='admin-promo-code-usage'
    ),
    
    # Estatísticas de códigos promocionais
    path(
        'admin/promo-code-stats/', 
        views.admin_promo_code_stats, 
        name='admin-promo-code-stats'
    ),
    
    # Relatórios detalhados de assinaturas
    path(
        'admin/reports/', 
        views.admin_subscription_reports, 
        name='admin-subscription-reports'
    ),
    
    # ========================================================================
    # UTILITIES ENDPOINTS - Analytics e verificação de limitações
    # ========================================================================
    
    # Analytics da assinatura do usuário
    path(
        'analytics/', 
        views.user_subscription_analytics, 
        name='user-subscription-analytics'
    ),
    
    # Verificar acesso a funcionalidade
    path(
        'check-access/', 
        views.check_feature_access, 
        name='check-feature-access'
    ),
    
    # Consumir recursos da assinatura
    path(
        'consume-usage/', 
        views.consume_feature_usage, 
        name='consume_feature_usage'
    ),
    
    # Status de limitações e uso atual
    path(
        'limits/', 
        views.subscription_limits_status, 
        name='subscription_limits_status'
    ),
]