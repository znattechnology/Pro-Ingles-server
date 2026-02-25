"""
Course Grading Models

This module contains models for course evaluation and grading:
- CourseGradingConfig: Configuration for course grading weights and requirements
- StudentCourseGrade: Calculated grades for students in courses
- GradeHistory: Audit trail for grade changes
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import BaseModel
from apps.users.models import User


class CourseGradingConfig(BaseModel):
    """
    Configuration for course grading weights and certificate eligibility requirements.
    Each course can have custom grading configuration.
    """
    course = models.OneToOneField(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='grading_config'
    )

    # ===== COMPONENT WEIGHTS (must sum to 100) =====
    quiz_weight = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight of quizzes in final grade (%)"
    )
    practice_weight = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight of practice exercises in final grade (%)"
    )
    conversation_weight = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Weight of Vapi conversations in final grade (%)"
    )

    # ===== MINIMUM REQUIREMENTS FOR CERTIFICATE =====
    min_quiz_average = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum quiz average required (%)"
    )
    min_practice_completion = models.FloatField(
        default=80.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum practice completion percentage (%)"
    )
    min_conversation_score = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum Vapi conversation score (%)"
    )
    min_final_grade = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum final grade for certificate (%)"
    )

    # ===== COMPONENT ENABLE/DISABLE =====
    quiz_enabled = models.BooleanField(
        default=True,
        help_text="Enable quiz component for grading"
    )
    practice_enabled = models.BooleanField(
        default=True,
        help_text="Enable practice exercises for grading"
    )
    conversation_enabled = models.BooleanField(
        default=True,
        help_text="Enable conversation practice for grading"
    )

    # ===== FLEXIBILITY OPTIONS =====
    require_all_quizzes_passed = models.BooleanField(
        default=True,
        help_text="Require all quizzes to be individually passed"
    )
    allow_quiz_retakes = models.BooleanField(
        default=True,
        help_text="Allow students to retake quizzes to improve grade"
    )
    use_best_quiz_attempt = models.BooleanField(
        default=True,
        help_text="Use best attempt for each quiz (vs latest)"
    )
    require_conversation_if_available = models.BooleanField(
        default=True,
        help_text="Require conversation practice if course has it"
    )
    auto_adjust_weights = models.BooleanField(
        default=True,
        help_text="Automatically redistribute weights when components don't exist"
    )

    # ===== GRADE SCALE (A-F) =====
    grade_a_min = models.FloatField(
        default=90.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage for grade A"
    )
    grade_b_min = models.FloatField(
        default=80.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage for grade B"
    )
    grade_c_min = models.FloatField(
        default=70.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage for grade C"
    )
    grade_d_min = models.FloatField(
        default=60.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage for grade D (below is F)"
    )

    class Meta:
        db_table = 'course_grading_config'
        verbose_name = 'Course Grading Configuration'
        verbose_name_plural = 'Course Grading Configurations'

    def clean(self):
        """Validate that weights sum to 100% for enabled components."""
        # Calculate total weight only for enabled components
        quiz_w = (self.quiz_weight or 0) if self.quiz_enabled else 0
        practice_w = (self.practice_weight or 0) if self.practice_enabled else 0
        conversation_w = (self.conversation_weight or 0) if self.conversation_enabled else 0

        total_weight = quiz_w + practice_w + conversation_w

        # Check if at least one component is enabled
        if not any([self.quiz_enabled, self.practice_enabled, self.conversation_enabled]):
            raise ValidationError(
                "At least one grading component must be enabled"
            )

        # If auto_adjust_weights is disabled, require weights to sum to 100
        if not getattr(self, 'auto_adjust_weights', True):
            full_total = (self.quiz_weight or 0) + (self.practice_weight or 0) + (self.conversation_weight or 0)
            if full_total != 100:
                raise ValidationError(
                    f"Component weights must sum to 100%. Current total: {full_total}%"
                )

        # Validate grade scale is in descending order
        if not (self.grade_a_min > self.grade_b_min > self.grade_c_min > self.grade_d_min):
            raise ValidationError(
                "Grade thresholds must be in descending order: A > B > C > D"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_grade_letter(self, percentage: float) -> str:
        """
        Return grade letter based on percentage.

        Args:
            percentage: Score percentage (0-100)

        Returns:
            str: Grade letter (A, B, C, D, or F)
        """
        if percentage >= self.grade_a_min:
            return 'A'
        elif percentage >= self.grade_b_min:
            return 'B'
        elif percentage >= self.grade_c_min:
            return 'C'
        elif percentage >= self.grade_d_min:
            return 'D'
        else:
            return 'F'

    def get_grade_with_plus_minus(self, percentage: float) -> str:
        """
        Return grade letter with +/- modifiers.

        Args:
            percentage: Score percentage (0-100)

        Returns:
            str: Grade with modifier (e.g., A+, B-, etc.)
        """
        base_letter = self.get_grade_letter(percentage)

        if base_letter == 'F':
            return 'F'

        # Calculate position within grade range
        if base_letter == 'A':
            if percentage >= 97:
                return 'A+'
            elif percentage >= 93:
                return 'A'
            else:
                return 'A-'
        elif base_letter == 'B':
            range_size = self.grade_a_min - self.grade_b_min
            position = (percentage - self.grade_b_min) / range_size
            if position >= 0.7:
                return 'B+'
            elif position >= 0.3:
                return 'B'
            else:
                return 'B-'
        elif base_letter == 'C':
            range_size = self.grade_b_min - self.grade_c_min
            position = (percentage - self.grade_c_min) / range_size
            if position >= 0.7:
                return 'C+'
            elif position >= 0.3:
                return 'C'
            else:
                return 'C-'
        elif base_letter == 'D':
            range_size = self.grade_c_min - self.grade_d_min
            position = (percentage - self.grade_d_min) / range_size
            if position >= 0.5:
                return 'D+'
            else:
                return 'D'

        return base_letter

    def __str__(self):
        return f"Grading Config: {self.course.title}"


class StudentCourseGrade(BaseModel):
    """
    Stores calculated grades for a student in a course.
    Updated automatically when quiz/practice scores change.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_grades'
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='student_grades'
    )

    # ===== QUIZ SCORES =====
    quiz_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Average quiz score (%)"
    )
    quiz_count = models.PositiveIntegerField(
        default=0,
        help_text="Total quizzes in course"
    )
    quiz_completed = models.PositiveIntegerField(
        default=0,
        help_text="Quizzes completed by student"
    )
    quiz_passed = models.PositiveIntegerField(
        default=0,
        help_text="Quizzes passed by student"
    )
    quiz_details = models.JSONField(
        default=list,
        help_text="Detailed scores per quiz"
    )

    # ===== PRACTICE SCORES =====
    practice_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Practice completion percentage (%)"
    )
    practice_count = models.PositiveIntegerField(
        default=0,
        help_text="Total practice exercises"
    )
    practice_completed = models.PositiveIntegerField(
        default=0,
        help_text="Practice exercises completed"
    )
    practice_details = models.JSONField(
        default=list,
        help_text="Detailed progress per chapter"
    )

    # ===== CONVERSATION SCORES =====
    conversation_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Average Vapi conversation score (%)"
    )
    conversation_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Total conversation sessions"
    )
    conversation_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total conversation minutes"
    )
    conversation_details = models.JSONField(
        default=list,
        help_text="Detailed session scores"
    )
    has_conversation_requirement = models.BooleanField(
        default=False,
        help_text="Whether course requires conversation practice"
    )

    # ===== CALCULATED FINAL GRADE =====
    final_grade_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Calculated final grade (%)"
    )
    final_grade_letter = models.CharField(
        max_length=3,
        default='F',
        choices=[
            ('A+', 'A+ (Exceptional)'),
            ('A', 'A (Excellent)'),
            ('A-', 'A- (Very Good)'),
            ('B+', 'B+ (Good)'),
            ('B', 'B (Above Average)'),
            ('B-', 'B- (Satisfactory)'),
            ('C+', 'C+ (Average)'),
            ('C', 'C (Adequate)'),
            ('C-', 'C- (Below Average)'),
            ('D+', 'D+ (Poor)'),
            ('D', 'D (Very Poor)'),
            ('F', 'F (Fail)'),
            ('N/A', 'N/A (Not Available)'),
        ]
    )

    # ===== CERTIFICATE ELIGIBILITY =====
    is_eligible_for_certificate = models.BooleanField(
        default=False,
        help_text="Whether all minimum requirements are met"
    )
    eligibility_details = models.JSONField(
        default=dict,
        help_text="Details of each requirement (met/not met)"
    )

    # ===== WEIGHT ADJUSTMENT INFO =====
    weight_info = models.JSONField(
        default=dict,
        help_text="Information about weight adjustments applied"
    )

    # ===== METADATA =====
    last_calculated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last grade calculation timestamp"
    )
    calculation_version = models.PositiveIntegerField(
        default=1,
        help_text="Version of calculation algorithm used"
    )

    class Meta:
        db_table = 'student_course_grades'
        verbose_name = 'Student Course Grade'
        verbose_name_plural = 'Student Course Grades'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', '-final_grade_percentage']),
            models.Index(fields=['course', '-final_grade_percentage']),
            models.Index(fields=['is_eligible_for_certificate']),
            models.Index(fields=['final_grade_letter']),
        ]

    def get_component_grades(self) -> dict:
        """Return grades broken down by component."""
        return {
            'quizzes': {
                'score': self.quiz_score,
                'count': self.quiz_count,
                'completed': self.quiz_completed,
                'passed': self.quiz_passed,
            },
            'practices': {
                'score': self.practice_score,
                'count': self.practice_count,
                'completed': self.practice_completed,
            },
            'conversation': {
                'score': self.conversation_score,
                'sessions': self.conversation_sessions,
                'minutes': self.conversation_minutes,
                'required': self.has_conversation_requirement,
            },
        }

    def get_missing_requirements(self) -> list:
        """Return list of requirements not yet met."""
        missing = []
        for key, detail in self.eligibility_details.items():
            if isinstance(detail, dict) and not detail.get('met', False):
                missing.append({
                    'requirement': key,
                    'message': detail.get('message', ''),
                    'required': detail.get('required'),
                    'actual': detail.get('actual'),
                })
        return missing

    def __str__(self):
        return f"{self.user.name} - {self.course.title}: {self.final_grade_letter} ({self.final_grade_percentage:.1f}%)"


