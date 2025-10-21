"""
Testes para views do sistema de assinaturas.

Testa endpoints públicos, de usuário e administrativos,
incluindo upgrade de planos, códigos promocionais e analytics.
"""

from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status

from ..models import (
    SubscriptionPlan, UserSubscription, SubscriptionHistory,
    PromotionalCode, PromoCodeUsage
)

User = get_user_model()


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class PublicSubscriptionPlansTest(APITestCase):
    """Testes para endpoints públicos de planos."""
    
    def setUp(self):
        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="FREE",
            defaults={
                "name": "Plano Gratuito",
                "description": "Plano básico gratuito",
                "monthly_price": Decimal('0.00'),
                "yearly_price": Decimal('0.00'),
                "daily_lessons_limit": 3,
                "is_active": True,
                "sort_order": 1
            }
        )
        
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Plano Premium",
                "description": "Plano premium",
                "monthly_price": Decimal('2500.00'),
                "yearly_price": Decimal('149500.00'),
                "daily_lessons_limit": None,
                "is_active": True,
                "sort_order": 2
            }
        )
        
        self.inactive_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM_PLUS",
            defaults={
                "name": "Plano Inativo",
                "description": "Plano inativo",
                "monthly_price": Decimal('3000.00'),
                "is_active": False,
                "sort_order": 3
            }
        )
        
        self.public_plans_url = reverse('subscriptions:public-plans-list')
    
    def test_public_plans_list_success(self):
        """Testa listagem pública de planos."""
        response = self.client.get(self.public_plans_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 2)  # Apenas planos ativos
        
        # Verificar dados do primeiro plano
        first_plan = results[0]
        self.assertEqual(first_plan['name'], "Plano Gratuito")
        self.assertEqual(first_plan['plan_type'], "FREE")
        self.assertIn('features', first_plan)
        self.assertIn('yearly_discount_percentage', first_plan)
    
    def test_public_plans_only_active(self):
        """Testa que apenas planos ativos são retornados."""
        response = self.client.get(self.public_plans_url)
        
        results = response.data['results'] if 'results' in response.data else response.data
        plan_names = [plan['name'] for plan in results]
        self.assertIn("Plano Gratuito", plan_names)
        self.assertIn("Plano Premium", plan_names)
        self.assertNotIn("Plano Inativo", plan_names)
    
    def test_public_plans_no_authentication_required(self):
        """Testa que não é necessária autenticação."""
        # Sem autenticação
        response = self.client.get(self.public_plans_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class UserSubscriptionViewTest(APITestCase):
    """Testes para endpoint de assinatura do usuário."""
    
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
                "daily_lessons_limit": 3
            }
        )
        
        self.subscription_url = reverse('subscriptions:user-subscription')
    
    def test_user_subscription_authenticated(self):
        """Testa acesso autenticado à assinatura."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.subscription_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan']['plan_type'], 'FREE')
        self.assertIn('daily_usage', response.data)
        self.assertIn('hearts_status', response.data)
    
    def test_user_subscription_unauthenticated(self):
        """Testa acesso não autenticado."""
        response = self.client.get(self.subscription_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_subscription_auto_creation(self):
        """Testa criação automática de assinatura gratuita."""
        self.client.force_authenticate(user=self.user)
        
        # Verificar que não existe assinatura
        self.assertFalse(UserSubscription.objects.filter(user=self.user).exists())
        
        response = self.client.get(self.subscription_url)
        
        # Verificar que foi criada
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserSubscription.objects.filter(user=self.user).exists())
        
        subscription = UserSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.plan.plan_type, 'FREE')


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class UpgradeSubscriptionTest(APITestCase):
    """Testes para upgrade de assinatura."""
    
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
                "monthly_price": Decimal('0.00')
            }
        )
        
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2500.00'),
                "yearly_price": Decimal('25000.00')
            }
        )
        
        self.upgrade_url = reverse('subscriptions:upgrade-subscription')
    
    def test_upgrade_monthly_success(self):
        """Testa upgrade mensal bem-sucedido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'MONTHLY'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('subscription', response.data)
        self.assertEqual(response.data['amount_paid'], Decimal('2500.00'))
        
        # Verificar que assinatura foi atualizada
        subscription = UserSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.plan, self.premium_plan)
        self.assertEqual(subscription.status, 'ACTIVE')
    
    def test_upgrade_yearly_success(self):
        """Testa upgrade anual bem-sucedido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'YEARLY'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount_paid'], Decimal('25000.00'))
    
    def test_upgrade_with_valid_promo_code(self):
        """Testa upgrade com código promocional válido."""
        promo = PromotionalCode.objects.create(
            code="SAVE20",
            name="Desconto 20%",
            description="20% off",
            discount_type="PERCENTAGE",
            discount_value=Decimal('20.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30)
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'MONTHLY',
            'promo_code': 'SAVE20'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 20% de desconto em 2500 = 500 de desconto
        expected_final_price = Decimal('2000.00')
        self.assertEqual(response.data['amount_paid'], expected_final_price)
        self.assertEqual(response.data['discount_applied'], Decimal('500.00'))
        
        # Verificar que código foi marcado como usado
        self.assertTrue(PromoCodeUsage.objects.filter(
            user=self.user, 
            promo_code=promo
        ).exists())
    
    def test_upgrade_with_invalid_promo_code(self):
        """Testa upgrade com código promocional inválido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'MONTHLY',
            'promo_code': 'INVALID'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_upgrade_invalid_plan(self):
        """Testa upgrade com plano inválido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': '00000000-0000-0000-0000-000000000000',
            'billing_cycle': 'MONTHLY'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_upgrade_unauthenticated(self):
        """Testa upgrade sem autenticação."""
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'MONTHLY'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_upgrade_creates_history(self):
        """Testa que upgrade cria histórico."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'plan_id': str(self.premium_plan.id),
            'billing_cycle': 'MONTHLY'
        }
        
        response = self.client.post(self.upgrade_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar histórico
        subscription = UserSubscription.objects.get(user=self.user)
        history = SubscriptionHistory.objects.filter(subscription=subscription).first()
        
        self.assertIsNotNone(history)
        self.assertEqual(history.event_type, 'UPGRADED')
        self.assertEqual(history.new_plan, self.premium_plan)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class PromoCodeTest(APITestCase):
    """Testes para códigos promocionais."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2500.00')
            }
        )
        
        self.valid_promo = PromotionalCode.objects.create(
            code="SAVE20",
            name="Desconto 20%",
            description="20% off",
            discount_type="PERCENTAGE",
            discount_value=Decimal('20.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30)
        )
        
        self.apply_promo_url = reverse('subscriptions:apply-promo-code')
    
    def test_apply_valid_promo_code(self):
        """Testa aplicação de código promocional válido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'promo_code': 'SAVE20',
            'plan_id': str(self.plan.id)
        }
        
        response = self.client.post(self.apply_promo_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['promo_code'], 'SAVE20')
        self.assertEqual(response.data['discount_amount'], Decimal('500.00'))
        self.assertEqual(response.data['final_price'], Decimal('2000.00'))
    
    def test_apply_invalid_promo_code(self):
        """Testa aplicação de código inválido."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'promo_code': 'INVALID',
            'plan_id': str(self.plan.id)
        }
        
        response = self.client.post(self.apply_promo_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_apply_expired_promo_code(self):
        """Testa código expirado."""
        expired_promo = PromotionalCode.objects.create(
            code="EXPIRED",
            name="Código Expirado",
            description="Expired code",
            discount_type="FIXED_AMOUNT",
            discount_value=Decimal('500.00'),
            max_uses=100,
            valid_from=timezone.now() - timedelta(days=30),
            valid_until=timezone.now() - timedelta(days=1)
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'promo_code': 'EXPIRED',
            'plan_id': str(self.plan.id)
        }
        
        response = self.client.post(self.apply_promo_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_apply_already_used_promo_code(self):
        """Testa código já usado pelo usuário."""
        # Marcar como já usado
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        PromoCodeUsage.objects.create(
            user=self.user,
            promo_code=self.valid_promo,
            subscription=subscription,
            discount_applied=Decimal('500.00')
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'promo_code': 'SAVE20',
            'plan_id': str(self.plan.id)
        }
        
        response = self.client.post(self.apply_promo_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('já utilizou', response.data['error'])


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class CancelSubscriptionTest(APITestCase):
    """Testes para cancelamento de assinatura."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2500.00')
            }
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        self.cancel_url = reverse('subscriptions:cancel-subscription')
    
    def test_cancel_subscription_success(self):
        """Testa cancelamento bem-sucedido."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.cancel_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verificar que foi cancelada
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'CANCELED')
        self.assertIsNotNone(self.subscription.canceled_at)
    
    def test_cancel_already_canceled(self):
        """Testa cancelamento de assinatura já cancelada."""
        self.subscription.status = 'CANCELED'
        self.subscription.save()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.cancel_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('já está cancelada', response.data['error'])
    
    def test_cancel_no_subscription(self):
        """Testa cancelamento sem assinatura existente."""
        # Remover assinatura
        self.subscription.delete()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.cancel_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cancel_creates_history(self):
        """Testa que cancelamento cria histórico."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(self.cancel_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar histórico
        history = SubscriptionHistory.objects.filter(
            subscription=self.subscription,
            event_type='CANCELED'
        ).first()
        
        self.assertIsNotNone(history)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class SubscriptionAnalyticsTest(APITestCase):
    """Testes para analytics de assinatura."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password123'
        )
        
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            plan_type="PREMIUM",
            defaults={
                "name": "Premium",
                "description": "Premium plan",
                "monthly_price": Decimal('2500.00'),
                "daily_lessons_limit": None,  # Ilimitado
                "hearts_limit": 0,  # Ilimitado
                "offline_downloads": True,
                "certificates": True
            }
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        self.analytics_url = reverse('subscriptions:user-subscription-analytics')
        self.limits_url = reverse('subscriptions:subscription_limits_status')
    
    def test_user_analytics_success(self):
        """Testa analytics do usuário."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.analytics_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar estrutura
        self.assertIn('subscription', response.data)
        self.assertIn('usage', response.data)
        self.assertIn('features', response.data)
        
        # Verificar dados
        subscription_data = response.data['subscription']
        self.assertEqual(subscription_data['plan_type'], 'PREMIUM')
        self.assertTrue(subscription_data['is_active'])
        
        features = response.data['features']
        self.assertTrue(features['offline_downloads'])
        self.assertTrue(features['certificates'])
    
    def test_subscription_limits_status(self):
        """Testa status dos limites."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.limits_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar estrutura
        self.assertIn('lessons', response.data)
        self.assertIn('speaking', response.data)
        self.assertIn('listening', response.data)
        self.assertIn('hearts', response.data)
        self.assertIn('plan', response.data)
        
        # Verificar dados de lições ilimitadas
        lessons = response.data['lessons']
        self.assertTrue(lessons['unlimited'])
        self.assertTrue(lessons['can_use'])
        
        # Verificar dados de vidas ilimitadas
        hearts = response.data['hearts']
        self.assertTrue(hearts['unlimited'])
    
    def test_analytics_unauthenticated(self):
        """Testa analytics sem autenticação."""
        response = self.client.get(self.analytics_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class FeatureAccessTest(APITestCase):
    """Testes para verificação de acesso a funcionalidades."""
    
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
                "daily_lessons_limit": 3,
                "daily_speaking_minutes": 10,
                "hearts_limit": 5
            }
        )
        
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            expires_at=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            daily_lessons_used=2  # Já usou 2 de 3 lições
        )
        
        self.check_access_url = reverse('subscriptions:check-feature-access')
        self.consume_usage_url = reverse('subscriptions:consume_feature_usage')
    
    def test_check_lesson_access_allowed(self):
        """Testa verificação de acesso a lições (permitido)."""
        self.client.force_authenticate(user=self.user)
        
        data = {'feature_type': 'lesson'}
        response = self.client.post(self.check_access_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['allowed'])
        self.assertEqual(response.data['current_usage'], 2)
        self.assertEqual(response.data['limit'], 3)
    
    def test_check_lesson_access_denied(self):
        """Testa verificação de acesso a lições (negado)."""
        # Esgotar limite
        self.subscription.daily_lessons_used = 3
        self.subscription.save()
        
        self.client.force_authenticate(user=self.user)
        
        data = {'feature_type': 'lesson'}
        response = self.client.post(self.check_access_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['allowed'])
        self.assertIn('error_message', response.data)
        self.assertTrue(response.data['upgrade_required'])
    
    def test_consume_lesson_usage(self):
        """Testa consumo de uso de lições."""
        self.client.force_authenticate(user=self.user)
        
        data = {'feature_type': 'lesson'}
        response = self.client.post(self.consume_usage_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verificar que uso foi atualizado
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.daily_lessons_used, 3)
    
    def test_consume_speaking_minutes(self):
        """Testa consumo de minutos de Speaking."""
        self.client.force_authenticate(user=self.user)
        
        data = {'feature_type': 'speaking_minutes', 'amount': 5}
        response = self.client.post(self.consume_usage_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verificar que uso foi atualizado
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.daily_speaking_minutes_used, 5)
    
    def test_consume_hearts(self):
        """Testa consumo de vidas."""
        self.client.force_authenticate(user=self.user)
        
        data = {'feature_type': 'hearts', 'amount': 2}
        response = self.client.post(self.consume_usage_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verificar que vidas foram reduzidas
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.current_hearts, 3)  # 5 - 2 = 3