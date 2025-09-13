"""
Subscription Utils - Utilitários para sistema de assinaturas

Funções auxiliares para verificar limitações, cálculos de preços,
e outras operações relacionadas às assinaturas.
"""

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import UserSubscription, SubscriptionPlan, PromotionalCode


def get_user_subscription(user):
    """
    Obtém ou cria a assinatura do usuário
    
    Args:
        user: Instance do usuário Django
        
    Returns:
        UserSubscription: Assinatura do usuário
    """
    subscription, created = UserSubscription.objects.get_or_create(
        user=user,
        defaults={
            'plan': SubscriptionPlan.objects.get(plan_type='FREE'),
            'status': 'ACTIVE'
        }
    )
    
    if created:
        # Configurar expiração para plano gratuito (10 anos)
        subscription.expires_at = timezone.now() + timedelta(days=365*10)
        subscription.save()
    
    return subscription


def check_subscription_limits(user, feature_type='general', amount=1):
    """
    Verifica se o usuário pode usar uma funcionalidade
    
    Args:
        user: Usuário Django
        feature_type: Tipo de funcionalidade ('lesson', 'speaking', 'listening', 'hearts')
        amount: Quantidade necessária (default: 1)
        
    Returns:
        dict: {
            'allowed': bool,
            'error_message': str,
            'current_usage': int,
            'limit': int,
            'subscription': UserSubscription
        }
    """
    subscription = get_user_subscription(user)
    
    # Resetar contadores se necessário
    subscription.reset_daily_usage_if_needed()
    
    # Verificar se assinatura está ativa
    if not subscription.is_active():
        return {
            'allowed': False,
            'error_message': 'Sua assinatura expirou',
            'subscription': subscription,
            'upgrade_required': True
        }
    
    result = {
        'allowed': True,
        'subscription': subscription,
        'upgrade_required': False
    }
    
    # Verificar limitações específicas
    if feature_type == 'lesson':
        can_use = subscription.can_take_lesson()
        if not can_use:
            result.update({
                'allowed': False,
                'error_message': f'Limite diário de lições atingido ({subscription.plan.daily_lessons_limit})',
                'current_usage': subscription.daily_lessons_used,
                'limit': subscription.plan.daily_lessons_limit,
                'upgrade_required': True
            })
    
    elif feature_type == 'speaking':
        if subscription.daily_speaking_minutes_used + amount > subscription.plan.daily_speaking_minutes:
            result.update({
                'allowed': False,
                'error_message': f'Limite diário de Speaking atingido ({subscription.plan.daily_speaking_minutes} min)',
                'current_usage': subscription.daily_speaking_minutes_used,
                'limit': subscription.plan.daily_speaking_minutes,
                'upgrade_required': True
            })
        else:
            result.update({
                'current_usage': subscription.daily_speaking_minutes_used,
                'limit': subscription.plan.daily_speaking_minutes
            })
    
    elif feature_type == 'listening':
        if subscription.daily_listening_minutes_used + amount > subscription.plan.daily_listening_minutes:
            result.update({
                'allowed': False,
                'error_message': f'Limite diário de Listening atingido ({subscription.plan.daily_listening_minutes} min)',
                'current_usage': subscription.daily_listening_minutes_used,
                'limit': subscription.plan.daily_listening_minutes,
                'upgrade_required': True
            })
        else:
            result.update({
                'current_usage': subscription.daily_listening_minutes_used,
                'limit': subscription.plan.daily_listening_minutes
            })
    
    elif feature_type == 'hearts':
        # Recarregar vidas se necessário
        subscription.recharge_hearts_if_needed()
        
        if subscription.current_hearts < amount:
            result.update({
                'allowed': False,
                'error_message': 'Você não tem vidas suficientes',
                'current_usage': subscription.current_hearts,
                'limit': subscription.plan.hearts_limit,
                'upgrade_required': True
            })
        else:
            result.update({
                'current_usage': subscription.current_hearts,
                'limit': subscription.plan.hearts_limit
            })
    
    return result


def consume_subscription_resource(user, feature_type, amount=1):
    """
    Consome recursos da assinatura do usuário
    
    Args:
        user: Usuário Django
        feature_type: Tipo ('lesson', 'speaking_minutes', 'listening_minutes', 'hearts')
        amount: Quantidade a consumir
        
    Returns:
        bool: True se consumiu com sucesso
    """
    subscription = get_user_subscription(user)
    
    try:
        if feature_type == 'lesson':
            subscription.daily_lessons_used += amount
        elif feature_type == 'speaking_minutes':
            subscription.daily_speaking_minutes_used += amount
        elif feature_type == 'listening_minutes':
            subscription.daily_listening_minutes_used += amount
        elif feature_type == 'hearts':
            subscription.current_hearts = max(0, subscription.current_hearts - amount)
        
        subscription.save()
        return True
        
    except Exception:
        return False


