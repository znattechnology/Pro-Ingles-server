"""
Django signals for ratings and reviews system.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count

from .models import BraiderReview, ProductReview, ReviewHelpfulness
from apps.braiders.models import Braider
from apps.ecommerce.models import Product


@receiver(post_save, sender=BraiderReview)
def update_braider_rating(sender, instance, created, **kwargs):
    """Update braider's average rating when a review is created or updated."""
    if instance.status == 'approved':
        braider = instance.braider
        
        # Calculate new average rating from approved reviews
        approved_reviews = BraiderReview.objects.filter(
            braider=braider,
            status='approved'
        )
        
        if approved_reviews.exists():
            avg_rating = approved_reviews.aggregate(
                overall=Avg('overall_rating'),
                quality=Avg('quality_rating'),
                professionalism=Avg('professionalism_rating'),
                communication=Avg('communication_rating'),
                value=Avg('value_rating'),
                total_count=Count('id')
            )
            
            # Update braider ratings
            braider.average_rating = round(avg_rating['overall'] or 0, 2)
            braider.total_reviews = avg_rating['total_count']
            
            # Update detailed ratings
            braider.quality_rating = round(avg_rating['quality'] or 0, 2)
            braider.professionalism_rating = round(avg_rating['professionalism'] or 0, 2)
            braider.communication_rating = round(avg_rating['communication'] or 0, 2)
            braider.value_rating = round(avg_rating['value'] or 0, 2)
            
            braider.save(update_fields=[
                'average_rating', 'total_reviews', 'quality_rating',
                'professionalism_rating', 'communication_rating', 'value_rating'
            ])


@receiver(post_delete, sender=BraiderReview)
def update_braider_rating_on_delete(sender, instance, **kwargs):
    """Update braider's average rating when a review is deleted."""
    if instance.status == 'approved':
        braider = instance.braider
        
        # Recalculate ratings after deletion
        approved_reviews = BraiderReview.objects.filter(
            braider=braider,
            status='approved'
        )
        
        if approved_reviews.exists():
            avg_rating = approved_reviews.aggregate(
                overall=Avg('overall_rating'),
                quality=Avg('quality_rating'),
                professionalism=Avg('professionalism_rating'),
                communication=Avg('communication_rating'),
                value=Avg('value_rating'),
                total_count=Count('id')
            )
            
            braider.average_rating = round(avg_rating['overall'] or 0, 2)
            braider.total_reviews = avg_rating['total_count']
            braider.quality_rating = round(avg_rating['quality'] or 0, 2)
            braider.professionalism_rating = round(avg_rating['professionalism'] or 0, 2)
            braider.communication_rating = round(avg_rating['communication'] or 0, 2)
            braider.value_rating = round(avg_rating['value'] or 0, 2)
        else:
            # No reviews left, reset ratings
            braider.average_rating = 0
            braider.total_reviews = 0
            braider.quality_rating = 0
            braider.professionalism_rating = 0
            braider.communication_rating = 0
            braider.value_rating = 0
        
        braider.save(update_fields=[
            'average_rating', 'total_reviews', 'quality_rating',
            'professionalism_rating', 'communication_rating', 'value_rating'
        ])


@receiver(post_save, sender=ProductReview)
def update_product_rating(sender, instance, created, **kwargs):
    """Update product's average rating when a review is created or updated."""
    if instance.status == 'approved':
        product = instance.product
        
        # Calculate new average rating from approved reviews
        approved_reviews = ProductReview.objects.filter(
            product=product,
            status='approved'
        )
        
        if approved_reviews.exists():
            avg_rating = approved_reviews.aggregate(
                overall=Avg('rating'),
                quality=Avg('quality_rating'),
                value=Avg('value_rating'),
                total_count=Count('id')
            )
            
            # Update product ratings
            product.average_rating = round(avg_rating['overall'] or 0, 2)
            product.total_reviews = avg_rating['total_count']
            
            product.save(update_fields=['average_rating', 'total_reviews'])


@receiver(post_delete, sender=ProductReview)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """Update product's average rating when a review is deleted."""
    if instance.status == 'approved':
        product = instance.product
        
        # Recalculate ratings after deletion
        approved_reviews = ProductReview.objects.filter(
            product=product,
            status='approved'
        )
        
        if approved_reviews.exists():
            avg_rating = approved_reviews.aggregate(
                overall=Avg('rating'),
                total_count=Count('id')
            )
            
            product.average_rating = round(avg_rating['overall'] or 0, 2)
            product.total_reviews = avg_rating['total_count']
        else:
            # No reviews left, reset ratings
            product.average_rating = 0
            product.total_reviews = 0
        
        product.save(update_fields=['average_rating', 'total_reviews'])


@receiver(post_save, sender=ReviewHelpfulness)
def update_review_helpfulness_counts(sender, instance, created, **kwargs):
    """Update helpfulness counts when a vote is created or updated."""
    if created:
        # Determine which review to update
        review = instance.braider_review or instance.product_review
        
        if review:
            # Recalculate helpfulness counts
            helpful_count = review.helpfulness_votes.filter(vote='helpful').count()
            not_helpful_count = review.helpfulness_votes.filter(vote='not_helpful').count()
            
            review.helpful_count = helpful_count
            review.not_helpful_count = not_helpful_count
            review.save(update_fields=['helpful_count', 'not_helpful_count'])


@receiver(post_delete, sender=ReviewHelpfulness)
def update_review_helpfulness_counts_on_delete(sender, instance, **kwargs):
    """Update helpfulness counts when a vote is deleted."""
    # Determine which review to update
    review = instance.braider_review or instance.product_review
    
    if review:
        # Recalculate helpfulness counts
        helpful_count = review.helpfulness_votes.filter(vote='helpful').count()
        not_helpful_count = review.helpfulness_votes.filter(vote='not_helpful').count()
        
        review.helpful_count = helpful_count
        review.not_helpful_count = not_helpful_count
        review.save(update_fields=['helpful_count', 'not_helpful_count'])