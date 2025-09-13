from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class LandingPageSettings(models.Model):
    """Configura��es gerais da landing page"""
    
    # Meta information
    site_title = models.CharField(max_length=200, default="ProEnglish Angola")
    site_description = models.TextField(default="A primeira plataforma de ingl�s feita para Angola")
    meta_keywords = models.TextField(blank=True, help_text="Palavras-chave separadas por v�rgula")
    
    # Contact information
    contact_email = models.EmailField(default="contato@proenglish.ao")
    contact_phone = models.CharField(max_length=50, default="+244 923 456 789")
    whatsapp_number = models.CharField(max_length=50, default="+244923456789")
    
    # Social media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    
    # Analytics
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)
    
    # Settings flags
    is_active = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configura��es da Landing Page"
        verbose_name_plural = "Configura��es da Landing Page"
    
    def __str__(self):
        return f"Configura��es - {self.site_title}"


class HeroSection(models.Model):
    """Se��o Hero da landing page"""
    
    # Badge
    badge_text = models.CharField(
        max_length=200, 
        default="<�<� A primeira plataforma de ingl�s feita para Angola"
    )
    badge_is_active = models.BooleanField(default=True)
    
    # Main content
    headline = models.CharField(
        max_length=300,
        default="Ingl�s Especializado"
    )
    headline_highlight = models.CharField(
        max_length=200,
        default="com IA Personal Tutor"
    )
    description = models.TextField(
        default="A �nica plataforma que combina intelig�ncia artificial com cursos especializados para setores como petr�leo, bancos e TI. Pre�os em AOA, conte�do adaptado para Angola."
    )
    
    # CTA Buttons
    primary_cta_text = models.CharField(max_length=100, default="Come�ar Gr�tis - 7 Dias")
    primary_cta_url = models.CharField(max_length=200, default="/signup")
    secondary_cta_text = models.CharField(max_length=100, default="Ver Demo do IA Tutor")
    secondary_cta_url = models.CharField(max_length=200, default="#demo")
    
    # Social proof
    social_proof_text = models.CharField(max_length=200, default="Mais de 10.000 angolanos")
    rating_value = models.DecimalField(max_digits=2, decimal_places=1, default=4.9)
    rating_count = models.CharField(max_length=50, default="2.1k reviews")
    
    # Background images
    hero_image = models.ImageField(upload_to='cms/hero/', blank=True, null=True)
    background_video = models.FileField(upload_to='cms/hero/videos/', blank=True, null=True)
    
    # Display settings
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Se��o Hero"
        verbose_name_plural = "Se��es Hero"
        ordering = ['order']
    
    def __str__(self):
        return f"Hero: {self.headline}"


class StatItem(models.Model):
    """Estat�sticas mostradas na hero e outras se��es"""
    
    value = models.CharField(max_length=20, help_text="Ex: 10K+, 94%, 50+")
    label = models.CharField(max_length=100, help_text="Ex: Angolanos aprendendo")
    icon = models.CharField(max_length=50, blank=True, help_text="Nome do �cone Lucide")
    
    # Display settings
    section = models.CharField(
        max_length=50,
        choices=[
            ('hero', 'Hero Section'),
            ('about', 'About Section'),
            ('footer', 'Footer'),
        ],
        default='hero'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Estat�stica"
        verbose_name_plural = "Estat�sticas"
        ordering = ['section', 'order']
    
    def __str__(self):
        return f"{self.value} - {self.label}"


class Company(models.Model):
    """Empresas parceiras e clientes"""
    
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='cms/companies/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    # Categories
    category = models.CharField(
        max_length=50,
        choices=[
            ('oil_gas', 'Petr�leo & G�s'),
            ('banking', 'Banc�rio'),
            ('telecoms', 'Telecomunica��es'),
            ('government', 'Governo'),
            ('education', 'Educa��o'),
            ('technology', 'Tecnologia'),
            ('other', 'Outros'),
        ],
        default='other'
    )
    
    # Display settings
    show_in_hero = models.BooleanField(default=False)
    show_in_ticker = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ServiceItem(models.Model):
    """Serviços especializados oferecidos"""
    
    SERVICE_TYPES = [
        ('course', 'Curso Especializado'),
        ('practice_lab', 'Practice Lab'),
        ('ai_tutor', 'IA Personal Tutor'),
        ('other', 'Outros'),
    ]
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField()
    icon = models.CharField(max_length=10, help_text="Emoji ou símbolo")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, default='course')
    
    # Service metadata
    target_companies = models.ManyToManyField(Company, blank=True)
    student_count = models.CharField(max_length=20, default="1K+")
    level = models.CharField(max_length=100, default="Iniciante-Avançado")
    duration = models.CharField(max_length=100, default="2-6 meses")
    certification = models.CharField(max_length=200, default="Certificado ProEnglish")
    
    # Visual elements
    service_image = models.ImageField(upload_to='cms/services/', blank=True, null=True)
    gradient_from = models.CharField(max_length=50, default="violet-600")
    gradient_to = models.CharField(max_length=50, default="purple-600")
    
    # Content structure
    features = models.JSONField(default=list, help_text="Lista de features do serviço")
    curriculum_topics = models.JSONField(default=list, help_text="Tópicos do currículo")
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title


