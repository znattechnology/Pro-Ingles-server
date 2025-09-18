"""
Custom validators for course-related models and forms.

This module provides comprehensive validation for business rules,
data integrity, and complex validation scenarios across the course system.
"""

import re
from typing import Any, Dict, List, Optional
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta


# =============================================================================
# Base Validator Classes
# =============================================================================

@deconstructible
class BusinessRuleValidator(BaseValidator):
    """
    Base class for business rule validators.
    Provides consistent error handling and logging.
    """
    
    def __init__(self, message=None, code=None):
        super().__init__(limit_value=None, message=message)
        self.code = code or 'invalid'
    
    def __call__(self, value):
        """Override this method in subclasses."""
        raise NotImplementedError("Subclasses must implement __call__ method")
    
    def format_error_message(self, field_name: str, value: Any, reason: str) -> str:
        """Format a consistent error message."""
        return f"{field_name} value '{value}' is invalid: {reason}"


# =============================================================================
# Course-Specific Validators
# =============================================================================

@deconstructible
class CourseContentValidator:
    """
    Validates course content requirements and quality standards.
    """
    
    MIN_TITLE_LENGTH = 5
    MAX_TITLE_LENGTH = 200
    MIN_DESCRIPTION_LENGTH = 50
    MAX_DESCRIPTION_LENGTH = 2000
    
    def __init__(self, field_type='title'):
        self.field_type = field_type
    
    def __call__(self, value):
        if self.field_type == 'title':
            self._validate_title(value)
        elif self.field_type == 'description':
            self._validate_description(value)
        elif self.field_type == 'category':
            self._validate_category(value)
    
    def _validate_title(self, title):
        """Validate course title requirements."""
        if not title or not title.strip():
            raise ValidationError(_('Course title cannot be empty.'))
        
        title = title.strip()
        
        if len(title) < self.MIN_TITLE_LENGTH:
            raise ValidationError(
                _('Course title must be at least %(min_length)d characters long.'),
                params={'min_length': self.MIN_TITLE_LENGTH}
            )
        
        if len(title) > self.MAX_TITLE_LENGTH:
            raise ValidationError(
                _('Course title cannot exceed %(max_length)d characters.'),
                params={'max_length': self.MAX_TITLE_LENGTH}
            )
        
        # Check for inappropriate content (basic)
        forbidden_words = ['spam', 'fake', 'scam', 'free money']
        if any(word.lower() in title.lower() for word in forbidden_words):
            raise ValidationError(_('Course title contains inappropriate content.'))
        
        # Must contain at least one letter (not just numbers/symbols)
        if not re.search(r'[a-zA-ZÀ-ÿ]', title):
            raise ValidationError(_('Course title must contain at least one letter.'))
    
    def _validate_description(self, description):
        """Validate course description requirements."""
        if not description or not description.strip():
            raise ValidationError(_('Course description cannot be empty.'))
        
        description = description.strip()
        
        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            raise ValidationError(
                _('Course description must be at least %(min_length)d characters long.'),
                params={'min_length': self.MIN_DESCRIPTION_LENGTH}
            )
        
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                _('Course description cannot exceed %(max_length)d characters.'),
                params={'max_length': self.MAX_DESCRIPTION_LENGTH}
            )
        
        # Check for minimum word count
        word_count = len(description.split())
        if word_count < 10:
            raise ValidationError(_('Course description must contain at least 10 words.'))
    
    def _validate_category(self, category):
        """Validate course category."""
        valid_categories = [
            'Inglês Geral', 'Inglês para Negócios', 'Inglês para Tecnologia',
            'Inglês Médico', 'Inglês Jurídico', 'Preparação para Exames',
            'Conversação', 'Gramática', 'Pronúncia', 'Writing'
        ]
        
        if category not in valid_categories:
            raise ValidationError(
                _('Invalid course category. Must be one of: %(categories)s'),
                params={'categories': ', '.join(valid_categories)}
            )


