"""
Core course models: Course, CourseSection, Chapter, and ChapterComment.

This module contains the main models that define the course structure
and content hierarchy.
"""

import uuid
from django.db import models
from django.core.validators import MaxValueValidator
from apps.core.models import BaseModel
from apps.users.models import User

from .base import (
    CourseChoices, ChapterChoices, OrderedModelMixin,
    TimestampedModelMixin, MetadataModelMixin
)


class Course(BaseModel):
    """
    Course model representing an English course.
    
    Maps from Express/DynamoDB Course model with the same structure.
    """
    
    # Use courseId as alias for id field for easier migration
    @property
    def courseId(self):
        return self.id
    
    # Teacher relationship
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='taught_courses',
        help_text="Teacher who created this course"
    )
    teacherName = models.CharField(
        max_length=255,
        help_text="Teacher's name (denormalized for performance)"
    )
    
    # Course basic info
    title = models.CharField(
        max_length=255,
        default="Curso sem título",
        help_text="Course title"
    )
    description = models.TextField(
        blank=True,
        help_text="Course description"
    )
    category = models.CharField(
        max_length=100,
        default="Sem categoria",
        help_text="Course category"
    )
    image = models.URLField(
        blank=True,
        help_text="Course thumbnail image URL (S3 or local)"
    )
    
    # Course details
    level = models.CharField(
        max_length=20,
        choices=CourseChoices.LEVEL_CHOICES,
        default='Beginner',
        help_text="Course difficulty level"
    )
    status = models.CharField(
        max_length=20,
        choices=CourseChoices.STATUS_CHOICES,
        default='Draft',
        help_text="Course publication status"
    )
    
    # Template information for visual styling
    template = models.CharField(
        max_length=20,
        choices=CourseChoices.TEMPLATE_CHOICES,
        default='general',
        help_text="Course template type for styling and content focus"
    )
    
    # Course type to distinguish between video courses and practice lab courses
    course_type = models.CharField(
        max_length=20,
        choices=CourseChoices.COURSE_TYPE_CHOICES,
        default='video',
        help_text="Type of course: video lessons or practice laboratory"
    )
    
    class Meta:
        db_table = 'courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        indexes = [
            # Single field indexes for basic filtering
            models.Index(fields=['teacher']),
            models.Index(fields=['category']),
            models.Index(fields=['level']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            # Composite indexes for common query patterns
            models.Index(fields=['status', 'category'], name='course_status_category_idx'),
            models.Index(fields=['teacher', 'status'], name='course_teacher_status_idx'),
            models.Index(fields=['status', 'created_at'], name='course_status_date_idx'),
            models.Index(fields=['category', 'level'], name='course_category_level_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.teacherName}"
    
    def save(self, *args, **kwargs):
        # Auto-populate teacherName from teacher relationship
        if self.teacher and not self.teacherName:
            self.teacherName = self.teacher.name
        super().save(*args, **kwargs)
    
    @property
    def total_sections(self):
        """Return total number of sections in this course."""
        return self.sections.count()
    
    @property
    def total_chapters(self):
        """Return total number of chapters across all sections."""
        # Optimized query to avoid N+1 problem
        from django.db.models import Count
        result = self.sections.aggregate(
            total=Count('chapters')
        )
        return result['total'] or 0
    
    @property
    def total_enrollments(self):
        """Return total number of students enrolled."""
        return self.enrollments.count()
    
    def is_enrolled(self, user):
        """Check if a user is enrolled in this course."""
        from apps.courses.models.enrollment import CourseEnrollment
        return CourseEnrollment.objects.filter(user=user, course=self).exists()
    
    def get_user_progress(self, user):
        """Get progress for a specific user."""
        from apps.courses.models.enrollment import UserCourseProgress
        try:
            return UserCourseProgress.objects.get(user=user, course=self)
        except UserCourseProgress.DoesNotExist:
            return None
    
    def can_be_accessed_by(self, user):
        """Check if a user can access this course."""
        if self.status == 'Published':
            return True
        if self.teacher == user:
            return True
        return False


class CourseSection(BaseModel, OrderedModelMixin):
    """
    Course section model representing a section within a course.
    
    Maps from Express sections array in Course model.
    """
    
    @property
    def sectionId(self):
        return self.id
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='sections',
        help_text="Course this section belongs to"
    )
    
    sectionTitle = models.CharField(
        max_length=255,
        help_text="Section title"
    )
    sectionDescription = models.TextField(
        blank=True,
        help_text="Section description"
    )
    
    class Meta:
        db_table = 'course_sections'
        verbose_name = 'Course Section'
        verbose_name_plural = 'Course Sections'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['course', 'order']),
        ]
    
    def __str__(self):
        return f"{self.course.title} - {self.sectionTitle}"
    
    @property
    def total_chapters(self):
        """Return total number of chapters in this section."""
        return self.chapters.count()
    
    def get_next_chapter_order(self):
        """Get the next chapter order number for this section."""
        last_chapter = self.chapters.order_by('-order').first()
        return (last_chapter.order + 1) if last_chapter else 1


