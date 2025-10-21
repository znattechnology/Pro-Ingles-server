"""
Subscription Views - API endpoints para sistema de assinaturas

Este módulo fornece views DRF para gerenciar assinaturas, planos,
códigos promocionais e relatórios administrativos.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import (
    SubscriptionPlan,
    UserSubscription, 
    SubscriptionHistory,
    PromotionalCode,
    PromoCodeUsage
)
from .serializers import (
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
    SubscriptionHistorySerializer,
    PromotionalCodeSerializer,
    PromoCodeUsageSerializer,
    SubscriptionUpgradeSerializer,
    ApplyPromoCodeSerializer,
    SubscriptionStatsSerializer
)
from .utils import get_subscription_analytics

User = get_user_model()


# ========================================================================
# PUBLIC ENDPOINTS - Planos disponíveis (sem autenticação)
# ========================================================================

class PublicSubscriptionPlansListView(generics.ListAPIView):
    """
    Lista pública de planos de assinatura disponíveis
    Usado na landing page e tela de preços
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = []  # Público
    
    def get_queryset(self):
        """Filtra apenas planos ativos ordenados"""
        return SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by('sort_order')


# ========================================================================
# USER ENDPOINTS - Gerenciamento de assinatura do usuário
# ========================================================================

class UserSubscriptionView(generics.RetrieveAPIView):
    """
    Retorna a assinatura atual do usuário autenticado
    """
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Retorna assinatura do usuário ou cria uma gratuita"""
        # Garantir que o plano FREE existe
        free_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type='FREE',
            defaults={
                'name': 'Free',
                'description': 'Plano gratuito',
                'monthly_price': Decimal('0.00'),
                'is_active': True
            }
        )
        
        subscription, created = UserSubscription.objects.get_or_create(
            user=self.request.user,
            defaults={
                'plan': free_plan,
                'expires_at': timezone.now() + timedelta(days=365*10),  # 10 anos para free
                'status': 'ACTIVE'
            }
        )
        return subscription


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upgrade_subscription(request):
    """
    Upgrade ou downgrade de plano de assinatura
    """
    serializer = SubscriptionUpgradeSerializer(data=request.data)
    
    if serializer.is_valid():
        plan_id = serializer.validated_data['plan_id']
        billing_cycle = serializer.validated_data['billing_cycle']
        promo_code = serializer.validated_data.get('promo_code')
        
        try:
            new_plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            
            # Garantir que o plano FREE existe
            free_plan, _ = SubscriptionPlan.objects.get_or_create(
                plan_type='FREE',
                defaults={
                    'name': 'Free',
                    'description': 'Plano gratuito',
                    'monthly_price': Decimal('0.00'),
                    'is_active': True
                }
            )
            
            # Obter ou criar assinatura atual
            subscription, created = UserSubscription.objects.get_or_create(
                user=request.user,
                defaults={
                    'plan': free_plan,
                    'expires_at': timezone.now() + timedelta(days=365*10),
                    'status': 'ACTIVE'
                }
            )
            
            old_plan = subscription.plan
            
            # Calcular preço final
            if billing_cycle == 'YEARLY' and new_plan.yearly_price:
                final_price = new_plan.yearly_price
                expires_at = timezone.now() + timedelta(days=365)
            else:
                final_price = new_plan.monthly_price
                expires_at = timezone.now() + timedelta(days=30)
            
            # Aplicar código promocional se fornecido
            discount_applied = Decimal('0.00')
            if promo_code:
                try:
                    promo = PromotionalCode.objects.get(code=promo_code.upper())
                    if promo.is_valid():
                        # Verificar se usuário já usou este código
                        if not PromoCodeUsage.objects.filter(
                            user=request.user, 
                            promo_code=promo
                        ).exists():
                            if promo.discount_type == 'PERCENTAGE':
                                discount_applied = (final_price * promo.discount_value) / 100
                            elif promo.discount_type == 'FIXED_AMOUNT':
                                discount_applied = min(promo.discount_value, final_price)
                            
                            final_price -= discount_applied
                            
                            # Registrar uso do código
                            PromoCodeUsage.objects.create(
                                user=request.user,
                                promo_code=promo,
                                subscription=subscription,
                                discount_applied=discount_applied
                            )
                            
                            # Incrementar contador de uso
                            promo.current_uses += 1
                            promo.save(update_fields=['current_uses'])
                
                except PromotionalCode.DoesNotExist:
                    return Response({
                        'error': 'Código promocional inválido'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Atualizar assinatura
            subscription.plan = new_plan
            subscription.expires_at = expires_at
            subscription.status = 'ACTIVE'
            subscription.last_payment_at = timezone.now()
            subscription.save()
            
            # Registrar no histórico
            SubscriptionHistory.objects.create(
                subscription=subscription,
                event_type='UPGRADED' if new_plan.monthly_price > old_plan.monthly_price else 'DOWNGRADED',
                previous_plan=old_plan,
                new_plan=new_plan,
                amount_paid=final_price,
                notes=f'Billing cycle: {billing_cycle}. Discount applied: {discount_applied} AOA'
            )
            
            serializer_response = UserSubscriptionSerializer(subscription)
            return Response({
                'message': 'Plano atualizado com sucesso!',
                'subscription': serializer_response.data,
                'amount_paid': final_price,
                'discount_applied': discount_applied
            })
            
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'error': 'Plano não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def apply_promo_code(request):
    """
    Valida um código promocional sem fazer upgrade
    """
    serializer = ApplyPromoCodeSerializer(data=request.data)
    
    if serializer.is_valid():
        promo_code = serializer.validated_data['promo_code']
        plan_id = serializer.validated_data['plan_id']
        
        try:
            promo = PromotionalCode.objects.get(code=promo_code)
            plan = SubscriptionPlan.objects.get(id=plan_id)
            
            # Verificar se usuário já usou este código
            if PromoCodeUsage.objects.filter(user=request.user, promo_code=promo).exists():
                return Response({
                    'error': 'Você já utilizou este código promocional'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calcular desconto
            original_price = plan.monthly_price
            discount_amount = Decimal('0.00')
            
            if promo.discount_type == 'PERCENTAGE':
                discount_amount = (original_price * promo.discount_value) / 100
            elif promo.discount_type == 'FIXED_AMOUNT':
                discount_amount = min(promo.discount_value, original_price)
            
            final_price = original_price - discount_amount
            
            return Response({
                'valid': True,
                'promo_code': promo.code,
                'discount_type': promo.discount_type,
                'discount_value': promo.discount_value,
                'original_price': original_price,
                'discount_amount': discount_amount,
                'final_price': final_price,
                'description': promo.description
            })
            
        except (PromotionalCode.DoesNotExist, SubscriptionPlan.DoesNotExist):
            return Response({
                'error': 'Código ou plano inválido'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request):
    """
    Cancela a assinatura do usuário (mantém até o fim do período pago)
    """
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        
        # Não cancelar se já está cancelado
        if subscription.status == 'CANCELED':
            return Response({
                'error': 'Assinatura já está cancelada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancelar assinatura
        subscription.status = 'CANCELED'
        subscription.canceled_at = timezone.now()
        subscription.save()
        
        # Registrar no histórico
        SubscriptionHistory.objects.create(
            subscription=subscription,
            event_type='CANCELED',
            previous_plan=subscription.plan,
            notes='Cancelamento solicitado pelo usuário'
        )
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response({
            'message': 'Assinatura cancelada com sucesso. Você mantém acesso até o fim do período pago.',
            'subscription': serializer.data
        })
        
    except UserSubscription.DoesNotExist:
        return Response({
            'error': 'Assinatura não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)


# ========================================================================
# ADMIN ENDPOINTS - Gerenciamento administrativo
# ========================================================================

class AdminSubscriptionPlansListView(generics.ListCreateAPIView):
    """
    Lista e cria planos de assinatura (admin only)
    """
    queryset = SubscriptionPlan.objects.all().order_by('sort_order')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission
    
    def get_queryset(self):
        """Admins veem todos os planos, incluindo inativos"""
        return SubscriptionPlan.objects.all().order_by('sort_order')


class AdminSubscriptionPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Gerencia plano específico (admin only)
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission


class AdminUserSubscriptionsListView(generics.ListAPIView):
    """
    Lista todas as assinaturas de usuários (admin only)
    """
    queryset = UserSubscription.objects.select_related('user', 'plan').order_by('-created_at')
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission
    
    def get_queryset(self):
        """Permite filtros por status, plano, etc"""
        queryset = UserSubscription.objects.select_related('user', 'plan').order_by('-created_at')
        
        # Filtros opcionais
        plan_type = self.request.query_params.get('plan_type')
        status_filter = self.request.query_params.get('status')
        
        if plan_type:
            queryset = queryset.filter(plan__plan_type=plan_type)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # TODO: Add IsAdmin permission
def admin_subscription_stats(request):
    """
    Retorna estatísticas gerais de assinatura para o dashboard admin
    """
    # Estatísticas básicas
    total_subscribers = UserSubscription.objects.filter(status='ACTIVE').count()
    
    # Receita mensal (últimos 30 dias)
    last_30_days = timezone.now() - timedelta(days=30)
    recent_payments = SubscriptionHistory.objects.filter(
        event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
        created_at__gte=last_30_days,
        amount_paid__isnull=False
    ).aggregate(
        total_revenue=Sum('amount_paid')
    )['total_revenue'] or Decimal('0.00')
    
    # Distribuição por plano
    plan_distribution = UserSubscription.objects.filter(
        status='ACTIVE'
    ).values('plan__plan_type').annotate(count=Count('id'))
    
    free_users = premium_users = premium_plus_users = 0
    for item in plan_distribution:
        if item['plan__plan_type'] == 'FREE':
            free_users = item['count']
        elif item['plan__plan_type'] == 'PREMIUM':
            premium_users = item['count']
        elif item['plan__plan_type'] == 'PREMIUM_PLUS':
            premium_plus_users = item['count']
    
    # Account for users without subscription records (they should be considered FREE users)
    total_users = User.objects.count()
    users_with_subscriptions = UserSubscription.objects.filter(status='ACTIVE').values('user').distinct().count()
    users_without_subscriptions = total_users - users_with_subscriptions
    free_users += users_without_subscriptions  # Add users without subscriptions to FREE count
    
    # Taxa de conversão (estimativa simples)
    paying_users = premium_users + premium_plus_users
    conversion_rate = (paying_users / total_users * 100) if total_users > 0 else 0
    
    # Taxa de churn (cancelamentos nos últimos 30 dias)
    recent_cancellations = UserSubscription.objects.filter(
        status='CANCELED',
        canceled_at__gte=last_30_days
    ).count()
    churn_rate = (recent_cancellations / total_subscribers * 100) if total_subscribers > 0 else 0
    
    # Assinaturas recentes
    recent_subscriptions = UserSubscription.objects.select_related(
        'user', 'plan'
    ).filter(
        status__in=['ACTIVE', 'TRIAL']
    ).order_by('-created_at')[:10]
    
    # Códigos promocionais ativos
    active_promo_codes = PromotionalCode.objects.filter(
        is_active=True,
        valid_until__gte=timezone.now()
    ).count()
    
    # Dados para gráfico de receita (últimos 12 meses)
    revenue_chart = {}
    for i in range(12):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        month_revenue = SubscriptionHistory.objects.filter(
            event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
            created_at__gte=month_start,
            created_at__lt=month_end,
            amount_paid__isnull=False
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        
        revenue_chart[month_start.strftime('%Y-%m')] = float(month_revenue)
    
    stats = {
        'total_subscribers': total_subscribers,
        'monthly_revenue': recent_payments,
        'conversion_rate': round(conversion_rate, 1),
        'churn_rate': round(churn_rate, 1),
        'free_users': free_users,
        'premium_users': premium_users,
        'premium_plus_users': premium_plus_users,
        'active_promo_codes': active_promo_codes,
        'recent_subscriptions': UserSubscriptionSerializer(recent_subscriptions, many=True).data,
        'revenue_chart': revenue_chart
    }
    
    return Response(stats)


class AdminPromotionalCodesListView(generics.ListCreateAPIView):
    """
    Lista e cria códigos promocionais (admin only)
    """
    queryset = PromotionalCode.objects.all().order_by('-created_at')
    serializer_class = PromotionalCodeSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission


class AdminPromotionalCodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Gerencia código promocional específico (admin only)
    """
    queryset = PromotionalCode.objects.all()
    serializer_class = PromotionalCodeSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission


