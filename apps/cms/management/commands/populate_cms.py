from django.core.management.base import BaseCommand
from apps.cms.models import (
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


class Command(BaseCommand):
    help = 'Populate CMS with initial data from current landing page'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting CMS population...'))

        # Create Landing Page Settings
        settings, created = LandingPageSettings.objects.get_or_create(
            defaults={
                'site_title': 'ProEnglish Angola',
                'site_description': 'A primeira plataforma de inglês feita para Angola',
                'meta_keywords': 'inglês, angola, aprender inglês, IA tutor, sonangol, petróleo, bancos',
                'contact_email': 'contato@proenglish.ao',
                'contact_phone': '+244 923 456 789',
                'whatsapp_number': '+244923456789',
                'is_active': True,
            }
        )
        
        # Create Hero Section
        hero, created = HeroSection.objects.get_or_create(
            headline='Inglês Especializado',
            defaults={
                'badge_text': '🇦🇴 A primeira plataforma de inglês feita para Angola',
                'badge_is_active': True,
                'headline_highlight': 'com IA Personal Tutor',
                'description': 'A única plataforma que combina inteligência artificial com cursos especializados para setores como petróleo, bancos e TI. Preços em AOA, conteúdo adaptado para Angola.',
                'primary_cta_text': 'Começar Grátis - 7 Dias',
                'primary_cta_url': '/signup',
                'secondary_cta_text': 'Ver Demo do IA Tutor',
                'secondary_cta_url': '#demo',
                'social_proof_text': 'Mais de 10.000 angolanos',
                'rating_value': 4.9,
                'rating_count': '2.1k reviews',
                'is_active': True,
                'order': 0,
            }
        )

        # Create Stats
        stats_data = [
            {'value': '10K+', 'label': 'Angolanos aprendendo', 'section': 'hero', 'order': 0},
            {'value': '94%', 'label': 'Taxa de sucesso', 'section': 'hero', 'order': 1},
            {'value': '50+', 'label': 'Cursos especializados', 'section': 'hero', 'order': 2},
        ]
        
        for stat_data in stats_data:
            StatItem.objects.get_or_create(
                value=stat_data['value'],
                label=stat_data['label'],
                section=stat_data['section'],
                defaults={
                    'is_active': True,
                    'order': stat_data['order']
                }
            )

        # Create Companies
        companies_data = [
            {'name': 'Sonangol', 'category': 'oil_gas', 'show_in_hero': True, 'show_in_ticker': True},
            {'name': 'BAI', 'category': 'banking', 'show_in_hero': True, 'show_in_ticker': True},
            {'name': 'Unitel', 'category': 'telecoms', 'show_in_hero': True, 'show_in_ticker': True},
            {'name': 'BFA', 'category': 'banking', 'show_in_hero': True, 'show_in_ticker': True},
            {'name': 'Total Angola', 'category': 'oil_gas', 'show_in_ticker': True},
            {'name': 'Chevron', 'category': 'oil_gas', 'show_in_ticker': True},
            {'name': 'Standard Bank', 'category': 'banking', 'show_in_ticker': True},
            {'name': 'MS Telecom', 'category': 'telecoms', 'show_in_ticker': True},
            {'name': 'Angola Telecom', 'category': 'telecoms', 'show_in_ticker': True},
        ]
        
        for i, company_data in enumerate(companies_data):
            Company.objects.get_or_create(
                name=company_data['name'],
                defaults={
                    'category': company_data['category'],
                    'show_in_hero': company_data.get('show_in_hero', False),
                    'show_in_ticker': company_data.get('show_in_ticker', False),
                    'is_active': True,
                    'order': i
                }
            )

        # Create Services
        services_data = [
            {
                'title': 'Inglês para Petróleo & Gás',
                'description': 'Especializado para Sonangol, Total Angola e Chevron. Aprenda terminologia técnica, protocolos de segurança e comunicação internacional específica do setor energético angolano.',
                'icon': '🛢️',
                'service_type': 'course',
                'student_count': '2.5K+',
                'level': 'Técnico-Professional',
                'duration': '3-6 meses',
                'certification': 'Certificado Internacional',
                'features': [
                    'Terminologia técnica do petróleo',
                    'Protocolos de segurança internacional',
                    'Comunicação com equipes multinacionais',
                    'Relatórios técnicos em inglês',
                    'Apresentações para executivos'
                ],
                'order': 0
            },
            {
                'title': 'Inglês Bancário',
                'description': 'Desenvolvido para BAI, BFA e Standard Bank. Domine transações internacionais, análise de crédito, compliance e atendimento a clientes internacionais.',
                'icon': '🏦',
                'service_type': 'course',
                'student_count': '1.8K+',
                'level': 'Professional-Executivo',
                'duration': '2-4 meses',
                'certification': 'Certificado Bancário',
                'features': [
                    'Transações internacionais',
                    'Análise de crédito em inglês',
                    'Compliance internacional',
                    'Atendimento a clientes estrangeiros',
                    'Documentação bancária'
                ],
                'order': 1
            },
            {
                'title': 'Inglês para TI & Telecomunicações',
                'description': 'Criado para Unitel, MS Telecom e startups tech. Vocabulário de programação, metodologias ágeis, cloud computing e liderança de equipes remotas.',
                'icon': '💻',
                'service_type': 'course',
                'student_count': '1.2K+',
                'level': 'Técnico-Avançado',
                'duration': '2-5 meses',
                'certification': 'Certificado Tech',
                'features': [
                    'Vocabulário de programação',
                    'Metodologias ágeis',
                    'Cloud computing',
                    'Liderança de equipes remotas',
                    'Documentação técnica'
                ],
                'order': 2
            },
            {
                'title': 'Inglês Executivo',
                'description': 'Para C-Level e gestores sênior. Liderança internacional, negociações estratégicas, apresentações executivas e networking global com foco no mercado angolano.',
                'icon': '👔',
                'service_type': 'course',
                'student_count': '950+',
                'level': 'Executivo-CEO',
                'duration': '4-8 meses',
                'certification': 'Certificado Executivo',
                'features': [
                    'Liderança internacional',
                    'Negociações estratégicas',
                    'Apresentações executivas',
                    'Networking global',
                    'Gestão multicultural'
                ],
                'order': 3
            },
            {
                'title': 'IA Personal Tutor',
                'description': 'Nossa tecnologia exclusiva! Correção de pronunciação em tempo real, feedback personalizado para sotaque angolano e aprendizado adaptativo com inteligência artificial.',
                'icon': '🤖',
                'service_type': 'ai_tutor',
                'student_count': '3.2K+',
                'level': 'Todos os níveis',
                'duration': 'Contínuo',
                'certification': 'Certificado IA-Enhanced',
                'features': [
                    'Correção de pronunciação em tempo real',
                    'Feedback personalizado para Angola',
                    'Aprendizado adaptativo',
                    'IA conversacional',
                    'Análise de progresso avançada'
                ],
                'order': 4
            },
            {
                'title': 'Practice Lab Inteligente',
                'description': 'O laboratório de prática mais avançado de Angola. Exercícios adaptativos com IA que se ajustam ao seu progresso e necessidades profissionais específicas.',
                'icon': '⚡',
                'service_type': 'practice_lab',
                'student_count': '2.8K+',
                'level': 'Todos os níveis',
                'duration': 'Prática contínua',
                'certification': 'Certificado Practice Lab',
                'features': [
                    'Speaking Challenge com IA',
                    'Listening Lab com áudios reais',
                    'Writing Workshop profissional',
                    'Cenários interativos de trabalho',
                    'Gamificação e conquistas',
                    'Analytics avançado de progresso'
                ],
                'order': 5
            }
        ]
        
        for service_data in services_data:
            ServiceItem.objects.get_or_create(
                title=service_data['title'],
                defaults={
                    'description': service_data['description'],
                    'icon': service_data['icon'],
                    'service_type': service_data['service_type'],
                    'student_count': service_data['student_count'],
                    'level': service_data['level'],
                    'duration': service_data['duration'],
                    'certification': service_data['certification'],
                    'features': service_data['features'],
                    'is_active': True,
                    'order': service_data['order']
                }
            )

        # Create Pricing Tiers
        pricing_data = [
            {
                'title': 'Básico',
                'subtitle': 'Para começar',
                'icon': '🚀',
                'monthly_price': 0,
                'yearly_price': 0,
                'currency': 'AOA',
                'angola_benefit': 'Ideal para testar nossa metodologia angolana',
                'features': [
                    '3 lições por dia',
                    '5 min de Speaking com IA',
                    '5 min de Listening diário',
                    '3 vidas (recarrega 4h)',
                    '1 curso: Inglês Geral',
                    'Progresso básico',
                    'Comunidade ProEnglish Angola'
                ],
                'button_text': 'Começar Grátis',
                'button_url': '/signup',
                'is_popular': False,
                'order': 0
            },
            {
                'title': 'Professional',
                'subtitle': 'Para quem quer crescer',
                'icon': '👑',
                'monthly_price': 14950,
                'yearly_price': 149500,
                'currency': 'AOA',
                'promotional_badge': 'Mais Escolhido',
                'yearly_discount_text': '2 meses grátis',
                'angola_benefit': 'Criado especificamente para profissionais angolanos',
                'features': [
                    'Lições ILIMITADAS',
                    'Speaking & Listening ILIMITADO',
                    'Vidas infinitas',
                    '15+ cursos especializados',
                    'Inglês para Petróleo & Gás',
                    'Inglês Bancário (BAI/BFA)',
                    'Certificados oficiais',
                    'Analytics detalhado',
                    'Download offline',
                    'Suporte especializado',
                    '2 dispositivos simultâneos'
                ],
                'button_text': 'Acelerar Carreira',
                'button_url': '/user/upgrade',
                'is_popular': True,
                'is_inverse_design': True,
                'order': 1
            },
            {
                'title': 'Enterprise',
                'subtitle': 'Para líderes',
                'icon': '⚡',
                'monthly_price': 24950,
                'yearly_price': 249500,
                'currency': 'AOA',
                'promotional_badge': 'Mais Avançado',
                'yearly_discount_text': '2 meses grátis',
                'angola_benefit': 'Para executivos que lideram em empresas multinacionais',
                'features': [
                    'TUDO do Professional',
                    'IA Personal Tutor exclusivo',
                    '2 sessões com nativos/mês',
                    'Correção avançada com IA',
                    'Inglês para C-Level',
                    'Preparação para reuniões internacionais',
                    'Suporte VIP 24/7',
                    'Acesso antecipado',
                    '3 dispositivos simultâneos',
                    'Relatórios executivos'
                ],
                'button_text': 'Ser Líder Global',
                'button_url': '/user/upgrade',
                'is_popular': False,
                'order': 2
            }
        ]
        
        for tier_data in pricing_data:
            PricingTier.objects.get_or_create(
                title=tier_data['title'],
                defaults=tier_data
            )

        # Create SEO Settings
        seo, created = SeoSettings.objects.get_or_create(
            page_type='home',
            defaults={
                'meta_title': 'ProEnglish Angola - Inglês Especializado com IA Personal Tutor',
                'meta_description': 'A primeira plataforma de inglês feita para Angola. Cursos especializados para petróleo, bancos e TI. Preços em AOA, IA Personal Tutor. Mais de 10K angolanos aprendendo.',
                'meta_keywords': 'inglês angola, aprender inglês, IA tutor, sonangol, petróleo, bancos, telecomunicações, cursos inglês',
                'og_title': 'ProEnglish Angola - Inglês Especializado',
                'og_description': 'A única plataforma que combina IA com cursos especializados para setores angolanos. Preços em AOA, conteúdo adaptado para Angola.',
                'og_type': 'website',
                'twitter_card': 'summary_large_image',
                'twitter_title': 'ProEnglish Angola - Inglês com IA',
                'twitter_description': 'Inglês especializado para profissionais angolanos com IA Personal Tutor.',
                'index_page': True,
                'follow_links': True,
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated CMS:\n'
                f'- Settings: {"created" if created else "existed"}\n'
                f'- Hero: {"created" if created else "existed"}\n'
                f'- Stats: {len(stats_data)} items\n'
                f'- Companies: {len(companies_data)} items\n'
                f'- Services: {len(services_data)} items\n'
                f'- Pricing: {len(pricing_data)} tiers\n'
                f'- SEO: {"created" if created else "existed"}'
            )
        )