"""
Practice app evaluation signals.

Handles automatic grade recalculation when:
- Challenge progress is completed (practice exercises)
- Vapi conversation session is saved

This module follows the established signal pattern from apps/users/signals.py
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ChallengeProgress, VapiSession

logger = logging.getLogger(__name__)


def _get_courses_for_challenge(challenge_progress):
    """
    Determine which video course(s) a practice challenge is linked to.

    A practice lesson can be linked to multiple video course chapters.
    Returns list of (user, course) tuples for courses where user is enrolled.

    Args:
        challenge_progress: ChallengeProgress instance

    Returns:
        List of (User, Course) tuples
    """
    from apps.courses.models import Chapter, CourseEnrollment

    challenge = challenge_progress.challenge
    if not challenge:
        return []

    # Get the lesson that contains this challenge
    # Challenge -> Unit -> Lesson
    unit = challenge.unit if hasattr(challenge, 'unit') else None
    if not unit:
        return []

    lesson = unit.lesson if hasattr(unit, 'lesson') else None
    if not lesson:
        return []

    practice_lesson_id = str(lesson.id)
    user = challenge_progress.user

    # Find chapters that reference this practice lesson
    chapters = Chapter.objects.filter(
        practice_lesson=practice_lesson_id
    ).select_related('section__course')

    courses = []
    for chapter in chapters:
        course = chapter.section.course
        # Only include if user is enrolled in this course
        if CourseEnrollment.objects.filter(user=user, course=course).exists():
            courses.append((user, course))

    return courses


def _get_courses_for_vapi_session(vapi_session):
    """
    Determine which video course(s) a Vapi session contributes to.

    Uses CEFR level mapping to match session level with course level.
    Returns list of (user, course) tuples for matching courses.

    Args:
        vapi_session: VapiSession instance

    Returns:
        List of (User, Course) tuples
    """
    from apps.courses.models import CourseEnrollment
    from apps.courses.services.grade_calculator import COURSE_LEVEL_TO_CEFR

    user = vapi_session.user
    session_level = vapi_session.level  # CEFR level (A1, A2, B1, etc.)

    # Get all courses where user is enrolled
    enrollments = CourseEnrollment.objects.filter(
        user=user
    ).select_related('course')

    courses = []
    for enrollment in enrollments:
        course = enrollment.course

        # Check if session CEFR level matches course level
        allowed_cefr = COURSE_LEVEL_TO_CEFR.get(course.level, [])

        # If no mapping exists, accept any session
        # If mapping exists, check if session level is in allowed levels
        if not allowed_cefr or session_level in allowed_cefr:
            courses.append((user, course))

    return courses


@receiver(post_save, sender=ChallengeProgress)
def on_challenge_completed(sender, instance, created, **kwargs):
    """
    Recalculate student grade when a practice challenge is completed.

    Only triggers if:
    - Challenge is marked as completed
    - Challenge's lesson is linked to a video course chapter
    - User is enrolled in that course

    The signal handler catches all exceptions to ensure challenge
    completion is never blocked by grade calculation failures.
    """
    # Skip if not completed - no point recalculating
    if not instance.completed:
        logger.debug(f"Challenge progress {instance.id} not completed, skipping")
        return

    # Skip raw mode (migrations, loaddata)
    if kwargs.get('raw', False):
        logger.debug("Skipping grade recalc - raw mode")
        return

    try:
        # Import here to avoid circular imports
        from apps.courses.services.grade_calculator import GradeCalculatorService

        courses = _get_courses_for_challenge(instance)

        if not courses:
            logger.debug(
                f"Challenge {instance.challenge_id} not linked to any enrolled courses"
            )
            return

        for user, course in courses:
            logger.info(
                f"Recalculating grade for user {user.id} ({user.email}) "
                f"in course {course.id} ({course.title}) "
                f"due to practice_completed"
            )

            calculator = GradeCalculatorService(user=user, course=course)
            result = calculator.calculate_and_save(change_reason='practice_completed')

            logger.info(
                f"Grade recalculated: {result.final_grade_percentage:.1f}% "
                f"({result.final_grade_letter})"
            )

    except Exception as e:
        # Log but don't raise - challenge completion should never fail
        logger.error(
            f"Error recalculating grade after challenge {instance.id}: {e}",
            exc_info=True
        )


@receiver(post_save, sender=VapiSession)
def on_vapi_session_saved(sender, instance, created, **kwargs):
    """
    Recalculate student grade when a Vapi conversation session is saved.

    Only triggers if:
    - This is a new session (created=True) - avoids duplicate recalcs on updates
    - Session has an overall_score > 0 (is complete, not empty)
    - User is enrolled in a course with matching CEFR level

    The signal handler catches all exceptions to ensure Vapi session
    saving is never blocked by grade calculation failures.
    """
    # Only trigger on creation to avoid duplicate recalculations
    if not created:
        logger.debug(f"Vapi session {instance.session_id} updated, skipping recalc")
        return

    # Skip if session doesn't have a meaningful score
    if instance.overall_score is None or instance.overall_score == 0:
        logger.debug(
            f"Vapi session {instance.session_id} has no score, skipping recalc"
        )
        return

    # Skip raw mode (migrations, loaddata)
    if kwargs.get('raw', False):
        logger.debug("Skipping grade recalc - raw mode")
        return

    try:
        # Import here to avoid circular imports
        from apps.courses.services.grade_calculator import GradeCalculatorService

        courses = _get_courses_for_vapi_session(instance)

        if not courses:
            logger.debug(
                f"Vapi session {instance.session_id} (level {instance.level}) "
                f"not matched to any enrolled courses"
            )
            return

        for user, course in courses:
            logger.info(
                f"Recalculating grade for user {user.id} ({user.email}) "
                f"in course {course.id} ({course.title}) "
                f"due to conversation_session (level: {instance.level}, "
                f"score: {instance.overall_score})"
            )

            calculator = GradeCalculatorService(user=user, course=course)
            result = calculator.calculate_and_save(change_reason='conversation_session')

            logger.info(
                f"Grade recalculated: {result.final_grade_percentage:.1f}% "
                f"({result.final_grade_letter})"
            )

    except Exception as e:
        # Log but don't raise - Vapi session save should never fail
        logger.error(
            f"Error recalculating grade after Vapi session {instance.session_id}: {e}",
            exc_info=True
        )
