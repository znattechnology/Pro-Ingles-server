"""
Models for the ProEnglish course management system.

This module contains all models related to courses, sections, chapters,
enrollments, transactions, and progress tracking.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
from apps.users.models import User


class Course(BaseModel):
    """
    Course model representing an English course.
    
    Maps from Express/DynamoDB Course model with the same structure.
    """
    
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
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Course price in EUR"
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='Beginner',
        help_text="Course difficulty level"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Draft',
        help_text="Course publication status"
    )
    
    # Template information for visual styling
    template = models.CharField(
        max_length=20,
        choices=TEMPLATE_CHOICES,
        default='general',
        help_text="Course template type for styling and content focus"
    )
    
    class Meta:
        db_table = 'courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['category']),
            models.Index(fields=['level']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
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
        return sum(section.chapters.count() for section in self.sections.all())
    
    @property
    def total_enrollments(self):
        """Return total number of students enrolled."""
        return self.enrollments.count()


class CourseSection(BaseModel):
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
    
    # Order for section sequence
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order of this section within the course"
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


class Chapter(BaseModel):
    """
    Chapter model representing individual lessons within a section.
    
    Maps from Express chapters array in sections.
    """
    
    TYPE_CHOICES = [
        ('Text', 'Text'),
        ('Quiz', 'Quiz'),
        ('Video', 'Video'),
    ]
    
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
        choices=TYPE_CHOICES,
        help_text="Type of chapter content"
    )
    
    # Video-specific field
    video = models.URLField(
        blank=True,
        help_text="Video URL for video-type chapters"
    )
    
    # Order for chapter sequence
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order of this chapter within the section"
    )
    
    # 🆕 ENHANCED FIELDS - Phase 1 Extensions (Non-breaking)
    transcript = models.TextField(
        blank=True,
        help_text="Video transcript with timestamps (JSON format)"
    )
    
    quiz_enabled = models.BooleanField(
        default=False,
        help_text="Whether this chapter has an interactive quiz"
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


class ChapterComment(BaseModel):
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
    
    class Meta:
        db_table = 'chapter_comments'
        verbose_name = 'Chapter Comment'
        verbose_name_plural = 'Chapter Comments'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['chapter', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.name} on {self.chapter.title}"


# 🆕 PHASE 1 - NEW BRIDGE MODELS

class ChapterResource(BaseModel):
    """
    Chapter Resources - PDFs, links, code examples, etc.
    Extends chapter functionality without breaking existing system.
    """
    
    RESOURCE_TYPES = [
        ('PDF', 'PDF Document'),
        ('LINK', 'External Link'),
        ('VIDEO', 'Supplementary Video'),
        ('CODE', 'Code Examples'),
        ('WORKSHEET', 'Exercise Worksheet'),
        ('AUDIO', 'Audio File'),
        ('IMAGE', 'Image/Infographic'),
    ]
    
    chapter = models.ForeignKey(
        Chapter,
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
        choices=RESOURCE_TYPES,
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
    
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of downloads"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Show prominently in resources tab"
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
        ]
    
    def __str__(self):
        return f"{self.title} ({self.resource_type}) - {self.chapter.title}"


class ChapterQuiz(BaseModel):
    """
    Chapter Quiz configuration - bridges Chapter system with Practice Lab.
    Connects chapters to gamified quiz experiences.
    """
    
    chapter = models.OneToOneField(
        Chapter,
        on_delete=models.CASCADE,
        related_name='quiz'
    )
    
    # Bridge to Practice Lab
    practice_lesson = models.ForeignKey(
        'practice.PracticeLesson',
        on_delete=models.CASCADE,
        help_text="Connected Practice Lab lesson"
    )
    
    # Quiz configuration
    title = models.CharField(
        max_length=200,
        help_text="Quiz title"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Quiz description/instructions"
    )
    
    points_reward = models.PositiveIntegerField(
        default=15,
        help_text="Points awarded for completing quiz"
    )
    
    hearts_cost = models.PositiveIntegerField(
        default=1,
        help_text="Hearts lost per wrong answer"
    )
    
    passing_score = models.PositiveIntegerField(
        default=80,
        help_text="Minimum score percentage to pass"
    )
    
    time_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Time limit in seconds (null = no limit)"
    )
    
    max_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum attempts allowed"
    )
    
    # Completion tracking
    total_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Total attempts by all students"
    )
    
    total_completions = models.PositiveIntegerField(
        default=0,
        help_text="Total successful completions"
    )
    
    average_score = models.FloatField(
        default=0.0,
        help_text="Average score across all attempts"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether quiz is active and available"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Teacher who created this quiz"
    )
    
    class Meta:
        db_table = 'chapter_quizzes'
        verbose_name = 'Chapter Quiz'
        verbose_name_plural = 'Chapter Quizzes'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
            models.Index(fields=['practice_lesson']),
        ]
    
    def __str__(self):
        return f"Quiz: {self.title} - {self.chapter.title}"
    
    @property
    def completion_rate(self):
        """Calculate completion rate percentage"""
        if self.total_attempts == 0:
            return 0
        return round((self.total_completions / self.total_attempts) * 100, 1)


class StudentQuizAttempt(BaseModel):
    """
    Track student quiz attempts and performance.
    Links to existing Practice Lab progress tracking.
    """
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chapter_quiz_attempts'
    )
    
    chapter_quiz = models.ForeignKey(
        ChapterQuiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    # Performance metrics
    score = models.PositiveIntegerField(help_text="Score achieved")
    max_score = models.PositiveIntegerField(help_text="Maximum possible score")
    
    time_taken = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Time taken in seconds"
    )
    
    hearts_lost = models.PositiveIntegerField(
        default=0,
        help_text="Hearts lost during this attempt"
    )
    
    points_earned = models.PositiveIntegerField(
        default=0,
        help_text="Points earned for this attempt"
    )
    
    # Status
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether the quiz was completed"
    )
    
    is_passed = models.BooleanField(
        default=False,
        help_text="Whether the passing score was achieved"
    )
    
    attempt_number = models.PositiveIntegerField(
        help_text="Attempt number for this student"
    )
    
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the quiz was completed"
    )
    
    # Link to Practice Lab progress
    practice_progress = models.ForeignKey(
        'practice.ChallengeProgress',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Related Practice Lab challenge progress"
    )
    
    class Meta:
        db_table = 'student_quiz_attempts'
        verbose_name = 'Student Quiz Attempt'
        verbose_name_plural = 'Student Quiz Attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'chapter_quiz']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['is_completed', 'is_passed']),
        ]
        unique_together = ['student', 'chapter_quiz', 'attempt_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.chapter_quiz.title} (Attempt {self.attempt_number})"
    
    @property
    def score_percentage(self):
        """Calculate score as percentage"""
        if self.max_score == 0:
            return 0
        return round((self.score / self.max_score) * 100, 1)


class CourseEnrollment(BaseModel):
    """
    Course enrollment model - maps from Express enrollments array in Course.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user enrolled in the course"
    )
    
    class Meta:
        db_table = 'course_enrollments'
        verbose_name = 'Course Enrollment'
        verbose_name_plural = 'Course Enrollments'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['enrollment_date']),
        ]
    
    def __str__(self):
        return f"{self.user.name} enrolled in {self.course.title}"