class AdminPromoCodeUsageListView(generics.ListAPIView):
    """
    Lista uso de códigos promocionais (admin only)
    """
    queryset = PromoCodeUsage.objects.select_related('user', 'promo_code').order_by('-used_at')
    serializer_class = PromoCodeUsageSerializer
    permission_classes = [permissions.IsAuthenticated]  # TODO: Add IsAdmin permission


# ========================================================================
# SUBSCRIPTION ANALYTICS AND UTILITIES
# ========================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_subscription_analytics(request):
    """
    GET /api/v1/subscriptions/analytics/
    
    Get comprehensive subscription analytics for the current user.
    """
    user = request.user
    analytics = get_subscription_analytics(user)
    
    return Response(analytics)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_feature_access(request):
    """
    POST /api/v1/subscriptions/check-access/
    
    Check if user has access to a specific feature.
    """
    feature_type = request.data.get('feature_type')
    amount = request.data.get('amount', 1)
    
    if not feature_type:
        return Response({
            'error': 'feature_type is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from .utils import check_subscription_limits
    result = check_subscription_limits(request.user, feature_type, amount)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def consume_feature_usage(request):
    """
    POST /api/v1/subscriptions/consume-usage/
    
    Consume usage for a specific feature.
    """
    feature_type = request.data.get('feature_type')
    amount = request.data.get('amount', 1)
    
    if not feature_type:
        return Response({
            'error': 'feature_type is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from .utils import consume_subscription_resource
    success = consume_subscription_resource(request.user, feature_type, amount)
    
    if success:
        return Response({
            'success': True,
            'message': f'Consumed {amount} {feature_type}'
        })
    else:
        return Response({
            'success': False,
            'error': 'Failed to consume resource'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def subscription_limits_status(request):
    """
    GET /api/v1/subscriptions/limits/
    
    Get current subscription limits and usage for all features.
    """
    from .utils import get_user_subscription
    
    subscription = get_user_subscription(request.user)
    subscription.reset_daily_usage_if_needed()
    subscription.recharge_hearts_if_needed()
    
    # Get current usage for all features
    limits_status = {
        'lessons': {
            'used': subscription.daily_lessons_used,
            'limit': subscription.plan.daily_lessons_limit,
            'unlimited': subscription.plan.daily_lessons_limit == 0,
            'can_use': subscription.can_take_lesson()
        },
        'speaking': {
            'used': subscription.daily_speaking_minutes_used,
            'limit': subscription.plan.daily_speaking_minutes,
            'unlimited': subscription.plan.daily_speaking_minutes == 0,
            'can_use': subscription.can_use_speaking()
        },
        'listening': {
            'used': subscription.daily_listening_minutes_used,
            'limit': subscription.plan.daily_listening_minutes,
            'unlimited': subscription.plan.daily_listening_minutes == 0,
            'can_use': subscription.can_use_listening()
        },
        'hearts': {
            'current': subscription.current_hearts,
            'limit': subscription.plan.hearts_limit,
            'unlimited': subscription.plan.hearts_limit == 0,
            'can_use': subscription.has_hearts(),
            'recharge_hours': subscription.plan.hearts_recharge_hours,
            'last_recharge': subscription.last_heart_recharge
        },
        'plan': {
            'name': subscription.plan.name,
            'type': subscription.plan.plan_type,
            'is_active': subscription.is_active(),
            'expires_at': subscription.expires_at,
            'days_remaining': subscription.days_until_expiry()
        }
    }
    
    return Response(limits_status)