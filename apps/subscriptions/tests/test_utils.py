"""
Testes para utilitários do sistema de assinaturas.

Testa funções auxiliares como verificação de limites,
cálculos de preços, analytics e verificação de funcionalidades premium.
"""

from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import SubscriptionPlan, UserSubscription, PromotionalCode, PromoCodeUsage
from ..utils import (
    get_user_subscription, check_subscription_limits, consume_subscription_resource,
    calculate_upgrade_price, get_subscription_analytics, check_premium_feature
)

User = get_user_model()


class GetUserSubscriptionTest(TestCase):
    """Testes para get_user_subscription."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        # Usar plano existente
        self.free_plan = SubscriptionPlan.objects.get(plan_type="FREE")
    
    def test_get_existing_subscription(self):
        """Testa obtenção de assinatura existente."""
        existing_subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        subscription = get_user_subscription(self.user)
        
        self.assertEqual(subscription, existing_subscription)
    
    def test_create_new_subscription(self):
        """Testa criação de nova assinatura."""
        # Verificar que não existe
        self.assertFalse(UserSubscription.objects.filter(user=self.user).exists())
        
        subscription = get_user_subscription(self.user)
        
        # Verificar que foi criada
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())
        self.assertEqual(subscription.plan.plan_type, 'FREE')
        self.assertEqual(subscription.status, 'ACTIVE')


class CheckSubscriptionLimitsTest(TestCase):
    """Testes para check_subscription_limits."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        # Usar planos existentes
        self.free_plan = SubscriptionPlan.objects.get(plan_type="FREE")
        self.premium_plan = SubscriptionPlan.objects.get(plan_type="PREMIUM")
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
    
    def test_check_lesson_allowed(self):
        """Testa verificação de lições permitidas."""
        self.subscription.daily_lessons_used = 2  # 2 de 3
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'lesson')
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['current_usage'], 2)
        self.assertEqual(result['limit'], 3)
        self.assertFalse(result['upgrade_required'])
    
    def test_check_lesson_denied(self):
        """Testa verificação de lições negadas (limite atingido)."""
        self.subscription.daily_lessons_used = 3  # 3 de 3
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'lesson')
        
        self.assertFalse(result['allowed'])
        self.assertIn('error_message', result)
        self.assertTrue(result['upgrade_required'])
        self.assertEqual(result['current_usage'], 3)
        self.assertEqual(result['limit'], 3)
    
    def test_check_speaking_allowed(self):
        """Testa verificação de Speaking Practice permitido."""
        self.subscription.daily_speaking_minutes_used = 5  # 5 de 10
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'speaking', 3)  # Quer usar 3 min
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['current_usage'], 5)
        self.assertEqual(result['limit'], 10)
    
    def test_check_speaking_denied(self):
        """Testa verificação de Speaking Practice negado."""
        self.subscription.daily_speaking_minutes_used = 8  # 8 de 10
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'speaking', 5)  # Quer usar 5 min (total seria 13)
        
        self.assertFalse(result['allowed'])
        self.assertIn('Speaking', result['error_message'])
        self.assertTrue(result['upgrade_required'])
    
    def test_check_listening_unlimited(self):
        """Testa verificação de Listening Practice ilimitado."""
        # Mudar para plano premium
        self.subscription.plan = self.premium_plan
        self.subscription.daily_listening_minutes_used = 100
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'listening', 50)
        
        self.assertTrue(result['allowed'])
        self.assertFalse(result['upgrade_required'])
    
    def test_check_hearts_allowed(self):
        """Testa verificação de vidas permitidas."""
        self.subscription.current_hearts = 3
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'hearts', 2)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['current_usage'], 3)
        self.assertEqual(result['limit'], 5)
    
    def test_check_hearts_denied(self):
        """Testa verificação de vidas negadas."""
        self.subscription.current_hearts = 1
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'hearts', 2)  # Quer usar 2 mas só tem 1
        
        self.assertFalse(result['allowed'])
        self.assertIn('vidas', result['error_message'])
        self.assertTrue(result['upgrade_required'])
    
    def test_check_expired_subscription(self):
        """Testa verificação com assinatura expirada."""
        self.subscription.expires_at = timezone.now() - timedelta(days=1)
        self.subscription.save()
        
        result = check_subscription_limits(self.user, 'lesson')
        
        self.assertFalse(result['allowed'])
        self.assertIn('expirou', result['error_message'])
        self.assertTrue(result['upgrade_required'])


