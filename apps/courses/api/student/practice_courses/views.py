"""
Practice Lab Views - REST API endpoints

This module provides DRF views for the Practice Lab system,
implementing all necessary endpoints for the Duolingo-style learning experience.
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)
from django.db import models, transaction
from django.utils import timezone
from rest_framework import generics, status as status_module
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

# Rate limiting for security
from apps.practice.throttling import ChallengeProgressThrottle

# Course management views removed - student endpoints only

# Import subscription decorators
from apps.subscriptions.decorators import (
    subscription_required,
    lesson_required,
    speaking_required,
    listening_required,
    hearts_required,
    premium_required,
    premium_plus_required
)
from apps.subscriptions.models import UserSubscription

from apps.courses.models import Course
from apps.practice.models import (
    PracticeUnit, 
    PracticeLesson, 
    PracticeChallenge, 
    ChallengeOption,
    UserProgress, 
    ChallengeProgress,
    UserLeague,
    LeaguePromotion,
    Competition,
    CompetitionParticipant,
    LeaderboardSnapshot,
    UserStreak,
    Achievement,
    UserAchievement,
    AchievementCategory,
    AchievementNotification
    # Note: AI Speaking/Listening models removed - now handled by Vapi integration
)
from .serializers import (
    PracticeUnitSerializer,
    PracticeLessonSerializer,
    PracticeChallengeSerializer,
    ChallengeOptionSerializer,
    ChallengeOptionWithAnswerSerializer,
    ChallengeOptionCreateSerializer,
    UserProgressSerializer,
    UserProgressUpdateSerializer,
    ChallengeProgressCreateSerializer,
    LessonDetailSerializer,
    UserStreakSerializer,
    UserLeagueSerializer,
    LeaderboardEntrySerializer,
    LeagueInfoSerializer,
    CompetitionSerializer,
    CompetitionParticipantSerializer,
    LeaderboardSnapshotSerializer,
    AchievementSerializer,
    UserAchievementSerializer,
    AchievementStatsSerializer,
    AchievementCategorySerializer,
    AchievementNotificationSerializer,
    DetailedAchievementSerializer,
    # Vapi AI Conversation Serializers
    VapiConversationSerializer,
    VapiConversationFeedbackSerializer
    # Note: AI Speaking/Listening serializers removed - now handled by Vapi integration
)


def has_unlimited_hearts(user):
    """
    Check if user has an active subscription with unlimited hearts.

    Returns True if user has a subscription where hearts_limit == 0 (unlimited).
    """
    try:
        subscription = UserSubscription.objects.select_related('plan').get(user=user)
        if subscription.plan and subscription.is_active() and subscription.plan.hearts_limit == 0:
            logger.info(f"User {user.username} has unlimited hearts (subscription: {subscription.plan.name})")
            return True
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error checking unlimited hearts for user {user}: {e}")
    return False


class CoursesListView(generics.ListAPIView):
    """
    GET /api/v1/student/practice-courses/courses/

    List all published practice courses for students.
    """
    permission_classes = []
    
    def get_queryset(self):
        """
        Get published practice courses for students only
        """
        try:
            # Students see only published practice courses
            queryset = Course.objects.filter(
                course_type='practice', 
                status='Published'
            ).distinct().order_by('-created_at')
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🎓 STUDENT - Found {queryset.count()} published practice courses")
            return queryset
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"🚨 ERROR in get_queryset: {str(e)}")
            return Course.objects.none()
    
    def list(self, request, *args, **kwargs):
        courses = self.get_queryset()
        data = []

        # Check if statistics are requested (for student course info)
        include_stats = request.query_params.get('include_stats', 'false').lower() in ['true', '1', 'yes']

        # Check if user is authenticated for progress calculation
        user = request.user if request.user.is_authenticated else None

        for course in courses:
            course_data = {
                'id': str(course.id),
                'title': course.title,
                'description': course.description,
                'image': course.image,
                'category': course.category,
                'level': course.level,
                'template': course.template,
                'created_at': course.created_at.isoformat() if course.created_at else None,
                'updated_at': course.updated_at.isoformat() if course.updated_at else None,
            }

            # Add statistics if requested for student course selection
            if include_stats:
                try:
                    # Get units count for this course
                    units_count = course.practice_units.count()

                    # Get lessons for this course
                    lessons = PracticeLesson.objects.filter(unit__course=course)
                    lessons_count = lessons.count()

                    # Get challenges count for this course
                    challenges_count = PracticeChallenge.objects.filter(
                        lesson__unit__course=course
                    ).count()

                    # Calculate user progress if authenticated
                    progress = 0
                    completed_lessons = 0
                    if user and lessons_count > 0:
                        # For each lesson, check if ALL its challenges are completed
                        for lesson in lessons:
                            lesson_challenges_count = lesson.challenges.count()
                            if lesson_challenges_count > 0:
                                completed_challenges = ChallengeProgress.objects.filter(
                                    user=user,
                                    challenge__lesson=lesson,
                                    completed=True
                                ).count()
                                if completed_challenges == lesson_challenges_count:
                                    completed_lessons += 1

                        # Calculate percentage
                        progress = round((completed_lessons / lessons_count) * 100)

                    course_data.update({
                        'units_count': units_count,
                        'lessons_count': lessons_count,
                        'challenges_count': challenges_count,
                        'totalUnits': units_count,
                        'total_lessons': lessons_count,
                        'total_challenges': challenges_count,
                        'progress': progress,
                        'completed_lessons': completed_lessons,
                    })

                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"⚠️ Failed to calculate statistics for course {course.id}: {str(e)}")
                    course_data.update({
                        'units_count': 0,
                        'lessons_count': 0,
                        'challenges_count': 0,
                        'totalUnits': 0,
                        'total_lessons': 0,
                        'total_challenges': 0,
                        'progress': 0,
                        'completed_lessons': 0,
                    })

            data.append(course_data)

        return Response(data)


# Course creation removed - student endpoints only


class CourseUnitsView(generics.ListAPIView):
    """
    GET /api/v1/practice/courses/{course_id}/units/
    
    List all practice units for a specific course.
    Maps to getCourse query from client project.
    """
    serializer_class = PracticeUnitSerializer
    permission_classes = []
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        course = get_object_or_404(Course, id=course_id)
        return PracticeUnit.objects.filter(course=course).prefetch_related(
            'lessons__challenges__options'
        )


class LessonDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/practice/lessons/{lesson_id}/

    Get detailed lesson with challenges for quiz page.
    Maps to getLesson query from client project.

    P1 FIX: Now enforces subscription limits via @subscription_required decorator.
    """
    serializer_class = LessonDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'lesson_id'

    # P1 FIX: Enforce subscription limits on lesson access
    @method_decorator(subscription_required('lesson'))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return PracticeLesson.objects.select_related('unit').prefetch_related(
            'challenges__options'
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UserProgressView(APIView):
    """
    GET/PUT /api/v1/practice/user-progress/
    
    Get or update user's practice progress (hearts, points, active course).
    Maps to getUserProgress query from client project.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's current progress including subscription status"""
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={
                'hearts': 5,
                'points': 0,
                'active_course': None
            }
        )
        serializer = UserProgressSerializer(user_progress)
        data = serializer.data

        # Add subscription status to response
        has_active_subscription = False
        has_unlimited_hearts_flag = False
        try:
            subscription = UserSubscription.objects.select_related('plan').get(user=request.user)
            if subscription.plan and subscription.is_active():
                has_active_subscription = True
                if subscription.plan.hearts_limit == 0:
                    has_unlimited_hearts_flag = True
        except UserSubscription.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error checking subscription for user {request.user}: {e}")

        data['has_active_subscription'] = has_active_subscription
        data['has_unlimited_hearts'] = has_unlimited_hearts_flag

        return Response(data)
    
    def put(self, request):
        """Update user's progress (hearts, points, active course)"""
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={
                'hearts': 5,
                'points': 0,
                'active_course': None
            }
        )
        
        # Handle active_course selection from frontend
        data = request.data.copy()
        if 'active_course' in data and isinstance(data['active_course'], dict):
            # Frontend sends full course object, we need just the ID
            course_id = data['active_course'].get('id')
            if course_id:
                try:
                    course = Course.objects.get(id=course_id)
                    data['active_course'] = course.id
                except Course.DoesNotExist:
                    return Response(
                        {'error': 'Course not found'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        serializer = UserProgressUpdateSerializer(
            user_progress, 
            data=data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            # Return the full serialized data including course details
            full_serializer = UserProgressSerializer(user_progress)
            return Response(full_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChallengeProgressView(APIView):
    """
    POST /api/v1/practice/challenge-progress/

    Create or update challenge progress when user completes a challenge.
    Maps to upsertChallengeProgress action from client project.

    Uses database transaction to ensure consistency when updating
    challenge progress and user points/hearts atomically.

    SECURITY: Rate limited to prevent abuse of points/hearts system.

    P1 FIX: Now enforces hearts requirement via @hearts_required decorator.

    Supports multiple challenge types:
    - SELECT/ASSIST/TRUE_FALSE: selected_option (option ID)
    - FILL_BLANK/TRANSLATION: text_answer (string with typo tolerance)
    - SENTENCE_ORDER: ordered_options (array of option IDs in user's order)
    - MATCH_PAIRS: paired_options (dict mapping left option ID to right option ID)
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChallengeProgressThrottle]

    # P1 FIX: Enforce hearts requirement before processing challenge
    @method_decorator(hearts_required())
    @transaction.atomic
    def post(self, request):
        """Complete a challenge and update user progress"""
        import logging
        from difflib import SequenceMatcher
        logger = logging.getLogger(__name__)

        logger.info(f"ChallengeProgress POST request: {request.data}")

        # Accept both 'challenge' and 'challenge_id' for compatibility
        challenge_id = request.data.get('challenge_id') or request.data.get('challenge')
        selected_option_id = request.data.get('selected_option')
        text_answer = request.data.get('text_answer')
        text_answers = request.data.get('text_answers')  # Array for multiple blanks
        ordered_options = request.data.get('ordered_options')
        paired_options = request.data.get('paired_options')
        pronunciation_score = request.data.get('pronunciation_score')

        logger.info(f"Challenge ID: {challenge_id}, Selected Option: {selected_option_id}, Text Answer: {text_answer is not None}, Text Answers: {text_answers is not None}")

        # Input length validation to prevent abuse
        MAX_TEXT_LENGTH = 2000
        MAX_ANSWER_COUNT = 50

        if text_answer and len(str(text_answer)) > MAX_TEXT_LENGTH:
            logger.warning(f"Text answer too long: {len(str(text_answer))} chars")
            return Response(
                {'error': f'Text answer exceeds maximum length of {MAX_TEXT_LENGTH} characters'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        if text_answers:
            if len(text_answers) > MAX_ANSWER_COUNT:
                logger.warning(f"Too many text answers: {len(text_answers)}")
                return Response(
                    {'error': f'Too many answers (max {MAX_ANSWER_COUNT})'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            for i, ans in enumerate(text_answers):
                if ans and len(str(ans)) > MAX_TEXT_LENGTH:
                    logger.warning(f"Text answer {i} too long: {len(str(ans))} chars")
                    return Response(
                        {'error': f'Text answer exceeds maximum length of {MAX_TEXT_LENGTH} characters'},
                        status=status_module.HTTP_400_BAD_REQUEST
                    )

        if not challenge_id:
            return Response(
                {'error': 'challenge is required'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        try:
            challenge = PracticeChallenge.objects.select_related('lesson', 'lesson__unit', 'lesson__unit__course').get(id=challenge_id)
            logger.info(f"Found challenge: {challenge}, type: {challenge.type}")

            # Validate hierarchy: challenge belongs to a valid lesson/unit/course
            if not challenge.lesson:
                logger.error(f"Challenge {challenge_id} has no associated lesson")
                return Response(
                    {'error': 'Invalid challenge configuration'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

        except PracticeChallenge.DoesNotExist:
            logger.error(f"Challenge not found: {challenge_id}")
            return Response(
                {'error': 'Invalid challenge'},
                status=status_module.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        logger.info(f"User progress: hearts={user_progress.hearts}, points={user_progress.points}, created={created}")

        # Check if this is practice mode (challenge already completed)
        existing_progress = ChallengeProgress.objects.filter(
            user=request.user,
            challenge=challenge
        ).first()

        is_practice = existing_progress is not None
        logger.info(f"Is practice mode: {is_practice}, existing progress: {existing_progress}")

        # Duplicate submission protection: prevent rapid re-submissions (within 2 seconds)
        if existing_progress and existing_progress.updated_at:
            from datetime import timedelta
            time_since_last = timezone.now() - existing_progress.updated_at
            if time_since_last < timedelta(seconds=2):
                logger.warning(f"Duplicate submission detected for challenge {challenge_id} by user {request.user.id}")
                # Return success with existing data to prevent frontend errors
                return Response({
                    'success': True,
                    'correct': existing_progress.completed,
                    'duplicate': True,
                    'message': 'Submission already processed',
                    'user_progress': {
                        'hearts': user_progress.hearts,
                        'points': user_progress.points
                    }
                }, status=status_module.HTTP_200_OK)

        # Check hearts for new challenges (skip for users with unlimited hearts subscription)
        if user_progress.hearts == 0 and not is_practice and not has_unlimited_hearts(request.user):
            logger.info("User has no hearts and this is not practice mode")
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        # Validate answer based on challenge type
        is_correct = False
        challenge_type = challenge.type

        # Initialize variables that may be used in response
        similarity = None
        matched = None

        if challenge_type in ['SELECT', 'ASSIST', 'TRUE_FALSE']:
            # Simple option selection - validate selected_option
            if not selected_option_id:
                return Response(
                    {'error': f'selected_option is required for {challenge_type} challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            try:
                selected_option = ChallengeOption.objects.get(id=selected_option_id, challenge=challenge)
                is_correct = selected_option.is_correct
                logger.info(f"Option validation: {selected_option.text}, is_correct: {is_correct}")
            except ChallengeOption.DoesNotExist:
                logger.error(f"Option not found: {selected_option_id} for challenge: {challenge_id}")
                return Response(
                    {'error': 'Invalid option'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

        elif challenge_type == 'LISTENING':
            # LISTENING can be either:
            # 1. Dictation style (has text_answer/text_answers) - validate like FILL_BLANK
            # 2. Multiple choice style (has selected_option) - validate option selection

            if text_answer or text_answers:
                # Dictation style - validate text answers like FILL_BLANK
                logger.info(f"LISTENING dictation mode: text_answer={text_answer}, text_answers={text_answers}")

                correct_options = list(challenge.options.filter(is_correct=True).order_by('order'))
                if not correct_options:
                    logger.error(f"No correct options for LISTENING challenge: {challenge_id}")
                    return Response(
                        {'error': 'Challenge has no correct answer configured'},
                        status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                from apps.practice.services.text_validation import TextValidationService

                # Handle multiple blanks
                if text_answers and isinstance(text_answers, list) and len(text_answers) > 1:
                    logger.info(f"LISTENING multiple blanks: {len(text_answers)} answers for {len(correct_options)} blanks")

                    # Validate answer count matches expected blank count
                    if len(text_answers) != len(correct_options):
                        logger.warning(f"LISTENING: Answer count mismatch. Expected {len(correct_options)}, got {len(text_answers)}")
                        return Response(
                            {'error': f'Expected {len(correct_options)} answers, received {len(text_answers)}'},
                            status=status_module.HTTP_400_BAD_REQUEST
                        )

                    all_correct = True
                    total_similarity = 0.0

                    for i, user_ans in enumerate(text_answers):
                        # Validate that answer is not empty
                        if not user_ans or not str(user_ans).strip():
                            logger.info(f"LISTENING Blank {i+1}: Empty answer provided")
                            all_correct = False
                            continue

                        correct_ans = correct_options[i].text
                        ans_correct, ans_similarity, _ = TextValidationService.validate_against_multiple(
                            user_answer=str(user_ans).strip(),
                            correct_answers=[correct_ans],
                            tolerance=TextValidationService.DEFAULT_TOLERANCE
                        )
                        if not ans_correct:
                            all_correct = False
                        total_similarity += ans_similarity
                        logger.info(f"LISTENING Blank {i+1}: '{user_ans}' vs '{correct_ans}' = {ans_correct} ({ans_similarity:.2%})")

                    is_correct = all_correct
                    similarity = total_similarity / len(text_answers) if text_answers else 0
                    matched = ', '.join([opt.text for opt in correct_options])
                    logger.info(f"LISTENING multiple blanks result: is_correct={is_correct}, avg_similarity={similarity:.2%}")
                else:
                    # Single blank
                    correct_answers = [opt.text for opt in correct_options]
                    is_correct, similarity, matched = TextValidationService.validate_against_multiple(
                        user_answer=text_answer,
                        correct_answers=correct_answers,
                        tolerance=TextValidationService.DEFAULT_TOLERANCE
                    )
                    logger.info(f"LISTENING single blank result: is_correct={is_correct}, similarity={similarity:.2%}")

            elif selected_option_id:
                # Multiple choice style - original behavior
                try:
                    selected_option = ChallengeOption.objects.get(id=selected_option_id, challenge=challenge)
                    is_correct = selected_option.is_correct
                    logger.info(f"LISTENING option validation: {selected_option.text}, is_correct: {is_correct}")
                except ChallengeOption.DoesNotExist:
                    logger.error(f"Option not found: {selected_option_id} for LISTENING challenge: {challenge_id}")
                    return Response(
                        {'error': 'Invalid option'},
                        status=status_module.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': 'Either selected_option or text_answer/text_answers is required for LISTENING challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

        elif challenge_type == 'TRANSLATION':
            # Translation with aggressive normalization and multiple correct answers
            if not text_answer:
                return Response(
                    {'error': 'text_answer is required for TRANSLATION challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Get all correct options (supports multiple correct translations)
            correct_options = challenge.options.filter(is_correct=True)
            if not correct_options.exists():
                logger.error(f"No correct options for challenge: {challenge_id}")
                return Response(
                    {'error': 'Challenge has no correct answer configured'},
                    status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Use specialized translation validation with aggressive normalization
            from apps.practice.services.text_validation import TextValidationService

            correct_answers = [opt.text for opt in correct_options]

            # Debug: Log expected answers for troubleshooting
            logger.info(f"TRANSLATION challenge {challenge_id}: "
                       f"User answer: '{text_answer}', "
                       f"Expected answers: {correct_answers}")

            is_correct, similarity, matched = TextValidationService.validate_translation(
                user_answer=text_answer,
                correct_answers=correct_answers
                # Uses TRANSLATION_TOLERANCE (70%) by default
            )

            logger.info(f"Translation validation result: is_correct={is_correct}, "
                       f"similarity={similarity:.2%}, matched='{matched}'")

        elif challenge_type == 'FILL_BLANK':
            # Fill blank with typo tolerance - supports single or multiple blanks
            if not text_answer and not text_answers:
                return Response(
                    {'error': 'text_answer or text_answers is required for FILL_BLANK challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Get correct options ordered by position
            correct_options = list(challenge.options.filter(is_correct=True).order_by('order'))
            if not correct_options:
                logger.error(f"No correct options for challenge: {challenge_id}")
                return Response(
                    {'error': 'Challenge has no correct answer configured'},
                    status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                )

            from apps.practice.services.text_validation import TextValidationService

            # Handle multiple blanks (text_answers array)
            if text_answers and isinstance(text_answers, list) and len(text_answers) > 1:
                logger.info(f"Multiple blanks validation: {len(text_answers)} answers for {len(correct_options)} blanks")

                # Validate answer count matches expected blank count
                if len(text_answers) != len(correct_options):
                    logger.warning(f"FILL_BLANK: Answer count mismatch. Expected {len(correct_options)}, got {len(text_answers)}")
                    return Response(
                        {'error': f'Expected {len(correct_options)} answers, received {len(text_answers)}'},
                        status=status_module.HTTP_400_BAD_REQUEST
                    )

                # Validate each answer against corresponding correct option
                all_correct = True
                total_similarity = 0.0
                results = []

                for i, user_ans in enumerate(text_answers):
                    # Validate that answer is not empty
                    if not user_ans or not str(user_ans).strip():
                        logger.info(f"Blank {i+1}: Empty answer provided")
                        all_correct = False
                        results.append({
                            'blank': i + 1,
                            'user': user_ans,
                            'correct': False,
                            'similarity': 0.0
                        })
                        continue

                    correct_ans = correct_options[i].text
                    ans_correct, ans_similarity, ans_matched = TextValidationService.validate_against_multiple(
                        user_answer=str(user_ans).strip(),
                        correct_answers=[correct_ans],
                        tolerance=TextValidationService.DEFAULT_TOLERANCE
                    )
                    results.append({
                        'blank': i + 1,
                        'user': user_ans,
                        'correct': ans_correct,
                        'similarity': ans_similarity
                    })
                    total_similarity += ans_similarity
                    if not ans_correct:
                        all_correct = False
                    logger.info(f"Blank {i+1}: '{user_ans}' vs '{correct_ans}' = {ans_correct} ({ans_similarity:.2%})")

                is_correct = all_correct
                similarity = total_similarity / len(text_answers) if text_answers else 0
                matched = ', '.join([opt.text for opt in correct_options])

                logger.info(f"Multiple blanks result: is_correct={is_correct}, avg_similarity={similarity:.2%}")
            else:
                # Single blank - original validation
                correct_answers = [opt.text for opt in correct_options]
                is_correct, similarity, matched = TextValidationService.validate_against_multiple(
                    user_answer=text_answer,
                    correct_answers=correct_answers,
                    tolerance=TextValidationService.DEFAULT_TOLERANCE  # 85%
                )
                logger.info(f"Fill blank validation: '{text_answer}', is_correct: {is_correct}, "
                           f"similarity: {similarity:.2%}, matched: '{matched}'")

        elif challenge_type == 'SENTENCE_ORDER':
            # Ordered sequence validation
            if not ordered_options or not isinstance(ordered_options, list):
                return Response(
                    {'error': 'ordered_options (array) is required for SENTENCE_ORDER challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Get correct order from options using the 'order' field
            correct_order = list(
                challenge.options.order_by('order')
                .values_list('id', flat=True)
            )
            correct_order_str = [str(opt_id) for opt_id in correct_order]

            # Convert user order to comparable format (string UUIDs)
            user_order = [str(opt_id) for opt_id in ordered_options]

            # Validate array length matches expected options
            if len(user_order) != len(correct_order_str):
                logger.warning(f"SENTENCE_ORDER: Length mismatch. Expected {len(correct_order_str)}, got {len(user_order)}")
                return Response(
                    {'error': f'Expected {len(correct_order_str)} items, received {len(user_order)}'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Check for duplicates in user submission
            if len(user_order) != len(set(user_order)):
                logger.warning(f"SECURITY: SENTENCE_ORDER duplicate IDs in submission")
                return Response(
                    {'error': 'Duplicate option IDs are not allowed'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # SECURITY: Validate that all submitted UUIDs belong to this challenge
            valid_option_ids = set(correct_order_str)
            submitted_ids = set(user_order)

            if submitted_ids != valid_option_ids:
                invalid_ids = submitted_ids - valid_option_ids
                missing_ids = valid_option_ids - submitted_ids
                logger.warning(f"SECURITY: SENTENCE_ORDER invalid submission. Invalid IDs: {invalid_ids}, Missing: {missing_ids}")
                return Response(
                    {'error': 'Invalid option IDs submitted'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            is_correct = user_order == correct_order_str
            logger.info(f"Sentence order validation: user={user_order}, correct={correct_order_str}, is_correct: {is_correct}")

        elif challenge_type == 'MATCH_PAIRS':
            # Paired matching validation
            # Frontend sends: { "option_id": "portuguese_text", ... }
            # Options are stored as "English - Portuguese" format
            if not paired_options or not isinstance(paired_options, dict):
                return Response(
                    {'error': 'paired_options (object) is required for MATCH_PAIRS challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Get all options for this challenge
            all_options = list(challenge.options.order_by('order'))
            valid_option_ids = {str(opt.id) for opt in all_options}

            # SECURITY: Validate that all submitted IDs belong to this challenge
            submitted_ids = set(paired_options.keys())
            if not submitted_ids.issubset(valid_option_ids):
                invalid_ids = submitted_ids - valid_option_ids
                logger.warning(f"SECURITY: MATCH_PAIRS invalid IDs submitted: {invalid_ids}")
                return Response(
                    {'error': 'Invalid option IDs submitted'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Check all options are paired
            if len(paired_options) != len(all_options):
                logger.info(f"MATCH_PAIRS: Incomplete pairs. Expected {len(all_options)}, got {len(paired_options)}")
                return Response(
                    {'error': 'All pairs must be matched'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Helper function for text normalization
            def normalize_text(text):
                if not text:
                    return ""
                return ' '.join(text.lower().strip().split())

            # TYPO_TOLERANCE for MATCH_PAIRS (85% - stricter than text input)
            MATCH_PAIRS_TOLERANCE = 0.85

            # Validate each pair
            all_correct = True
            for opt in all_options:
                opt_id = str(opt.id)
                if opt_id in paired_options:
                    # Parse the expected format - support multiple delimiters
                    text = opt.text
                    parts = None

                    # Try common delimiters: " - ", " – ", " = ", " : "
                    for delimiter in [' - ', ' – ', ' = ', ' : ']:
                        if delimiter in text:
                            parts = text.split(delimiter, 1)  # Split only on first occurrence
                            break

                    if parts and len(parts) == 2:
                        expected_portuguese = normalize_text(parts[1])
                        submitted_portuguese = normalize_text(paired_options[opt_id])

                        if expected_portuguese != submitted_portuguese:
                            similarity = SequenceMatcher(None, expected_portuguese, submitted_portuguese).ratio()
                            if similarity < MATCH_PAIRS_TOLERANCE:
                                all_correct = False
                                logger.info(f"MATCH_PAIRS: Mismatch for {opt_id}. Expected: '{parts[1]}', Got: '{paired_options[opt_id]}' (similarity: {similarity:.2%})")
                                break
                    else:
                        # Fallback: compare full text if no delimiter found
                        logger.warning(f"MATCH_PAIRS: No delimiter found in '{opt.text}', using full text comparison")
                        expected = normalize_text(opt.text)
                        submitted = normalize_text(paired_options[opt_id])
                        similarity = SequenceMatcher(None, expected, submitted).ratio()
                        if similarity < MATCH_PAIRS_TOLERANCE:
                            all_correct = False
                            break

            is_correct = all_correct
            logger.info(f"Match pairs validation: paired_options={paired_options}, is_correct: {is_correct}")

        elif challenge_type == 'VAPI_CONVERSATION':
            # SECURITY FIX: Verify score from server-side VapiSession, not client
            # Frontend must send: { "session_id": "uuid" }
            session_id = request.data.get('session_id')

            if not session_id:
                logger.warning("VAPI_CONVERSATION: No session_id provided")
                return Response(
                    {'error': 'session_id is required for VAPI_CONVERSATION challenges'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Look up the VapiSession to get the authoritative score
            try:
                from apps.practice.models import VapiSession
                vapi_session = VapiSession.objects.get(
                    session_id=session_id,
                    user=request.user  # Ensure session belongs to this user
                )
                score = float(vapi_session.overall_score)
                logger.info(f"VAPI_CONVERSATION: Retrieved server-side score={score} for session={session_id}")
            except VapiSession.DoesNotExist:
                logger.warning(f"VAPI_CONVERSATION: Session not found or doesn't belong to user: {session_id}")
                return Response(
                    {'error': 'Invalid session_id or session not found'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Minimum passing score is 60%
            VAPI_PASSING_SCORE = 60.0
            is_correct = score >= VAPI_PASSING_SCORE
            logger.info(f"VAPI_CONVERSATION: score={score}, passing={VAPI_PASSING_SCORE}, is_correct={is_correct}")

        elif challenge_type == 'SPEAKING':
            # SECURITY FIX: SPEAKING challenges must use AIPronunciationAnalysisView endpoint
            # which performs server-side AI validation (Whisper + GPT-4) and updates progress.
            #
            # This endpoint does NOT accept client-supplied pronunciation_score to prevent
            # score injection attacks. Users must call:
            # POST /api/v1/practice/analyze-ai-pronunciation/
            # with audio file and challenge_id for proper server-side validation.
            #
            # The AIPronunciationAnalysisView already handles:
            # - Server-side AI pronunciation analysis
            # - ChallengeProgress creation/update
            # - Hearts and points management
            # - Subscription-based AI analysis limits

            logger.warning(f"SPEAKING: Direct validation not allowed. Use AIPronunciationAnalysisView endpoint.")
            return Response(
                {
                    'error': 'SPEAKING challenges must use the AI pronunciation analysis endpoint',
                    'endpoint': '/api/v1/practice/analyze-ai-pronunciation/',
                    'message': 'Submit audio file with challenge_id for server-side pronunciation analysis'
                },
                status=status_module.HTTP_400_BAD_REQUEST
            )

        else:
            logger.warning(f"Unknown challenge type: {challenge_type}")
            return Response(
                {'error': f'Unsupported challenge type: {challenge_type}'},
                status=status_module.HTTP_400_BAD_REQUEST
            )

        # Process result based on correctness
        if is_correct:
            # Correct answer: mark challenge as completed
            if existing_progress:
                existing_progress.completed = True
                existing_progress.save()
                progress = existing_progress
            else:
                progress = ChallengeProgress.objects.create(
                    user=request.user,
                    challenge=challenge,
                    completed=True
                )

            # Update user progress based on practice mode
            if is_practice:
                # Practice mode: restore hearts and add points
                user_progress.add_hearts(1)
                user_progress.add_points(10)
            else:
                # New challenge: just add points
                user_progress.add_points(10)

            return Response({
                'success': True,
                'correct': True,
                'challenge_progress': {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                },
                'user_progress': {
                    'hearts': user_progress.hearts,
                    'points': user_progress.points
                }
            }, status=status_module.HTTP_200_OK)
        else:
            # Wrong answer: don't complete challenge, reduce hearts if not practice
            # Check if user has active subscription with unlimited hearts
            user_has_unlimited = has_unlimited_hearts(request.user)

            if not is_practice and user_progress.hearts > 0 and not user_has_unlimited:
                user_progress.reduce_hearts()

            # Build response with optional feedback for text challenges
            response_data = {
                'success': True,
                'correct': False,
                'user_progress': {
                    'hearts': user_progress.hearts if not user_has_unlimited else 999,
                    'points': user_progress.points
                },
                'heartsUsed': 1 if not user_has_unlimited and not is_practice else 0,
            }

            # Add feedback for TRANSLATION/FILL_BLANK challenges
            if challenge_type in ('TRANSLATION', 'FILL_BLANK', 'LISTENING') and similarity is not None:
                response_data['feedback'] = {
                    'similarity': round(similarity * 100, 1),
                }
                if matched:
                    # Give a hint without revealing full answer
                    hint_text = matched[:3] + '...' if len(matched) > 3 else matched
                    response_data['feedback']['hint'] = hint_text

            return Response(response_data, status=status_module.HTTP_200_OK)


class ReduceHeartsView(APIView):
    """
    POST /api/v1/practice/reduce-hearts/
    
    Reduce user hearts when they get an answer wrong.
    Maps to reduceHearts action from client project.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Reduce user hearts by 1 (skip for users with unlimited hearts subscription)"""
        # Check if user has unlimited hearts subscription
        if has_unlimited_hearts(request.user):
            return Response({
                'hearts': 999,  # Symbolic infinite value
                'points': 0,
                'unlimited': True
            })

        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )

        if user_progress.hearts > 0:
            user_progress.reduce_hearts()

            return Response({
                'hearts': user_progress.hearts,
                'points': user_progress.points
            })

        return Response(
            {'error': 'No hearts to reduce'},
            status=status.HTTP_400_BAD_REQUEST
        )


class RefillHeartsView(APIView):
    """
    POST /api/v1/practice/refill-hearts/

    Refill user hearts (for premium users only).

    P1 FIX: This is a premium feature - now enforces premium subscription.
    """
    permission_classes = [IsAuthenticated]

    # P1 FIX: Require premium subscription for heart refill
    @method_decorator(premium_required())
    def post(self, request):
        """Refill hearts to maximum (5) - PREMIUM ONLY"""
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )

        user_progress.hearts = 5
        user_progress.save()

        return Response({
            'hearts': user_progress.hearts,
            'points': user_progress.points,
            'message': 'Hearts refilled successfully (Premium feature)'
        })


class ValidateTextAnswerView(APIView):
    """
    POST /api/v1/practice/validate-text-answer/
    
    Validate text-based answers for FILL_BLANK, TRANSLATION, and other text input challenges.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate user's text answer against correct option"""
        import logging
        logger = logging.getLogger(__name__)
        
        challenge_id = request.data.get('challenge_id')
        user_answer = request.data.get('user_answer', '').strip()
        
        if not challenge_id or not user_answer:
            return Response(
                {'error': 'challenge_id and user_answer are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            challenge = PracticeChallenge.objects.get(id=challenge_id)
        except PracticeChallenge.DoesNotExist:
            return Response(
                {'error': 'Challenge not found'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )
        
        # Get user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        # Check if user already completed this challenge
        existing_progress = ChallengeProgress.objects.filter(
            user=request.user,
            challenge=challenge
        ).first()
        
        is_practice = existing_progress is not None
        logger.info(f"Text answer validation - Practice mode: {is_practice}")
        
        # Check hearts for new challenges (skip for users with unlimited hearts subscription)
        if user_progress.hearts == 0 and not is_practice and not has_unlimited_hearts(request.user):
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'},
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Get the correct answer from challenge options
        correct_option = challenge.options.filter(is_correct=True).first()
        if not correct_option:
            return Response(
                {'error': 'No correct answer found for this challenge'},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Use TextValidationService for consistent validation with typo tolerance
        from apps.practice.services.text_validation import TextValidationService

        is_correct, similarity = TextValidationService.validate(
            user_answer=user_answer,
            correct_answer=correct_option.text,
            tolerance=TextValidationService.DEFAULT_TOLERANCE  # 85%
        )

        logger.info(f"Text validation: '{user_answer}' vs '{correct_option.text}' "
                   f"(similarity: {similarity:.2%}, correct: {is_correct})")
        
        if is_correct:
            # Correct answer: mark challenge as completed
            if existing_progress:
                existing_progress.completed = True
                existing_progress.save()
                progress = existing_progress
            else:
                progress = ChallengeProgress.objects.create(
                    user=request.user,
                    challenge=challenge,
                    completed=True
                )
            
            # Update user progress based on practice mode
            if is_practice:
                # Practice mode: restore hearts and add points
                user_progress.add_hearts(1)
                user_progress.add_points(10)
            else:
                # New challenge: just add points
                user_progress.add_points(10)
            
            return Response({
                'success': True,
                'correct': True,
                'user_answer': user_answer,
                'correct_answer': correct_option.text,
                'challenge_progress': {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                },
                'user_progress': {
                    'hearts': user_progress.hearts,
                    'points': user_progress.points
                }
            }, status=status_module.HTTP_200_OK)
        else:
            # Wrong answer: don't complete challenge, reduce hearts if not practice
            # P1 FIX: Check has_unlimited_hearts before reducing hearts
            user_has_unlimited = has_unlimited_hearts(request.user)
            if not is_practice and user_progress.hearts > 0 and not user_has_unlimited:
                user_progress.reduce_hearts()

            return Response({
                'success': True,
                'correct': False,
                'user_answer': user_answer,
                'correct_answer': correct_option.text,
                'user_progress': {
                    'hearts': user_progress.hearts,
                    'points': user_progress.points
                }
            }, status=status_module.HTTP_200_OK)


class GetAudioUploadUrlView(APIView):
    """
    POST /api/v1/practice/challenges/{challenge_id}/get-audio-upload-url/

    Get presigned S3 URL for audio upload in listening challenges.

    Security:
    - Validates user ownership (must be course teacher or staff)
    - Validates MIME type (audio only)
    - Validates file size (max 50MB)
    - Validates file extension
    """
    permission_classes = [IsAuthenticated]

    # Allowed audio MIME types
    ALLOWED_AUDIO_TYPES = [
        'audio/mpeg',
        'audio/mp3',
        'audio/wav',
        'audio/x-wav',
        'audio/ogg',
        'audio/webm',
        'audio/x-m4a',
        'audio/mp4',
        'audio/aac',
    ]

    # Allowed audio extensions
    ALLOWED_AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'webm', 'm4a', 'aac', 'mp4']

    # Max file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def post(self, request, challenge_id):
        """Generate presigned URL for audio upload to S3"""
        import boto3
        import uuid
        import os
        from django.conf import settings

        try:
            # Validate request data
            lesson_id = request.data.get('lessonId')
            file_name = request.data.get('fileName', '')
            file_type = request.data.get('fileType', '')
            file_size = request.data.get('fileSize', 0)

            if not all([lesson_id, file_name, file_type]):
                return Response(
                    {'error': 'lessonId, fileName, and fileType são obrigatórios'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Verify challenge exists and get ownership info
            try:
                challenge = PracticeChallenge.objects.select_related(
                    'lesson__unit__course'
                ).get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Desafio não encontrado'},
                    status=status_module.HTTP_404_NOT_FOUND
                )

            # SECURITY: Verify user ownership
            course = challenge.lesson.unit.course
            if course.teacher != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'Não autorizado. Apenas o professor do curso pode fazer upload de áudio.'},
                    status=status_module.HTTP_403_FORBIDDEN
                )

            # SECURITY: Validate MIME type
            if file_type not in self.ALLOWED_AUDIO_TYPES:
                return Response(
                    {'error': f'Tipo de arquivo não permitido. Use: MP3, WAV, OGG, WebM, M4A, AAC'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # SECURITY: Validate file extension
            file_extension = os.path.splitext(file_name)[1].lower().lstrip('.')
            if not file_extension or file_extension not in self.ALLOWED_AUDIO_EXTENSIONS:
                return Response(
                    {'error': f'Extensão de arquivo não permitida. Use: {", ".join(self.ALLOWED_AUDIO_EXTENSIONS)}'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # SECURITY: Validate file size
            if file_size and int(file_size) > self.MAX_FILE_SIZE:
                max_mb = self.MAX_FILE_SIZE // (1024 * 1024)
                return Response(
                    {'error': f'Arquivo muito grande. Tamanho máximo: {max_mb}MB'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Generate unique file name to avoid conflicts (use validated extension)
            unique_filename = f"audio/{lesson_id}/{challenge_id}/{uuid.uuid4().hex}.{file_extension}"

            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME or 'us-east-1'
            )

            # Generate presigned URL for upload
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': unique_filename,
                    'ContentType': file_type
                },
                ExpiresIn=3600  # 1 hour
            )

            # Construct the final audio URL
            audio_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

            return Response({
                'message': 'URL de upload de áudio gerada com sucesso',
                'data': {
                    'uploadUrl': presigned_url,
                    'audioUrl': audio_url,
                    'fileName': unique_filename
                }
            }, status=status_module.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Falha ao gerar URL de upload: {str(e)}'},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetImageUploadUrlView(APIView):
    """
    POST /api/v1/practice/challenges/{challenge_id}/get-image-upload-url/

    Get presigned S3 URL for image upload in listening challenges.

    Security:
    - Validates user ownership (must be course teacher or staff)
    - Validates MIME type (images only)
    - Validates file size (max 10MB)
    - Validates file extension
    """
    permission_classes = [IsAuthenticated]

    # Allowed image MIME types
    ALLOWED_IMAGE_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp',
        'image/gif',
        'image/svg+xml',
    ]

    # Allowed image extensions
    ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']

    # Max file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def post(self, request, challenge_id):
        """Generate presigned URL for image upload to S3"""
        import boto3
        import uuid
        import os
        from django.conf import settings

        try:
            # Validate request data
            lesson_id = request.data.get('lessonId')
            file_name = request.data.get('fileName', '')
            file_type = request.data.get('fileType', '')
            file_size = request.data.get('fileSize', 0)

            if not all([lesson_id, file_name, file_type]):
                return Response(
                    {'error': 'lessonId, fileName, and fileType são obrigatórios'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Verify challenge exists and get ownership info
            try:
                challenge = PracticeChallenge.objects.select_related(
                    'lesson__unit__course'
                ).get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Desafio não encontrado'},
                    status=status_module.HTTP_404_NOT_FOUND
                )

            # SECURITY: Verify user ownership
            course = challenge.lesson.unit.course
            if course.teacher != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'Não autorizado. Apenas o professor do curso pode fazer upload de imagens.'},
                    status=status_module.HTTP_403_FORBIDDEN
                )

            # SECURITY: Validate MIME type
            if file_type not in self.ALLOWED_IMAGE_TYPES:
                return Response(
                    {'error': f'Tipo de arquivo não permitido. Use: JPG, PNG, WebP, GIF, SVG'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # SECURITY: Validate file extension
            file_extension = os.path.splitext(file_name)[1].lower().lstrip('.')
            if not file_extension or file_extension not in self.ALLOWED_IMAGE_EXTENSIONS:
                return Response(
                    {'error': f'Extensão de arquivo não permitida. Use: {", ".join(self.ALLOWED_IMAGE_EXTENSIONS)}'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # SECURITY: Validate file size
            if file_size and int(file_size) > self.MAX_FILE_SIZE:
                max_mb = self.MAX_FILE_SIZE // (1024 * 1024)
                return Response(
                    {'error': f'Arquivo muito grande. Tamanho máximo: {max_mb}MB'},
                    status=status_module.HTTP_400_BAD_REQUEST
                )

            # Generate unique file name to avoid conflicts (use validated extension)
            unique_filename = f"images/{lesson_id}/{challenge_id}/{uuid.uuid4().hex}.{file_extension}"

            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME or 'us-east-1'
            )

            # Generate presigned URL for upload
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': unique_filename,
                    'ContentType': file_type
                },
                ExpiresIn=3600  # 1 hour
            )

            # Construct the final image URL
            image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"

            return Response({
                'message': 'URL de upload de imagem gerada com sucesso',
                'data': {
                    'uploadUrl': presigned_url,
                    'imageUrl': image_url,
                    'fileName': unique_filename
                }
            }, status=status_module.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Falha ao gerar URL de upload: {str(e)}'},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_units_with_progress(request, course_id):
    """
    GET /api/v1/practice/courses/{course_id}/units-with-progress/
    
    Get course units with user completion progress.
    Enhanced version that includes lesson completion status and course details.
    """
    # Filter specifically for practice courses
    course = get_object_or_404(Course, id=course_id, course_type='practice')
    units = PracticeUnit.objects.filter(course=course).prefetch_related(
        'lessons__challenges'
    )
    
    # Serialize course data manually for practice courses
    course_data = {
        'id': str(course.id),
        'title': course.title,
        'description': course.description,
        'category': course.category,
        'level': course.level,
        'status': course.status,
        'course_type': course.course_type,
        'template': course.template,
        'image': course.image,
        'created_at': course.created_at.isoformat(),
        'updated_at': course.updated_at.isoformat(),
        'teacher': {
            'id': str(course.teacher.id),
            'username': course.teacher.username,
            'email': course.teacher.email,
            'first_name': getattr(course.teacher, 'first_name', ''),
            'last_name': getattr(course.teacher, 'last_name', ''),
        } if course.teacher else None,
        'teacherName': course.teacherName,
    }
    
    # Serialize units data
    units_serializer = PracticeUnitSerializer(
        units, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'course': course_data,
        'units': units_serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lesson_percentage(request, lesson_id):
    """
    GET /api/v1/practice/lessons/{lesson_id}/percentage/
    
    Get lesson completion percentage for current user.
    """
    lesson = get_object_or_404(PracticeLesson, id=lesson_id)
    total_challenges = lesson.challenges.count()
    
    if total_challenges == 0:
        return Response({'percentage': 0})
    
    completed_challenges = ChallengeProgress.objects.filter(
        user=request.user,
        challenge__lesson=lesson,
        completed=True
    ).count()
    
    percentage = (completed_challenges / total_challenges) * 100
    
    return Response({
        'percentage': round(percentage, 2),
        'completed_challenges': completed_challenges,
        'total_challenges': total_challenges
    })


# ============================================================================
# TEACHER MANAGEMENT VIEWS - CRUD operations for practice content
# ============================================================================

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class PracticeUnitCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/practice/units/ - List units by course (query param: course)
    POST /api/v1/practice/units/ - Create a new practice unit (Teacher only)
    """
    queryset = PracticeUnit.objects.all()
    serializer_class = PracticeUnitSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter units by course if course parameter is provided"""
        queryset = super().get_queryset()
        course_id = self.request.GET.get('course')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        return queryset.order_by('order')
    
    def list(self, request, *args, **kwargs):
        """GET method - List units with same format as units_list_simple"""
        queryset = self.get_queryset()
        
        units_data = []
        for unit in queryset:
            units_data.append({
                'id': str(unit.id),
                'title': unit.title,
                'description': unit.description,
                'order': unit.order,
                'course_id': str(unit.course.id),
                'lessons_count': unit.lessons.count()
            })
        
        return Response({
            'results': units_data,
            'count': len(units_data),
            'message': 'Units retrieved successfully'
        })
    
    def perform_create(self, serializer):
        """POST method - Create new unit"""
        # Add validation for teacher role if needed
        serializer.save()


class PracticeUnitUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/units/{unit_id}/
    
    Update or delete practice unit (Teacher only).
    """
    queryset = PracticeUnit.objects.all()
    serializer_class = PracticeUnitSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'unit_id'


class PracticeLessonCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/practice/lessons/ - List lessons by unit (query param: unit)
    POST /api/v1/practice/lessons/ - Create a new practice lesson (Teacher only)
    """
    serializer_class = PracticeLessonSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        unit_id = self.request.GET.get('unit')
        if unit_id:
            return PracticeLesson.objects.filter(unit_id=unit_id).order_by('order')
        return PracticeLesson.objects.all().order_by('order')
    
    def list(self, request, *args, **kwargs):
        # Same format as lessons_list_simple
        unit_id = request.GET.get('unit')
        if not unit_id:
            return Response(
                {"error": "unit parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lessons = PracticeLesson.objects.filter(
                unit_id=unit_id
            ).order_by('order')
            
            serializer = self.get_serializer(lessons, many=True)
            return Response({
                "message": "Lessons retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            return Response(
                {"error": f"Error fetching lessons: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PracticeLessonUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/lessons/{lesson_id}/
    
    Update or delete practice lesson (Teacher only).
    """
    queryset = PracticeLesson.objects.all()
    serializer_class = PracticeLessonSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'lesson_id'


class PracticeChallengeCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/practice/challenges/ - List challenges by lesson (query param: lesson)
    POST /api/v1/practice/challenges/ - Create a new practice challenge (Teacher only)
    """
    serializer_class = PracticeChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lesson_id = self.request.GET.get('lesson')
        if lesson_id:
            return PracticeChallenge.objects.filter(lesson_id=lesson_id).order_by('order')
        return PracticeChallenge.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        """
        Create a new challenge with options.

        The serializer's create() method handles creating nested options.
        """
        logger.info(f"=== CREATE CHALLENGE ===")
        logger.info(f"Request data: {request.data}")
        logger.info(f"Options in request: {request.data.get('options', 'NOT FOUND')}")

        serializer = self.get_serializer(data=request.data)
        logger.info(f"Serializer initial_data: {serializer.initial_data}")
        logger.info(f"Options in initial_data: {serializer.initial_data.get('options', 'NOT FOUND')}")

        serializer.is_valid(raise_exception=True)
        challenge = serializer.save()

        # Re-fetch to include created options in response
        response_serializer = self.get_serializer(challenge)

        logger.info(f"Challenge created: {challenge.id} with {challenge.options.count()} options")
        logger.info(f"=== END CREATE CHALLENGE ===")

        return Response(response_serializer.data, status=status_module.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        # Same format as challenges_list_simple
        lesson_id = request.GET.get('lesson')
        if not lesson_id:
            return Response(
                {"error": "lesson parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            challenges = PracticeChallenge.objects.filter(
                lesson_id=lesson_id
            ).order_by('order')

            serializer = self.get_serializer(challenges, many=True)
            return Response({
                "message": "Challenges retrieved successfully",
                "data": serializer.data
            })
        except Exception as e:
            return Response(
                {"error": f"Error fetching challenges: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PracticeChallengeUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/challenges/{challenge_id}/
    
    Update or delete practice challenge (Teacher only).
    """
    queryset = PracticeChallenge.objects.all()
    serializer_class = PracticeChallengeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'challenge_id'


class ChallengeOptionCreateView(generics.CreateAPIView):
    """
    POST /api/v1/practice/challenge-options/
    
    Create a new challenge option (Teacher only).
    """
    queryset = ChallengeOption.objects.all()
    serializer_class = ChallengeOptionCreateSerializer
    permission_classes = [IsAuthenticated]


class ChallengeOptionUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/challenge-options/{option_id}/
    
    Update or delete challenge option (Teacher only).
    """
    queryset = ChallengeOption.objects.all()
    serializer_class = ChallengeOptionWithAnswerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'option_id'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_practice_analytics(request):
    """
    GET /api/v1/practice/analytics/
    
    Get analytics data for teacher dashboard.
    """
    # Get all courses
    total_courses = Course.objects.filter(status='Published').count()
    
    # Get total students with progress
    total_students = UserProgress.objects.count()
    
    # Get total challenges
    total_challenges = PracticeChallenge.objects.count()
    
    # Calculate average completion rate
    if total_students > 0:
        all_progress = UserProgress.objects.all()
        completion_rates = []
        
        for progress in all_progress:
            if progress.active_course:
                course_units = PracticeUnit.objects.filter(course=progress.active_course)
                if course_units.exists():
                    total_lessons = PracticeLesson.objects.filter(unit__in=course_units).count()
                    if total_lessons > 0:
                        completed_lessons = ChallengeProgress.objects.filter(
                            user=progress.user,
                            challenge__lesson__unit__course=progress.active_course,
                            completed=True
                        ).values('challenge__lesson').distinct().count()
                        
                        completion_rate = (completed_lessons / total_lessons) * 100
                        completion_rates.append(completion_rate)
        
        avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
    else:
        avg_completion_rate = 0
    
    return Response({
        'total_courses': total_courses,
        'total_students': total_students,
        'total_challenges': total_challenges,
        'avg_completion_rate': round(avg_completion_rate, 2)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_progress_list(request):
    """
    GET /api/v1/practice/student-progress/
    
    Get list of all students and their progress for teacher dashboard.
    """
    students_progress = UserProgress.objects.select_related('user', 'active_course').all()
    
    students_data = []
    for progress in students_progress:
        # Calculate completion stats
        if progress.active_course:
            course_units = PracticeUnit.objects.filter(course=progress.active_course)
            total_lessons = PracticeLesson.objects.filter(unit__in=course_units).count()
            
            completed_lessons = ChallengeProgress.objects.filter(
                user=progress.user,
                challenge__lesson__unit__course=progress.active_course,
                completed=True
            ).values('challenge__lesson').distinct().count()
            
            # Calculate accuracy
            total_attempts = ChallengeProgress.objects.filter(user=progress.user).count()
            correct_attempts = ChallengeProgress.objects.filter(
                user=progress.user, 
                completed=True
            ).count()
            accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        else:
            total_lessons = 0
            completed_lessons = 0
            accuracy = 0
        
        students_data.append({
            'id': progress.user.id,
            'name': f"{progress.user.first_name} {progress.user.last_name}".strip() or progress.user.email,
            'email': progress.user.email,
            'total_points': progress.points,
            'hearts': progress.hearts,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'average_accuracy': round(accuracy, 1),
            'active_course': progress.active_course.title if progress.active_course else None,
            'last_activity': progress.updated_at.isoformat(),
            'joined_at': progress.created_at.isoformat()
        })
    
    return Response(students_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unit_lessons(request, unit_id):
    """
    GET /api/v1/practice/units/{unit_id}/lessons/
    
    Get all lessons for a specific unit.
    """
    unit = get_object_or_404(PracticeUnit, id=unit_id)
    lessons = PracticeLesson.objects.filter(unit=unit).prefetch_related('challenges')
    
    serializer = PracticeLessonSerializer(
        lessons, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)


# ============================================================================
# LEADERBOARD VIEWS - Competition and ranking system
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_global_leaderboard(request):
    """
    GET /api/v1/practice/leaderboard/global/
    
    Get global leaderboard with top users ranked by points.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import F
    
    User = get_user_model()
    
    # Get top users with progress, ordered by points
    leaderboard_data = []
    
    # Get all users with progress, ordered by points
    users_with_progress = UserProgress.objects.select_related('user').order_by('-points')[:50]
    
    current_user_rank = None
    current_user_data = None
    
    for index, user_progress in enumerate(users_with_progress):
        # Get or create league
        user_league, created = UserLeague.objects.get_or_create(
            user=user_progress.user,
            defaults={'current_league': UserLeague.get_league_for_points(user_progress.points)}
        )
        
        if created or user_league.current_league != UserLeague.get_league_for_points(user_progress.points):
            user_league.update_league()
        
        # Get or create streak
        user_streak, _ = UserStreak.objects.get_or_create(
            user=user_progress.user,
            defaults={'current_streak': 0}
        )
        
        # Calculate rank change (mock for now - would need historical data)
        rank_change = 'same'  # TODO: Implement based on LeaderboardSnapshot
        change_amount = None
        
        # Check if this is current user
        is_current_user = user_progress.user == request.user
        if is_current_user:
            current_user_rank = index + 1
            current_user_data = {
                'id': str(user_progress.user.id),
                'rank': index + 1,
                'username': user_progress.user.name if hasattr(user_progress.user, 'name') else user_progress.user.first_name or user_progress.user.email,
                'points': user_progress.points,
                'streak': user_streak.current_streak,
                'league': user_league.current_league,
                'change': rank_change,
                'changeAmount': change_amount,
                'isCurrentUser': True
            }
        
        entry = {
            'id': str(user_progress.user.id),
            'rank': index + 1,
            'username': user_progress.user.name if hasattr(user_progress.user, 'name') else user_progress.user.first_name or user_progress.user.email,
            'avatar': user_progress.user_image_src,
            'points': user_progress.points,
            'streak': user_streak.current_streak,
            'league': user_league.current_league,
            'change': rank_change,
            'changeAmount': change_amount,
            'isCurrentUser': is_current_user
        }
        
        leaderboard_data.append(entry)
    
    # If current user not in top 10, add separately
    response_data = {
        'leaderboard': leaderboard_data[:10],  # Top 10
        'currentUser': current_user_data
    }
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_leagues_info(request):
    """
    GET /api/v1/practice/leaderboard/leagues/
    
    Get leagues information with participant counts.
    """
    leagues_info = []
    
    for league_id, league_name in UserLeague.LEAGUE_CHOICES:
        league_data = UserLeague.get_league_info(league_id)
        
        # Count participants in this league
        participants_count = UserLeague.objects.filter(current_league=league_id).count()
        
        leagues_info.append({
            'id': league_id,
            'name': league_data['name'],
            'icon': league_data['icon'],
            'color': f'text-{league_id}-400' if league_id != 'bronze' else 'text-amber-600',
            'minPoints': league_data['min_points'],
            'maxPoints': league_data['max_points'],
            'participants': participants_count
        })
    
    return Response(leagues_info)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_competitions(request):
    """
    GET /api/v1/practice/leaderboard/competitions/
    
    Get active competitions.
    """
    # Get active competitions
    competitions = Competition.objects.filter(status='active').order_by('-start_date')
    
    serializer = CompetitionSerializer(
        competitions, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_leaderboard_position(request):
    """
    GET /api/v1/practice/leaderboard/user-position/
    
    Get current user's leaderboard position and stats.
    """
    user = request.user
    
    try:
        user_progress = UserProgress.objects.get(user=user)
    except UserProgress.DoesNotExist:
        return Response({'error': 'User progress not found'}, status=404)
    
    # Get or create league
    user_league, created = UserLeague.objects.get_or_create(
        user=user,
        defaults={'current_league': UserLeague.get_league_for_points(user_progress.points)}
    )
    
    # Get or create streak
    user_streak, _ = UserStreak.objects.get_or_create(
        user=user,
        defaults={'current_streak': 0}
    )
    
    # Calculate rank (count users with more points)
    users_with_more_points = UserProgress.objects.filter(points__gt=user_progress.points).count()
    current_rank = users_with_more_points + 1
    
    # Get league info
    league_info = UserLeague.get_league_info(user_league.current_league)
    
    return Response({
        'rank': current_rank,
        'points': user_progress.points,
        'hearts': user_progress.hearts,
        'streak': user_streak.current_streak,
        'league': {
            'id': user_league.current_league,
            'name': league_info['name'],
            'icon': league_info['icon'],
            'min_points': league_info['min_points'],
            'max_points': league_info['max_points']
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_competition(request, competition_id):
    """
    POST /api/v1/practice/leaderboard/competitions/{competition_id}/join/
    
    Join a competition.
    """
    competition = get_object_or_404(Competition, id=competition_id, status='active')
    user = request.user
    
    # Check if user meets requirements
    try:
        user_progress = UserProgress.objects.get(user=user)
        if user_progress.points < competition.min_points_to_participate:
            return Response(
                {'error': f'Minimum {competition.min_points_to_participate} points required'}, 
                status=400
            )
    except UserProgress.DoesNotExist:
        return Response({'error': 'User progress not found'}, status=400)
    
    # Check if already joined
    if CompetitionParticipant.objects.filter(competition=competition, user=user).exists():
        return Response({'error': 'Already joined this competition'}, status=400)
    
    # Check participant limit
    if competition.max_participants and competition.participant_count >= competition.max_participants:
        return Response({'error': 'Competition is full'}, status=400)
    
    # Join competition
    participant = CompetitionParticipant.objects.create(
        competition=competition,
        user=user,
        points_earned=0,
        current_rank=competition.participant_count + 1
    )
    
    return Response({
        'message': 'Successfully joined competition',
        'participant_id': str(participant.id),
        'current_rank': participant.current_rank
    })


class LeaderboardSnapshotCreateView(APIView):
    """
    POST /api/v1/practice/leaderboard/snapshot/

    Create a leaderboard snapshot (for automated tasks).
    Admin only - used by Celery tasks for scheduled snapshots.
    """
    permission_classes = [IsAdminUser]  # SECURITY FIX: Admin only
    
    def post(self, request):
        """Create snapshot of current leaderboard"""
        snapshot_type = request.data.get('type', 'daily')
        
        # Get all users with progress
        users_with_progress = UserProgress.objects.select_related('user').order_by('-points')
        
        snapshots_created = 0
        for index, user_progress in enumerate(users_with_progress):
            # Get user's league
            user_league, _ = UserLeague.objects.get_or_create(
                user=user_progress.user,
                defaults={'current_league': UserLeague.get_league_for_points(user_progress.points)}
            )
            
            # Create snapshot
            snapshot, created = LeaderboardSnapshot.objects.get_or_create(
                user=user_progress.user,
                snapshot_type=snapshot_type,
                defaults={
                    'rank': index + 1,
                    'points': user_progress.points,
                    'league': user_league.current_league,
                    'rank_change': 0,
                    'points_change': 0
                }
            )
            
            if created:
                snapshots_created += 1
        
        return Response({
            'message': f'Created {snapshots_created} leaderboard snapshots',
            'snapshot_type': snapshot_type
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_streak(request):
    """
    PUT /api/v1/practice/leaderboard/update-streak/
    
    Update user's practice streak (called after completing activities).
    """
    user = request.user
    
    # Get or create streak
    user_streak, created = UserStreak.objects.get_or_create(
        user=user,
        defaults={'current_streak': 0}
    )
    
    # Update streak
    user_streak.update_streak()
    
    return Response({
        'current_streak': user_streak.current_streak,
        'longest_streak': user_streak.longest_streak,
        'last_practice_date': user_streak.last_practice_date
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])  # SECURITY FIX: Admin only - was public, leaked PII
def test_leaderboard_data(request):
    """
    Test endpoint to check leaderboard data (Admin only).
    WARNING: This endpoint exposes user PII - use only for debugging.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get all users with progress, ordered by points
    users_with_progress = UserProgress.objects.select_related('user').order_by('-points')[:10]
    
    leaderboard_data = []
    
    for index, user_progress in enumerate(users_with_progress):
        # Get or create league
        user_league, created = UserLeague.objects.get_or_create(
            user=user_progress.user,
            defaults={'current_league': UserLeague.get_league_for_points(user_progress.points)}
        )
        
        # Get or create streak
        user_streak, _ = UserStreak.objects.get_or_create(
            user=user_progress.user,
            defaults={'current_streak': 0}
        )
        
        entry = {
            'id': str(user_progress.user.id),
            'rank': index + 1,
            'username': user_progress.user.name if hasattr(user_progress.user, 'name') else user_progress.user.first_name or user_progress.user.email,
            'avatar': user_progress.user_image_src,
            'points': user_progress.points,
            'streak': user_streak.current_streak,
            'league': user_league.current_league,
            'change': 'same',
            'changeAmount': None,
            'isCurrentUser': False
        }
        
        leaderboard_data.append(entry)
    
    # Get leagues info
    leagues_info = []
    for league_id, league_name in UserLeague.LEAGUE_CHOICES:
        league_data = UserLeague.get_league_info(league_id)
        participants_count = UserLeague.objects.filter(current_league=league_id).count()
        
        leagues_info.append({
            'id': league_id,
            'name': league_data['name'],
            'icon': league_data['icon'],
            'color': f'text-{league_id}-400' if league_id != 'bronze' else 'text-amber-600',
            'minPoints': league_data['min_points'],
            'maxPoints': league_data['max_points'],
            'participants': participants_count
        })
    
    # Get active competitions
    competitions = Competition.objects.filter(status='active').order_by('-start_date')
    competitions_data = []
    
    for competition in competitions:
        competitions_data.append({
            'id': str(competition.id),
            'title': competition.title,
            'description': competition.description,
            'type': competition.type,
            'startDate': competition.start_date.strftime('%Y-%m-%d'),
            'endDate': competition.end_date.strftime('%Y-%m-%d'),
            'participants': competition.participant_count,
            'currentPosition': None,
            'prize': competition.first_place_prize
        })
    
    return Response({
        'leaderboard': {
            'leaderboard': leaderboard_data,
            'currentUser': None
        },
        'leagues': leagues_info,
        'competitions': competitions_data,
        'stats': {
            'total_users': User.objects.count(),
            'users_with_progress': UserProgress.objects.count(),
            'active_competitions': Competition.objects.filter(status='active').count()
        }
    })


# ============================================================================
# ACHIEVEMENT VIEWS - Gamification and badge system
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_achievements(request):
    """
    GET /api/v1/practice/achievements/
    
    Get all achievements with user progress and unlock status.
    """
    user = request.user
    
    # Get all active achievements
    achievements = Achievement.objects.filter(is_active=True).order_by('order', 'category', 'rarity')
    
    # Build response data matching frontend interface
    achievements_data = []
    
    for achievement in achievements:
        # Get or create user achievement record
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={'current_progress': 0}
        )
        
        # Build progress data
        progress_data = None
        if not user_achievement.is_unlocked and achievement.requirement_target > 0:
            progress_data = {
                'current': user_achievement.current_progress,
                'target': achievement.requirement_target,
                'unit': achievement.requirement_unit
            }
        
        # Format unlock date
        unlocked_at_formatted = None
        if user_achievement.unlocked_at:
            from django.utils import timezone
            now = timezone.now()
            diff = now - user_achievement.unlocked_at
            
            if diff.days == 0:
                unlocked_at_formatted = "hoje"
            elif diff.days == 1:
                unlocked_at_formatted = "1 dia atrás"
            elif diff.days < 7:
                unlocked_at_formatted = f"{diff.days} dias atrás"
            else:
                unlocked_at_formatted = f"{diff.days // 7} semana{'s' if diff.days // 7 > 1 else ''} atrás"
        
        achievement_data = {
            'id': str(achievement.id),
            'title': achievement.title,
            'description': achievement.description,
            'icon': achievement.icon,
            'category': achievement.category,
            'rarity': achievement.rarity,
            'points': achievement.points,
            'isUnlocked': user_achievement.is_unlocked,
            'unlockedAt': unlocked_at_formatted,
            'progress': progress_data
        }
        
        achievements_data.append(achievement_data)
    
    return Response(achievements_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_achievement_stats(request):
    """
    GET /api/v1/practice/achievements/stats/
    
    Get achievement statistics for the current user.
    """
    user = request.user
    
    # Get all achievements and user achievements
    total_achievements = Achievement.objects.filter(is_active=True).count()
    user_achievements = UserAchievement.objects.filter(user=user)
    
    # Calculate stats
    unlocked_achievements = user_achievements.filter(is_unlocked=True)
    total_unlocked = unlocked_achievements.count()
    
    # Calculate total points from unlocked achievements
    total_points = 0
    for ua in unlocked_achievements:
        total_points += ua.achievement.points
    
    # Count rare achievements (rare, epic, legendary)
    rare_achievements = unlocked_achievements.filter(
        achievement__rarity__in=['rare', 'epic', 'legendary']
    ).count()
    
    # Count recent unlocks (last 7 days)
    from datetime import timedelta
    from django.utils import timezone
    
    recent_cutoff = timezone.now() - timedelta(days=7)
    recent_unlocked = unlocked_achievements.filter(
        unlocked_at__gte=recent_cutoff
    ).count()
    
    stats = {
        'totalUnlocked': total_unlocked,
        'totalAvailable': total_achievements,
        'totalPoints': total_points,
        'rareAchievements': rare_achievements,
        'recentUnlocked': recent_unlocked
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_achievement_categories(request):
    """
    GET /api/v1/practice/achievements/categories/
    
    Get achievement categories with counts.
    """
    categories = AchievementCategory.objects.filter(is_active=True).order_by('order')
    
    serializer = AchievementCategorySerializer(
        categories, 
        many=True, 
        context={'request': request}
    )
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_achievement_notifications(request):
    """
    GET /api/v1/practice/achievements/notifications/
    
    Get unread achievement notifications for the current user.
    """
    notifications = AchievementNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')
    
    serializer = AchievementNotificationSerializer(notifications, many=True)
    
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    POST /api/v1/practice/achievements/notifications/{notification_id}/read/
    
    Mark an achievement notification as read.
    """
    try:
        notification = AchievementNotification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        
        return Response({'message': 'Notification marked as read'})
        
    except AchievementNotification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_achievement_celebrated(request, achievement_id):
    """
    POST /api/v1/practice/achievements/{achievement_id}/celebrate/
    
    Mark an achievement as celebrated (popup shown).
    """
    try:
        notification = AchievementNotification.objects.get(
            achievement_id=achievement_id,
            user=request.user
        )
        notification.mark_as_celebrated()
        
        return Response({'message': 'Achievement marked as celebrated'})
        
    except AchievementNotification.DoesNotExist:
        return Response(
            {'error': 'Achievement notification not found'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


def check_achievement_progress(user, achievement_type, current_value):
    """
    Helper function to check and update achievement progress.
    
    Called from other parts of the system when user actions occur.
    """
    # Get achievements of the specified type
    achievements = Achievement.objects.filter(
        requirement_type=achievement_type,
        is_active=True
    )
    
    newly_unlocked = []
    
    for achievement in achievements:
        # Get or create user achievement
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={'current_progress': 0}
        )
        
        # Update progress if not already unlocked
        if not user_achievement.is_unlocked:
            was_unlocked = user_achievement.update_progress(current_value)
            
            if was_unlocked:
                # Create notification
                notification, created = AchievementNotification.objects.get_or_create(
                    user=user,
                    achievement=achievement
                )
                newly_unlocked.append(achievement)
    
    return newly_unlocked


@api_view(['GET'])
@permission_classes([IsAdminUser])  # SECURITY FIX: Admin only - was public, wrote to DB
def test_achievements_data(request):
    """
    Test endpoint to check achievements data (Admin only).
    WARNING: This endpoint creates UserAchievement records - use only for debugging.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get first user for testing
    user = User.objects.first()
    if not user:
        return Response({'error': 'No users found'})
    
    # Get all active achievements
    achievements = Achievement.objects.filter(is_active=True).order_by('order', 'category', 'rarity')
    
    # Build achievements data
    achievements_data = []
    
    for achievement in achievements:
        # Get or create user achievement record
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={'current_progress': 0}
        )
        
        # Build progress data
        progress_data = None
        if not user_achievement.is_unlocked and achievement.requirement_target > 0:
            progress_data = {
                'current': user_achievement.current_progress,
                'target': achievement.requirement_target,
                'unit': achievement.requirement_unit
            }
        
        # Format unlock date
        unlocked_at_formatted = None
        if user_achievement.unlocked_at:
            from django.utils import timezone
            now = timezone.now()
            diff = now - user_achievement.unlocked_at
            
            if diff.days == 0:
                unlocked_at_formatted = "hoje"
            elif diff.days == 1:
                unlocked_at_formatted = "1 dia atrás"
            elif diff.days < 7:
                unlocked_at_formatted = f"{diff.days} dias atrás"
            else:
                unlocked_at_formatted = f"{diff.days // 7} semana{'s' if diff.days // 7 > 1 else ''} atrás"
        
        achievement_data = {
            'id': str(achievement.id),
            'title': achievement.title,
            'description': achievement.description,
            'icon': achievement.icon,
            'category': achievement.category,
            'rarity': achievement.rarity,
            'points': achievement.points,
            'isUnlocked': user_achievement.is_unlocked,
            'unlockedAt': unlocked_at_formatted,
            'progress': progress_data
        }
        
        achievements_data.append(achievement_data)
    
    # Calculate stats
    total_achievements = Achievement.objects.filter(is_active=True).count()
    user_achievements = UserAchievement.objects.filter(user=user)
    unlocked_achievements = user_achievements.filter(is_unlocked=True)
    total_unlocked = unlocked_achievements.count()
    
    total_points = 0
    for ua in unlocked_achievements:
        total_points += ua.achievement.points
    
    rare_achievements = unlocked_achievements.filter(
        achievement__rarity__in=['rare', 'epic', 'legendary']
    ).count()
    
    from datetime import timedelta
    from django.utils import timezone
    recent_cutoff = timezone.now() - timedelta(days=7)
    recent_unlocked = unlocked_achievements.filter(
        unlocked_at__gte=recent_cutoff
    ).count()
    
    stats = {
        'totalUnlocked': total_unlocked,
        'totalAvailable': total_achievements,
        'totalPoints': total_points,
        'rareAchievements': rare_achievements,
        'recentUnlocked': recent_unlocked
    }
    
    return Response({
        'achievements': achievements_data,
        'stats': stats,
        'user': user.name if hasattr(user, 'name') else user.email,
        'total_created': len(achievements_data)
    })


# ============================================================================
# 🚀 VAPI AI CONVERSATION PRACTICE ENDPOINTS
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_vapi_conversation(request):
    """Start a new Vapi AI conversation session"""
    return Response({
        'message': 'Vapi conversation endpoints coming soon',
        'status': 'success'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_vapi_conversation(request, conversation_id):
    """End a Vapi AI conversation session"""
    return Response({
        'message': 'Vapi conversation end endpoint coming soon',
        'conversation_id': conversation_id,
        'status': 'success'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_feedback(request, conversation_id):
    """Get conversation feedback and analysis"""
    return Response({
        'message': 'Vapi conversation feedback endpoint coming soon',
        'conversation_id': conversation_id,
        'status': 'success'
    })

# ============================================================================
# TEST ENDPOINTS - Required by URLs
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_units_simple(request):
    """Test endpoint for units"""
    return Response({
        'message': 'Test units endpoint active',
        'status': 'success'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_lessons_simple(request):
    """Test endpoint for lessons"""
    return Response({
        'message': 'Test lessons endpoint active',
        'status': 'success'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_challenges_simple(request):
    """Test endpoint for challenges"""
    return Response({
        'message': 'Test challenges endpoint active',
        'status': 'success'
    })


# ============================================================================
# PLACEHOLDER VIEWS - Required by URLs but functionality moved to Vapi
# ============================================================================

class AITranslationValidationView(APIView):
    """Placeholder for AI translation validation - moved to Vapi"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({
            'message': 'AI translation validation moved to Vapi integration',
            'status': 'placeholder'
        })

class AIPronunciationAnalysisView(APIView):
    """Placeholder for AI pronunciation analysis - moved to Vapi"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({
            'message': 'AI pronunciation analysis moved to Vapi integration',
            'status': 'placeholder'
        })