def calculate_upgrade_price(user, new_plan_id, billing_cycle='MONTHLY', promo_code=None):
    """
    Calcula o preço de upgrade considerando descontos e promoções
    
    Args:
        user: Usuário Django
        new_plan_id: UUID do novo plano
        billing_cycle: 'MONTHLY' ou 'YEARLY'
        promo_code: Código promocional (opcional)
        
    Returns:
        dict: Dados do cálculo de preço
    """
    try:
        new_plan = SubscriptionPlan.objects.get(id=new_plan_id, is_active=True)
        subscription = get_user_subscription(user)
        
        # Preço base
        if billing_cycle == 'YEARLY' and new_plan.yearly_price:
            base_price = new_plan.yearly_price
        else:
            base_price = new_plan.monthly_price
        
        result = {
            'new_plan': new_plan.name,
            'billing_cycle': billing_cycle,
            'base_price': base_price,
            'discount_applied': Decimal('0.00'),
            'final_price': base_price,
            'promo_code_valid': False,
            'promo_code_error': None
        }
        
        # Aplicar código promocional se fornecido
        if promo_code:
            try:
                promo = PromotionalCode.objects.get(code=promo_code.upper())
                
                # Verificar se é válido
                if not promo.is_valid():
                    result['promo_code_error'] = 'Código promocional expirado ou esgotado'
                else:
                    # Verificar se usuário já usou
                    from .models import PromoCodeUsage
                    if PromoCodeUsage.objects.filter(user=user, promo_code=promo).exists():
                        result['promo_code_error'] = 'Código já utilizado por este usuário'
                    else:
                        # Calcular desconto
                        if promo.discount_type == 'PERCENTAGE':
                            discount = (base_price * promo.discount_value) / 100
                        else:  # FIXED_AMOUNT
                            discount = min(promo.discount_value, base_price)
                        
                        result.update({
                            'discount_applied': discount,
                            'final_price': base_price - discount,
                            'promo_code_valid': True,
                            'promo_code_name': promo.name
                        })
                        
            except PromotionalCode.DoesNotExist:
                result['promo_code_error'] = 'Código promocional não encontrado'
        
        return result
        
    except SubscriptionPlan.DoesNotExist:
        return {
            'error': 'Plano não encontrado'
        }


def get_subscription_analytics(user):
    """
    Retorna analytics da assinatura do usuário
    
    Args:
        user: Usuário Django
        
    Returns:
        dict: Dados analytics
    """
    subscription = get_user_subscription(user)
    subscription.reset_daily_usage_if_needed()
    subscription.recharge_hearts_if_needed()
    
    plan = subscription.plan
    
    # Cálculos de uso
    lesson_usage_pct = 0
    if plan.daily_lessons_limit > 0:
        lesson_usage_pct = (subscription.daily_lessons_used / plan.daily_lessons_limit) * 100
    
    speaking_usage_pct = 0
    if plan.daily_speaking_minutes > 0:
        speaking_usage_pct = (subscription.daily_speaking_minutes_used / plan.daily_speaking_minutes) * 100
    
    listening_usage_pct = 0
    if plan.daily_listening_minutes > 0:
        listening_usage_pct = (subscription.daily_listening_minutes_used / plan.daily_listening_minutes) * 100
    
    hearts_pct = 0
    if plan.hearts_limit > 0:
        hearts_pct = (subscription.current_hearts / plan.hearts_limit) * 100
    
    return {
        'subscription': {
            'plan_name': plan.name,
            'plan_type': plan.plan_type,
            'status': subscription.status,
            'expires_at': subscription.expires_at,
            'days_remaining': subscription.days_until_expiry,
            'is_trial': subscription.is_trial(),
            'is_active': subscription.is_active()
        },
        'usage': {
            'lessons': {
                'used': subscription.daily_lessons_used,
                'limit': plan.daily_lessons_limit,
                'unlimited': plan.daily_lessons_limit == 0,
                'percentage': min(100, lesson_usage_pct),
                'can_use': subscription.can_take_lesson()
            },
            'speaking': {
                'used': subscription.daily_speaking_minutes_used,
                'limit': plan.daily_speaking_minutes,
                'unlimited': plan.daily_speaking_minutes == 0,
                'percentage': min(100, speaking_usage_pct),
                'can_use': subscription.can_use_speaking()
            },
            'listening': {
                'used': subscription.daily_listening_minutes_used,
                'limit': plan.daily_listening_minutes,
                'unlimited': plan.daily_listening_minutes == 0,
                'percentage': min(100, listening_usage_pct),
                'can_use': subscription.can_use_listening()
            },
            'hearts': {
                'current': subscription.current_hearts,
                'limit': plan.hearts_limit,
                'unlimited': plan.hearts_limit == 0,
                'percentage': hearts_pct if plan.hearts_limit > 0 else 100,
                'recharge_hours': plan.hearts_recharge_hours,
                'last_recharge': subscription.last_heart_recharge
            }
        },
        'features': {
            'offline_downloads': plan.offline_downloads,
            'certificates': plan.certificates,
            'ai_tutor': plan.ai_tutor,
            'native_teacher_sessions': plan.native_teacher_sessions,
            'advanced_analytics': plan.advanced_analytics,
            'priority_support': plan.priority_support,
            'streak_freeze': plan.streak_freeze,
            'multiple_devices': plan.multiple_devices
        }
    }


def check_premium_feature(user, feature_name):
    """
    Verifica se o usuário tem acesso a uma funcionalidade premium
    
    Args:
        user: Usuário Django
        feature_name: Nome da funcionalidade
        
    Returns:
        bool: True se tem acesso
    """
    subscription = get_user_subscription(user)
    plan = subscription.plan
    
    if not subscription.is_active():
        return False
    
    feature_mapping = {
        'offline_downloads': plan.offline_downloads,
        'certificates': plan.certificates,
        'ai_tutor': plan.ai_tutor,
        'native_teacher_sessions': plan.native_teacher_sessions > 0,
        'advanced_analytics': plan.advanced_analytics,
        'priority_support': plan.priority_support,
        'streak_freeze': plan.streak_freeze > 0,
        'multiple_devices': plan.multiple_devices > 1
    }
    
    return feature_mapping.get(feature_name, False)