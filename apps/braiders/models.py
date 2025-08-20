"""
Braiders models for the Tuwi platform.

Professional hair braiders and their services.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

from apps.core.models import BaseModel, Address
from apps.users.models import User


class Braider(BaseModel):
    """
    Professional braider profile.
    
    Improvements over original schema:
    - Better field organization
    - Proper relationship with User
    - Enhanced location handling
    - Portfolio management
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('beginner', 'Beginner (0-2 years)'),
        ('intermediate', 'Intermediate (2-5 years)'),
        ('advanced', 'Advanced (5-10 years)'),
        ('expert', 'Expert (10+ years)'),
    ]
    
    # Relationship with User (optional - can be created by admin)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='braider_profile'
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text="Professional name or business name"
    )
    contact_email = models.EmailField(
        help_text="Primary contact email for bookings"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Primary contact phone number"
    )
    bio = models.TextField(
        blank=True,
        help_text="Professional bio and description"
    )
    
    # Location Information (improved structure)
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='braiders',
        help_text="Primary business address"
    )
    service_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="List of areas where braider provides services"
    )
    provides_home_service = models.BooleanField(
        default=True,
        help_text="Whether braider goes to client's location"
    )
    has_physical_location = models.BooleanField(
        default=False,
        help_text="Whether braider has a physical salon/studio"
    )
    
    # Media
    profile_image = models.ImageField(
        upload_to='braiders/profiles/%Y/%m/',
        blank=True,
        null=True,
        help_text="Profile picture"
    )
    
    # Professional Information
    years_experience = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        null=True,
        blank=True,
        help_text="Years of professional experience"
    )
    experience_level = models.CharField(
        max_length=20,
        choices=EXPERIENCE_LEVELS,
        blank=True,
        help_text="Professional experience level"
    )
    specialties = models.JSONField(
        default=list,
        blank=True,
        help_text="List of specialties (e.g., 'Box Braids', 'Senegalese Twists')"
    )
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text="Professional certifications and courses"
    )
    
    # Status and Approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Approval status"
    )
    status_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection or suspension"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the braider was approved"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_braiders',
        help_text="Admin who approved this braider"
    )
    
    # Rating and Reviews (will be calculated via signals)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average rating from reviews"
    )
    total_reviews = models.PositiveIntegerField(
        default=0,
        help_text="Total number of reviews"
    )
    
    # Detailed ratings (calculated from reviews)
    quality_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average quality rating"
    )
    professionalism_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average professionalism rating"
    )
    communication_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average communication rating"
    )
    value_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average value for money rating"
    )
    
    # Featured Status
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether braider is featured on homepage"
    )
    featured_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When featured status expires"
    )
    
    # Business Information
    availability_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Weekly availability schedule"
    )
    pricing_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Base pricing information and policies"
    )
    booking_advance_days = models.PositiveIntegerField(
        default=1,
        help_text="Minimum days in advance for booking"
    )
    cancellation_policy = models.TextField(
        blank=True,
        help_text="Cancellation and refund policy"
    )
    
    # Social Media
    instagram_handle = models.CharField(
        max_length=100,
        blank=True,
        help_text="Instagram username (without @)"
    )
    facebook_url = models.URLField(
        blank=True,
        help_text="Facebook page URL"
    )
    website_url = models.URLField(
        blank=True,
        help_text="Personal website or portfolio"
    )
    
    class Meta:
        verbose_name = 'Braider'
        verbose_name_plural = 'Braiders'
        db_table = 'braiders'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['created_at']),
            models.Index(fields=['approved_at']),
        ]
        
    def __str__(self):
        return self.name
    
    @property
    def is_active(self):
        """Check if braider is active and approved."""
        return self.status == 'approved'
    
    @property
    def is_featured_now(self):
        """Check if braider is currently featured."""
        if not self.is_featured:
            return False
        if self.featured_until and self.featured_until < timezone.now():
            return False
        return True
    
    @property
    def location_display(self):
        """Get display-friendly location."""
        if self.address:
            return f"{self.address.city}, {self.address.district}"
        return "Location not specified"
    
    def can_provide_service_at_location(self, location_type='home'):
        """Check if braider can provide service at given location type."""
        if location_type == 'home':
            return self.provides_home_service
        elif location_type == 'salon':
            return self.has_physical_location
        return False


class BraiderPortfolioImage(BaseModel):
    """
    Portfolio images for braiders.
    
    Separate model for better management and performance.
    """
    
    braider = models.ForeignKey(
        Braider,
        on_delete=models.CASCADE,
        related_name='portfolio_images'
    )
    image = models.ImageField(
        upload_to='braiders/portfolio/%Y/%m/',
        help_text="Portfolio image"
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Image title or description"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the work"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorizing the image"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this image should be featured in profile"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in portfolio"
    )
    
    class Meta:
        verbose_name = 'Portfolio Image'
        verbose_name_plural = 'Portfolio Images'
        db_table = 'braider_portfolio_images'
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['braider', 'is_featured']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"{self.braider.name} - {self.title or 'Portfolio Image'}"


