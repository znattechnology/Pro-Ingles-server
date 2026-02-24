"""
Student Engagement Models

This module contains models for student engagement features:
- CourseWishlist: Courses students want to take
- CourseReview: Student reviews and ratings
- StudentNote: Personal notes on chapters
- StudentBookmark: Bookmarked chapters
- CourseCertificate: Completion certificates
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.core.models import BaseModel
from apps.users.models import User


class CourseWishlist(BaseModel):
    """
    Student wishlist for courses they want to take later.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_wishlist'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_wishlist'
        verbose_name = 'Course Wishlist'
        verbose_name_plural = 'Course Wishlists'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', '-added_at']),
            models.Index(fields=['course']),
        ]

    def __str__(self):
        return f"{self.user.name} - {self.course.title}"


class CourseReview(BaseModel):
    """
    Student reviews and ratings for courses.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_reviews'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Review title"
    )
    content = models.TextField(
        blank=True,
        help_text="Review content"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the reviewer completed the course"
    )
    helpful_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of users who found this review helpful"
    )

    class Meta:
        db_table = 'course_reviews'
        verbose_name = 'Course Review'
        verbose_name_plural = 'Course Reviews'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['course', '-created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.user.name} - {self.course.title} ({self.rating}★)"


class StudentNote(BaseModel):
    """
    Personal notes students take while watching courses.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_notes'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='student_notes'
    )
    chapter = models.ForeignKey(
        'courses.Chapter',
        on_delete=models.CASCADE,
        related_name='student_notes',
        null=True,
        blank=True,
        help_text="Optional: specific chapter this note relates to"
    )
    content = models.TextField(
        help_text="Note content"
    )
    timestamp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Video timestamp in seconds (if applicable)"
    )

    class Meta:
        db_table = 'student_notes'
        verbose_name = 'Student Note'
        verbose_name_plural = 'Student Notes'
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['chapter']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        chapter_info = f" - {self.chapter.title}" if self.chapter else ""
        return f"Note by {self.user.name} on {self.course.title}{chapter_info}"


class StudentBookmark(BaseModel):
    """
    Bookmarked chapters for quick access.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chapter_bookmarks'
    )
    chapter = models.ForeignKey(
        'courses.Chapter',
        on_delete=models.CASCADE,
        related_name='bookmarked_by'
    )
    timestamp = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Video timestamp in seconds (if applicable)"
    )
    note = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional note about this bookmark"
    )

    class Meta:
        db_table = 'student_bookmarks'
        verbose_name = 'Student Bookmark'
        verbose_name_plural = 'Student Bookmarks'
        unique_together = ['user', 'chapter', 'timestamp']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['chapter']),
        ]

    def __str__(self):
        return f"Bookmark by {self.user.name} on {self.chapter.title}"


class CourseCertificate(BaseModel):
    """
    Completion certificates for courses.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    certificate_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique certificate identifier"
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the certificate was issued"
    )
    completion_percentage = models.FloatField(
        default=100.0,
        help_text="Course completion percentage at time of certificate"
    )
    final_grade = models.FloatField(
        null=True,
        blank=True,
        help_text="Final grade percentage (0-100)"
    )
    final_grade_letter = models.CharField(
        max_length=2,
        blank=True,
        help_text="Final grade letter (A+, A, B+, etc.)"
    )
    certificate_url = models.URLField(
        blank=True,
        help_text="URL to the certificate PDF"
    )
    verification_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Code for certificate verification"
    )

    class Meta:
        db_table = 'course_certificates'
        verbose_name = 'Course Certificate'
        verbose_name_plural = 'Course Certificates'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['certificate_number']),
        ]

    def __str__(self):
        return f"Certificate for {self.user.name} - {self.course.title}"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            import uuid
            self.certificate_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