class ConsumeSubscriptionResourceTest(TestCase):
    """Testes para consume_subscription_resource."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="FREE",
            defaults={
                "name": "Free",
                "description": "Free plan",
                "monthly_price": Decimal('0.00'),
                "daily_lessons_limit": 3
            }
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
    
    def test_consume_lesson(self):
        """Testa consumo de lição."""
        initial_usage = self.subscription.daily_lessons_used
        
        success = consume_subscription_resource(self.user, 'lesson', 1)
        
        self.assertTrue(success)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.daily_lessons_used, initial_usage + 1)
    
    def test_consume_speaking_minutes(self):
        """Testa consumo de minutos de Speaking."""
        initial_usage = self.subscription.daily_speaking_minutes_used
        
        success = consume_subscription_resource(self.user, 'speaking_minutes', 5)
        
        self.assertTrue(success)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.daily_speaking_minutes_used, initial_usage + 5)
    
    def test_consume_listening_minutes(self):
        """Testa consumo de minutos de Listening."""
        initial_usage = self.subscription.daily_listening_minutes_used
        
        success = consume_subscription_resource(self.user, 'listening_minutes', 3)
        
        self.assertTrue(success)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.daily_listening_minutes_used, initial_usage + 3)
    
    def test_consume_hearts(self):
        """Testa consumo de vidas."""
        initial_hearts = self.subscription.current_hearts
        
        success = consume_subscription_resource(self.user, 'hearts', 2)
        
        self.assertTrue(success)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.current_hearts, initial_hearts - 2)
    
    def test_consume_hearts_minimum_zero(self):
        """Testa que vidas não ficam negativas."""
        self.subscription.current_hearts = 1
        self.subscription.save()
        
        success = consume_subscription_resource(self.user, 'hearts', 3)
        
        self.assertTrue(success)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.current_hearts, 0)  # Não fica negativo


class CalculateUpgradePriceTest(TestCase):
    """Testes para calculate_upgrade_price."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2000.00'),
                "yearly_price": Decimal('20000.00'),
                "is_active": True
            }
        )
        
        self.promo_percentage = PromotionalCode.objects.create(
            code="SAVE20",
            name="Desconto 20%",
            description="20% off",
            discount_type="PERCENTAGE",
            discount_value=Decimal('20.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30)
        )
        
        self.promo_fixed = PromotionalCode.objects.create(
            code="SAVE500",
            name="Desconto 500 Kz",
            description="500 Kz off",
            discount_type="FIXED_AMOUNT",
            discount_value=Decimal('500.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30)
        )
    
    def test_calculate_monthly_price(self):
        """Testa cálculo de preço mensal."""
        result = calculate_upgrade_price(self.user, self.premium_plan.id, 'MONTHLY')
        
        self.assertEqual(result['base_price'], Decimal('2000.00'))
        self.assertEqual(result['final_price'], Decimal('2000.00'))
        self.assertEqual(result['discount_applied'], Decimal('0.00'))
        self.assertEqual(result['billing_cycle'], 'MONTHLY')
        self.assertFalse(result['promo_code_valid'])
    
    def test_calculate_yearly_price(self):
        """Testa cálculo de preço anual."""
        result = calculate_upgrade_price(self.user, self.premium_plan.id, 'YEARLY')
        
        self.assertEqual(result['base_price'], Decimal('20000.00'))
        self.assertEqual(result['final_price'], Decimal('20000.00'))
        self.assertEqual(result['billing_cycle'], 'YEARLY')
    
    def test_calculate_with_percentage_promo(self):
        """Testa cálculo com código de desconto percentual."""
        result = calculate_upgrade_price(
            self.user, 
            self.premium_plan.id, 
            'MONTHLY', 
            'SAVE20'
        )
        
        self.assertEqual(result['base_price'], Decimal('2000.00'))
        self.assertEqual(result['discount_applied'], Decimal('400.00'))  # 20% de 2000
        self.assertEqual(result['final_price'], Decimal('1600.00'))
        self.assertTrue(result['promo_code_valid'])
        self.assertEqual(result['promo_code_name'], "Desconto 20%")
    
    def test_calculate_with_fixed_promo(self):
        """Testa cálculo com código de desconto fixo."""
        result = calculate_upgrade_price(
            self.user, 
            self.premium_plan.id, 
            'MONTHLY', 
            'SAVE500'
        )
        
        self.assertEqual(result['base_price'], Decimal('2000.00'))
        self.assertEqual(result['discount_applied'], Decimal('500.00'))
        self.assertEqual(result['final_price'], Decimal('1500.00'))
        self.assertTrue(result['promo_code_valid'])
    
    def test_calculate_with_invalid_promo(self):
        """Testa cálculo com código inválido."""
        result = calculate_upgrade_price(
            self.user, 
            self.premium_plan.id, 
            'MONTHLY', 
            'INVALID'
        )
        
        self.assertEqual(result['final_price'], Decimal('2000.00'))  # Preço original
        self.assertFalse(result['promo_code_valid'])
        self.assertIn('não encontrado', result['promo_code_error'])
    
    def test_calculate_with_expired_promo(self):
        """Testa cálculo com código expirado."""
        expired_promo = PromotionalCode.objects.create(
            code="EXPIRED",
            name="Expirado",
            description="Expired",
            discount_type="PERCENTAGE",
            discount_value=Decimal('10.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=30),
            valid_until=timezone.now() - timedelta(days=1)
        )
        
        result = calculate_upgrade_price(
            self.user, 
            self.premium_plan.id, 
            'MONTHLY', 
            'EXPIRED'
        )
        
        self.assertEqual(result['final_price'], Decimal('2000.00'))
        self.assertFalse(result['promo_code_valid'])
        self.assertIn('expirado', result['promo_code_error'])
    
    def test_calculate_with_used_promo(self):
        """Testa cálculo com código já usado."""
        # Marcar como usado
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_plan,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        PromoCodeUsage.objects.create(
            user=self.user,
            promo_code=self.promo_percentage,
            subscription=subscription,
            discount_applied=Decimal('400.00')
        )
        
        result = calculate_upgrade_price(
            self.user, 
            self.premium_plan.id, 
            'MONTHLY', 
            'SAVE20'
        )
        
        self.assertEqual(result['final_price'], Decimal('2000.00'))
        self.assertFalse(result['promo_code_valid'])
        self.assertIn('já utilizado', result['promo_code_error'])
    
    def test_calculate_invalid_plan(self):
        """Testa cálculo com plano inválido."""
        import uuid
        invalid_id = uuid.uuid4()
        
        result = calculate_upgrade_price(self.user, invalid_id, 'MONTHLY')
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Plano não encontrado')


class GetSubscriptionAnalyticsTest(TestCase):
    """Testes para get_subscription_analytics."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2000.00'),
                "daily_lessons_limit": None,  # Ilimitado
                "daily_speaking_minutes": None,
                "daily_listening_minutes": None,
                "hearts_limit": 0,  # Ilimitado
                "offline_downloads": True,
                "certificates": True,
                "ai_tutor": False,
                "advanced_analytics": True
            }
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
    
    def test_analytics_structure(self):
        """Testa estrutura dos analytics."""
        analytics = get_subscription_analytics(self.user)
        
        # Verificar estrutura principal
        self.assertIn('subscription', analytics)
        self.assertIn('usage', analytics)
        self.assertIn('features', analytics)
        
        # Verificar dados da assinatura
        subscription = analytics['subscription']
        self.assertEqual(subscription['plan_type'], 'PREMIUM')
        self.assertTrue(subscription['is_active'])
        self.assertFalse(subscription['is_trial'])
        
        # Verificar uso
        usage = analytics['usage']
        self.assertIn('lessons', usage)
        self.assertIn('speaking', usage)
        self.assertIn('listening', usage)
        self.assertIn('hearts', usage)
        
        # Verificar funcionalidades
        features = analytics['features']
        self.assertTrue(features['offline_downloads'])
        self.assertTrue(features['certificates'])
        self.assertFalse(features['ai_tutor'])
        self.assertTrue(features['advanced_analytics'])
    
    def test_analytics_unlimited_features(self):
        """Testa analytics para funcionalidades ilimitadas."""
        analytics = get_subscription_analytics(self.user)
        
        usage = analytics['usage']
        
        # Lições ilimitadas
        lessons = usage['lessons']
        self.assertTrue(lessons['unlimited'])
        self.assertIsNone(lessons['limit'])
        self.assertTrue(lessons['can_use'])
        
        # Speaking ilimitado
        speaking = usage['speaking']
        self.assertTrue(speaking['unlimited'])
        self.assertIsNone(speaking['limit'])
        self.assertTrue(speaking['can_use'])
        
        # Vidas ilimitadas
        hearts = usage['hearts']
        self.assertTrue(hearts['unlimited'])
        self.assertEqual(hearts['limit'], 0)


class CheckPremiumFeatureTest(TestCase):
    """Testes para check_premium_feature."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="FREE",
            defaults={
                "name": "Free",
                "description": "Free plan",
                "monthly_price": Decimal('0.00'),
                "offline_downloads": False,
                "certificates": False,
                "ai_tutor": False,
                "native_teacher_sessions": 0
            }
        )
        
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2000.00'),
                "offline_downloads": True,
                "certificates": True,
                "ai_tutor": False,
                "native_teacher_sessions": 2,
                "multiple_devices": 3
            }
        )
    
    def test_free_plan_features(self):
        """Testa funcionalidades do plano gratuito."""
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        # Funcionalidades que o free não tem
        self.assertFalse(check_premium_feature(self.user, 'offline_downloads'))
        self.assertFalse(check_premium_feature(self.user, 'certificates'))
        self.assertFalse(check_premium_feature(self.user, 'ai_tutor'))
        self.assertFalse(check_premium_feature(self.user, 'native_teacher_sessions'))
        self.assertFalse(check_premium_feature(self.user, 'multiple_devices'))
    
    def test_premium_plan_features(self):
        """Testa funcionalidades do plano premium."""
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        # Funcionalidades que o premium tem
        self.assertTrue(check_premium_feature(self.user, 'offline_downloads'))
        self.assertTrue(check_premium_feature(self.user, 'certificates'))
        self.assertTrue(check_premium_feature(self.user, 'native_teacher_sessions'))
        self.assertTrue(check_premium_feature(self.user, 'multiple_devices'))
        
        # Funcionalidades que ainda não tem
        self.assertFalse(check_premium_feature(self.user, 'ai_tutor'))
    
    def test_expired_subscription_features(self):
        """Testa funcionalidades com assinatura expirada."""
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_plan,
            expires_at=timezone.now() - timedelta(days=1),  # Expirada
            status='ACTIVE'
        )
        
        # Não deve ter acesso a funcionalidades premium
        self.assertFalse(check_premium_feature(self.user, 'offline_downloads'))
        self.assertFalse(check_premium_feature(self.user, 'certificates'))
    
    def test_unknown_feature(self):
        """Testa funcionalidade desconhecida."""
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        # Funcionalidade que não existe
        self.assertFalse(check_premium_feature(self.user, 'unknown_feature'))