"""
Quiz and assessment models.

This module contains models for chapter quizzes, student attempts,
and assessment tracking.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
from apps.users.models import User

from .base import (
    StatisticsModelMixin, TimestampedModelMixin, 
    MetadataModelMixin, ProgressTrackingMixin
)


class ChapterQuiz(BaseModel, StatisticsModelMixin, TimestampedModelMixin, MetadataModelMixin):
    """
    Chapter Quiz configuration - bridges Chapter system with Practice Lab.
    Connects chapters to gamified quiz experiences.
    """
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]
    
    chapter = models.OneToOneField(
        'courses.Chapter',
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
    
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium',
        help_text="Quiz difficulty level"
    )
    
    # Scoring configuration
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
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum score percentage to pass"
    )
    
    # Time and attempt limits
    time_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Time limit in seconds (null = no limit)"
    )
    
    max_attempts = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Maximum attempts allowed"
    )
    
    # Quiz settings
    randomize_questions = models.BooleanField(
        default=True,
        help_text="Whether to randomize question order"
    )
    
    show_correct_answers = models.BooleanField(
        default=True,
        help_text="Whether to show correct answers after completion"
    )
    
    allow_review = models.BooleanField(
        default=True,
        help_text="Whether students can review their answers"
    )
    
    # Availability settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether quiz is active and available"
    )
    
    available_from = models.DateTimeField(
        null=True, blank=True,
        help_text="When the quiz becomes available"
    )
    
    available_until = models.DateTimeField(
        null=True, blank=True,
        help_text="When the quiz stops being available"
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
            models.Index(fields=['difficulty']),
            models.Index(fields=['available_from', 'available_until']),
        ]
    
    def __str__(self):
        return f"Quiz: {self.title} - {self.chapter.title}"
    
    def is_available(self):
        """Check if the quiz is currently available."""
        if not self.is_active:
            return False
        
        from django.utils import timezone
        now = timezone.now()
        
        if self.available_from and now < self.available_from:
            return False
        
        if self.available_until and now > self.available_until:
            return False
        
        return True
    
    def can_user_attempt(self, user):
        """Check if a user can attempt this quiz."""
        if not self.is_available():
            return False, "Quiz is not currently available"
        
        # Check if user is enrolled in the course
        if not self.chapter.course.is_enrolled(user):
            return False, "You must be enrolled in the course"
        
        # Check attempt limit
        user_attempts = self.attempts.filter(student=user).count()
        if user_attempts >= self.max_attempts:
            return False, f"Maximum attempts ({self.max_attempts}) reached"
        
        # Check if user has access to this chapter
        if not self.chapter.is_accessible_by(user):
            return False, "Chapter is not accessible"
        
        return True, "Can attempt"
    
    def get_user_best_attempt(self, user):
        """Get the user's best quiz attempt."""
        return (self.attempts.filter(student=user, is_completed=True)
                .order_by('-score').first())
    
    def get_user_attempts_count(self, user):
        """Get the number of attempts a user has made."""
        return self.attempts.filter(student=user).count()
    
    def get_remaining_attempts(self, user):
        """Get the number of remaining attempts for a user."""
        used = self.get_user_attempts_count(user)
        return max(0, self.max_attempts - used)


