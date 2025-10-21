"""
Subscription Plan Decorators - Sistema de limitações

Decoradores para verificar e aplicar limitações dos planos de assinatura
em views e funcionalidades da plataforma.
"""

from functools import wraps
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required
from .models import UserSubscription, SubscriptionPlan


def subscription_required(feature_type='general', amount=1):
    """
    Decorator para verificar se o usuário tem permissão para usar uma funcionalidade
    
    Args:
        feature_type: Tipo de funcionalidade ('lesson', 'speaking', 'listening', 'hearts')
        amount: Quantidade necessária (para speaking/listening = minutos, hearts = vidas)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response({
                    'error': 'Autenticação necessária'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Obter ou criar assinatura
            subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': SubscriptionPlan.objects.get(plan_type='FREE'),
                    'status': 'ACTIVE'
                }
            )
            
            # Verificar se a assinatura está ativa
            if not subscription.is_active():
                return Response({
                    'error': 'Sua assinatura expirou',
                    'upgrade_required': True,
                    'subscription_status': subscription.status
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # Resetar contadores diários se necessário
            subscription.reset_daily_usage_if_needed()
            
            # Verificar limitações específicas por tipo de recurso
            if feature_type == 'lesson':
                if not subscription.can_take_lesson():
                    return Response({
                        'error': f'Limite diário de lições atingido ({subscription.plan.daily_lessons_limit})',
                        'upgrade_required': True,
                        'current_usage': subscription.daily_lessons_used,
                        'limit': subscription.plan.daily_lessons_limit,
                        'feature_type': 'lesson'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            elif feature_type == 'speaking':
                if not subscription.can_use_speaking(amount):
                    return Response({
                        'error': f'Limite diário de Speaking atingido ({subscription.plan.daily_speaking_minutes} min)',
                        'upgrade_required': True,
                        'current_usage': subscription.daily_speaking_minutes_used,
                        'limit': subscription.plan.daily_speaking_minutes,
                        'feature_type': 'speaking'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            elif feature_type == 'listening':
                if not subscription.can_use_listening(amount):
                    return Response({
                        'error': f'Limite diário de Listening atingido ({subscription.plan.daily_listening_minutes} min)',
                        'upgrade_required': True,
                        'current_usage': subscription.daily_listening_minutes_used,
                        'limit': subscription.plan.daily_listening_minutes,
                        'feature_type': 'listening'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            elif feature_type == 'hearts':
                # Recarregar vidas se necessário
                subscription.recharge_hearts_if_needed()
                
                if subscription.current_hearts < amount:
                    return Response({
                        'error': 'Você não tem vidas suficientes',
                        'upgrade_required': True,
                        'current_hearts': subscription.current_hearts,
                        'max_hearts': subscription.plan.hearts_limit,
                        'recharge_hours': subscription.plan.hearts_recharge_hours,
                        'feature_type': 'hearts'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Anexar subscription ao request para uso posterior
            request.user_subscription = subscription
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def premium_required():
    """
    Decorator para funcionalidades que requerem plano Premium ou superior
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response({
                    'error': 'Autenticação necessária'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Obter assinatura
            try:
                subscription = UserSubscription.objects.get(user=user)
            except UserSubscription.DoesNotExist:
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=SubscriptionPlan.objects.get(plan_type='FREE'),
                    status='ACTIVE'
                )
            
            # Verificar se tem plano Premium ou superior
            if subscription.plan.plan_type == 'FREE':
                return Response({
                    'error': 'Esta funcionalidade requer plano Premium ou superior',
                    'upgrade_required': True,
                    'current_plan': subscription.plan.plan_type,
                    'required_plan': 'PREMIUM'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # Verificar se a assinatura está ativa
            if not subscription.is_active():
                return Response({
                    'error': 'Sua assinatura expirou',
                    'upgrade_required': True,
                    'subscription_status': subscription.status
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            request.user_subscription = subscription
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def premium_plus_required():
    """
    Decorator para funcionalidades exclusivas do Premium Plus
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response({
                    'error': 'Autenticação necessária'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Obter assinatura
            try:
                subscription = UserSubscription.objects.get(user=user)
            except UserSubscription.DoesNotExist:
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=SubscriptionPlan.objects.get(plan_type='FREE'),
                    status='ACTIVE'
                )
            
            # Verificar se tem plano Premium Plus
            if subscription.plan.plan_type != 'PREMIUM_PLUS':
                return Response({
                    'error': 'Esta funcionalidade requer plano Premium Plus',
                    'upgrade_required': True,
                    'current_plan': subscription.plan.plan_type,
                    'required_plan': 'PREMIUM_PLUS'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # Verificar se a assinatura está ativa
            if not subscription.is_active():
                return Response({
                    'error': 'Sua assinatura expirou',
                    'upgrade_required': True,
                    'subscription_status': subscription.status
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            request.user_subscription = subscription
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def track_usage(feature_type, amount=1):
    """
    Decorator para rastrear o uso de funcionalidades
    
    Args:
        feature_type: Tipo ('lesson', 'speaking_minutes', 'listening_minutes', 'hearts')
        amount: Quantidade a ser consumida (default: 1)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Executar a view primeiro
            response = view_func(request, *args, **kwargs)
            
            # Se a view foi bem sucedida, rastrear o uso
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                # Obter subscription do request se anexada, senão buscar no DB
                if hasattr(request, 'user_subscription'):
                    subscription = request.user_subscription
                elif request.user.is_authenticated:
                    # Obter ou criar assinatura se não anexada ao request
                    subscription, created = UserSubscription.objects.get_or_create(
                        user=request.user,
                        defaults={
                            'plan': SubscriptionPlan.objects.get(plan_type='FREE'),
                            'status': 'ACTIVE'
                        }
                    )
                else:
                    subscription = None
                
                if subscription:
                    if feature_type == 'lesson':
                        subscription.daily_lessons_used += amount
                    elif feature_type == 'speaking_minutes':
                        subscription.daily_speaking_minutes_used += amount
                    elif feature_type == 'listening_minutes':
                        subscription.daily_listening_minutes_used += amount
                    elif feature_type == 'hearts':
                        subscription.current_hearts = max(0, subscription.current_hearts - amount)
                    
                    subscription.save()
            
            return response
        
        return wrapper
    return decorator


# Combinação comum de decoradores
def lesson_required():
    """Combina verificação de assinatura + rastreamento para lições"""
    def decorator(view_func):
        @subscription_required('lesson')
        @track_usage('lesson')
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def speaking_required(minutes=1):
    """Combina verificação + rastreamento para Speaking Practice"""
    def decorator(view_func):
        @subscription_required('speaking', minutes)
        @track_usage('speaking_minutes', minutes)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def listening_required(minutes=1):
    """Combina verificação + rastreamento para Listening Practice"""
    def decorator(view_func):
        @subscription_required('listening', minutes)
        @track_usage('listening_minutes', minutes)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def hearts_required(hearts=1):
    """Combina verificação + rastreamento para sistema de vidas"""
    def decorator(view_func):
        @subscription_required('hearts', hearts)
        @track_usage('hearts', hearts)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator