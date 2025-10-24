"""
Testes para modelos do sistema CMS.

Testa funcionalidades dos modelos de conteúdo da landing page,
incluindo configurações, hero sections, empresas, serviços, etc.
"""

import os
import django
from django.conf import settings

# Configure Django settings before any imports
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.test_settings')
    django.setup()

import json
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

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


class LandingPageSettingsModelTest(TestCase):
    """Testes para o modelo LandingPageSettings."""
    
    def setUp(self):
        self.settings = LandingPageSettings.objects.create(
            site_title="ProEnglish Test",
            site_description="Test description",
            contact_email="test@proenglish.ao",
            contact_phone="+244 999 000 111"
        )
    
    def test_settings_creation(self):
        """Testa criação das configurações."""
        self.assertEqual(self.settings.site_title, "ProEnglish Test")
        self.assertEqual(self.settings.contact_email, "test@proenglish.ao")
        self.assertTrue(self.settings.is_active)
        self.assertFalse(self.settings.maintenance_mode)
    
    def test_string_representation(self):
        """Testa representação string das configurações."""
        expected = "Configura��es - ProEnglish Test"  # Usando a string exata do modelo
        self.assertEqual(str(self.settings), expected)
    
    def test_email_validation(self):
        """Testa validação de email."""
        self.settings.contact_email = "invalid-email"
        with self.assertRaises(ValidationError):
            self.settings.full_clean()
    
    def test_maintenance_mode(self):
        """Testa modo de manutenção."""
        self.settings.maintenance_mode = True
        self.settings.maintenance_message = "Site em manutenção"
        self.settings.save()
        
        self.assertTrue(self.settings.maintenance_mode)
        self.assertEqual(self.settings.maintenance_message, "Site em manutenção")


class HeroSectionModelTest(TestCase):
    """Testes para o modelo HeroSection."""
    
    def setUp(self):
        self.hero = HeroSection.objects.create(
            headline="Inglês Especializado",
            headline_highlight="com IA Personal Tutor",
            description="Plataforma de inglês para Angola",
            primary_cta_text="Começar Grátis",
            primary_cta_url="/signup"
        )
    
    def test_hero_creation(self):
        """Testa criação da hero section."""
        self.assertEqual(self.hero.headline, "Inglês Especializado")
        self.assertEqual(self.hero.headline_highlight, "com IA Personal Tutor")
        self.assertTrue(self.hero.is_active)
        self.assertEqual(self.hero.order, 0)
    
    def test_string_representation(self):
        """Testa representação string da hero."""
        expected = "Hero: Inglês Especializado"
        self.assertEqual(str(self.hero), expected)
    
    def test_badge_functionality(self):
        """Testa funcionalidade do badge."""
        self.hero.badge_text = "🚀 Nova funcionalidade"
        self.hero.badge_is_active = True
        self.hero.save()
        
        self.assertEqual(self.hero.badge_text, "🚀 Nova funcionalidade")
        self.assertTrue(self.hero.badge_is_active)
    
    def test_rating_validation(self):
        """Testa validação do rating."""
        self.hero.rating_value = Decimal('4.9')
        self.hero.save()
        
        self.assertEqual(self.hero.rating_value, Decimal('4.9'))
    
    def test_ordering(self):
        """Testa ordenação das hero sections."""
        hero2 = HeroSection.objects.create(
            headline="Segunda Hero",
            order=1
        )
        
        heroes = list(HeroSection.objects.all())
        self.assertEqual(heroes[0], self.hero)  # order=0
        self.assertEqual(heroes[1], hero2)     # order=1


class StatItemModelTest(TestCase):
    """Testes para o modelo StatItem."""
    
    def setUp(self):
        self.stat = StatItem.objects.create(
            value="10K+",
            label="Angolanos aprendendo",
            icon="users",
            section="hero"
        )
    
    def test_stat_creation(self):
        """Testa criação da estatística."""
        self.assertEqual(self.stat.value, "10K+")
        self.assertEqual(self.stat.label, "Angolanos aprendendo")
        self.assertEqual(self.stat.section, "hero")
        self.assertTrue(self.stat.is_active)
    
    def test_string_representation(self):
        """Testa representação string da estatística."""
        expected = "10K+ - Angolanos aprendendo"
        self.assertEqual(str(self.stat), expected)
    
    def test_section_choices(self):
        """Testa choices das seções."""
        valid_sections = ['hero', 'about', 'footer']
        for section in valid_sections:
            stat = StatItem.objects.create(
                value="100%",
                label=f"Test {section}",
                section=section
            )
            self.assertEqual(stat.section, section)
    
    def test_ordering(self):
        """Testa ordenação das estatísticas."""
        stat2 = StatItem.objects.create(
            value="94%",
            label="Taxa de satisfação",
            section="hero",
            order=1
        )
        
        stats = list(StatItem.objects.filter(section="hero"))
        self.assertEqual(stats[0], self.stat)  # order=0
        self.assertEqual(stats[1], stat2)      # order=1