class Transaction(BaseModel):
    """
    Transaction model for course purchases - maps from Express Transaction model.
    """
    
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
    ]
    
    # Keep same field names as Express for easier migration
    transactionId = models.CharField(
        max_length=255,
        unique=True,
        help_text="External transaction ID from payment provider"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    dateTime = models.DateTimeField(
        auto_now_add=True,
        help_text="Transaction timestamp"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Transaction amount"
    )
    paymentProvider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='stripe',
        help_text="Payment provider used"
    )
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['dateTime']),
            models.Index(fields=['transactionId']),
        ]
        ordering = ['-dateTime']
    
    def __str__(self):
        return f"Transaction {self.transactionId} - {self.user.name} - {self.course.title}"


class UserCourseProgress(BaseModel):
    """
    User progress in a specific course - maps from Express UserCourseProgress model.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_progress'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    enrollmentDate = models.DateTimeField(
        help_text="When user enrolled in the course"
    )
    overallProgress = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Overall completion percentage (0-100)"
    )
    lastAccessedTimestamp = models.DateTimeField(
        auto_now=True,
        help_text="Last time user accessed this course"
    )
    
    class Meta:
        db_table = 'user_course_progress'
        verbose_name = 'User Course Progress'
        verbose_name_plural = 'User Course Progress'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['lastAccessedTimestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.course.title} ({self.overallProgress:.1f}%)"


class ChapterProgress(BaseModel):
    """
    User progress on individual chapters - maps from Express sections.chapters progress.
    """
    
    user_progress = models.ForeignKey(
        UserCourseProgress,
        on_delete=models.CASCADE,
        related_name='chapter_progress'
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    completed = models.BooleanField(
        default=False,
        help_text="Whether this chapter has been completed"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this chapter was completed"
    )
    
    class Meta:
        db_table = 'chapter_progress'
        verbose_name = 'Chapter Progress'
        verbose_name_plural = 'Chapter Progress'
        unique_together = ['user_progress', 'chapter']
        indexes = [
            models.Index(fields=['user_progress']),
            models.Index(fields=['chapter']),
            models.Index(fields=['completed']),
        ]
    
    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.user_progress.user.name} - {self.chapter.title}"
    
    def save(self, *args, **kwargs):
        # Set completed_at when marking as completed
        if self.completed and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None
        super().save(*args, **kwargs)