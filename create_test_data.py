#!/usr/bin/env python
"""
Script para criar dados de teste para o sistema de assinaturas
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from apps.subscriptions.models import (
    SubscriptionPlan, 
    UserSubscription, 
    PromotionalCode, 
    PromoCodeUsage,
    SubscriptionHistory
)
from django.contrib.auth import get_user_model

User = get_user_model()

def create_subscription_plans():
    """Criar planos de assinatura se não existirem"""
    plans_data = [
        {
            'name': 'Plano Gratuito',
            'plan_type': 'FREE',
            'description': 'Acesso básico ao ProEnglish com limitações',
            'monthly_price': Decimal('0.00'),
            'yearly_price': Decimal('0.00'),
            'daily_lessons_limit': 3,
            'daily_speaking_minutes': 10,
            'daily_listening_minutes': 15,
            'hearts_limit': 5,
            'hearts_recharge_hours': 4,
            'sort_order': 1,
        },
        {
            'name': 'Premium',
            'plan_type': 'PREMIUM',
            'description': 'Acesso completo ao ProEnglish com recursos avançados',
            'monthly_price': Decimal('25000.00'),  # 25,000 AOA
            'yearly_price': Decimal('250000.00'),  # 250,000 AOA (desconto de ~17%)
            'daily_lessons_limit': None,  # Ilimitado
            'daily_speaking_minutes': None,  # Ilimitado
            'daily_listening_minutes': None,  # Ilimitado
            'hearts_limit': 0,  # Vidas infinitas
            'hearts_recharge_hours': 0,
            'offline_downloads': True,
            'certificates': True,
            'ai_tutor': False,
            'advanced_analytics': True,
            'priority_support': True,
            'streak_freeze': 2,
            'multiple_devices': 2,
            'sort_order': 2,
        },
        {
            'name': 'Premium Plus',
            'plan_type': 'PREMIUM_PLUS',
            'description': 'Experiência premium completa com IA e professores nativos',
            'monthly_price': Decimal('45000.00'),  # 45,000 AOA
            'yearly_price': Decimal('450000.00'),  # 450,000 AOA (desconto de ~17%)
            'daily_lessons_limit': None,  # Ilimitado
            'daily_speaking_minutes': None,  # Ilimitado
            'daily_listening_minutes': None,  # Ilimitado
            'hearts_limit': 0,  # Vidas infinitas
            'hearts_recharge_hours': 0,
            'offline_downloads': True,
            'certificates': True,
            'ai_tutor': True,
            'native_teacher_sessions': 4,  # 4 sessões por mês
            'advanced_analytics': True,
            'priority_support': True,
            'streak_freeze': 5,
            'multiple_devices': 5,
            'sort_order': 3,
        }
    ]
    
    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type=plan_data['plan_type'],
            defaults=plan_data
        )
        if created:
            print(f"✅ Criado plano: {plan.name}")
        else:
            print(f"📋 Plano já existe: {plan.name}")

def create_promotional_codes():
    """Criar códigos promocionais de teste"""
    codes_data = [
        {
            'code': 'PROENGLISH20',
            'name': 'Desconto ProEnglish 20%',
            'description': 'Desconto de 20% para novos usuários',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('20.00'),
            'max_uses': 100,
            'valid_from': timezone.now() - timedelta(days=30),
            'valid_until': timezone.now() + timedelta(days=60),
            'first_time_users_only': True,
        },
        {
            'code': 'SAVE5000',
            'name': 'Desconto 5000 AOA',
            'description': 'Desconto fixo de 5000 Kuanzas',
            'discount_type': 'FIXED_AMOUNT',
            'discount_value': Decimal('5000.00'),
            'max_uses': 50,
            'valid_from': timezone.now() - timedelta(days=15),
            'valid_until': timezone.now() + timedelta(days=45),
            'first_time_users_only': False,
        },
        {
            'code': 'BLACKFRIDAY',
            'name': 'Black Friday 50%',
            'description': 'Mega desconto de Black Friday',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('50.00'),
            'max_uses': 200,
            'valid_from': timezone.now() - timedelta(days=5),
            'valid_until': timezone.now() + timedelta(days=15),
            'first_time_users_only': False,
        },
        {
            'code': 'EXPIRED10',
            'name': 'Código Expirado',
            'description': 'Código de teste expirado',
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('10.00'),
            'max_uses': 25,
            'valid_from': timezone.now() - timedelta(days=60),
            'valid_until': timezone.now() - timedelta(days=30),
            'first_time_users_only': False,
        }
    ]
    
    for code_data in codes_data:
        code, created = PromotionalCode.objects.get_or_create(
            code=code_data['code'],
            defaults=code_data
        )
        if created:
            print(f"✅ Criado código promocional: {code.code}")
        else:
            print(f"📋 Código já existe: {code.code}")

def create_test_subscriptions():
    """Criar assinaturas de teste para usuários existentes"""
    # Pegar alguns usuários para criar assinaturas
    users = User.objects.filter(role__in=['student', 'teacher'])[:10]
    plans = SubscriptionPlan.objects.all()
    
    if not users.exists():
        print("⚠️ Nenhum usuário encontrado para criar assinaturas")
        return
    
    for i, user in enumerate(users):
        # Criar assinatura se não existir
        if not hasattr(user, 'subscription'):
            # Distribuir planos: 60% Free, 30% Premium, 10% Premium Plus
            if i < 6:
                plan = plans.get(plan_type='FREE')
                status = 'ACTIVE'
                expires_at = timezone.now() + timedelta(days=365*10)  # 10 anos para free
            elif i < 9:
                plan = plans.get(plan_type='PREMIUM')
                status = 'ACTIVE'
                expires_at = timezone.now() + timedelta(days=30)
            else:
                plan = plans.get(plan_type='PREMIUM_PLUS')
                status = 'ACTIVE'
                expires_at = timezone.now() + timedelta(days=30)
            
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                status=status,
                expires_at=expires_at,
                started_at=timezone.now() - timedelta(days=i*3)  # Variação nas datas
            )
            
            # Criar histórico de pagamento para planos pagos
            if plan.plan_type != 'FREE':
                SubscriptionHistory.objects.create(
                    subscription=subscription,
                    event_type='CREATED',
                    new_plan=plan,
                    amount_paid=plan.monthly_price,
                    notes=f'Assinatura inicial do plano {plan.name}'
                )
            
            print(f"✅ Criada assinatura {plan.name} para {user.email}")

def create_promo_code_usage():
    """Criar alguns usos de códigos promocionais"""
    codes = PromotionalCode.objects.filter(is_active=True)
    subscriptions = UserSubscription.objects.filter(
        plan__plan_type__in=['PREMIUM', 'PREMIUM_PLUS']
    )[:5]
    
    for i, subscription in enumerate(subscriptions):
        if i < len(codes):
            code = codes[i]
            
            # Criar uso do código se não existir
            usage, created = PromoCodeUsage.objects.get_or_create(
                user=subscription.user,
                promo_code=code,
                subscription=subscription,
                defaults={
                    'discount_applied': Decimal('5000.00'),
                    'used_at': timezone.now() - timedelta(days=i*5)
                }
            )
            
            if created:
                # Incrementar contador de uso
                code.current_uses += 1
                code.save()
                print(f"✅ Criado uso do código {code.code} por {subscription.user.email}")

def main():
    print("🚀 Criando dados de teste para o sistema de assinaturas...")
    
    try:
        create_subscription_plans()
        print()
        
        create_promotional_codes()
        print()
        
        create_test_subscriptions()
        print()
        
        create_promo_code_usage()
        print()
        
        print("✨ Dados de teste criados com sucesso!")
        
        # Resumo
        print("\n📊 RESUMO:")
        print(f"📋 Planos: {SubscriptionPlan.objects.count()}")
        print(f"🎟️ Códigos promocionais: {PromotionalCode.objects.count()}")
        print(f"👥 Assinaturas: {UserSubscription.objects.count()}")
        print(f"💰 Histórico de pagamentos: {SubscriptionHistory.objects.count()}")
        print(f"🏷️ Usos de códigos: {PromoCodeUsage.objects.count()}")
        
    except Exception as e:
        print(f"❌ Erro ao criar dados de teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()