@deconstructible
class CoursePriceValidator:
    """
    Validates course pricing according to business rules.
    """
    
    MIN_PRICE = Decimal('0.00')
    MAX_PRICE = Decimal('999.99')
    ALLOWED_FREE_CATEGORIES = ['Inglês Geral', 'Gramática']
    
    def __init__(self, category=None):
        self.category = category
    
    def __call__(self, value):
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError(_('Price must be a valid number.'))
        
        price = Decimal(str(value))
        
        if price < self.MIN_PRICE:
            raise ValidationError(
                _('Course price cannot be negative.')
            )
        
        if price > self.MAX_PRICE:
            raise ValidationError(
                _('Course price cannot exceed €%(max_price)s'),
                params={'max_price': self.MAX_PRICE}
            )
        
        # Business rule: Free courses only allowed for certain categories
        if price == 0 and self.category and self.category not in self.ALLOWED_FREE_CATEGORIES:
            raise ValidationError(
                _('Free courses are only allowed for these categories: %(categories)s'),
                params={'categories': ', '.join(self.ALLOWED_FREE_CATEGORIES)}
            )
        
        # Business rule: Premium categories have minimum price
        premium_categories = ['Inglês Médico', 'Inglês Jurídico', 'Inglês para Negócios']
        if self.category in premium_categories and price < Decimal('29.99'):
            raise ValidationError(
                _('%(category)s courses must be priced at least €29.99'),
                params={'category': self.category}
            )


@deconstructible
class CourseStructureValidator:
    """
    Validates course structure and content organization.
    """
    
    def __call__(self, course):
        """Validate entire course structure."""
        errors = []
        
        # Check minimum content requirements
        if not hasattr(course, 'sections') or course.sections.count() == 0:
            errors.append(_('Course must have at least one section.'))
        else:
            # Check each section
            for section in course.sections.all():
                section_errors = self._validate_section(section)
                errors.extend(section_errors)
        
        if errors:
            raise ValidationError(errors)
    
    def _validate_section(self, section):
        """Validate individual section."""
        errors = []
        
        if not section.chapters.exists():
            errors.append(
                _('Section "%(section_title)s" must have at least one chapter.'),
                params={'section_title': section.sectionTitle}
            )
        
        # Check chapter distribution
        chapter_count = section.chapters.count()
        if chapter_count > 20:
            errors.append(
                _('Section "%(section_title)s" has too many chapters (%(count)d). Maximum is 20.'),
                params={'section_title': section.sectionTitle, 'count': chapter_count}
            )
        
        return errors


# =============================================================================
# Enrollment and Progress Validators
# =============================================================================

@deconstructible
class EnrollmentValidator:
    """
    Validates course enrollment business rules.
    """
    
    def __call__(self, enrollment_data):
        """Validate enrollment request."""
        user = enrollment_data.get('user')
        course = enrollment_data.get('course')
        
        if not user or not course:
            raise ValidationError(_('User and course are required for enrollment.'))
        
        # Check if course is published
        if course.status != 'Published':
            raise ValidationError(_('Cannot enroll in unpublished courses.'))
        
        # Check if already enrolled
        from apps.courses.models.enrollment import CourseEnrollment
        if CourseEnrollment.objects.filter(user=user, course=course, is_active=True).exists():
            raise ValidationError(_('User is already enrolled in this course.'))
        
        # Check enrollment limits
        if hasattr(course, 'max_students') and course.max_students:
            current_enrollments = CourseEnrollment.objects.filter(
                course=course, is_active=True
            ).count()
            
            if current_enrollments >= course.max_students:
                raise ValidationError(_('Course is full. No more enrollments accepted.'))
        
        # Check prerequisites (if implemented)
        self._check_prerequisites(user, course)
    
    def _check_prerequisites(self, user, course):
        """Check if user meets course prerequisites."""
        # This would check if user has completed prerequisite courses
        # For now, we'll implement a basic level check
        
        if course.level == 'Advanced':
            # Check if user has completed at least one Intermediate course
            from apps.courses.models.enrollment import UserCourseProgress
            intermediate_completed = UserCourseProgress.objects.filter(
                user=user,
                course__level='Intermediate',
                overallProgress__gte=80.0
            ).exists()
            
            if not intermediate_completed:
                raise ValidationError(
                    _('Advanced courses require completion of at least one Intermediate course.')
                )