class Service(BaseModel):
    """
    Services offered by braiders.
    
    Improvements:
    - Better categorization
    - Enhanced pricing options
    - Detailed service information
    """
    
    CATEGORY_CHOICES = [
        ('braids', 'Tranças'),
        ('twists', 'Twists'),
        ('locs', 'Locs/Dreadlocks'),
        ('protective', 'Penteados Protetores'),
        ('natural_care', 'Cuidados Naturais'),
        ('styling', 'Penteados e Styling'),
        ('maintenance', 'Manutenção'),
        ('consultation', 'Consultoria'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('beginner', 'Iniciante'),
        ('intermediate', 'Intermediário'),
        ('advanced', 'Avançado'),
        ('expert', 'Especialista'),
    ]
    
    HAIR_TYPES = [
        ('1a', 'Tipo 1A - Liso Fino'),
        ('1b', 'Tipo 1B - Liso Médio'),
        ('1c', 'Tipo 1C - Liso Grosso'),
        ('2a', 'Tipo 2A - Ondulado Fino'),
        ('2b', 'Tipo 2B - Ondulado Médio'),
        ('2c', 'Tipo 2C - Ondulado Grosso'),
        ('3a', 'Tipo 3A - Cacheado Solto'),
        ('3b', 'Tipo 3B - Cacheado Médio'),
        ('3c', 'Tipo 3C - Cacheado Apertado'),
        ('4a', 'Tipo 4A - Crespo Macio'),
        ('4b', 'Tipo 4B - Crespo Médio'),
        ('4c', 'Tipo 4C - Crespo Apertado'),
    ]
    
    braider = models.ForeignKey(
        Braider,
        on_delete=models.CASCADE,
        related_name='services'
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text="Service name"
    )
    description = models.TextField(
        help_text="Detailed description of the service"
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Brief description for listings"
    )
    
    # Categorization
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Service category"
    )
    subcategory = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific subcategory or style"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional tags for search and filtering"
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Base price for the service"
    )
    price_varies = models.BooleanField(
        default=False,
        help_text="Whether price varies based on factors (length, complexity, etc.)"
    )
    price_from = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Starting price (when price varies)"
    )
    price_to = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum price (when price varies)"
    )
    price_factors = models.JSONField(
        default=list,
        blank=True,
        help_text="Factors that affect pricing (e.g., hair length, extensions needed)"
    )
    
    # Duration
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(15)],
        help_text="Estimated duration in minutes"
    )
    duration_varies = models.BooleanField(
        default=False,
        help_text="Whether duration varies"
    )
    min_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum duration when varies"
    )
    max_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum duration when varies"
    )
    
    # Service Details
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_LEVELS,
        blank=True,
        help_text="Difficulty level of the service"
    )
    hair_type_compatibility = models.JSONField(
        default=list,
        blank=True,
        help_text="Compatible hair types"
    )
    required_hair_length = models.CharField(
        max_length=100,
        blank=True,
        help_text="Minimum hair length required"
    )
    
    # Requirements and Materials
    client_preparation = models.TextField(
        blank=True,
        help_text="What client needs to do before appointment"
    )
    braider_provides = models.JSONField(
        default=list,
        blank=True,
        help_text="Materials/products provided by braider"
    )
    client_brings = models.JSONField(
        default=list,
        blank=True,
        help_text="Materials client needs to bring"
    )
    
    # Care Instructions
    aftercare_instructions = models.TextField(
        blank=True,
        help_text="How to care for the style"
    )
    maintenance_schedule = models.CharField(
        max_length=200,
        blank=True,
        help_text="Recommended maintenance schedule"
    )
    style_duration = models.CharField(
        max_length=100,
        blank=True,
        help_text="How long the style typically lasts"
    )
    
    # Media
    image = models.ImageField(
        upload_to='services/%Y/%m/',
        blank=True,
        null=True,
        help_text="Main service image"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether service is currently offered"
    )
    is_popular = models.BooleanField(
        default=False,
        help_text="Whether service should be highlighted as popular"
    )
    
    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        db_table = 'services'
        indexes = [
            models.Index(fields=['braider', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['base_price']),
            models.Index(fields=['is_popular']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.braider.name} - {self.name}"
    
    @property
    def price_display(self):
        """Get display-friendly price."""
        if self.price_varies and self.price_from and self.price_to:
            return f"€{self.price_from} - €{self.price_to}"
        return f"€{self.base_price}"
    
    @property
    def duration_display(self):
        """Get display-friendly duration."""
        if self.duration_varies and self.min_duration and self.max_duration:
            return f"{self.min_duration//60}h{self.min_duration%60:02d} - {self.max_duration//60}h{self.max_duration%60:02d}"
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}h{minutes:02d}"
        return f"{minutes}min"
    
    def is_suitable_for_hair_type(self, hair_type):
        """Check if service is suitable for given hair type."""
        if not self.hair_type_compatibility:
            return True  # No restrictions
        return hair_type in self.hair_type_compatibility


class ServiceImage(BaseModel):
    """
    Additional images for services (before/after, process shots, etc.).
    """
    
    IMAGE_TYPES = [
        ('before', 'Before'),
        ('after', 'After'),
        ('process', 'Process'),
        ('detail', 'Detail'),
        ('styling', 'Styling Option'),
    ]
    
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(
        upload_to='services/gallery/%Y/%m/',
        help_text="Service image"
    )
    image_type = models.CharField(
        max_length=20,
        choices=IMAGE_TYPES,
        default='after',
        help_text="Type of image"
    )
    caption = models.CharField(
        max_length=500,
        blank=True,
        help_text="Image caption or description"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    class Meta:
        verbose_name = 'Service Image'
        verbose_name_plural = 'Service Images'
        db_table = 'service_images'
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['service', 'image_type']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.get_image_type_display()}"