class StudentQuizAttempt(BaseModel, TimestampedModelMixin, MetadataModelMixin):
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
    score = models.PositiveIntegerField(
        help_text="Score achieved"
    )
    
    max_score = models.PositiveIntegerField(
        help_text="Maximum possible score"
    )
    
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
    
    # Status fields
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
    
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the attempt was started"
    )
    
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the quiz was completed"
    )
    
    # Answer tracking
    answers_data = models.JSONField(
        default=dict,
        help_text="Student's answers and question data"
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
            models.Index(fields=['chapter_quiz', 'is_completed']),
        ]
        unique_together = ['student', 'chapter_quiz', 'attempt_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.chapter_quiz.title} (Attempt {self.attempt_number})"
    
    @property
    def score_percentage(self):
        """Calculate score as percentage."""
        if self.max_score == 0:
            return 0
        return round((self.score / self.max_score) * 100, 1)
    
    def save(self, *args, **kwargs):
        # Set attempt number if not set
        if not self.attempt_number:
            last_attempt = StudentQuizAttempt.objects.filter(
                student=self.student,
                chapter_quiz=self.chapter_quiz
            ).order_by('-attempt_number').first()
            
            self.attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1
        
        # Calculate if passed
        if self.is_completed and self.score_percentage >= self.chapter_quiz.passing_score:
            self.is_passed = True
        
        # Set completion timestamp
        if self.is_completed and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update chapter quiz statistics
        if self.is_completed:
            self.chapter_quiz.update_statistics(
                new_score=self.score_percentage,
                is_completion=self.is_passed
            )
    
    def complete_attempt(self, answers_data, final_score, hearts_used=0):
        """Mark attempt as completed with final results."""
        from django.utils import timezone
        
        self.is_completed = True
        self.completed_at = timezone.now()
        self.answers_data = answers_data
        self.score = final_score
        self.hearts_lost = hearts_used
        
        # Calculate time taken
        if self.started_at:
            time_diff = self.completed_at - self.started_at
            self.time_taken = int(time_diff.total_seconds())
        
        # Award points if passed
        if self.is_passed:
            self.points_earned = self.chapter_quiz.points_reward
            
            # Mark chapter as completed
            self.chapter_quiz.chapter.mark_completed_for_user(self.student)
        
        self.save()
    
    def can_be_reviewed(self):
        """Check if this attempt can be reviewed."""
        return (self.is_completed and 
                self.chapter_quiz.allow_review and
                self.chapter_quiz.show_correct_answers)
    
    def get_time_taken_formatted(self):
        """Get formatted time taken string."""
        if not self.time_taken:
            return "N/A"
        
        minutes = self.time_taken // 60
        seconds = self.time_taken % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class QuizQuestion(BaseModel, TimestampedModelMixin, MetadataModelMixin):
    """
    Individual questions within a quiz.
    """
    
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
        ('essay', 'Essay'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
        ('ordering', 'Ordering'),
    ]
    
    quiz = models.ForeignKey(
        ChapterQuiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        help_text="Type of question"
    )
    
    question_text = models.TextField(
        help_text="The question text"
    )
    
    # Question media
    image = models.URLField(
        blank=True,
        help_text="Optional image for the question"
    )
    
    audio = models.URLField(
        blank=True,
        help_text="Optional audio for the question"
    )
    
    # Question configuration
    points = models.PositiveIntegerField(
        default=1,
        help_text="Points awarded for correct answer"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within the quiz"
    )
    
    # Answer options (JSON format for flexibility)
    options = models.JSONField(
        default=list,
        help_text="Question options and correct answers (format varies by type)"
    )
    
    explanation = models.TextField(
        blank=True,
        help_text="Explanation shown after answering"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this question is active"
    )
    
    class Meta:
        db_table = 'quiz_questions'
        verbose_name = 'Quiz Question'
        verbose_name_plural = 'Quiz Questions'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['quiz', 'order']),
            models.Index(fields=['question_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.quiz.title} - Question {self.order + 1}"
    
    def check_answer(self, student_answer):
        """
        Check if a student answer is correct.
        Returns (is_correct: bool, points_earned: int, explanation: str)
        """
        if not self.is_active:
            return False, 0, "Question is not active"
        
        if self.question_type == 'multiple_choice':
            correct_option = next(
                (opt for opt in self.options if opt.get('is_correct')), 
                None
            )
            is_correct = (correct_option and 
                         student_answer == correct_option.get('id'))
            
        elif self.question_type == 'true_false':
            correct_answer = self.options.get('correct_answer', False)
            is_correct = student_answer == correct_answer
            
        elif self.question_type == 'short_answer':
            correct_answers = self.options.get('correct_answers', [])
            is_correct = any(
                answer.lower().strip() == student_answer.lower().strip()
                for answer in correct_answers
            )
            
        else:
            # For other question types, implement specific logic
            is_correct = False
        
        points_earned = self.points if is_correct else 0
        
        return is_correct, points_earned, self.explanation
    
    def get_formatted_options(self):
        """Get formatted options for display."""
        if self.question_type == 'multiple_choice':
            return [
                {
                    'id': opt.get('id'),
                    'text': opt.get('text'),
                    'is_correct': opt.get('is_correct', False)
                }
                for opt in self.options
            ]
        
        return self.options