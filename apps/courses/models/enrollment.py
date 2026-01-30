"""
Enrollment and progress tracking models.

This module contains models for course enrollments, user progress tracking,
and chapter completion records.
"""

from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.core.models import BaseModel
from apps.users.models import User

from .base import ProgressTrackingMixin, TimestampedModelMixin


class CourseEnrollment(BaseModel, TimestampedModelMixin):
    """
    Course enrollment model - maps from Express enrollments array in Course.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user enrolled in the course"
    )
    
    # Additional enrollment metadata
    enrollment_source = models.CharField(
        max_length=50,
        default='direct',
        help_text="Source of enrollment (direct, promotion, gift, etc.)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the enrollment is currently active"
    )
    
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this enrollment expires (if applicable)"
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
            models.Index(fields=['is_active']),
            # Composite index for recent enrollments by course
            models.Index(fields=['course', 'enrollment_date'], name='enrollment_course_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.name} enrolled in {self.course.title}"
    
    def is_valid(self):
        """Check if the enrollment is currently valid."""
        if not self.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        return True
    
    def deactivate(self, reason=""):
        """Deactivate this enrollment."""
        self.is_active = False
        self.save(update_fields=['is_active'])
        
        # Log the deactivation
        EnrollmentLog.objects.create(
            enrollment=self,
            action='deactivated',
            details=reason
        )
    
    def reactivate(self, reason=""):
        """Reactivate this enrollment."""
        self.is_active = True
        self.save(update_fields=['is_active'])
        
        # Log the reactivation
        EnrollmentLog.objects.create(
            enrollment=self,
            action='reactivated',
            details=reason
        )


class UserCourseProgress(BaseModel, TimestampedModelMixin):
    """
    User progress in a specific course - maps from Express UserCourseProgress model.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_progress'
    )
    course = models.ForeignKey(
        'courses.Course',
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
    
    # Additional progress tracking fields
    total_time_spent = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent in course (minutes)"
    )
    
    current_chapter = models.ForeignKey(
        'courses.Chapter',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="Current chapter user is working on"
    )
    
    completion_date = models.DateTimeField(
        null=True, blank=True,
        help_text="When the course was completed (if completed)"
    )
    
    # 🆕 PROGRESSO DAS PRÁTICAS AUXILIARES
    speaking_practice_progress = models.JSONField(
        default=dict,
        help_text="Progresso nas práticas de speaking específicas do curso"
    )
    listening_practice_progress = models.JSONField(
        default=dict,
        help_text="Progresso nas práticas de listening específicas do curso"
    )
    
    # Estatísticas das práticas
    total_speaking_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Total de sessões de speaking completadas"
    )
    total_listening_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Total de sessões de listening completadas"
    )
    avg_speaking_score = models.FloatField(
        default=0.0,
        help_text="Pontuação média nas práticas de speaking"
    )
    avg_listening_score = models.FloatField(
        default=0.0,
        help_text="Pontuação média nas práticas de listening"
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
            models.Index(fields=['overallProgress']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.course.title} ({self.overallProgress:.1f}%)"
    
    @transaction.atomic
    def update_overall_progress(self):
        """Recalculate and update overall progress based on completed chapters.

        Uses atomic transaction to ensure data consistency.
        """
        total_chapters = self.course.total_chapters
        if total_chapters == 0:
            self.overallProgress = 0.0
        else:
            completed_chapters = self.chapter_progress.filter(completed=True).count()
            self.overallProgress = (completed_chapters / total_chapters) * 100

        # Check if course is completed
        if self.overallProgress >= 100.0 and not self.completion_date:
            self.completion_date = timezone.now()
        elif self.overallProgress < 100.0 and self.completion_date:
            self.completion_date = None

        self.save(update_fields=['overallProgress', 'completion_date'])
    
    def get_next_chapter(self):
        """Get the next uncompleted chapter."""
        completed_chapters = set(
            self.chapter_progress.filter(completed=True)
            .values_list('chapter_id', flat=True)
        )
        
        for section in self.course.sections.all().order_by('order'):
            for chapter in section.chapters.all().order_by('order'):
                if chapter.id not in completed_chapters:
                    return chapter
        
        return None
    
    def is_completed(self):
        """Check if the course is completed."""
        return self.overallProgress >= 100.0
    
    def get_completion_rate(self):
        """Get completion rate as a percentage."""
        return round(self.overallProgress, 1)
    
    def add_time_spent(self, minutes):
        """Add time spent studying to the total."""
        self.total_time_spent += minutes
        self.save(update_fields=['total_time_spent', 'lastAccessedTimestamp'])
    
    # 🆕 MÉTODOS PARA PRÁTICAS AUXILIARES
    @transaction.atomic
    def update_speaking_progress(self, exercise_id, score, completed=True):
        """
        Atualiza progresso de exercício de speaking específico.

        Uses transaction.atomic to ensure data consistency when updating
        multiple fields simultaneously.
        """
        # Lock the row for update to prevent race conditions
        locked_progress = UserCourseProgress.objects.select_for_update().get(pk=self.pk)

        if not locked_progress.speaking_practice_progress:
            locked_progress.speaking_practice_progress = {}

        locked_progress.speaking_practice_progress[str(exercise_id)] = {
            'completed': completed,
            'score': score,
            'completed_at': timezone.now().isoformat() if completed else None
        }

        if completed:
            locked_progress.total_speaking_sessions += 1
            # Recalcular média
            completed_exercises = [
                ex for ex in locked_progress.speaking_practice_progress.values()
                if ex.get('completed')
            ]
            if completed_exercises:
                total_scores = sum(ex['score'] for ex in completed_exercises)
                locked_progress.avg_speaking_score = total_scores / len(completed_exercises)

        locked_progress.save(update_fields=[
            'speaking_practice_progress',
            'total_speaking_sessions',
            'avg_speaking_score'
        ])

        # Refresh self to get updated values
        self.refresh_from_db()

    @transaction.atomic
    def update_listening_progress(self, exercise_id, score, completed=True):
        """
        Atualiza progresso de exercício de listening específico.

        Uses transaction.atomic to ensure data consistency when updating
        multiple fields simultaneously.
        """
        # Lock the row for update to prevent race conditions
        locked_progress = UserCourseProgress.objects.select_for_update().get(pk=self.pk)

        if not locked_progress.listening_practice_progress:
            locked_progress.listening_practice_progress = {}

        locked_progress.listening_practice_progress[str(exercise_id)] = {
            'completed': completed,
            'score': score,
            'completed_at': timezone.now().isoformat() if completed else None
        }

        if completed:
            locked_progress.total_listening_sessions += 1
            # Recalcular média
            completed_exercises = [
                ex for ex in locked_progress.listening_practice_progress.values()
                if ex.get('completed')
            ]
            if completed_exercises:
                total_scores = sum(ex['score'] for ex in completed_exercises)
                locked_progress.avg_listening_score = total_scores / len(completed_exercises)

        locked_progress.save(update_fields=[
            'listening_practice_progress',
            'total_listening_sessions',
            'avg_listening_score'
        ])

        # Refresh self to get updated values
        self.refresh_from_db()
    
    def get_overall_progress_with_practices(self):
        """Calcula progresso geral incluindo práticas (80% trilha principal, 20% práticas)."""
        main_progress = self.overallProgress
        
        # Calcular progresso das práticas
        practice_progress = 0.0
        if self.total_speaking_sessions > 0 or self.total_listening_sessions > 0:
            speaking_weight = 0.5
            listening_weight = 0.5
            
            speaking_progress = min(100.0, (self.total_speaking_sessions / 10) * 100)  # Máximo 10 sessões
            listening_progress = min(100.0, (self.total_listening_sessions / 10) * 100)  # Máximo 10 sessões
            
            practice_progress = (speaking_progress * speaking_weight) + (listening_progress * listening_weight)
        
        # Ponderação: 80% trilha principal, 20% práticas
        overall_with_practices = (main_progress * 0.8) + (practice_progress * 0.2)
        return round(overall_with_practices, 1)
    
    def get_practice_summary(self):
        """Retorna resumo das práticas do curso."""
        return {
            'speaking': {
                'total_sessions': self.total_speaking_sessions,
                'avg_score': round(self.avg_speaking_score, 1),
                'exercises_completed': len([ex for ex in self.speaking_practice_progress.values() if ex.get('completed', False)])
            },
            'listening': {
                'total_sessions': self.total_listening_sessions,
                'avg_score': round(self.avg_listening_score, 1),
                'exercises_completed': len([ex for ex in self.listening_practice_progress.values() if ex.get('completed', False)])
            }
        }


class ChapterProgress(BaseModel, ProgressTrackingMixin, TimestampedModelMixin):
    """
    User progress on individual chapters - maps from Express sections.chapters progress.
    """
    
    user_progress = models.ForeignKey(
        UserCourseProgress,
        on_delete=models.CASCADE,
        related_name='chapter_progress'
    )
    chapter = models.ForeignKey(
        'courses.Chapter',
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    # Additional progress fields
    attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of attempts for this chapter"
    )
    
    time_spent = models.PositiveIntegerField(
        default=0,
        help_text="Time spent on this chapter (minutes)"
    )
    
    best_score = models.FloatField(
        null=True, blank=True,
        help_text="Best score achieved on this chapter (if applicable)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="User's personal notes for this chapter"
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
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.user_progress.user.name} - {self.chapter.title}"
    
    def save(self, *args, **kwargs):
        # Set completed_at when marking as completed
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None
        
        super().save(*args, **kwargs)
        
        # Update overall course progress
        if hasattr(self, 'user_progress'):
            self.user_progress.update_overall_progress()
    
    def mark_complete_with_score(self, score=None):
        """Mark chapter as complete and optionally record a score."""
        self.completed = True
        self.completed_at = timezone.now()
        self.attempts += 1
        
        if score is not None:
            if self.best_score is None or score > self.best_score:
                self.best_score = score
        
        self.save()
        
        # Update current chapter in user progress
        next_chapter = self.user_progress.get_next_chapter()
        if next_chapter:
            self.user_progress.current_chapter = next_chapter
            self.user_progress.save(update_fields=['current_chapter'])
    
    def add_time_spent(self, minutes):
        """Add time spent on this chapter."""
        self.time_spent += minutes
        self.save(update_fields=['time_spent'])
        
        # Also add to overall course time
        self.user_progress.add_time_spent(minutes)
    
    def get_progress_percentage(self):
        """Get progress as a percentage (0-100)."""
        return 100.0 if self.completed else 0.0


class EnrollmentLog(BaseModel):
    """
    Log of enrollment actions for auditing purposes.
    """
    
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    action = models.CharField(
        max_length=50,
        help_text="Action performed (enrolled, deactivated, reactivated, etc.)"
    )
    
    details = models.TextField(
        blank=True,
        help_text="Additional details about the action"
    )
    
    performed_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="User who performed the action (if applicable)"
    )
    
    class Meta:
        db_table = 'enrollment_logs'
        verbose_name = 'Enrollment Log'
        verbose_name_plural = 'Enrollment Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.enrollment} - {self.action}"