@deconstructible
class ProgressValidator:
    """
    Validates progress tracking data.
    """
    
    def __call__(self, progress_data):
        """Validate progress update data."""
        progress_value = progress_data.get('overallProgress', 0)
        
        if not isinstance(progress_value, (int, float)):
            raise ValidationError(_('Progress must be a number.'))
        
        if progress_value < 0 or progress_value > 100:
            raise ValidationError(_('Progress must be between 0 and 100.'))
        
        # Validate chapter progress consistency
        sections_data = progress_data.get('sections', [])
        if sections_data:
            self._validate_chapter_progress_consistency(sections_data)
    
    def _validate_chapter_progress_consistency(self, sections_data):
        """Ensure chapter progress is consistent with overall progress."""
        total_chapters = 0
        completed_chapters = 0
        
        for section in sections_data:
            for chapter in section.get('chapters', []):
                total_chapters += 1
                if chapter.get('completed', False):
                    completed_chapters += 1
        
        if total_chapters > 0:
            calculated_progress = (completed_chapters / total_chapters) * 100
            # Allow 5% tolerance for rounding
            if abs(calculated_progress - progress_data.get('overallProgress', 0)) > 5:
                raise ValidationError(
                    _('Chapter completion data is inconsistent with overall progress.')
                )


# =============================================================================
# Quiz and Assessment Validators
# =============================================================================

@deconstructible
class QuizConfigurationValidator:
    """
    Validates quiz configuration and settings.
    """
    
    MIN_PASSING_SCORE = 50
    MAX_PASSING_SCORE = 100
    MIN_TIME_LIMIT = 60  # 1 minute
    MAX_TIME_LIMIT = 7200  # 2 hours
    
    def __call__(self, quiz_data):
        """Validate quiz configuration."""
        passing_score = quiz_data.get('passing_score', 80)
        time_limit = quiz_data.get('time_limit')
        max_attempts = quiz_data.get('max_attempts', 3)
        
        # Validate passing score
        if not isinstance(passing_score, int) or passing_score < self.MIN_PASSING_SCORE or passing_score > self.MAX_PASSING_SCORE:
            raise ValidationError(
                _('Passing score must be between %(min)d and %(max)d.'),
                params={'min': self.MIN_PASSING_SCORE, 'max': self.MAX_PASSING_SCORE}
            )
        
        # Validate time limit
        if time_limit is not None:
            if not isinstance(time_limit, int) or time_limit < self.MIN_TIME_LIMIT or time_limit > self.MAX_TIME_LIMIT:
                raise ValidationError(
                    _('Time limit must be between %(min)d and %(max)d seconds.'),
                    params={'min': self.MIN_TIME_LIMIT, 'max': self.MAX_TIME_LIMIT}
                )
        
        # Validate max attempts
        if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 10:
            raise ValidationError(_('Maximum attempts must be between 1 and 10.'))


@deconstructible
class QuizAnswerValidator:
    """
    Validates quiz answer submissions.
    """
    
    def __call__(self, answer_data):
        """Validate quiz answer submission."""
        answers = answer_data.get('answers', {})
        quiz = answer_data.get('quiz')
        
        if not quiz:
            raise ValidationError(_('Quiz reference is required.'))
        
        if not answers:
            raise ValidationError(_('At least one answer is required.'))
        
        # Check if all required questions are answered
        required_questions = quiz.questions.filter(is_active=True)
        for question in required_questions:
            if str(question.id) not in answers:
                raise ValidationError(
                    _('Question "%(question)s" is required.'),
                    params={'question': question.question_text[:50]}
                )
        
        # Validate individual answers
        for question_id, answer in answers.items():
            try:
                question = required_questions.get(id=question_id)
                self._validate_single_answer(question, answer)
            except Exception as e:
                raise ValidationError(
                    _('Invalid answer for question %(question_id)s: %(error)s'),
                    params={'question_id': question_id, 'error': str(e)}
                )
    
    def _validate_single_answer(self, question, answer):
        """Validate a single question answer."""
        if question.question_type == 'multiple_choice':
            # Ensure answer is one of the valid options
            valid_options = [opt.get('id') for opt in question.options if 'id' in opt]
            if answer not in valid_options:
                raise ValidationError(_('Invalid option selected.'))
        
        elif question.question_type == 'short_answer':
            # Ensure answer is not empty and within length limits
            if not answer or len(str(answer).strip()) < 1:
                raise ValidationError(_('Answer cannot be empty.'))
            
            if len(str(answer)) > 500:
                raise ValidationError(_('Answer is too long (maximum 500 characters).'))