class CompanyModelTest(TestCase):
    """Testes para o modelo Company."""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Sonangol",
            category="oil_gas",
            description="Empresa petrolífera nacional"
        )
    
    def test_company_creation(self):
        """Testa criação da empresa."""
        self.assertEqual(self.company.name, "Sonangol")
        self.assertEqual(self.company.category, "oil_gas")
        self.assertTrue(self.company.is_active)
        self.assertTrue(self.company.show_in_ticker)
        self.assertFalse(self.company.show_in_hero)
    
    def test_string_representation(self):
        """Testa representação string da empresa."""
        self.assertEqual(str(self.company), "Sonangol")
    
    def test_category_choices(self):
        """Testa choices das categorias."""
        categories = [
            'oil_gas', 'banking', 'telecoms', 'government',
            'education', 'technology', 'other'
        ]
        for category in categories:
            company = Company.objects.create(
                name=f"Empresa {category}",
                category=category
            )
            self.assertEqual(company.category, category)
    
    def test_display_settings(self):
        """Testa configurações de exibição."""
        self.company.show_in_hero = True
        self.company.show_in_ticker = False
        self.company.save()
        
        self.assertTrue(self.company.show_in_hero)
        self.assertFalse(self.company.show_in_ticker)


class ServiceItemModelTest(TestCase):
    """Testes para o modelo ServiceItem."""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Banco BIC",
            category="banking"
        )
        
        self.service = ServiceItem.objects.create(
            title="Inglês para Bancos",
            subtitle="Especialização bancária",
            description="Curso focado no setor bancário",
            icon="🏦",
            service_type="course"
        )
        self.service.target_companies.add(self.company)
    
    def test_service_creation(self):
        """Testa criação do serviço."""
        self.assertEqual(self.service.title, "Inglês para Bancos")
        self.assertEqual(self.service.service_type, "course")
        self.assertTrue(self.service.is_active)
        self.assertFalse(self.service.is_featured)
    
    def test_string_representation(self):
        """Testa representação string do serviço."""
        self.assertEqual(str(self.service), "Inglês para Bancos")
    
    def test_service_type_choices(self):
        """Testa choices dos tipos de serviço."""
        service_types = ['course', 'practice_lab', 'ai_tutor', 'other']
        for service_type in service_types:
            service = ServiceItem.objects.create(
                title=f"Serviço {service_type}",
                description="Descrição teste",
                icon="📚",
                service_type=service_type
            )
            self.assertEqual(service.service_type, service_type)
    
    def test_json_fields(self):
        """Testa campos JSON."""
        features = ["Feature 1", "Feature 2", "Feature 3"]
        curriculum = ["Tópico 1", "Tópico 2"]
        
        self.service.features = features
        self.service.curriculum_topics = curriculum
        self.service.save()
        
        self.assertEqual(self.service.features, features)
        self.assertEqual(self.service.curriculum_topics, curriculum)
    
    def test_target_companies_relationship(self):
        """Testa relacionamento com empresas alvo."""
        self.assertEqual(self.service.target_companies.count(), 1)
        self.assertIn(self.company, self.service.target_companies.all())


class PricingTierModelTest(TestCase):
    """Testes para o modelo PricingTier."""
    
    def setUp(self):
        self.tier = PricingTier.objects.create(
            title="Premium",
            subtitle="Plano completo",
            icon="⭐",
            monthly_price=Decimal('2500.00'),
            yearly_price=Decimal('25000.00'),
            angola_benefit="Suporte em português",
            button_text="Escolher Premium"
        )
    
    def test_tier_creation(self):
        """Testa criação do plano."""
        self.assertEqual(self.tier.title, "Premium")
        self.assertEqual(self.tier.monthly_price, Decimal('2500.00'))
        self.assertEqual(self.tier.currency, "AOA")
        self.assertTrue(self.tier.is_active)
        self.assertFalse(self.tier.is_popular)
    
    def test_string_representation(self):
        """Testa representação string do plano."""
        expected = "Premium - 2500.00 AOA/mês"
        self.assertEqual(str(self.tier), expected)
    
    def test_features_json_field(self):
        """Testa campo JSON de features."""
        features = [
            "Lições ilimitadas",
            "IA Personal Tutor",
            "Certificados"
        ]
        
        self.tier.features = features
        self.tier.save()
        
        self.assertEqual(self.tier.features, features)
    
    def test_popular_and_inverse_design(self):
        """Testa flags de design."""
        self.tier.is_popular = True
        self.tier.is_inverse_design = True
        self.tier.save()
        
        self.assertTrue(self.tier.is_popular)
        self.assertTrue(self.tier.is_inverse_design)


