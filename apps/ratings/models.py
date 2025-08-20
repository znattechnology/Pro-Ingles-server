"""
Models for ratings and reviews system.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import BaseModel
from apps.braiders.models import Braider
from apps.ecommerce.models import Product, Order
from apps.bookings.models import Booking

User = get_user_model()


class BraiderReview(BaseModel):
    """Reviews for braiders based on completed bookings."""
    
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'), 
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Moderation'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]
    
    # Review details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='braider_reviews')
    braider = models.ForeignKey(Braider, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(
        Booking, 
        on_delete=models.CASCADE, 
        related_name='review',
        help_text="The completed booking this review is based on"
    )
    
    # Rating and content
    overall_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Detailed ratings
    quality_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Quality of work"
    )
    professionalism_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Professionalism and punctuality"
    )
    communication_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication quality"
    )
    value_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Value for money"
    )
    
    # Review content
    title = models.CharField(max_length=200, help_text="Brief review title")
    comment = models.TextField(help_text="Detailed review comment")
    
    # Recommendations
    would_recommend = models.BooleanField(
        default=True,
        help_text="Would you recommend this braider?"
    )
    
    # Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    moderation_notes = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='moderated_braider_reviews'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    # Helpfulness tracking
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Verification
    is_verified = models.BooleanField(
        default=True,
        help_text="Review is from a verified booking"
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'booking']  # One review per booking
        indexes = [
            models.Index(fields=['braider', 'status']),
            models.Index(fields=['braider', 'overall_rating']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['is_verified']),
        ]
        verbose_name = 'Braider Review'
        verbose_name_plural = 'Braider Reviews'
    
    def __str__(self):
        return f"Review of {self.braider.name} by {self.user.email} ({self.overall_rating}★)"
    
    @property
    def average_detailed_rating(self):
        """Calculate average of detailed ratings."""
        ratings = [
            self.quality_rating,
            self.professionalism_rating,
            self.communication_rating,
            self.value_rating
        ]
        return sum(ratings) / len(ratings)
    
    @property
    def helpfulness_ratio(self):
        """Calculate helpfulness ratio."""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100
    
    def save(self, *args, **kwargs):
        # Auto-approve reviews from verified bookings initially
        if self._state.adding and self.booking and self.booking.status == 'completed':
            self.is_verified = True
            self.status = 'approved'
        
        super().save(*args, **kwargs)


class ProductReview(BaseModel):
    """Reviews for products based on purchase verification."""
    
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Moderation'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]
    
    # Review details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        help_text="The order this review is based on"
    )
    
    # Rating and content
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Review content
    title = models.CharField(max_length=200, help_text="Brief review title")
    comment = models.TextField(help_text="Detailed review comment")
    
    # Product-specific ratings
    quality_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Product quality"
    )
    value_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Value for money"
    )
    
    # Recommendations
    would_recommend = models.BooleanField(
        default=True,
        help_text="Would you recommend this product?"
    )
    
    # Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    moderation_notes = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_product_reviews'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    # Helpfulness tracking
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Verification
    is_verified_purchase = models.BooleanField(
        default=True,
        help_text="Review is from a verified purchase"
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'product', 'order']  # One review per product per order
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['product', 'rating']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['is_verified_purchase']),
        ]
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'
    
    def __str__(self):
        return f"Review of {self.product.name} by {self.user.email} ({self.rating}★)"
    
    @property
    def helpfulness_ratio(self):
        """Calculate helpfulness ratio."""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100
    
    def save(self, *args, **kwargs):
        # Auto-verify if order is delivered
        if self._state.adding and self.order and self.order.status == 'delivered':
            self.is_verified_purchase = True
            self.status = 'approved'
        
        super().save(*args, **kwargs)


class ReviewImage(BaseModel):
    """Images attached to reviews."""
    
    IMAGE_TYPES = [
        ('before', 'Before Photo'),
        ('after', 'After Photo'),
        ('process', 'Process Photo'),
        ('product', 'Product Photo'),
        ('general', 'General Photo'),
    ]
    
    # Link to either braider or product review
    braider_review = models.ForeignKey(
        BraiderReview,
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True
    )
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True
    )
    
    # Image details
    image = models.ImageField(upload_to='review_images/')
    caption = models.CharField(max_length=200, blank=True)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='general')
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['braider_review', 'image_type']),
            models.Index(fields=['product_review', 'image_type']),
        ]
    
    def __str__(self):
        if self.braider_review:
            return f"Image for braider review {self.braider_review.id}"
        elif self.product_review:
            return f"Image for product review {self.product_review.id}"
        return f"Review image {self.id}"
    
    def clean(self):
        """Ensure image belongs to either braider or product review, not both."""
        if not self.braider_review and not self.product_review:
            raise ValidationError("Image must belong to either braider or product review")
        if self.braider_review and self.product_review:
            raise ValidationError("Image cannot belong to both braider and product review")


class ReviewHelpfulness(BaseModel):
    """Track user votes on review helpfulness."""
    
    VOTE_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Link to either braider or product review
    braider_review = models.ForeignKey(
        BraiderReview,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes',
        null=True,
        blank=True
    )
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes',
        null=True,
        blank=True
    )
    
    vote = models.CharField(max_length=20, choices=VOTE_CHOICES)
    
    class Meta:
        unique_together = [
            ['user', 'braider_review'],
            ['user', 'product_review']
        ]
        indexes = [
            models.Index(fields=['braider_review', 'vote']),
            models.Index(fields=['product_review', 'vote']),
        ]
    
    def __str__(self):
        review_type = "braider" if self.braider_review else "product"
        return f"{self.user.email} voted {self.vote} on {review_type} review"
    
    def clean(self):
        """Ensure vote belongs to either braider or product review, not both."""
        if not self.braider_review and not self.product_review:
            raise ValidationError("Vote must be for either braider or product review")
        if self.braider_review and self.product_review:
            raise ValidationError("Vote cannot be for both braider and product review")


class ReviewResponse(BaseModel):
    """Official responses to reviews from braiders or admin."""
    
    # Link to either braider or product review
    braider_review = models.OneToOneField(
        BraiderReview,
        on_delete=models.CASCADE,
        related_name='response',
        null=True,
        blank=True
    )
    product_review = models.OneToOneField(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='response',
        null=True,
        blank=True
    )
    
    # Response details
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="User who wrote the response (braider or admin)"
    )
    response_text = models.TextField(help_text="Official response to the review")
    
    # Status
    is_official = models.BooleanField(
        default=True,
        help_text="Is this an official response?"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['braider_review']),
            models.Index(fields=['product_review']),
            models.Index(fields=['responder']),
        ]
    
    def __str__(self):
        review_type = "braider" if self.braider_review else "product"
        return f"Response to {review_type} review by {self.responder.email}"
    
    def clean(self):
        """Ensure response belongs to either braider or product review, not both."""
        if not self.braider_review and not self.product_review:
            raise ValidationError("Response must be for either braider or product review")
        if self.braider_review and self.product_review:
            raise ValidationError("Response cannot be for both braider and product review")


class ReviewReport(BaseModel):
    """Reports of inappropriate reviews."""
    
    REPORT_REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('fake', 'Fake Review'),
        ('offensive', 'Offensive Language'),
        ('irrelevant', 'Irrelevant Content'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Reporter
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_reports')
    
    # Link to either braider or product review
    braider_review = models.ForeignKey(
        BraiderReview,
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    
    # Report details
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(help_text="Detailed description of the issue")
    
    # Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [
            ['reporter', 'braider_review'],
            ['reporter', 'product_review']
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['reason']),
            models.Index(fields=['braider_review']),
            models.Index(fields=['product_review']),
        ]
    
    def __str__(self):
        review_type = "braider" if self.braider_review else "product"
        return f"Report of {review_type} review by {self.reporter.email}"
    
    def clean(self):
        """Ensure report is for either braider or product review, not both."""
        if not self.braider_review and not self.product_review:
            raise ValidationError("Report must be for either braider or product review")
        if self.braider_review and self.product_review:
            raise ValidationError("Report cannot be for both braider and product review")