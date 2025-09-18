"""
Base classes and constants for course models.

This module contains shared choices, mixins, and base functionality
used across multiple course models.
"""

from django.db import models


# Shared choices for course models
class CourseChoices:
    """Course-specific choices and constants."""
    
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    ]
    
    TEMPLATE_CHOICES = [
        ('general', 'Inglês Geral'),
        ('business', 'Inglês para Negócios'),
        ('technology', 'Inglês para Tecnologia'),
        ('medical', 'Inglês Médico'),
        ('legal', 'Inglês Jurídico'),
    ]
    
    COURSE_TYPE_CHOICES = [
        ('video', 'Curso de Vídeo'),
        ('practice', 'Curso do Laboratório'),
    ]


class ChapterChoices:
    """Chapter-specific choices and constants."""
    
    TYPE_CHOICES = [
        ('Text', 'Text'),
        ('Quiz', 'Quiz'),
        ('Video', 'Video'),
    ]


class ResourceChoices:
    """Resource-specific choices and constants."""
    
    RESOURCE_TYPES = [
        ('PDF', 'PDF Document'),
        ('LINK', 'External Link'),
        ('VIDEO', 'Supplementary Video'),
        ('CODE', 'Code Examples'),
        ('WORKSHEET', 'Exercise Worksheet'),
        ('AUDIO', 'Audio File'),
        ('IMAGE', 'Image/Infographic'),
    ]


class TransactionChoices:
    """Transaction-specific choices and constants."""
    
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
    ]


class OrderedModelMixin(models.Model):
    """
    Abstract mixin for models that need ordering functionality.
    """
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    class Meta:
        abstract = True
        ordering = ['order', 'created_at']


class TimestampedModelMixin(models.Model):
    """
    Abstract mixin for models that need timestamp functionality.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class ProgressTrackingMixin(models.Model):
    """
    Abstract mixin for models that track completion/progress.
    """
    completed = models.BooleanField(
        default=False,
        help_text="Whether this item has been completed"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this item was completed"
    )
    
    class Meta:
        abstract = True
    
    def mark_complete(self):
        """Mark this item as completed with timestamp."""
        from django.utils import timezone
        self.completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['completed', 'completed_at'])
    
    def mark_incomplete(self):
        """Mark this item as incomplete."""
        self.completed = False
        self.completed_at = None
        self.save(update_fields=['completed', 'completed_at'])


class StatisticsModelMixin(models.Model):
    """
    Abstract mixin for models that track statistics.
    """
    total_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Total attempts by all users"
    )
    
    total_completions = models.PositiveIntegerField(
        default=0,
        help_text="Total successful completions"
    )
    
    average_score = models.FloatField(
        default=0.0,
        help_text="Average score across all attempts"
    )
    
    class Meta:
        abstract = True
    
    @property
    def completion_rate(self):
        """Calculate completion rate percentage."""
        if self.total_attempts == 0:
            return 0
        return round((self.total_completions / self.total_attempts) * 100, 1)
    
    def update_statistics(self, new_score=None, is_completion=False):
        """Update model statistics with new data."""
        self.total_attempts += 1
        
        if is_completion:
            self.total_completions += 1
        
        if new_score is not None:
            # Recalculate average score
            total_score = (self.average_score * (self.total_attempts - 1)) + new_score
            self.average_score = total_score / self.total_attempts
        
        self.save(update_fields=['total_attempts', 'total_completions', 'average_score'])


class MetadataModelMixin(models.Model):
    """
    Abstract mixin for models that need metadata storage.
    """
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata for this model"
    )
    
    class Meta:
        abstract = True
    
    def get_metadata(self, key, default=None):
        """Get a specific metadata value."""
        return self.metadata.get(key, default)
    
    def set_metadata(self, key, value):
        """Set a specific metadata value."""
        self.metadata[key] = value
        self.save(update_fields=['metadata'])
    
    def update_metadata(self, updates_dict):
        """Update multiple metadata values at once."""
        self.metadata.update(updates_dict)
        self.save(update_fields=['metadata'])