# =============================================================================
# File and Media Validators
# =============================================================================

@deconstructible
class CourseImageValidator:
    """
    Validates course cover images.
    """
    
    ALLOWED_FORMATS = ['JPEG', 'PNG', 'WebP']
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    MIN_WIDTH = 800
    MIN_HEIGHT = 600
    MAX_WIDTH = 1920
    MAX_HEIGHT = 1080
    
    def __call__(self, image_file):
        """Validate course image file."""
        if not image_file:
            return
        
        # Check file size
        if image_file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                _('Image file is too large. Maximum size is %(max_size)s MB.'),
                params={'max_size': self.MAX_FILE_SIZE // (1024 * 1024)}
            )
        
        try:
            from PIL import Image
            
            # Open and validate image
            with Image.open(image_file) as img:
                # Check format
                if img.format not in self.ALLOWED_FORMATS:
                    raise ValidationError(
                        _('Invalid image format. Allowed formats: %(formats)s'),
                        params={'formats': ', '.join(self.ALLOWED_FORMATS)}
                    )
                
                # Check dimensions
                width, height = img.size
                
                if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                    raise ValidationError(
                        _('Image is too small. Minimum size is %(min_width)dx%(min_height)d pixels.'),
                        params={'min_width': self.MIN_WIDTH, 'min_height': self.MIN_HEIGHT}
                    )
                
                if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                    raise ValidationError(
                        _('Image is too large. Maximum size is %(max_width)dx%(max_height)d pixels.'),
                        params={'max_width': self.MAX_WIDTH, 'max_height': self.MAX_HEIGHT}
                    )
                
                # Check aspect ratio (should be roughly 4:3 or 16:9)
                aspect_ratio = width / height
                if not (1.2 <= aspect_ratio <= 2.0):
                    raise ValidationError(
                        _('Image aspect ratio should be between 4:3 and 16:9.')
                    )
        
        except ImportError:
            # PIL not available, skip image validation
            pass
        except Exception as e:
            raise ValidationError(
                _('Invalid image file: %(error)s'),
                params={'error': str(e)}
            )


# =============================================================================
# Utility Functions
# =============================================================================

def validate_course_creation_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation for course creation data.
    
    Args:
        data: Course creation data dictionary
        
    Returns:
        Validated and cleaned data dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    errors = {}
    
    # Validate title
    try:
        title_validator = CourseContentValidator(field_type='title')
        title_validator(data.get('title', ''))
    except ValidationError as e:
        errors['title'] = e.messages
    
    # Validate description
    try:
        description_validator = CourseContentValidator(field_type='description')
        description_validator(data.get('description', ''))
    except ValidationError as e:
        errors['description'] = e.messages
    
    # Validate category
    try:
        category_validator = CourseContentValidator(field_type='category')
        category_validator(data.get('category', ''))
    except ValidationError as e:
        errors['category'] = e.messages
    
    # Validate price
    try:
        price_validator = CoursePriceValidator(category=data.get('category'))
        price_validator(data.get('price', 0))
    except ValidationError as e:
        errors['price'] = e.messages
    
    if errors:
        raise ValidationError(errors)
    
    return data


def validate_enrollment_eligibility(user, course) -> bool:
    """
    Check if a user is eligible to enroll in a course.
    
    Args:
        user: User instance
        course: Course instance
        
    Returns:
        True if eligible, raises ValidationError if not
    """
    validator = EnrollmentValidator()
    validator({'user': user, 'course': course})
    return True


def validate_quiz_submission(quiz, answers_data) -> Dict[str, Any]:
    """
    Validate a complete quiz submission.
    
    Args:
        quiz: Quiz instance
        answers_data: Dictionary of answers
        
    Returns:
        Validated answers data
    """
    validator = QuizAnswerValidator()
    submission_data = {
        'quiz': quiz,
        'answers': answers_data
    }
    validator(submission_data)
    return answers_data