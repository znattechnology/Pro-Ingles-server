"""
Serializer validators for REST API endpoints.

This module provides validation functions specifically designed for
DRF serializers with comprehensive error handling and business rule enforcement.
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from typing import Any, Dict, List
from decimal import Decimal

from .validators import (
    CourseContentValidator,
    CoursePriceValidator, 
    EnrollmentValidator,
    ProgressValidator,
    QuizConfigurationValidator
)


# =============================================================================
# Serializer Field Validators
# =============================================================================

def validate_course_title(title: str) -> str:
    """
    Validate course title for serializers.
    
    Args:
        title: Course title string
        
    Returns:
        Cleaned title string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        validator = CourseContentValidator(field_type='title')
        validator(title)
        return title.strip()
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)


def validate_course_description(description: str) -> str:
    """
    Validate course description for serializers.
    
    Args:
        description: Course description string
        
    Returns:
        Cleaned description string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        validator = CourseContentValidator(field_type='description')
        validator(description)
        return description.strip()
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)


def validate_course_category(category: str) -> str:
    """
    Validate course category for serializers.
    
    Args:
        category: Course category string
        
    Returns:
        Validated category string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        validator = CourseContentValidator(field_type='category')
        validator(category)
        return category
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)


def validate_course_price(price: Any) -> Decimal:
    """
    Validate course price for serializers.
    
    Args:
        price: Price value (can be string, int, float, or Decimal)
        
    Returns:
        Validated Decimal price
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        # Convert to Decimal for precise validation
        if isinstance(price, str):
            price = Decimal(price)
        elif isinstance(price, (int, float)):
            price = Decimal(str(price))
        elif not isinstance(price, Decimal):
            raise serializers.ValidationError(_('Price must be a valid number.'))
        
        validator = CoursePriceValidator()
        validator(price)
        return price
    except (ValueError, DjangoValidationError) as e:
        if isinstance(e, DjangoValidationError):
            raise serializers.ValidationError(e.messages)
        else:
            raise serializers.ValidationError(_('Invalid price format.'))


def validate_course_level(level: str) -> str:
    """
    Validate course level for serializers.
    
    Args:
        level: Course level string
        
    Returns:
        Validated level string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    valid_levels = ['Beginner', 'Intermediate', 'Advanced']
    
    if level not in valid_levels:
        raise serializers.ValidationError(
            _('Invalid level. Must be one of: %(levels)s') % {
                'levels': ', '.join(valid_levels)
            }
        )
    
    return level


def validate_section_title(title: str) -> str:
    """
    Validate section title for serializers.
    
    Args:
        title: Section title string
        
    Returns:
        Cleaned title string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    if not title or not title.strip():
        raise serializers.ValidationError(_('Section title cannot be empty.'))
    
    title = title.strip()
    
    if len(title) < 3:
        raise serializers.ValidationError(_('Section title must be at least 3 characters long.'))
    
    if len(title) > 100:
        raise serializers.ValidationError(_('Section title cannot exceed 100 characters.'))
    
    return title


def validate_chapter_title(title: str) -> str:
    """
    Validate chapter title for serializers.
    
    Args:
        title: Chapter title string
        
    Returns:
        Cleaned title string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    if not title or not title.strip():
        raise serializers.ValidationError(_('Chapter title cannot be empty.'))
    
    title = title.strip()
    
    if len(title) < 3:
        raise serializers.ValidationError(_('Chapter title must be at least 3 characters long.'))
    
    if len(title) > 200:
        raise serializers.ValidationError(_('Chapter title cannot exceed 200 characters.'))
    
    return title


def validate_chapter_content(content: str) -> str:
    """
    Validate chapter content for serializers.
    
    Args:
        content: Chapter content string
        
    Returns:
        Cleaned content string
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    if not content or not content.strip():
        raise serializers.ValidationError(_('Chapter content cannot be empty.'))
    
    content = content.strip()
    
    if len(content) < 10:
        raise serializers.ValidationError(_('Chapter content must be at least 10 characters long.'))
    
    if len(content) > 10000:
        raise serializers.ValidationError(_('Chapter content cannot exceed 10,000 characters.'))
    
    return content


def validate_chapter_type(chapter_type: str) -> str:
    """
    Validate chapter type for serializers.
    
    Args:
        chapter_type: Chapter type string
        
    Returns:
        Validated chapter type
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    valid_types = ['Text', 'Quiz', 'Video']
    
    if chapter_type not in valid_types:
        raise serializers.ValidationError(
            _('Invalid chapter type. Must be one of: %(types)s') % {
                'types': ', '.join(valid_types)
            }
        )
    
    return chapter_type