class FeatureModelTest(TestCase):
    """Testes para o modelo Feature."""
    
    def setUp(self):
        self.feature = Feature.objects.create(
            title="IA Personal Tutor",
            description="Tutor inteligente personalizado",
            icon="brain"
        )
    
    def test_feature_creation(self):
        """Testa criação da funcionalidade."""
        self.assertEqual(self.feature.title, "IA Personal Tutor")
        self.assertEqual(self.feature.icon, "brain")
        self.assertEqual(self.feature.grid_column_span, 1)
        self.assertTrue(self.feature.is_active)
        self.assertFalse(self.feature.is_highlighted)
    
    def test_string_representation(self):
        """Testa representação string da funcionalidade."""
        self.assertEqual(str(self.feature), "IA Personal Tutor")
    
    def test_grid_column_span_validation(self):
        """Testa validação do grid column span."""
        # Valores válidos (1-3)
        for span in [1, 2, 3]:
            self.feature.grid_column_span = span
            self.feature.save()
            self.assertEqual(self.feature.grid_column_span, span)
    
    def test_json_fields(self):
        """Testa campos JSON."""
        benefits = ["Aprendizado personalizado", "Feedback instantâneo"]
        use_cases = ["Prática de conversação", "Correção de gramática"]
        
        self.feature.benefits = benefits
        self.feature.use_cases = use_cases
        self.feature.save()
        
        self.assertEqual(self.feature.benefits, benefits)
        self.assertEqual(self.feature.use_cases, use_cases)


class TestimonialModelTest(TestCase):
    """Testes para o modelo Testimonial."""
    
    def setUp(self):
        self.company = Company.objects.create(
            name="Unitel",
            category="telecoms"
        )
        
        self.testimonial = Testimonial.objects.create(
            name="João Silva",
            title="Gerente de TI",
            company=self.company,
            location="Luanda",
            text="Excelente plataforma para aprender inglês técnico",
            result_achieved="Promoção para cargo internacional",
            rating=5,
            sector="telecoms"
        )
    
    def test_testimonial_creation(self):
        """Testa criação do depoimento."""
        self.assertEqual(self.testimonial.name, "João Silva")
        self.assertEqual(self.testimonial.company, self.company)
        self.assertEqual(self.testimonial.rating, 5)
        self.assertEqual(self.testimonial.sector, "telecoms")
        self.assertFalse(self.testimonial.verified)
        self.assertFalse(self.testimonial.is_featured)
    
    def test_string_representation(self):
        """Testa representação string do depoimento."""
        expected = "João Silva - Unitel"
        self.assertEqual(str(self.testimonial), expected)
    
    def test_string_representation_without_company(self):
        """Testa representação string sem empresa."""
        testimonial = Testimonial.objects.create(
            name="Maria Santos",
            title="Estudante",
            text="Ótima experiência",
            result_achieved="Aprovação em teste",
            rating=4
        )
        expected = "Maria Santos - Cliente"
        self.assertEqual(str(testimonial), expected)
    
    def test_rating_validation(self):
        """Testa validação do rating."""
        # Valores válidos (1-5)
        for rating in [1, 2, 3, 4, 5]:
            self.testimonial.rating = rating
            self.testimonial.save()
            self.assertEqual(self.testimonial.rating, rating)
    
    def test_sector_choices(self):
        """Testa choices dos setores."""
        sectors = [
            'oil_gas', 'banking', 'telecoms', 'government',
            'education', 'technology', 'other'
        ]
        for sector in sectors:
            testimonial = Testimonial.objects.create(
                name=f"Cliente {sector}",
                title="Cargo teste",
                text="Texto teste",
                result_achieved="Resultado teste",
                sector=sector
            )
            self.assertEqual(testimonial.sector, sector)
    
    def test_verification_and_featured(self):
        """Testa flags de verificação e destaque."""
        self.testimonial.verified = True
        self.testimonial.is_featured = True
        self.testimonial.save()
        
        self.assertTrue(self.testimonial.verified)
        self.assertTrue(self.testimonial.is_featured)


