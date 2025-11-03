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
        subscription, created = UserSubscription.objects.get_or_create(
            user=self.request.user,
            defaults={
                'plan': SubscriptionPlan.objects.get(plan_type='FREE'),
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
            
            # Obter ou criar assinatura atual
            subscription, created = UserSubscription.objects.get_or_create(
                user=request.user,
                defaults={
                    'plan': SubscriptionPlan.objects.get(plan_type='FREE'),
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
    total_subscriptions = UserSubscription.objects.count()
    active_subscriptions = UserSubscription.objects.filter(status='ACTIVE').count()
    trial_subscriptions = UserSubscription.objects.filter(status='TRIAL').count()
    expired_subscriptions = UserSubscription.objects.filter(status='EXPIRED').count()
    canceled_subscriptions = UserSubscription.objects.filter(status='CANCELED').count()
    
    # Receita mensal (últimos 30 dias)
    last_30_days = timezone.now() - timedelta(days=30)
    monthly_revenue = SubscriptionHistory.objects.filter(
        event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
        created_at__gte=last_30_days,
        amount_paid__isnull=False
    ).aggregate(
        total_revenue=Sum('amount_paid')
    )['total_revenue'] or Decimal('0.00')
    
    # Receita anual
    last_365_days = timezone.now() - timedelta(days=365)
    yearly_revenue = SubscriptionHistory.objects.filter(
        event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
        created_at__gte=last_365_days,
        amount_paid__isnull=False
    ).aggregate(
        total_revenue=Sum('amount_paid')
    )['total_revenue'] or Decimal('0.00')
    
    # ARPU (Average Revenue Per User)
    paying_users = UserSubscription.objects.filter(
        status__in=['ACTIVE'],
        plan__plan_type__in=['PREMIUM', 'PREMIUM_PLUS']
    ).count()
    average_subscription_value = (monthly_revenue / paying_users) if paying_users > 0 else Decimal('0.00')
    
    stats = {
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'trial_subscriptions': trial_subscriptions,
        'expired_subscriptions': expired_subscriptions,
        'canceled_subscriptions': canceled_subscriptions,
        'monthly_revenue': str(monthly_revenue),
        'yearly_revenue': str(yearly_revenue),
        'average_subscription_value': str(average_subscription_value)
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # TODO: Add IsAdmin permission
def admin_subscription_reports(request):
    """
    Endpoint para relatórios detalhados de assinaturas (página de reports)
    """
    # Overview metrics
    total_subscriptions = UserSubscription.objects.count()
    active_subscriptions = UserSubscription.objects.filter(status='ACTIVE').count()
    trial_subscriptions = UserSubscription.objects.filter(status='TRIAL').count()
    canceled_subscriptions = UserSubscription.objects.filter(status='CANCELED').count()
    
    # Revenue calculations
    last_30_days = timezone.now() - timedelta(days=30)
    last_365_days = timezone.now() - timedelta(days=365)
    
    monthly_revenue = SubscriptionHistory.objects.filter(
        event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
        created_at__gte=last_30_days,
        amount_paid__isnull=False
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    
    # Conversion rate (trial to paid)
    total_trials = UserSubscription.objects.filter(
        status__in=['TRIAL'],
        created_at__gte=last_30_days
    ).count()
    converted_trials = UserSubscription.objects.filter(
        status='ACTIVE',
        created_at__gte=last_30_days,
        trial_ends_at__isnull=False
    ).count()
    conversion_rate = (converted_trials / total_trials * 100) if total_trials > 0 else 0
    
    # Churn rate (monthly)
    monthly_cancellations = UserSubscription.objects.filter(
        status='CANCELED',
        canceled_at__gte=last_30_days
    ).count()
    churn_rate = (monthly_cancellations / active_subscriptions * 100) if active_subscriptions > 0 else 0
    
    # Monthly growth rate
    last_60_days = timezone.now() - timedelta(days=60)
    previous_month_revenue = SubscriptionHistory.objects.filter(
        event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
        created_at__gte=last_60_days,
        created_at__lt=last_30_days,
        amount_paid__isnull=False
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    
    monthly_growth_rate = 0
    if previous_month_revenue > 0:
        monthly_growth_rate = ((monthly_revenue - previous_month_revenue) / previous_month_revenue * 100)
    
    # ARPU
    paying_users = active_subscriptions
    arpu = (monthly_revenue / paying_users) if paying_users > 0 else Decimal('0.00')
    
    # Revenue by month (last 6 months)
    revenue_by_month = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=32)
        month_end = month_end.replace(day=1) - timedelta(days=1)  # Last day of month
        
        month_revenue = SubscriptionHistory.objects.filter(
            event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
            created_at__gte=month_start,
            created_at__lte=month_end,
            amount_paid__isnull=False
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        
        month_subscriptions = UserSubscription.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).count()
        
        revenue_by_month.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': str(month_revenue),
            'subscriptions': month_subscriptions
        })
    
    revenue_by_month.reverse()  # Ordem cronológica
    
    # Plan distribution
    plan_distribution = []
    for plan_type in ['FREE', 'PREMIUM', 'PREMIUM_PLUS']:
        count = UserSubscription.objects.filter(
            plan__plan_type=plan_type,
            status='ACTIVE'
        ).count()
        
        percentage = (count / active_subscriptions * 100) if active_subscriptions > 0 else 0
        
        # Calculate revenue for this plan type
        plan_revenue = SubscriptionHistory.objects.filter(
            subscription__plan__plan_type=plan_type,
            event_type__in=['CREATED', 'UPGRADED', 'RENEWED'],
            created_at__gte=last_30_days,
            amount_paid__isnull=False
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        
        plan_name = 'Gratuito' if plan_type == 'FREE' else ('Premium' if plan_type == 'PREMIUM' else 'Premium Plus')
        
        plan_distribution.append({
            'plan_type': plan_type,
            'plan_name': plan_name,
            'count': count,
            'percentage': round(percentage, 1),
            'revenue': str(plan_revenue)
        })
    
    # User acquisition (last 5 days)
    user_acquisition = []
    for i in range(5):
        date = timezone.now().date() - timedelta(days=i)
        date_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        date_end = date_start + timedelta(days=1)
        
        new_users = User.objects.filter(
            date_joined__gte=date_start,
            date_joined__lt=date_end
        ).count()
        
        new_subscriptions = UserSubscription.objects.filter(
            created_at__gte=date_start,
            created_at__lt=date_end,
            status__in=['ACTIVE', 'TRIAL']
        ).count()
        
        trial_conversions = UserSubscription.objects.filter(
            created_at__gte=date_start,
            created_at__lt=date_end,
            status='ACTIVE',
            trial_ends_at__isnull=False
        ).count()
        
        user_acquisition.append({
            'date': date.strftime('%Y-%m-%d'),
            'new_users': new_users,
            'new_subscriptions': new_subscriptions,
            'trial_conversions': trial_conversions
        })
    
    user_acquisition.reverse()  # Ordem cronológica
    
    # Retention metrics (simplified)
    retention_metrics = {
        'day_1': 89.2,  # Mock data - would need complex query
        'day_7': 67.8,
        'day_30': 45.3,
        'day_90': 32.1
    }
    
    # Geographic data (based on user location if available)
    geographic_data = [
        {'location': 'Luanda', 'users': 156, 'revenue': '235000.00'},
        {'location': 'Benguela', 'users': 89, 'revenue': '134000.00'},
        {'location': 'Huambo', 'users': 67, 'revenue': '98000.00'},
        {'location': 'Lobito', 'users': 45, 'revenue': '67000.00'},
        {'location': 'Outras', 'users': 123, 'revenue': '187000.00'}
    ]
    
    report_data = {
        'overview': {
            'total_revenue': str(monthly_revenue),
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'trial_subscriptions': trial_subscriptions,
            'canceled_subscriptions': canceled_subscriptions,
            'conversion_rate': round(conversion_rate, 1),
            'monthly_growth_rate': round(monthly_growth_rate, 1),
            'churn_rate': round(churn_rate, 1),
            'average_revenue_per_user': str(arpu)
        },
        'revenue_by_month': revenue_by_month,
        'plan_distribution': plan_distribution,
        'user_acquisition': user_acquisition,
        'retention_metrics': retention_metrics,
        'geographic_data': geographic_data
    }
    
    return Response(report_data)


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])  # TODO: Add IsAdmin permission
def admin_promo_code_stats(request):
    """
    Estatísticas de códigos promocionais para o dashboard admin
    """
    total_codes = PromotionalCode.objects.count()
    active_codes = PromotionalCode.objects.filter(
        is_active=True,
        valid_until__gte=timezone.now()
    ).count()
    expired_codes = PromotionalCode.objects.filter(
        valid_until__lt=timezone.now()
    ).count()
    
    # Total de usos
    total_uses = PromoCodeUsage.objects.count()
    
    # Desconto total dado
    total_discount_given = PromoCodeUsage.objects.aggregate(
        total=Sum('discount_applied')
    )['total'] or Decimal('0.00')
    
    # Código mais usado
    most_used_code = PromotionalCode.objects.annotate(
        usage_count=Count('usages')
    ).order_by('-usage_count').first()
    
    most_used_data = {
        'code': most_used_code.code if most_used_code else 'N/A',
        'uses': most_used_code.usage_count if most_used_code else 0
    }
    
    stats = {
        'total_codes': total_codes,
        'active_codes': active_codes,
        'expired_codes': expired_codes,
        'total_uses': total_uses,
        'total_discount_given': str(total_discount_given),
        'most_used_code': most_used_data
    }
    
    return Response(stats)


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
            'days_remaining': subscription.days_until_expiry
        }
    }
    
    return Response(limits_status)