def validate_progress_percentage(progress: Any) -> float:
    """
    Validate progress percentage for serializers.
    
    Args:
        progress: Progress value
        
    Returns:
        Validated progress float
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        progress = float(progress)
    except (ValueError, TypeError):
        raise serializers.ValidationError(_('Progress must be a valid number.'))
    
    if progress < 0 or progress > 100:
        raise serializers.ValidationError(_('Progress must be between 0 and 100.'))
    
    return round(progress, 2)


# =============================================================================
# Complex Validation Functions
# =============================================================================

def validate_course_creation_data(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation for course creation in serializers.
    
    Args:
        attrs: Serializer validated data
        
    Returns:
        Validated and cleaned data
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    errors = {}
    
    # Cross-field validation for price and category
    price = attrs.get('price', 0)
    category = attrs.get('category', '')
    
    if price and category:
        try:
            price_validator = CoursePriceValidator(category=category)
            price_validator(price)
        except DjangoValidationError as e:
            errors['price'] = e.messages
    
    # Validate level compatibility with category
    level = attrs.get('level', '')
    if level and category:
        # Business rule: Medical and Legal courses should be Advanced
        if category in ['Inglês Médico', 'Inglês Jurídico'] and level == 'Beginner':
            errors['level'] = [_('Medical and Legal courses should not be at Beginner level.')]
    
    # Validate template compatibility
    template = attrs.get('template', 'general')
    if template and category:
        template_category_map = {
            'general': ['Inglês Geral', 'Conversação', 'Gramática'],
            'business': ['Inglês para Negócios'],
            'technology': ['Inglês para Tecnologia'],
            'medical': ['Inglês Médico'],
            'legal': ['Inglês Jurídico']
        }
        
        valid_categories = template_category_map.get(template, [])
        if valid_categories and category not in valid_categories:
            errors['template'] = [
                _('Template "%(template)s" is not compatible with category "%(category)s"') % {
                    'template': template,
                    'category': category
                }
            ]
    
    if errors:
        raise serializers.ValidationError(errors)
    
    return attrs


def validate_enrollment_request(attrs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate enrollment request data.
    
    Args:
        attrs: Serializer validated data
        context: Serializer context with request info
        
    Returns:
        Validated data
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    user = context.get('request').user if context.get('request') else None
    course = attrs.get('course')
    
    if not user:
        raise serializers.ValidationError(_('Authentication required for enrollment.'))
    
    if not course:
        raise serializers.ValidationError(_('Course is required for enrollment.'))
    
    try:
        enrollment_data = {'user': user, 'course': course}
        validator = EnrollmentValidator()
        validator(enrollment_data)
    except DjangoValidationError as e:
        raise serializers.ValidationError({'non_field_errors': e.messages})
    
    return attrs


def validate_progress_update(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate progress update data.
    
    Args:
        attrs: Serializer validated data
        
    Returns:
        Validated data
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        validator = ProgressValidator()
        validator(attrs)
    except DjangoValidationError as e:
        raise serializers.ValidationError({'non_field_errors': e.messages})
    
    return attrs


def validate_quiz_configuration(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate quiz configuration data.
    
    Args:
        attrs: Serializer validated data
        
    Returns:
        Validated data
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    try:
        validator = QuizConfigurationValidator()
        validator(attrs)
    except DjangoValidationError as e:
        raise serializers.ValidationError({'non_field_errors': e.messages})
    
    # Additional quiz-specific validations
    points_reward = attrs.get('points_reward', 15)
    hearts_cost = attrs.get('hearts_cost', 1)
    
    if points_reward < 1 or points_reward > 100:
        raise serializers.ValidationError({
            'points_reward': [_('Points reward must be between 1 and 100.')]
        })
    
    if hearts_cost < 0 or hearts_cost > 5:
        raise serializers.ValidationError({
            'hearts_cost': [_('Hearts cost must be between 0 and 5.')]
        })
    
    return attrs


def validate_transaction_data(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate transaction creation data.
    
    Args:
        attrs: Serializer validated data
        
    Returns:
        Validated data
        
    Raises:
        serializers.ValidationError: If validation fails
    """
    amount = attrs.get('amount')
    transaction_id = attrs.get('transactionId', '')
    
    # Validate amount
    if not amount or amount <= 0:
        raise serializers.ValidationError({
            'amount': [_('Transaction amount must be greater than zero.')]
        })
    
    if amount > 9999.99:
        raise serializers.ValidationError({
            'amount': [_('Transaction amount cannot exceed €9,999.99')]
        })
    
    # Validate transaction ID format
    if not transaction_id or len(transaction_id) < 10:
        raise serializers.ValidationError({
            'transactionId': [_('Transaction ID must be at least 10 characters long.')]
        })
    
    # Basic format check for common payment providers
    if transaction_id.startswith('pi_'):  # Stripe Payment Intent
        if len(transaction_id) < 27:  # Stripe PI IDs are typically 27+ chars
            raise serializers.ValidationError({
                'transactionId': [_('Invalid Stripe Payment Intent ID format.')]
            })
    
    return attrs