class GradeHistory(BaseModel):
    """
    Audit trail for grade changes.
    Records snapshots when grades are recalculated.
    """
    student_grade = models.ForeignKey(
        StudentCourseGrade,
        on_delete=models.CASCADE,
        related_name='history'
    )

    # Snapshot of grades at this point
    quiz_score = models.FloatField()
    practice_score = models.FloatField()
    conversation_score = models.FloatField()
    final_grade_percentage = models.FloatField()
    final_grade_letter = models.CharField(max_length=3)
    is_eligible = models.BooleanField()

    # Change metadata
    change_reason = models.CharField(
        max_length=50,
        choices=[
            ('quiz_completed', 'Quiz Completed'),
            ('quiz_retake', 'Quiz Retake'),
            ('practice_completed', 'Practice Completed'),
            ('conversation_session', 'Conversation Session'),
            ('manual_adjustment', 'Manual Adjustment'),
            ('recalculation', 'Automatic Recalculation'),
            ('config_change', 'Grading Config Changed'),
            ('initial', 'Initial Calculation'),
        ]
    )
    change_details = models.JSONField(
        default=dict,
        help_text="Additional details about the change"
    )

    class Meta:
        db_table = 'grade_history'
        verbose_name = 'Grade History'
        verbose_name_plural = 'Grade Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student_grade', '-created_at']),
            models.Index(fields=['change_reason']),
        ]

    def __str__(self):
        return f"{self.student_grade.user.name} - {self.change_reason}: {self.final_grade_letter}"
