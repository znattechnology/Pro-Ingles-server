"""
Course evaluation signals.

Handles automatic grade recalculation when evaluation events occur:
- Quiz attempt completed
- Automatic certificate generation when eligible

This module follows the established signal pattern from apps/users/signals.py
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import StudentQuizAttempt, StudentCourseGrade, UserCourseProgress, CourseCertificate

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StudentQuizAttempt)
def on_quiz_attempt_saved(sender, instance, created, **kwargs):
    """
    Recalculate student grade when a quiz attempt is saved.

    Triggers:
    - New quiz attempt created (created=True)
    - Quiz attempt updated (e.g., completed)

    Only recalculates if:
    - Attempt is completed (is_completed=True)
    - Student and course can be determined

    The signal handler catches all exceptions to ensure quiz submission
    is never blocked by grade calculation failures.
    """
    # Skip if not completed - no point recalculating for incomplete attempts
    if not instance.is_completed:
        logger.debug(f"Quiz attempt {instance.id} not completed, skipping grade recalc")
        return

    # Skip if in raw mode (bulk inserts, migrations, loaddata)
    if kwargs.get('raw', False):
        logger.debug("Skipping grade recalc - raw mode")
        return

    try:
        # Get course from quiz -> chapter -> section -> course
        quiz = instance.chapter_quiz
        if not quiz:
            logger.warning(f"Quiz attempt {instance.id} has no chapter_quiz")
            return

        chapter = quiz.chapter
        if not chapter:
            logger.warning(f"Quiz {quiz.id} has no chapter")
            return

        section = chapter.section
        if not section:
            logger.warning(f"Chapter {chapter.id} has no section")
            return

        course = section.course
        if not course:
            logger.warning(f"Section {section.id} has no course")
            return

        user = instance.student
        if not user:
            logger.warning(f"Quiz attempt {instance.id} has no student")
            return

        # Determine change reason based on whether this is a new or updated attempt
        change_reason = 'quiz_completed' if created else 'quiz_retake'

        # Import here to avoid circular imports
        from .services.grade_calculator import GradeCalculatorService

        logger.info(
            f"Recalculating grade for user {user.id} ({user.email}) "
            f"in course {course.id} ({course.title}) "
            f"due to {change_reason}"
        )

        # Instantiate calculator and recalculate
        calculator = GradeCalculatorService(user=user, course=course)
        result = calculator.calculate_and_save(change_reason=change_reason)

        logger.info(
            f"Grade recalculated successfully: "
            f"{result.final_grade_percentage:.1f}% ({result.final_grade_letter})"
        )

    except Exception as e:
        # Log the error but DON'T raise - we don't want to break quiz submission
        # The grade will be calculated on-demand when user views grades page
        logger.error(
            f"Error recalculating grade after quiz attempt {instance.id}: {e}",
            exc_info=True
        )


@receiver(post_save, sender=StudentCourseGrade)
def on_grade_saved_check_certificate(sender, instance, created, **kwargs):
    """
    Automatically generate certificate when student becomes eligible.

    Triggers when:
    - Grade is saved and is_eligible_for_certificate becomes True
    - Course progress is 100%
    - No existing certificate

    This allows automatic certificate issuance without student action.
    """
    # Skip if not eligible
    if not instance.is_eligible_for_certificate:
        return

    # Skip if in raw mode
    if kwargs.get('raw', False):
        return

    try:
        user = instance.user
        course = instance.course

        # Check if certificate already exists
        if CourseCertificate.objects.filter(user=user, course=course).exists():
            logger.debug(f"Certificate already exists for user {user.id} in course {course.id}")
            return

        # Check course progress is 100%
        try:
            progress = UserCourseProgress.objects.get(user=user, course=course)
            if progress.overallProgress < 100.0:
                logger.debug(
                    f"Course progress not complete ({progress.overallProgress}%), "
                    f"certificate not auto-generated"
                )
                return
        except UserCourseProgress.DoesNotExist:
            logger.debug("No progress record found, certificate not auto-generated")
            return

        # Import here to avoid circular imports
        from .services.certificate_service import generate_certificate_for_user

        logger.info(
            f"Auto-generating certificate for user {user.id} ({user.email}) "
            f"in course {course.id} ({course.title})"
        )

        certificate = generate_certificate_for_user(user, course)

        if certificate:
            logger.info(
                f"Certificate auto-generated successfully: {certificate.certificate_number}"
            )
        else:
            logger.warning(
                f"Certificate generation returned None for user {user.id} in course {course.id}"
            )

    except Exception as e:
        # Log but don't raise - certificate can be generated manually later
        logger.error(
            f"Error auto-generating certificate for grade {instance.id}: {e}",
            exc_info=True
        )


@receiver(post_save, sender=UserCourseProgress)
def on_progress_complete_check_certificate(sender, instance, **kwargs):
    """
    Check for certificate eligibility when course progress reaches 100%.

    This handles the case where a student completes the course but the
    grade was calculated earlier (already eligible).
    """
    # Only trigger when progress reaches 100%
    if instance.overallProgress < 100.0:
        return

    # Skip if in raw mode
    if kwargs.get('raw', False):
        return

    try:
        user = instance.user
        course = instance.course

        # Check if certificate already exists
        if CourseCertificate.objects.filter(user=user, course=course).exists():
            return

        # Check if eligible for certificate
        try:
            grade = StudentCourseGrade.objects.get(user=user, course=course)
            if not grade.is_eligible_for_certificate:
                return
        except StudentCourseGrade.DoesNotExist:
            # No grade yet, will be handled when grade is calculated
            return

        # Import here to avoid circular imports
        from .services.certificate_service import generate_certificate_for_user

        logger.info(
            f"Progress complete - auto-generating certificate for user {user.id} "
            f"in course {course.id}"
        )

        certificate = generate_certificate_for_user(user, course)

        if certificate:
            logger.info(
                f"Certificate auto-generated on completion: {certificate.certificate_number}"
            )

    except Exception as e:
        logger.error(
            f"Error checking certificate on progress completion: {e}",
            exc_info=True
        )