# =============================================================================
# Serializer Mixins with Validation
# =============================================================================

class ValidatedSerializerMixin:
    """
    Mixin for serializers that adds comprehensive validation support.
    """
    
    def validate(self, attrs):
        """Override to add custom validation logic."""
        attrs = super().validate(attrs) if hasattr(super(), 'validate') else attrs
        
        # Apply model-specific validation
        model_name = getattr(self.Meta, 'model', None)
        if model_name:
            model_name = model_name.__name__.lower()
            
            if model_name == 'course':
                attrs = validate_course_creation_data(attrs)
            elif model_name == 'courseenrollment':
                attrs = validate_enrollment_request(attrs, self.context)
            elif model_name == 'usercourseprogress':
                attrs = validate_progress_update(attrs)
            elif model_name == 'chapterquiz':
                attrs = validate_quiz_configuration(attrs)
            elif model_name == 'transaction':
                attrs = validate_transaction_data(attrs)
        
        return attrs
    
    def to_internal_value(self, data):
        """Override to add pre-validation data cleaning."""
        # Clean string fields
        if isinstance(data, dict):
            cleaned_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Strip whitespace and normalize
                    value = value.strip()
                    if not value:  # Convert empty strings to None
                        value = None
                cleaned_data[key] = value
            data = cleaned_data
        
        return super().to_internal_value(data)


# =============================================================================
# Field-Level Validators for Common Use Cases
# =============================================================================

def validate_positive_number(value):
    """Validate that a number is positive."""
    if value is not None and value <= 0:
        raise serializers.ValidationError(_('Value must be positive.'))
    return value


def validate_non_empty_string(value):
    """Validate that a string is not empty or whitespace-only."""
    if value is not None and not value.strip():
        raise serializers.ValidationError(_('This field cannot be empty.'))
    return value.strip() if value else value


def validate_url_format(value):
    """Validate URL format with enhanced checking."""
    if not value:
        return value
    
    import re
    from urllib.parse import urlparse
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(value):
        raise serializers.ValidationError(_('Enter a valid URL.'))
    
    # Additional security checks
    parsed = urlparse(value)
    if parsed.hostname and parsed.hostname.lower() in ['localhost', '127.0.0.1'] and not settings.DEBUG:
        raise serializers.ValidationError(_('Local URLs are not allowed in production.'))
    
    return value


def validate_file_size(max_size_mb=5):
    """Create a validator for file size limits."""
    def validator(file_obj):
        if file_obj and hasattr(file_obj, 'size'):
            max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
            if file_obj.size > max_size:
                raise serializers.ValidationError(
                    _('File size cannot exceed %(max_size)s MB.') % {'max_size': max_size_mb}
                )
        return file_obj
    return validator