class PricingTier(models.Model):
    """Planos de preços da plataforma"""
    
    # Basic information
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, help_text="Emoji")
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="AOA")
    
    # Discounts
    yearly_discount_text = models.CharField(max_length=100, blank=True)
    promotional_badge = models.CharField(max_length=100, blank=True)
    
    # Content
    description = models.TextField(blank=True)
    angola_benefit = models.TextField(help_text="Benefício específico para Angola")
    features = models.JSONField(default=list, help_text="Lista de features do plano")
    
    # CTA
    button_text = models.CharField(max_length=100, default="Escolher Plano")
    button_url = models.CharField(max_length=200, default="/signup")
    
    # Design
    is_popular = models.BooleanField(default=False)
    is_inverse_design = models.BooleanField(default=False)
    gradient_from = models.CharField(max_length=50, default="violet-600")
    gradient_to = models.CharField(max_length=50, default="purple-600")
    
    # Display settings
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Plano de Preços"
        verbose_name_plural = "Planos de Preços"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.title} - {self.monthly_price} {self.currency}/mês"


class Feature(models.Model):
    """Funcionalidades da plataforma"""
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Nome do ícone Lucide")
    
    # Visual design
    gradient_from = models.CharField(max_length=50, default="violet-600")
    gradient_to = models.CharField(max_length=50, default="purple-600")
    background_image = models.ImageField(upload_to='cms/features/', blank=True, null=True)
    
    # Content details
    benefits = models.JSONField(default=list, help_text="Lista de benefícios")
    use_cases = models.JSONField(default=list, help_text="Casos de uso")
    
    # Layout
    grid_column_span = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="Quantas colunas ocupar no grid (1-3)"
    )
    
    # Display settings
    is_highlighted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Funcionalidade"
        verbose_name_plural = "Funcionalidades"
        ordering = ['order']
    
    def __str__(self):
        return self.title


class Testimonial(models.Model):
    """Depoimentos de clientes"""
    
    # Client information
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=200, help_text="Cargo/Função")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=100, default="Luanda")
    avatar = models.ImageField(upload_to='cms/testimonials/', blank=True, null=True)
    
    # Testimonial content
    text = models.TextField()
    result_achieved = models.CharField(max_length=200, help_text="Resultado alcançado")
    rating = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Categorization
    sector = models.CharField(
        max_length=50,
        choices=[
            ('oil_gas', 'Petróleo & Gás'),
            ('banking', 'Bancário'),
            ('telecoms', 'Telecomunicações'),
            ('government', 'Governo'),
            ('education', 'Educação'),
            ('technology', 'Tecnologia'),
            ('other', 'Outros'),
        ],
        default='other'
    )
    
    # Metadata
    date_given = models.DateField(default=timezone.now)
    verified = models.BooleanField(default=False)
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Depoimento"
        verbose_name_plural = "Depoimentos"
        ordering = ['order', '-date_given']
    
    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else 'Cliente'}"


class FAQItem(models.Model):
    """Perguntas frequentes"""
    
    question = models.CharField(max_length=300)
    answer = models.TextField()
    
    # Categorization
    category = models.CharField(
        max_length=50,
        choices=[
            ('general', 'Geral'),
            ('pricing', 'Preços'),
            ('technical', 'Técnico'),
            ('courses', 'Cursos'),
            ('payment', 'Pagamento'),
            ('support', 'Suporte'),
        ],
        default='general'
    )
    
    # SEO
    keywords = models.CharField(max_length=200, blank=True)
    
    # Display settings
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['category', 'order']
    
    def __str__(self):
        return self.question[:100]


class CallToAction(models.Model):
    """Chamadas para ação espalhadas pela página"""
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    
    # Button configuration
    primary_button_text = models.CharField(max_length=100)
    primary_button_url = models.CharField(max_length=200)
    secondary_button_text = models.CharField(max_length=100, blank=True)
    secondary_button_url = models.CharField(max_length=200, blank=True)
    
    # Visual elements
    icon = models.CharField(max_length=50, help_text="Nome do ícone Lucide")
    background_image = models.ImageField(upload_to='cms/cta/', blank=True, null=True)
    gradient_from = models.CharField(max_length=50, default="violet-600")
    gradient_to = models.CharField(max_length=50, default="purple-600")
    
    # Positioning
    section = models.CharField(
        max_length=50,
        choices=[
            ('hero', 'Hero Section'),
            ('middle', 'Middle Section'),
            ('pricing', 'After Pricing'),
            ('footer', 'Before Footer'),
        ],
        default='middle'
    )
    
    # Display settings
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Call to Action"
        verbose_name_plural = "Calls to Action"
        ordering = ['section', 'order']
    
    def __str__(self):
        return f"{self.title} ({self.section})"


class SeoSettings(models.Model):
    """Configurações de SEO específicas por página"""
    
    page_type = models.CharField(
        max_length=50,
        choices=[
            ('home', 'Página Inicial'),
            ('pricing', 'Preços'),
            ('about', 'Sobre'),
            ('contact', 'Contato'),
        ],
        unique=True
    )
    
    # Meta tags
    meta_title = models.CharField(max_length=200)
    meta_description = models.CharField(max_length=300)
    meta_keywords = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True)
    
    # Open Graph
    og_title = models.CharField(max_length=200, blank=True)
    og_description = models.CharField(max_length=300, blank=True)
    og_image = models.ImageField(upload_to='cms/seo/', blank=True, null=True)
    og_type = models.CharField(max_length=50, default="website")
    
    # Twitter Card
    twitter_card = models.CharField(max_length=50, default="summary_large_image")
    twitter_title = models.CharField(max_length=200, blank=True)
    twitter_description = models.CharField(max_length=300, blank=True)
    twitter_image = models.ImageField(upload_to='cms/seo/', blank=True, null=True)
    
    # Schema.org
    schema_markup = models.JSONField(default=dict, help_text="Schema.org JSON-LD")
    
    # Settings
    index_page = models.BooleanField(default=True)
    follow_links = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração SEO"
        verbose_name_plural = "Configurações SEO"
    
    def __str__(self):
        return f"SEO - {self.get_page_type_display()}"