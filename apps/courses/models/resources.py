"""
Course resource models.

This module contains models for additional course resources like PDFs,
links, videos, and other supplementary materials.
"""

from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel
from apps.users.models import User

from .base import (
    ResourceChoices, OrderedModelMixin, 
    TimestampedModelMixin, MetadataModelMixin
)


class ChapterResource(BaseModel, OrderedModelMixin, TimestampedModelMixin, MetadataModelMixin):
    """
    Chapter Resources - PDFs, links, code examples, etc.
    Extends chapter functionality without breaking existing system.
    """
    
    ACCESS_LEVELS = [
        ('free', 'Free Access'),
        ('enrolled', 'Enrolled Students Only'),
        ('premium', 'Premium Students Only'),
        ('teacher', 'Teachers Only'),
    ]
    
    chapter = models.ForeignKey(
        'courses.Chapter',
        on_delete=models.CASCADE,
        related_name='resources'
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Resource title"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Resource description"
    )
    
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceChoices.RESOURCE_TYPES,
        help_text="Type of resource"
    )
    
    # File storage (for PDFs, videos, etc.)
    file = models.FileField(
        upload_to='chapter_resources/',
        null=True, blank=True,
        help_text="Uploaded file"
    )
    
    # External URL (for links, external videos, etc.)
    external_url = models.URLField(
        blank=True,
        help_text="External URL"
    )
    
    # File metadata
    file_size = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="File size in bytes"
    )
    
    file_format = models.CharField(
        max_length=20,
        blank=True,
        help_text="File format/extension"
    )
    
    # Usage tracking
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of downloads"
    )
    
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of views"
    )
    
    # Display settings
    is_featured = models.BooleanField(
        default=False,
        help_text="Show prominently in resources tab"
    )
    
    is_downloadable = models.BooleanField(
        default=True,
        help_text="Whether the resource can be downloaded"
    )
    
    # Access control
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVELS,
        default='enrolled',
        help_text="Who can access this resource"
    )
    
    # Availability settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the resource is currently active"
    )
    
    available_from = models.DateTimeField(
        null=True, blank=True,
        help_text="When the resource becomes available"
    )
    
    available_until = models.DateTimeField(
        null=True, blank=True,
        help_text="When the resource stops being available"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Teacher who created this resource"
    )
    
    class Meta:
        db_table = 'chapter_resources'
        verbose_name = 'Chapter Resource'
        verbose_name_plural = 'Chapter Resources'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['chapter', 'order']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_active']),
            models.Index(fields=['access_level']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.resource_type}) - {self.chapter.title}"
    
    def save(self, *args, **kwargs):
        # Auto-detect file format from uploaded file
        if self.file and not self.file_format:
            import os
            self.file_format = os.path.splitext(self.file.name)[1].lower()
        
        # Auto-detect file size
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (AttributeError, OSError):
                pass
        
        super().save(*args, **kwargs)
    
    def is_available(self):
        """Check if the resource is currently available."""
        if not self.is_active:
            return False
        
        from django.utils import timezone
        now = timezone.now()
        
        if self.available_from and now < self.available_from:
            return False
        
        if self.available_until and now > self.available_until:
            return False
        
        return True
    
    def can_be_accessed_by(self, user):
        """Check if a user can access this resource."""
        if not self.is_available():
            return False
        
        # Check access level
        if self.access_level == 'free':
            return True
        elif self.access_level == 'teacher':
            return user.role == 'teacher' or self.chapter.course.teacher == user
        elif self.access_level == 'enrolled':
            return self.chapter.course.is_enrolled(user)
        elif self.access_level == 'premium':
            # Check if user has premium access (implement based on your business logic)
            return self.chapter.course.is_enrolled(user)  # Simplified for now
        
        return False
    
    def get_file_url(self):
        """Get the appropriate URL for accessing this resource."""
        if self.file:
            return self.file.url
        elif self.external_url:
            return self.external_url
        return None
    
    def increment_download_count(self):
        """Increment the download count."""
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def increment_view_count(self):
        """Increment the view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def get_file_size_formatted(self):
        """Get formatted file size string."""
        if not self.file_size:
            return "Unknown"
        
        # Convert bytes to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def get_usage_stats(self):
        """Get usage statistics for this resource."""
        return {
            'downloads': self.download_count,
            'views': self.view_count,
            'total_interactions': self.download_count + self.view_count
        }


class ResourceCategory(BaseModel, TimestampedModelMixin):
    """
    Categories for organizing course resources.
    """
    
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='resource_categories'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Category name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Category description"
    )
    
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text="Category color (hex code)"
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class or name"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the category is active"
    )
    
    class Meta:
        db_table = 'resource_categories'
        verbose_name = 'Resource Category'
        verbose_name_plural = 'Resource Categories'
        ordering = ['order', 'name']
        unique_together = ['course', 'name']
        indexes = [
            models.Index(fields=['course', 'order']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.course.title} - {self.name}"
    
    def get_resources_count(self):
        """Get the number of resources in this category."""
        return self.resources.filter(is_active=True).count()


class ResourceTag(BaseModel):
    """
    Tags for categorizing and filtering resources.
    """
    
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Tag name"
    )
    
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text="Tag color (hex code)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Tag description"
    )
    
    class Meta:
        db_table = 'resource_tags'
        verbose_name = 'Resource Tag'
        verbose_name_plural = 'Resource Tags'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_resources_count(self):
        """Get the number of resources with this tag."""
        return self.resources.filter(is_active=True).count()


class ChapterResourceTag(BaseModel):
    """
    Many-to-many relationship between resources and tags.
    """
    
    resource = models.ForeignKey(
        ChapterResource,
        on_delete=models.CASCADE,
        related_name='resource_tags'
    )
    
    tag = models.ForeignKey(
        ResourceTag,
        on_delete=models.CASCADE,
        related_name='resources'
    )
    
    class Meta:
        db_table = 'chapter_resource_tags'
        verbose_name = 'Chapter Resource Tag'
        verbose_name_plural = 'Chapter Resource Tags'
        unique_together = ['resource', 'tag']
        indexes = [
            models.Index(fields=['resource']),
            models.Index(fields=['tag']),
        ]
    
    def __str__(self):
        return f"{self.resource.title} - {self.tag.name}"


class ResourceAccessLog(BaseModel):
    """
    Log of resource access for analytics and tracking.
    """
    
    ACCESS_TYPES = [
        ('view', 'View'),
        ('download', 'Download'),
        ('share', 'Share'),
    ]
    
    resource = models.ForeignKey(
        ChapterResource,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    
    user = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="User who accessed the resource (if logged in)"
    )
    
    access_type = models.CharField(
        max_length=20,
        choices=ACCESS_TYPES,
        help_text="Type of access"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="IP address of the access"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    referrer = models.URLField(
        blank=True,
        help_text="Referrer URL"
    )
    
    session_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Session identifier"
    )
    
    class Meta:
        db_table = 'resource_access_logs'
        verbose_name = 'Resource Access Log'
        verbose_name_plural = 'Resource Access Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['resource', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['access_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        user_info = self.user.name if self.user else "Anonymous"
        return f"{user_info} - {self.access_type} - {self.resource.title}"