class FAQItemModelTest(TestCase):
    """Testes para o modelo FAQItem."""
    
    def setUp(self):
        self.faq = FAQItem.objects.create(
            question="Como funciona o plano gratuito?",
            answer="O plano gratuito inclui 3 lições por dia...",
            category="pricing"
        )
    
    def test_faq_creation(self):
        """Testa criação do FAQ."""
        self.assertEqual(self.faq.question, "Como funciona o plano gratuito?")
        self.assertEqual(self.faq.category, "pricing")
        self.assertTrue(self.faq.is_active)
        self.assertFalse(self.faq.is_featured)
    
    def test_string_representation(self):
        """Testa representação string do FAQ."""
        expected = "Como funciona o plano gratuito?"
        self.assertEqual(str(self.faq), expected)
    
    def test_string_representation_truncated(self):
        """Testa representação string truncada."""
        long_question = "Esta é uma pergunta muito longa que deveria ser truncada para mostrar apenas os primeiros 100 caracteres da pergunta completa"
        faq = FAQItem.objects.create(
            question=long_question,
            answer="Resposta",
            category="general"
        )
        self.assertEqual(len(str(faq)), 100)
    
    def test_category_choices(self):
        """Testa choices das categorias."""
        categories = [
            'general', 'pricing', 'technical',
            'courses', 'payment', 'support'
        ]
        for category in categories:
            faq = FAQItem.objects.create(
                question=f"Pergunta {category}?",
                answer="Resposta teste",
                category=category
            )
            self.assertEqual(faq.category, category)


class CallToActionModelTest(TestCase):
    """Testes para o modelo CallToAction."""
    
    def setUp(self):
        self.cta = CallToAction.objects.create(
            title="Pronto para começar?",
            subtitle="Junte-se a milhares de angolanos",
            primary_button_text="Começar Agora",
            primary_button_url="/signup",
            icon="rocket",
            section="middle"
        )
    
    def test_cta_creation(self):
        """Testa criação do CTA."""
        self.assertEqual(self.cta.title, "Pronto para começar?")
        self.assertEqual(self.cta.section, "middle")
        self.assertTrue(self.cta.is_active)
    
    def test_string_representation(self):
        """Testa representação string do CTA."""
        expected = "Pronto para começar? (middle)"
        self.assertEqual(str(self.cta), expected)
    
    def test_section_choices(self):
        """Testa choices das seções."""
        sections = ['hero', 'middle', 'pricing', 'footer']
        for section in sections:
            cta = CallToAction.objects.create(
                title=f"CTA {section}",
                primary_button_text="Clique aqui",
                primary_button_url="/action",
                icon="star",
                section=section
            )
            self.assertEqual(cta.section, section)
    
    def test_secondary_button_optional(self):
        """Testa que botão secundário é opcional."""
        self.assertEqual(self.cta.secondary_button_text, "")
        self.assertEqual(self.cta.secondary_button_url, "")
        
        # Adicionar botão secundário
        self.cta.secondary_button_text = "Saiba Mais"
        self.cta.secondary_button_url = "/about"
        self.cta.save()
        
        self.assertEqual(self.cta.secondary_button_text, "Saiba Mais")
        self.assertEqual(self.cta.secondary_button_url, "/about")


class SeoSettingsModelTest(TestCase):
    """Testes para o modelo SeoSettings."""
    
    def setUp(self):
        self.seo = SeoSettings.objects.create(
            page_type="home",
            meta_title="ProEnglish Angola - Inglês Especializado",
            meta_description="A primeira plataforma de inglês feita para Angola"
        )
    
    def test_seo_creation(self):
        """Testa criação das configurações SEO."""
        self.assertEqual(self.seo.page_type, "home")
        self.assertEqual(self.seo.meta_title, "ProEnglish Angola - Inglês Especializado")
        self.assertTrue(self.seo.index_page)
        self.assertTrue(self.seo.follow_links)
    
    def test_string_representation(self):
        """Testa representação string do SEO."""
        expected = "SEO - Página Inicial"
        self.assertEqual(str(self.seo), expected)
    
    def test_page_type_choices(self):
        """Testa choices dos tipos de página."""
        page_types = ['pricing', 'about', 'contact']  # 'home' já existe no setUp
        for page_type in page_types:
            seo = SeoSettings.objects.create(
                page_type=page_type,
                meta_title=f"Título {page_type}",
                meta_description=f"Descrição {page_type}"
            )
            self.assertEqual(seo.page_type, page_type)
    
    def test_unique_page_type(self):
        """Testa que page_type é único."""
        with self.assertRaises(Exception):  # IntegrityError
            SeoSettings.objects.create(
                page_type="home",  # Já existe
                meta_title="Outro título",
                meta_description="Outra descrição"
            )
    
    def test_schema_markup_json_field(self):
        """Testa campo JSON do schema markup."""
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "ProEnglish Angola"
        }
        
        self.seo.schema_markup = schema
        self.seo.save()
        
        self.assertEqual(self.seo.schema_markup, schema)
    
    def test_twitter_and_og_fields(self):
        """Testa campos do Twitter e Open Graph."""
        self.seo.og_title = "ProEnglish Angola"
        self.seo.og_description = "Inglês para Angola"
        self.seo.og_type = "website"
        self.seo.twitter_card = "summary_large_image"
        self.seo.twitter_title = "ProEnglish Angola"
        self.seo.save()
        
        self.assertEqual(self.seo.og_title, "ProEnglish Angola")
        self.assertEqual(self.seo.twitter_card, "summary_large_image")