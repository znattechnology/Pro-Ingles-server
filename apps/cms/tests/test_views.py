"""
Testes para views do sistema CMS.

Testa endpoints públicos e administrativos,
incluindo CRUD operations e endpoints customizados.
"""

import json
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status

from ..models import (
    LandingPageSettings,
    HeroSection,
    StatItem,
    Company,
    ServiceItem,
    PricingTier,
    Feature,
    Testimonial,
    FAQItem,
    CallToAction,
    SeoSettings
)

User = get_user_model()


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class PublicCMSEndpointsTest(APITestCase):
    """Testes para endpoints públicos do CMS."""
    
    def setUp(self):
        # Limpar dados existentes para garantir testes isolados
        HeroSection.objects.all().delete()
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        Feature.objects.all().delete()
        LandingPageSettings.objects.all().delete()
        CallToAction.objects.all().delete()
        SeoSettings.objects.all().delete()
        # Criar dados de teste
        self.settings = LandingPageSettings.objects.create(
            site_title="ProEnglish Test",
            site_description="Test description"
        )
        
        self.hero = HeroSection.objects.create(
            headline="Test Hero",
            description="Test description"
        )
        
        self.stat = StatItem.objects.create(
            value="100%",
            label="Test stat",
            section="hero"
        )
        
        self.company = Company.objects.create(
            name="Test Company",
            category="technology"
        )
        
        self.service = ServiceItem.objects.create(
            title="Test Service",
            description="Test description",
            icon="📚"
        )
        
        self.pricing = PricingTier.objects.create(
            title="Test Plan",
            subtitle="Test subtitle",
            icon="⭐",
            monthly_price=Decimal('1000.00')
        )
        
        self.feature = Feature.objects.create(
            title="Test Feature",
            description="Test description",
            icon="star"
        )
        
        self.testimonial = Testimonial.objects.create(
            name="Test User",
            title="Test Title",
            text="Great platform!",
            result_achieved="Success",
            rating=5
        )
        
        self.faq = FAQItem.objects.create(
            question="Test question?",
            answer="Test answer",
            category="general"
        )
        
        self.cta = CallToAction.objects.create(
            title="Test CTA",
            primary_button_text="Click here",
            primary_button_url="/test",
            icon="rocket",
            section="middle"
        )
        
        self.seo = SeoSettings.objects.create(
            page_type="home",
            meta_title="Test SEO",
            meta_description="Test description"
        )
    
    def tearDown(self):
        """Limpar dados após cada teste para garantir isolamento."""
        # Limpar cache
        cache.clear()
        # Limpar dados
        HeroSection.objects.all().delete()
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        Feature.objects.all().delete()
        LandingPageSettings.objects.all().delete()
        CallToAction.objects.all().delete()
        SeoSettings.objects.all().delete()
    
    def test_landing_page_settings_list_public(self):
        """Testa listagem pública das configurações."""
        url = reverse('cms:landingpagesettings-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['site_title'], "ProEnglish Test")
    
    def test_hero_sections_list_public(self):
        """Testa listagem pública das hero sections."""
        url = reverse('cms:herosection-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['headline'], "Test Hero")
    
    def test_companies_list_public(self):
        """Testa listagem pública das empresas."""
        url = reverse('cms:company-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Test Company")
    
    def test_services_list_public(self):
        """Testa listagem pública dos serviços."""
        url = reverse('cms:serviceitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Service")
    
    def test_pricing_list_public(self):
        """Testa listagem pública dos planos de preço."""
        url = reverse('cms:pricingtier-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Plan")
    
    def test_features_list_public(self):
        """Testa listagem pública das funcionalidades."""
        url = reverse('cms:feature-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Feature")
    
    def test_testimonials_list_public(self):
        """Testa listagem pública dos depoimentos."""
        url = reverse('cms:testimonial-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Test User")
    
    def test_faqs_list_public(self):
        """Testa listagem pública dos FAQs."""
        url = reverse('cms:faqitem-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['question'], "Test question?")
    
    def test_ctas_list_public(self):
        """Testa listagem pública dos CTAs."""
        url = reverse('cms:calltoaction-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test CTA")
    
    def test_seo_settings_list_public(self):
        """Testa listagem pública das configurações SEO."""
        url = reverse('cms:seosettings-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['page_type'], "home")


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class LandingPageDataEndpointTest(APITestCase):
    """Testes para o endpoint consolidado de dados da landing page."""
    
    def setUp(self):
        # Limpar cache antes de cada teste
        cache.clear()
        
        # Criar dados completos
        self.settings = LandingPageSettings.objects.create(
            site_title="ProEnglish Angola",
            site_description="Plataforma de inglês para Angola"
        )
        
        self.hero = HeroSection.objects.create(
            headline="Inglês Especializado",
            description="Para Angola",
            is_active=True
        )
        
        self.inactive_hero = HeroSection.objects.create(
            headline="Hero Inativo",
            description="Não deve aparecer",
            is_active=False
        )
    
    def tearDown(self):
        """Limpar dados após cada teste para garantir isolamento."""
        cache.clear()
        HeroSection.objects.all().delete()
        LandingPageSettings.objects.all().delete()
    
    def test_landing_page_data_success(self):
        """Testa sucesso do endpoint de dados da landing page."""
        url = reverse('cms:landing-page-data')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('settings', response.data)
        self.assertIn('hero', response.data)
    
    def test_landing_page_data_cached(self):
        """Testa que dados são cacheados."""
        url = reverse('cms:landing-page-data')
        
        # Primeira requisição
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Segunda requisição (deve vir do cache)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)
    
    def test_landing_page_data_only_active(self):
        """Testa que apenas dados ativos são retornados."""
        url = reverse('cms:landing-page-data')
        response = self.client.get(url)
        
        # Deve conter apenas a hero section ativa
        hero = response.data.get('hero')
        self.assertIsNotNone(hero)
        self.assertEqual(hero['headline'], "Inglês Especializado")


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class AdminCMSEndpointsTest(APITestCase):
    """Testes para endpoints administrativos do CMS."""
    
    def authenticate_as_admin(self):
        """Helper para autenticar como admin."""
        self.client.force_authenticate(user=self.admin_user)
        
    def authenticate_as_regular_user(self):
        """Helper para autenticar como usuário regular."""
        self.client.force_authenticate(user=self.regular_user)
    
    def setUp(self):
        # Limpar dados existentes para garantir testes isolados
        HeroSection.objects.all().delete()
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        Feature.objects.all().delete()
        User.objects.all().delete()
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            name='Admin User',
            password='adminpass123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        
        # Criar usuário regular
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            name='Regular User',
            password='userpass123'
        )
        
        self.hero = HeroSection.objects.create(
            headline="Test Hero",
            description="Test description"
        )
    
    def tearDown(self):
        """Limpar dados após cada teste para garantir isolamento."""
        HeroSection.objects.all().delete()
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        Feature.objects.all().delete()
        User.objects.all().delete()
    
    def test_create_hero_section_admin(self):
        """Testa criação de hero section por admin."""
        self.authenticate_as_admin()
        
        url = reverse('cms:herosection-list')
        data = {
            'headline': 'Nova Hero Section',
            'description': 'Nova descrição',
            'primary_cta_text': 'Começar',
            'primary_cta_url': '/signup'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['headline'], 'Nova Hero Section')
    
    def test_create_hero_section_denied_regular_user(self):
        """Testa que usuário regular não pode criar hero section."""
        self.authenticate_as_regular_user()
        
        url = reverse('cms:herosection-list')
        data = {
            'headline': 'Tentativa de criação',
            'description': 'Não deveria funcionar'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_hero_section_admin(self):
        """Testa atualização de hero section por admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:herosection-detail', args=[self.hero.id])
        data = {
            'headline': 'Hero Atualizada',
            'description': 'Descrição atualizada'
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['headline'], 'Hero Atualizada')
    
    def test_delete_hero_section_admin(self):
        """Testa exclusão de hero section por admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:herosection-detail', args=[self.hero.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(HeroSection.objects.filter(id=self.hero.id).exists())


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class CustomCMSEndpointsTest(APITestCase):
    """Testes para endpoints customizados do CMS."""
    
    def authenticate_as_admin(self):
        """Helper para autenticar como admin."""
        self.client.force_authenticate(user=self.admin_user)
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            name='Admin User',
            password='adminpass123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        
        # Limpar dados existentes para testes isolados
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        
        # Criar alguns dados para estatísticas
        Company.objects.create(name="Sonangol", category="oil_gas", is_active=True)
        Company.objects.create(name="BIC", category="banking", is_active=True)
        ServiceItem.objects.create(title="Service 1", description="Desc", icon="📚", is_active=True)
        Testimonial.objects.create(
            name="João", title="Dev", text="Great!", 
            result_achieved="Success", rating=5, 
            is_active=True, verified=True
        )
        FAQItem.objects.create(question="Q1?", answer="A1", is_active=True)
        PricingTier.objects.create(title="Free", subtitle="Basic", icon="💰", is_active=True)
    
    def tearDown(self):
        """Limpar dados após cada teste para garantir isolamento."""
        Company.objects.all().delete()
        ServiceItem.objects.all().delete()
        Testimonial.objects.all().delete()
        FAQItem.objects.all().delete()
        PricingTier.objects.all().delete()
        User.objects.all().delete()
    
    def test_landing_page_stats_success(self):
        """Testa endpoint de estatísticas da landing page."""
        url = reverse('cms:stats-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_companies', response.data)
        self.assertIn('total_services', response.data)
        self.assertIn('total_testimonials', response.data)
        self.assertIn('total_faqs', response.data)
        self.assertIn('active_pricing_tiers', response.data)
        self.assertIn('sectors', response.data)
        
        # Verificar valores
        self.assertEqual(response.data['total_companies'], 2)
        self.assertEqual(response.data['total_services'], 1)
        self.assertEqual(response.data['total_testimonials'], 1)
        self.assertEqual(response.data['total_faqs'], 1)
        self.assertEqual(response.data['active_pricing_tiers'], 1)
        
        # Verificar setores
        sectors = response.data['sectors']
        self.assertEqual(sectors['oil_gas'], 1)
        self.assertEqual(sectors['banking'], 1)
        self.assertEqual(sectors['telecoms'], 0)
        self.assertEqual(sectors['technology'], 0)
    
    def test_health_check_success(self):
        """Testa endpoint de health check."""
        url = reverse('cms:health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['service'], 'ProEnglish CMS API')
        self.assertEqual(response.data['version'], '1.0.0')
        self.assertIn('timestamp', response.data)
    
    def test_clear_cache_admin(self):
        """Testa limpeza de cache por admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:clear-cache')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Cache cleared successfully')
        self.assertIn('cleared_keys', response.data)
    
    def test_clear_cache_denied_unauthenticated(self):
        """Testa que limpeza de cache é negada para usuários não autenticados."""
        url = reverse('cms:clear-cache')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_preview_changes_admin(self):
        """Testa preview de mudanças por admin."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:preview-changes')
        data = {
            'model_type': 'hero',
            'data': {
                'headline': 'Preview Hero',
                'description': 'Preview description'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('preview', response.data)
        self.assertIn('formatted', response.data)
        self.assertEqual(response.data['preview']['headline'], 'Preview Hero')
    
    def test_preview_changes_invalid_model_type(self):
        """Testa preview com tipo de modelo inválido."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:preview-changes')
        data = {
            'model_type': 'invalid_type',
            'data': {'title': 'Test'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid model type')
        self.assertIn('valid_types', response.data)
    
    def test_preview_changes_invalid_data(self):
        """Testa preview com dados inválidos."""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('cms:preview-changes')
        data = {
            'model_type': 'pricing',
            'data': {
                'monthly_price': 'invalid_price'  # Deve ser numérico
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)


@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
@override_settings(
    RATELIMIT_ENABLE=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
)
class CMSFilteringAndOrderingTest(APITestCase):
    """Testes para filtragem e ordenação nos endpoints do CMS."""
    
    def setUp(self):
        # Limpar dados existentes para garantir testes isolados
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        Testimonial.objects.all().delete()
        
        # Criar múltiplos itens para testar filtragem
        StatItem.objects.create(value="100%", label="Hero Stat", section="hero", order=1, is_active=True)
        StatItem.objects.create(value="50+", label="About Stat", section="about", order=2, is_active=True)
        StatItem.objects.create(value="95%", label="Inactive Stat", section="hero", order=3, is_active=False)
        
        Company.objects.create(name="Sonangol", category="oil_gas", is_active=True, show_in_hero=True)
        Company.objects.create(name="BIC", category="banking", is_active=True, show_in_ticker=True)
        Company.objects.create(name="Inactive Corp", category="technology", is_active=False)
        
        Testimonial.objects.create(
            name="João", title="Dev", text="Great!", 
            result_achieved="Success", rating=5, 
            sector="oil_gas", is_featured=True, verified=True
        )
        Testimonial.objects.create(
            name="Maria", title="Manager", text="Excellent!", 
            result_achieved="Promotion", rating=4, 
            sector="banking", is_featured=False, verified=True
        )
    
    def tearDown(self):
        """Limpar dados após cada teste para garantir isolamento."""
        StatItem.objects.all().delete()
        Company.objects.all().delete()
        Testimonial.objects.all().delete()
    
    def test_stat_items_filter_by_section(self):
        """Testa filtragem de estatísticas por seção."""
        url = reverse('cms:statitem-list')
        response = self.client.get(url, {'section': 'hero'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 2)  # 1 ativo + 1 inativo
        
        for item in results:
            self.assertEqual(item['section'], 'hero')
    
    def test_stat_items_filter_by_active(self):
        """Testa filtragem de estatísticas por status ativo."""
        url = reverse('cms:statitem-list')
        response = self.client.get(url, {'is_active': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 2)  # Apenas os ativos
        
        for item in results:
            self.assertTrue(item['is_active'])
    
    def test_companies_filter_by_category(self):
        """Testa filtragem de empresas por categoria."""
        url = reverse('cms:company-list')
        response = self.client.get(url, {'category': 'oil_gas'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['category'], 'oil_gas')
    
    def test_companies_filter_by_show_in_hero(self):
        """Testa filtragem de empresas que aparecem na hero."""
        url = reverse('cms:company-list')
        response = self.client.get(url, {'show_in_hero': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Sonangol')
    
    def test_testimonials_filter_by_sector(self):
        """Testa filtragem de depoimentos por setor."""
        url = reverse('cms:testimonial-list')
        response = self.client.get(url, {'sector': 'banking'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Maria')
    
    def test_testimonials_filter_by_featured(self):
        """Testa filtragem de depoimentos em destaque."""
        url = reverse('cms:testimonial-list')
        response = self.client.get(url, {'is_featured': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'João')
    
    def test_stat_items_ordering(self):
        """Testa ordenação de estatísticas."""
        url = reverse('cms:statitem-list')
        response = self.client.get(url, {'ordering': 'order'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        
        # Verificar que estão ordenados por order
        orders = [item['order'] for item in results]
        self.assertEqual(orders, sorted(orders))
    
    def test_companies_ordering(self):
        """Testa ordenação de empresas."""
        url = reverse('cms:company-list')
        response = self.client.get(url, {'ordering': 'name'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        
        # Verificar que estão ordenados por nome
        names = [item['name'] for item in results]
        self.assertEqual(names, sorted(names))