class Chapter(BaseModel, OrderedModelMixin, MetadataModelMixin):
    """
    Chapter model representing individual lessons within a section.
    
    Maps from Express chapters array in sections.
    """
    
    @property
    def chapterId(self):
        return self.id
    
    section = models.ForeignKey(
        CourseSection,
        on_delete=models.CASCADE,
        related_name='chapters',
        help_text="Section this chapter belongs to"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Chapter title"
    )
    content = models.TextField(
        help_text="Chapter content (text, quiz questions, etc.)"
    )
    type = models.CharField(
        max_length=20,
        choices=ChapterChoices.TYPE_CHOICES,
        help_text="Type of chapter content"
    )
    
    # Video-specific field
    video = models.URLField(
        blank=True,
        help_text="Video URL for video-type chapters"
    )
    
    # Enhanced fields - Phase 1 Extensions (Non-breaking)
    transcript = models.TextField(
        blank=True,
        help_text="Video transcript with timestamps (JSON format)"
    )
    
    quiz_enabled = models.BooleanField(
        default=False,
        help_text="Whether this chapter has an interactive quiz"
    )
    
    # Quiz data storage for frontend compatibility (Quiz chapters)
    quiz_data = models.JSONField(
        null=True, blank=True,
        help_text="Quiz questions and settings data (JSON format)"
    )
    
    # Practice selection for exercise chapters (Exercise chapters)  
    practice_selection = models.JSONField(
        null=True, blank=True,
        help_text="Practice course selection data for exercise chapters"
    )
    
    resources_data = models.JSONField(
        default=list,
        help_text="Array of chapter resources (PDFs, links, etc.)"
    )
    
    # Bridge to Practice Lab system
    practice_lesson = models.ForeignKey(
        'practice.PracticeLesson',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Connected Practice Lab lesson for gamified quizzes"
    )
    
    class Meta:
        db_table = 'chapters'
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['section', 'order']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"{self.section.course.title} - {self.section.sectionTitle} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Auto-enable quiz when chapter type is Quiz
        if self.type == 'Quiz' and not self.quiz_enabled:
            self.quiz_enabled = True
        
        # Auto-populate practice_selection for Exercise chapters if not set
        if self.type == 'Exercise' and not self.practice_selection:
            # Set default empty selection structure
            self.practice_selection = {
                "course_id": None,
                "lesson_ids": [],
                "settings": {
                    "shuffle": True,
                    "time_limit": None
                }
            }
        
        super().save(*args, **kwargs)
    
    @property
    def course(self):
        """Get the course this chapter belongs to."""
        return self.section.course
    
    def is_accessible_by(self, user):
        """Check if a user can access this chapter."""
        return self.course.can_be_accessed_by(user)
    
    def get_user_progress(self, user):
        """Get progress for this chapter for a specific user."""
        from .enrollment import ChapterProgress, UserCourseProgress
        try:
            course_progress = UserCourseProgress.objects.get(
                user=user, course=self.course
            )
            return ChapterProgress.objects.get(
                user_progress=course_progress, chapter=self
            )
        except (UserCourseProgress.DoesNotExist, ChapterProgress.DoesNotExist):
            return None
    
    def mark_completed_for_user(self, user):
        """Mark this chapter as completed for a specific user."""
        from .enrollment import ChapterProgress, UserCourseProgress
        from django.utils import timezone
        
        course_progress, created = UserCourseProgress.objects.get_or_create(
            user=user,
            course=self.course,
            defaults={
                'enrollmentDate': timezone.now(),
                'overallProgress': 0.0
            }
        )
        
        chapter_progress, created = ChapterProgress.objects.get_or_create(
            user_progress=course_progress,
            chapter=self,
            defaults={'completed': True, 'completed_at': timezone.now()}
        )
        
        if not created and not chapter_progress.completed:
            chapter_progress.completed = True
            chapter_progress.completed_at = timezone.now()
            chapter_progress.save()
        
        # Update overall course progress
        course_progress.update_overall_progress()


class ChapterComment(BaseModel, TimestampedModelMixin):
    """
    Comments on chapters - maps from Express comments array in chapters.
    """
    
    @property
    def commentId(self):
        return self.id
    
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chapter_comments'
    )
    
    text = models.TextField(help_text="Comment text")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional fields for enhanced functionality
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this comment/question has been resolved"
    )
    
    parent_comment = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text="Parent comment for threaded replies"
    )
    
    class Meta:
        db_table = 'chapter_comments'
        verbose_name = 'Chapter Comment'
        verbose_name_plural = 'Chapter Comments'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['chapter', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['parent_comment']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.name} on {self.chapter.title}"
    
    def is_reply(self):
        """Check if this comment is a reply to another comment."""
        return self.parent_comment is not None
    
    def can_be_edited_by(self, user):
        """Check if a user can edit this comment."""
        return (self.user == user or 
                self.chapter.course.teacher == user or 
                user.role == 'admin')
    
    def can_be_deleted_by(self, user):
        """Check if a user can delete this comment."""
        return self.can_be_edited_by(user)
    
    def toggle_resolved(self, user):
        """Toggle the resolved status of this comment."""
        if self.chapter.course.teacher == user or user.role == 'admin':
            self.is_resolved = not self.is_resolved
            self.save(update_fields=['is_resolved'])
            return True
        return False