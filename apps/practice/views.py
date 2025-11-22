"""
Practice Lab Views - REST API endpoints

This module provides DRF views for the Practice Lab system,
implementing all necessary endpoints for the Duolingo-style learning experience.
"""

from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
import time
from rest_framework import generics, status as status_module
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

# Import course management views
from .views_course_management import PracticeCourseManagementView

# Import Vapi views
from .views.vapi_views import VapiSessionView, vapi_templates, vapi_simulate, vapi_webhook, vapi_assistant_manager

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

from apps.courses.models import Course
from .models import (
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
    AchievementNotification,
    # AI Speaking Practice Models
    SpeakingExercise,
    SpeakingSession,
    SpeakingTurn,
    SpeakingProgress,
    # AI Listening Practice Models
    ListeningExercise,
    ListeningSession,
    ListeningAttempt,
    ListeningProgress,
    AudioSegment
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
    # AI Speaking Practice Serializers
    SpeakingExerciseSerializer,
    SpeakingExerciseListSerializer,
    SpeakingSessionSerializer,
    SpeakingSessionCreateSerializer,
    SpeakingTurnSerializer,
    SpeakingTurnCreateSerializer,
    SpeakingProgressSerializer,
    SpeakingAnalysisSerializer,
    SpeakingStatsSerializer,
    QuickSpeakingFeedbackSerializer,
    # AI Listening Practice Serializers
    ListeningExerciseSerializer,
    ListeningExerciseListSerializer,
    ListeningSessionSerializer,
    ListeningSessionCreateSerializer,
    ListeningAttemptSerializer,
    ListeningAttemptCreateSerializer,
    ListeningProgressSerializer,
    ListeningAnalysisSerializer,
    ListeningStatsSerializer,
    AudioSegmentSerializer,
    QuickListeningFeedbackSerializer
)


class CoursesListView(generics.ListAPIView):
    """
    GET /api/v1/practice/courses/
    
    List all available courses for practice selection and teacher management.
    Maps to getCourses query from client project.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        DEFENSIVE PROGRAMMING: Get courses with proper filtering and error handling
        """
        try:
            # Validate user authentication
            user = self.request.user
            if not user or not user.is_authenticated:
                logger.warning("🚨 SECURITY - Unauthenticated access attempt to courses")
                return Course.objects.none()
            
            # Get query parameter to include drafts with validation
            query_params = getattr(self.request, 'query_params', self.request.GET)
            include_drafts_param = query_params.get('include_drafts', 'false')
            
            # Defensive parsing of boolean parameter
            include_drafts = False
            if isinstance(include_drafts_param, str):
                include_drafts = include_drafts_param.lower() in ['true', '1', 'yes']
            
            # Log filtering info for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔍 COURSE FILTER - User: {getattr(user, 'id', 'N/A')} ({getattr(user, 'email', 'N/A')}), Role: {getattr(user, 'role', 'No role')}, Include drafts: {include_drafts}")
            
            # Validate user role with defensive checks
            user_role = getattr(user, 'role', None)
            if not user_role:
                logger.warning(f"⚠️ USER ROLE MISSING - User {getattr(user, 'id', 'N/A')} has no role assigned")
                # Default to student behavior for safety
                user_role = 'student'
            
            if user_role == 'teacher':
                try:
                    # For teachers: show ONLY their own practice lab courses
                    base_filter = {
                        'course_type': 'practice',
                        'teacher': user
                    }
                    
                    if include_drafts:
                        # Include all statuses for teacher's own courses
                        queryset = Course.objects.filter(**base_filter).distinct().order_by('-created_at')
                        logger.info(f"📚 TEACHER WITH DRAFTS - Found {queryset.count()} courses for teacher {getattr(user, 'id', 'N/A')}")
                    else:
                        # Only published courses from this teacher
                        base_filter['status'] = 'Published'
                        queryset = Course.objects.filter(**base_filter).distinct().order_by('-created_at')
                        logger.info(f"📚 TEACHER PUBLISHED ONLY - Found {queryset.count()} courses for teacher {getattr(user, 'id', 'N/A')}")
                    
                    return queryset
                    
                except Exception as e:
                    logger.error(f"❌ ERROR filtering teacher courses for user {getattr(user, 'id', 'N/A')}: {str(e)}")
                    return Course.objects.none()
            
            else:
                try:
                    # For students: only published practice lab courses (all teachers)
                    queryset = Course.objects.filter(
                        course_type='practice', 
                        status='Published'
                    ).distinct().order_by('-created_at')
                    logger.info(f"🎓 STUDENT - Found {queryset.count()} published courses from all teachers")
                    return queryset
                    
                except Exception as e:
                    logger.error(f"❌ ERROR filtering student courses: {str(e)}")
                    return Course.objects.none()
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"🚨 CRITICAL ERROR in get_queryset: {str(e)}")
            # Return empty queryset on any critical error
            return Course.objects.none()
    
    def list(self, request, *args, **kwargs):
        courses = self.get_queryset()
        data = []
        
        # Check if statistics are requested (for teacher management)
        include_stats = request.query_params.get('include_stats', 'false').lower() in ['true', '1', 'yes']
        
        for course in courses:
            course_data = {
                'id': str(course.id),
                'title': course.title,
                'description': course.description,
                'image': course.image,
                'category': course.category,
                'level': course.level,
                'status': course.status,  # Include status for teacher management
                'template': course.template,  # Include template for card styling
                'created_at': course.created_at.isoformat() if course.created_at else None,
                'updated_at': course.updated_at.isoformat() if course.updated_at else None,
            }
            
            # Add statistics if requested (optimized for teacher dashboard)
            if include_stats:
                try:
                    # Get units count for this course
                    units_count = course.practice_units.count()
                    
                    # Get lessons count for this course  
                    lessons_count = PracticeLesson.objects.filter(
                        unit__course=course
                    ).count()
                    
                    # Get challenges count for this course
                    challenges_count = PracticeChallenge.objects.filter(
                        lesson__unit__course=course
                    ).count()
                    
                    # Debug logging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"📊 STATS DEBUG - Course {course.title} ({course.id}): units={units_count}, lessons={lessons_count}, challenges={challenges_count}")
                    
                    course_data.update({
                        'units_count': units_count,
                        'lessons_count': lessons_count,
                        'challenges_count': challenges_count,
                        'totalUnits': units_count,  # For compatibility with existing frontend
                        'total_lessons': lessons_count,  # For compatibility with existing frontend
                        'total_challenges': challenges_count,  # For compatibility with existing frontend
                    })
                    
                except Exception as e:
                    # If statistics calculation fails, log error but don't break the response
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
                    })
            
            data.append(course_data)
        
        return Response(data)


class CreateCourseView(APIView):
    """
    POST /api/v1/practice/courses/create/
    
    Create a new course for practice laboratory.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        DEFENSIVE PROGRAMMING: Create a new course with comprehensive validation
        """
        try:
            # Validate user authentication
            if not request.user or not request.user.is_authenticated:
                logger.warning("🚨 SECURITY - Unauthenticated course creation attempt")
                return Response(
                    {'error': 'Authentication required'}, 
                    status=status_module.HTTP_401_UNAUTHORIZED
                )
            
            # Validate user role
            user_role = getattr(request.user, 'role', None)
            if user_role != 'teacher':
                logger.warning(f"🚨 SECURITY - Non-teacher course creation attempt by user {getattr(request.user, 'id', 'N/A')}")
                return Response(
                    {'error': 'Only teachers can create courses'}, 
                    status=status_module.HTTP_403_FORBIDDEN
                )
            
            # Log request data for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🚀 CREATING PRACTICE COURSE - Full request data: {request.data}")
            logger.info(f"👤 Authenticated user: {request.user}")
            logger.info(f"📦 Request data keys: {list(request.data.keys())}")
            
            # DEFENSIVE VALIDATION: Extract and validate core course data
            title = request.data.get('title', '').strip()
            if not title or len(title) < 3:
                return Response(
                    {'error': 'Title is required and must be at least 3 characters'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            if len(title) > 200:
                return Response(
                    {'error': 'Title must be less than 200 characters'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            description = request.data.get('description', '').strip()
            if not description or len(description) < 10:
                return Response(
                    {'error': 'Description is required and must be at least 10 characters'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            # Validate category
            category = request.data.get('category', '').strip()
            valid_categories = ['General', 'Oil & Gas', 'Banking', 'Technology', 'Executive', 'AI Enhanced']
            if not category or category not in valid_categories:
                return Response(
                    {'error': f'Category must be one of: {", ".join(valid_categories)}'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            # Validate level
            level = request.data.get('level', 'Beginner').strip()
            valid_levels = ['Beginner', 'Intermediate', 'Advanced']
            if level not in valid_levels:
                level = 'Beginner'  # Default fallback
                
            # Validate status
            status = request.data.get('status', 'Draft').strip()
            valid_statuses = ['Draft', 'Published', 'Archived']
            if status not in valid_statuses:
                status = 'Draft'  # Default fallback
                
            # Validate template
            template = request.data.get('template', 'general').strip()
            valid_templates = ['general', 'oil-gas', 'banking', 'technology', 'executive', 'ai-personal']
            if template not in valid_templates:
                template = 'general'  # Default fallback
            
            # Extract additional teacher and metadata fields sent by frontend
            teacher_id = request.data.get('teacher_id')
            teacher_email = request.data.get('teacher_email')
            teacher_name = request.data.get('teacher_name')
            created_by = request.data.get('created_by')
            language = request.data.get('language', 'pt-BR')
            difficulty_level = request.data.get('difficulty_level')
            
            # Extract learning configuration fields
            learning_objectives = request.data.get('learningObjectives', [])
            target_audience = request.data.get('targetAudience', '')
            hearts = request.data.get('hearts', 5)
            points_per_challenge = request.data.get('pointsPerChallenge', 10)
            passing_score = request.data.get('passingScore', 70)
            
            logger.info(f"📝 Extracted frontend data:")
            logger.info(f"   Core: title={title}, category={category}, level={level}")
            logger.info(f"   Teacher: id={teacher_id}, email={teacher_email}, name={teacher_name}")
            logger.info(f"   Meta: created_by={created_by}, language={language}")
            logger.info(f"   Learning: objectives={len(learning_objectives)}, audience={target_audience}")
            
            if not title or not category:
                return Response(
                    {'error': 'Title and category are required'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            # Create the course with all available data
            course = Course.objects.create(
                title=title,
                description=description,
                category=category,
                level=level,
                status=status,
                template=template,
                # Required fields - use authenticated user as teacher
                teacher=request.user,
                teacherName=teacher_name or f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
                course_type='practice',  # Set as practice lab course
            )
            
            logger.info(f"✅ Course created successfully with ID: {course.id}")
            
            # Prepare comprehensive response including all fields the frontend expects
            response_data = {
                # Core course fields
                'id': str(course.id),
                'courseId': str(course.id),  # Add courseId alias like video courses
                'title': course.title,
                'description': course.description,
                'category': course.category,
                'level': course.level,
                'status': course.status,
                'template': course.template,
                'image': course.image or '',
                
                # Teacher information - consistent with video courses structure
                'teacher': str(course.teacher.id),  # Add this field like video courses
                'teacherId': str(course.teacher.id),  # Add this field like video courses  
                'teacherName': course.teacherName,
                'teacher_id': teacher_id or str(course.teacher.id),
                'teacher_email': teacher_email or course.teacher.email,
                'teacher_name': teacher_name or course.teacherName,
                
                # Course metadata
                'course_type': course.course_type,
                'created_by': created_by or str(request.user.id),
                'language': language or 'pt-BR',
                'difficulty_level': difficulty_level or level,
                
                # Learning configuration
                'learningObjectives': learning_objectives,
                'targetAudience': target_audience,
                'hearts': hearts,
                'pointsPerChallenge': points_per_challenge,
                'passingScore': passing_score,
                
                # Timestamps
                'created_at': course.created_at.isoformat() if course.created_at else None,
                'updated_at': course.updated_at.isoformat() if course.updated_at else None,
                
                # Additional metadata from request
                **{k: v for k, v in request.data.items() 
                   if k.startswith('test_') or k in ['custom_metadata']},
            }
            
            logger.info(f"📤 RESPONSE DATA - Keys being returned: {list(response_data.keys())}")
            logger.info(f"🎯 Critical fields in response:")
            logger.info(f"   teacher_id: {response_data.get('teacher_id')}")
            logger.info(f"   teacher_email: {response_data.get('teacher_email')}")
            logger.info(f"   teacher_name: {response_data.get('teacher_name')}")
            logger.info(f"   course_type: {response_data.get('course_type')}")
            logger.info(f"   created_by: {response_data.get('created_by')}")
            
            return Response(response_data, status=status_module.HTTP_201_CREATED)
            
        except Exception as e:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating course: {str(e)}", exc_info=True)
            
            return Response(
                {'error': f'Failed to create course: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CourseUnitsView(generics.ListAPIView):
    """
    GET /api/v1/practice/courses/{course_id}/units/
    
    List all practice units for a specific course.
    Maps to getCourse query from client project.
    """
    serializer_class = PracticeUnitSerializer
    permission_classes = [IsAuthenticated]
    
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
    """
    serializer_class = LessonDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'lesson_id'
    
    # @subscription_required('lesson')  # Commented out - will implement later
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
        """Get user's current progress"""
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={
                'hearts': 5,
                'points': 0,
                'active_course': None
            }
        )
        serializer = UserProgressSerializer(user_progress)
        return Response(serializer.data)
    
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
    """
    permission_classes = [IsAuthenticated]
    
    # @hearts_required()  # Commented out - will implement later
    def post(self, request):
        """Complete a challenge and update user progress"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"ChallengeProgress POST request: {request.data}")
        
        challenge_id = request.data.get('challenge')
        selected_option_id = request.data.get('selected_option')
        
        logger.info(f"Challenge ID: {challenge_id}, Selected Option: {selected_option_id}")
        
        if not challenge_id or not selected_option_id:
            return Response(
                {'error': 'challenge and selected_option are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            challenge = PracticeChallenge.objects.get(id=challenge_id)
            logger.info(f"Found challenge: {challenge}")
            
            selected_option = ChallengeOption.objects.get(id=selected_option_id, challenge=challenge)
            logger.info(f"Found option: {selected_option}")
        except PracticeChallenge.DoesNotExist:
            logger.error(f"Challenge not found: {challenge_id}")
            return Response(
                {'error': 'Invalid challenge'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        except ChallengeOption.DoesNotExist:
            logger.error(f"Option not found: {selected_option_id} for challenge: {challenge_id}")
            return Response(
                {'error': 'Invalid option'}, 
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
        
        # Check hearts for new challenges
        if user_progress.hearts == 0 and not is_practice:
            logger.info("User has no hearts and this is not practice mode")
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Check if the selected option is correct
        if selected_option.is_correct:
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
            if not is_practice and user_progress.hearts > 0:
                user_progress.reduce_hearts()
            
            return Response({
                'success': True,
                'correct': False,
                'user_progress': {
                    'hearts': user_progress.hearts,
                    'points': user_progress.points
                }
            }, status=status_module.HTTP_200_OK)


class ReduceHeartsView(APIView):
    """
    POST /api/v1/practice/reduce-hearts/
    
    Reduce user hearts when they get an answer wrong.
    Maps to reduceHearts action from client project.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Reduce user hearts by 1"""
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
    
    Refill user hearts (for premium users or heart purchases).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Refill hearts to maximum (5)"""
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        user_progress.hearts = 5
        user_progress.save()
        
        return Response({
            'hearts': user_progress.hearts,
            'points': user_progress.points
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
        
        # Check hearts for new challenges
        if user_progress.hearts == 0 and not is_practice:
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
        
        # Normalize answers for comparison
        user_answer_normalized = user_answer.lower().strip()
        correct_answer_normalized = correct_option.text.lower().strip()
        
        # Check if answers match (case-insensitive, whitespace trimmed)
        is_correct = user_answer_normalized == correct_answer_normalized
        
        # Additional flexible matching for fill-blank
        if not is_correct and challenge.type == 'FILL_BLANK':
            # Remove extra spaces and check again
            user_words = user_answer_normalized.split()
            correct_words = correct_answer_normalized.split()
            is_correct = user_words == correct_words
        
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
            if not is_practice and user_progress.hearts > 0:
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
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, challenge_id):
        """Generate presigned URL for audio upload to S3"""
        import boto3
        import uuid
        from django.conf import settings
        
        try:
            # Validate request data
            lesson_id = request.data.get('lessonId')
            file_name = request.data.get('fileName')
            file_type = request.data.get('fileType')
            
            if not all([lesson_id, file_name, file_type]):
                return Response(
                    {'error': 'lessonId, fileName, and fileType are required'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            # Verify challenge exists
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'}, 
                    status=status_module.HTTP_404_NOT_FOUND
                )
            
            # Generate unique file name to avoid conflicts
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'mp3'
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
                'message': 'Audio upload URL generated successfully',
                'data': {
                    'uploadUrl': presigned_url,
                    'audioUrl': audio_url,
                    'fileName': unique_filename
                }
            }, status=status_module.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate upload URL: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetImageUploadUrlView(APIView):
    """
    POST /api/v1/practice/challenges/{challenge_id}/get-image-upload-url/
    
    Get presigned S3 URL for image upload in listening challenges.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, challenge_id):
        """Generate presigned URL for image upload to S3"""
        import boto3
        import uuid
        from django.conf import settings
        
        try:
            # Validate request data
            lesson_id = request.data.get('lessonId')
            file_name = request.data.get('fileName')
            file_type = request.data.get('fileType')
            
            if not all([lesson_id, file_name, file_type]):
                return Response(
                    {'error': 'lessonId, fileName, and fileType are required'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            # Verify challenge exists
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'}, 
                    status=status_module.HTTP_404_NOT_FOUND
                )
            
            # Generate unique file name to avoid conflicts
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'jpg'
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
                'message': 'Image upload URL generated successfully',
                'data': {
                    'uploadUrl': presigned_url,
                    'imageUrl': image_url,
                    'fileName': unique_filename
                }
            }, status=status_module.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate upload URL: {str(e)}'}, 
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
    """
    permission_classes = [IsAuthenticated]  # Should be admin only in production
    
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
@permission_classes([])  # No authentication required for testing
def test_leaderboard_data(request):
    """
    Test endpoint to check leaderboard data without authentication
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
@permission_classes([])  # No authentication required for testing
def test_achievements_data(request):
    """
    Test endpoint to check achievements data without authentication
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
# AI SPEAKING PRACTICE VIEWS - AI-powered conversation and pronunciation
# ============================================================================

class SpeakingExerciseListView(generics.ListAPIView):
    """
    GET /api/v1/practice/speaking/exercises/
    
    List available speaking exercises with filtering and recommendations.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingExerciseListSerializer
    
    def get_queryset(self):
        """Get speaking exercises with optional filtering"""
        queryset = SpeakingExercise.objects.filter(is_active=True)
        
        # Filter by exercise type
        exercise_type = self.request.query_params.get('type', None)
        if exercise_type:
            queryset = queryset.filter(exercise_type=exercise_type)
        
        # Filter by difficulty
        difficulty = self.request.query_params.get('difficulty', None)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Filter by course
        course_id = self.request.query_params.get('course', None)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        return queryset.order_by('difficulty', 'created_at')


class SpeakingExerciseDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/practice/speaking/exercises/{id}/
    
    Get detailed information about a specific speaking exercise.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingExerciseSerializer
    queryset = SpeakingExercise.objects.filter(is_active=True)


class SpeakingSessionCreateView(generics.CreateAPIView):
    """
    POST /api/v1/practice/speaking/sessions/
    
    Start a new speaking practice session.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingSessionCreateSerializer
    
    def post(self, request, *args, **kwargs):
        # TODO: Re-add subscription check for speaking practice
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Create session and initialize AI conversation if needed"""
        session = serializer.save(user=self.request.user)
        
        # If this is a conversation exercise, initialize AI
        if session.exercise.exercise_type == 'CONVERSATION':
            from .services.conversation_engine import AIConversationEngine
            
            engine = AIConversationEngine()
            # Initialize conversation asynchronously
            # In a real implementation, this would be handled by Celery or similar
        
        return session
    
    def create(self, request, *args, **kwargs):
        """Override to return complete session data"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = self.perform_create(serializer)
        
        # Return complete session data using detailed serializer
        from apps.practice.serializers import SpeakingSessionSerializer
        response_serializer = SpeakingSessionSerializer(session)
        headers = self.get_success_headers(response_serializer.data)
        
        return Response(response_serializer.data, status=status_module.HTTP_201_CREATED, headers=headers)


class SpeakingSessionDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/practice/speaking/sessions/{id}/
    
    Get detailed information about a speaking session with all turns.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingSessionSerializer
    
    def get_queryset(self):
        return SpeakingSession.objects.filter(user=self.request.user)


class SpeakingSessionListView(generics.ListAPIView):
    """
    GET /api/v1/practice/speaking/sessions/
    
    List user's speaking sessions with pagination and filtering.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingSessionSerializer
    
    def get_queryset(self):
        queryset = SpeakingSession.objects.filter(user=self.request.user)
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by exercise type
        exercise_type = self.request.query_params.get('exercise_type', None)
        if exercise_type:
            queryset = queryset.filter(exercise__exercise_type=exercise_type)
        
        return queryset.order_by('-started_at')


class SpeakingTurnCreateView(generics.CreateAPIView):
    """
    POST /api/v1/practice/speaking/turns/
    
    Create a new speaking turn (user speech input).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakingTurnCreateSerializer
    
    def create(self, request, *args, **kwargs):
        """Create turn and process audio if provided"""
        response = super().create(request, *args, **kwargs)
        
        # If audio was provided, process it asynchronously
        if 'audio_file' in request.FILES:
            # In production, this would trigger async processing
            # For now, return success
            pass
        
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_speech(request):
    """
    POST /api/v1/practice/speaking/analyze/
    
    Analyze uploaded speech audio using AI services.
    """
    # Debug logging
    print(f"🎙️ ANALYZE_SPEECH DEBUG:")
    print(f"📁 FILES: {list(request.FILES.keys())}")
    print(f"📄 DATA: {dict(request.data)}")
    print(f"👤 USER: {request.user}")
    
    audio_file = request.FILES.get('audio_file')
    target_text = request.data.get('target_text', '')
    
    print(f"🎵 audio_file: {audio_file}")
    print(f"🎯 target_text: '{target_text}'")
    
    if not audio_file:
        print(f"❌ No audio file provided!")
        return Response(
            {'error': 'Audio file is required'}, 
            status=status_module.HTTP_400_BAD_REQUEST
        )
    
    try:
        from .services.speech_analyzer import SpeechAnalyzer
        import asyncio
        
        analyzer = SpeechAnalyzer()
        
        # Run analysis (in production, this would be async/Celery)
        # For demo, we'll create a mock result
        mock_result = {
            'overall_score': 85.0,
            'pronunciation_score': 82.0,
            'fluency_score': 88.0,
            'accuracy_score': 86.0,
            'confidence_score': 84.0,
            'transcribed_text': target_text or "Sample transcription",
            'target_text': target_text,
            'word_analysis': [],
            'phoneme_analysis': [],
            'grammar_errors': [],
            'feedback_text': "Great job! Keep practicing to improve further.",
            'improvement_suggestions': [
                "Focus on pronunciation of specific sounds",
                "Try speaking more slowly for clarity"
            ],
            'next_exercises': [
                "Practice word pronunciation",
                "Try conversation practice"
            ]
        }
        
        serializer = SpeakingAnalysisSerializer(data=mock_result)
        if serializer.is_valid():
            print(f"✅ Serializer valid, returning response")
            return Response(serializer.data)
        else:
            print(f"❌ Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status_module.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        import traceback
        print(f"💥 EXCEPTION in analyze_speech: {str(e)}")
        print(f"📊 TRACEBACK: {traceback.format_exc()}")
        return Response(
            {'error': f'Analysis failed: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ========================================================================
# AI CONVERSATION ENDPOINTS - Real-time conversation practice with AI
# ========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_ai_conversation(request):
    """
    POST /api/v1/practice/speaking/conversation/start/
    
    Inicia nova conversação com IA
    
    Body: {
        "level": "BEGINNER|INTERMEDIATE|ADVANCED",
        "topic": "introductions|travel|work|etc",
        "user_profile": {...} (opcional)
    }
    """
    try:
        level = request.data.get('level', '').upper()
        topic = request.data.get('topic', '')
        user_profile = request.data.get('user_profile', {})
        
        if not level or not topic:
            return Response(
                {'error': 'Level and topic are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Importar serviço de IA
        from .services.conversation_ai import ConversationAIService
        
        ai_service = ConversationAIService()
        
        # Verificar se nível é válido
        if level not in ai_service.LEVELS:
            return Response(
                {
                    'error': f'Invalid level: {level}',
                    'available_levels': list(ai_service.LEVELS.keys())
                },
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se tópico é válido para o nível
        available_topics = ai_service.get_available_topics(level)
        if topic not in available_topics:
            return Response(
                {
                    'error': f'Invalid topic for level {level}',
                    'available_topics': available_topics
                },
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Iniciar conversa
        import asyncio
        ai_response = asyncio.run(ai_service.start_conversation(level, topic, user_profile))
        
        # Criar sessão (opcional - pode ser apenas em memória)
        level_info = ai_service.get_level_info(level)
        
        response_data = {
            'session_id': f'conv_{level.lower()}_{topic}_{request.user.id}_{int(time.time())}',
            'ai_message': {
                'content': ai_response.text,
                'audio_url': ai_response.audio_url,
                'metadata': ai_response.conversation_metadata
            },
            'session_config': {
                'level': level,
                'topic': topic,
                'target_turns': level_info['target_turns'] if level_info else 10,
                'conversation_style': level_info['conversation_style'] if level_info else 'natural'
            }
        }
        
        return Response(response_data, status=status_module.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"💥 EXCEPTION in start_ai_conversation: {str(e)}")
        print(f"📊 TRACEBACK: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to start conversation: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def continue_ai_conversation(request):
    """
    POST /api/v1/practice/speaking/conversation/continue/
    
    Continua conversação existente
    
    Body: {
        "session_id": "...",
        "level": "BEGINNER|INTERMEDIATE|ADVANCED", 
        "topic": "...",
        "conversation_history": [...],
        "user_input": "user speech transcription",
        "user_audio_analysis": {
            "pronunciation_score": 85,
            "fluency_score": 78,
            ...
        }
    }
    """
    try:
        session_id = request.data.get('session_id', '')
        level = request.data.get('level', '').upper()
        topic = request.data.get('topic', '')
        conversation_history = request.data.get('conversation_history', [])
        user_input = request.data.get('user_input', '')
        user_audio_analysis = request.data.get('user_audio_analysis', {})
        
        if not all([session_id, level, topic, user_input]):
            return Response(
                {'error': 'session_id, level, topic, and user_input are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Importar e configurar serviço
        from .services.conversation_ai import ConversationAIService, ConversationContext
        
        ai_service = ConversationAIService()
        
        # Verificar nível válido
        if level not in ai_service.LEVELS:
            return Response(
                {'error': f'Invalid level: {level}'},
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Reconstruir contexto da conversa
        level_obj = ai_service.LEVELS[level]
        
        context = ConversationContext(
            level=level_obj,
            topic=topic,
            turns=conversation_history,
            user_language_level=level.lower(),
            conversation_goals=['practice_speaking', 'improve_fluency']
        )
        
        # Continuar conversa
        import asyncio
        ai_response = asyncio.run(ai_service.continue_conversation(
            context, 
            user_input, 
            user_audio_analysis
        ))
        
        response_data = {
            'session_id': session_id,
            'ai_message': {
                'content': ai_response.text,
                'audio_url': ai_response.audio_url,
                'metadata': ai_response.conversation_metadata
            },
            'conversation_progress': {
                'current_turn': len(context.turns),
                'target_turns': context.level.target_turns,
                'progress_percentage': min(100, (len(context.turns) / context.level.target_turns) * 100)
            }
        }
        
        return Response(response_data, status=status_module.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"💥 EXCEPTION in continue_ai_conversation: {str(e)}")
        print(f"📊 TRACEBACK: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to continue conversation: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_ai_conversation(request):
    """
    POST /api/v1/practice/speaking/conversation/analyze/
    
    Analisa conversa completa e gera feedback
    
    Body: {
        "session_id": "...",
        "level": "BEGINNER|INTERMEDIATE|ADVANCED",
        "topic": "...",
        "conversation_history": [
            {
                "speaker": "user|ai",
                "content": "...",
                "analysis": {...} (para turnos do usuário)
            }
        ]
    }
    """
    try:
        session_id = request.data.get('session_id', '')
        level = request.data.get('level', '').upper()
        topic = request.data.get('topic', '')
        conversation_history = request.data.get('conversation_history', [])
        
        if not all([session_id, level, topic, conversation_history]):
            return Response(
                {'error': 'session_id, level, topic, and conversation_history are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Importar e configurar serviço
        from .services.conversation_ai import ConversationAIService, ConversationContext
        
        ai_service = ConversationAIService()
        
        # Verificar nível válido
        if level not in ai_service.LEVELS:
            return Response(
                {'error': f'Invalid level: {level}'},
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Criar contexto para análise
        level_obj = ai_service.LEVELS[level]
        
        context = ConversationContext(
            level=level_obj,
            topic=topic,
            turns=conversation_history,
            user_language_level=level.lower(),
            conversation_goals=['practice_speaking']
        )
        
        # Analisar conversa completa
        import asyncio
        analysis_result = asyncio.run(ai_service.analyze_conversation_completion(context))
        
        response_data = {
            'session_id': session_id,
            'analysis': analysis_result,
            'session_summary': {
                'level': level,
                'topic': topic,
                'total_turns': len([t for t in conversation_history if t['speaker'] == 'user']),
                'target_turns': level_obj.target_turns,
                'completion_rate': min(100, (len(conversation_history) / (level_obj.target_turns * 2)) * 100)
            }
        }
        
        return Response(response_data, status=status_module.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"💥 EXCEPTION in analyze_ai_conversation: {str(e)}")
        print(f"📊 TRACEBACK: {traceback.format_exc()}")
        return Response(
            {'error': f'Failed to analyze conversation: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def speaking_progress_stats(request):
    """
    GET /api/v1/practice/speaking/progress/
    
    Get user's speaking progress and statistics.
    """
    user = request.user
    
    try:
        progress = SpeakingProgress.objects.get(user=user)
        serializer = SpeakingProgressSerializer(progress)
        return Response(serializer.data)
        
    except SpeakingProgress.DoesNotExist:
        # Create initial progress record
        progress = SpeakingProgress.objects.create(user=user)
        serializer = SpeakingProgressSerializer(progress)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def speaking_dashboard_stats(request):
    """
    GET /api/v1/practice/speaking/dashboard/
    
    Get speaking statistics for dashboard display.
    """
    user = request.user
    
    # Get or create progress
    progress, _ = SpeakingProgress.objects.get_or_create(user=user)
    
    # Calculate this week's activity
    from datetime import timedelta
    from django.utils import timezone
    
    week_start = timezone.now() - timedelta(days=7)
    sessions_this_week = SpeakingSession.objects.filter(
        user=user,
        started_at__gte=week_start
    ).count()
    
    # Calculate minutes this week
    sessions_this_week_queryset = SpeakingSession.objects.filter(
        user=user,
        started_at__gte=week_start,
        total_duration__isnull=False
    )
    
    total_seconds = sum(
        session.total_duration.total_seconds() 
        for session in sessions_this_week_queryset
    )
    minutes_this_week = total_seconds / 60
    
    # Determine improvement trend (simplified)
    improvement_trend = 'stable'
    if progress.total_sessions > 5:
        recent_avg = progress.overall_average
        if recent_avg > 80:
            improvement_trend = 'up'
        elif recent_avg < 60:
            improvement_trend = 'down'
    
    # Get favorite exercise type
    favorite_type = SpeakingSession.objects.filter(
        user=user
    ).values('exercise__exercise_type').annotate(
        count=models.Count('id')
    ).order_by('-count').first()
    
    favorite_exercise_type = 'CONVERSATION'  # Default
    if favorite_type:
        favorite_exercise_type = favorite_type['exercise__exercise_type']
    
    stats = {
        'total_sessions': progress.total_sessions,
        'total_hours': progress.total_hours_practiced,
        'average_score': progress.overall_average,
        'current_streak': progress.current_streak,
        'longest_streak': progress.longest_streak,
        'sessions_this_week': sessions_this_week,
        'minutes_this_week': minutes_this_week,
        'improvement_trend': improvement_trend,
        'favorite_exercise_type': favorite_exercise_type,
        'weak_areas': progress.weak_phonemes[:3],  # Top 3 weak areas
        'strong_areas': progress.strong_areas[:3]   # Top 3 strong areas
    }
    
    serializer = SpeakingStatsSerializer(data=stats)
    if serializer.is_valid():
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status_module.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@speaking_required(5)  # 5 minutes consumed when completing
def complete_speaking_session(request, session_id):
    """
    POST /api/v1/practice/speaking/sessions/{session_id}/complete/
    
    Mark a speaking session as completed and update progress.
    """
    try:
        session = SpeakingSession.objects.get(
            id=session_id,
            user=request.user
        )
        
        if session.status != 'ACTIVE':
            return Response(
                {'error': 'Session is not active'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Mark as completed
        from django.utils import timezone
        session.status = 'COMPLETED'
        session.completed_at = timezone.now()
        
        # Calculate final scores (simplified)
        if session.turns_count > 0:
            turns = SpeakingTurn.objects.filter(session=session, turn_type='USER_SPEECH')
            if turns.exists():
                session.pronunciation_score = turns.aggregate(
                    avg=models.Avg('pronunciation_score')
                )['avg'] or 0
                session.fluency_score = turns.aggregate(
                    avg=models.Avg('fluency_score')
                )['avg'] or 0
                session.accuracy_score = turns.aggregate(
                    avg=models.Avg('accuracy_score')
                )['avg'] or 0
                
                # Calculate overall score
                session.overall_score = (
                    session.pronunciation_score * 0.4 +
                    session.fluency_score * 0.3 +
                    session.accuracy_score * 0.3
                )
        
        # Calculate duration
        if session.started_at:
            session.total_duration = timezone.now() - session.started_at
        
        # Determine if passed
        session.is_passed = session.overall_score >= session.exercise.minimum_score
        
        # Calculate points earned
        base_points = session.exercise.points_reward
        if session.is_passed:
            if session.overall_score >= 90:
                session.points_earned = int(base_points * 1.5)
            elif session.overall_score >= 80:
                session.points_earned = int(base_points * 1.2)
            else:
                session.points_earned = base_points
        else:
            session.points_earned = int(base_points * 0.5)  # Partial credit
        
        session.save()
        
        # Update user progress
        progress, _ = SpeakingProgress.objects.get_or_create(user=request.user)
        progress.total_sessions += 1
        if session.total_duration:
            progress.total_hours_practiced += session.total_duration.total_seconds() / 3600
        
        # Update averages
        if session.pronunciation_score:
            if progress.average_pronunciation == 0:
                progress.average_pronunciation = session.pronunciation_score
            else:
                alpha = 0.2
                progress.average_pronunciation = (
                    alpha * session.pronunciation_score + 
                    (1 - alpha) * progress.average_pronunciation
                )
        
        if session.fluency_score:
            if progress.average_fluency == 0:
                progress.average_fluency = session.fluency_score
            else:
                alpha = 0.2
                progress.average_fluency = (
                    alpha * session.fluency_score + 
                    (1 - alpha) * progress.average_fluency
                )
        
        # Update overall average
        progress.overall_average = (
            progress.average_pronunciation * 0.4 +
            progress.average_fluency * 0.3 +
            progress.average_accuracy * 0.3
        )
        
        progress.last_session_date = timezone.now()
        progress.save()
        
        # Update user points
        try:
            user_progress = UserProgress.objects.get(user=request.user)
            user_progress.points += session.points_earned
            user_progress.save()
        except UserProgress.DoesNotExist:
            pass
        
        return Response({
            'message': 'Session completed successfully',
            'session': SpeakingSessionSerializer(session).data,
            'points_earned': session.points_earned,
            'is_passed': session.is_passed
        })
        
    except SpeakingSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_tts_audio(request):
    """
    POST /api/v1/practice/speaking/tts/
    
    Generate TTS audio for AI responses.
    """
    text = request.data.get('text', '')
    voice = request.data.get('voice', 'nova')
    
    if not text:
        return Response(
            {'error': 'Text is required'}, 
            status=status_module.HTTP_400_BAD_REQUEST
        )
    
    try:
        from .services.conversation_engine import TTSEngine
        
        tts_engine = TTSEngine()
        # In production, this would generate actual audio
        # For demo, return a mock URL
        
        return Response({
            'audio_url': f'/media/tts/generated_audio_{hash(text)}.mp3',
            'text': text,
            'voice': voice
        })
        
    except Exception as e:
        return Response(
            {'error': f'TTS generation failed: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# 🎧 AI LISTENING PRACTICE VIEWS
# =============================================================================

class ListeningExerciseListView(generics.ListAPIView):
    """
    GET /api/v1/practice/listening/exercises/
    
    List all available listening exercises.
    """
    serializer_class = ListeningExerciseListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['difficulty', 'exercise_type', 'accent_type', 'course']
    
    def get_queryset(self):
        return ListeningExercise.objects.filter(
            is_active=True
        ).select_related('course').order_by('difficulty', 'created_at')


class ListeningExerciseDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/practice/listening/exercises/{id}/
    
    Get detailed listening exercise information.
    """
    queryset = ListeningExercise.objects.filter(is_active=True)
    serializer_class = ListeningExerciseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class ListeningSessionCreateView(generics.CreateAPIView):
    """
    POST /api/v1/practice/listening/sessions/
    
    Create a new listening practice session.
    """
    serializer_class = ListeningSessionCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @subscription_required('listening')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        session = serializer.save()
        
        # Update user progress statistics
        user_progress, created = UserProgress.objects.get_or_create(
            user=self.request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        # Update listening session count
        user_progress.total_listening_sessions += 1
        user_progress.save()
        
        return session


class ListeningSessionDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/practice/listening/sessions/{id}/
    
    Get detailed listening session information with attempts.
    """
    serializer_class = ListeningSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return ListeningSession.objects.filter(
            user=self.request.user
        ).select_related('exercise').prefetch_related('attempts')


class ListeningAttemptCreateView(generics.CreateAPIView):
    """
    POST /api/v1/practice/listening/attempts/
    
    Record a user's attempt to answer a listening question.
    """
    serializer_class = ListeningAttemptCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        attempt = serializer.save()
        
        # Update session statistics
        session = attempt.session
        if attempt.is_correct:
            session.points_earned += session.exercise.points_reward
        else:
            session.hearts_used += 1
            # Reduce user hearts if answer is wrong
            user_progress = UserProgress.objects.get(user=session.user)
            user_progress.reduce_hearts()
        
        session.save()
        
        return attempt


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_listening_progress(request):
    """
    GET /api/v1/practice/listening/progress/
    
    Get user's listening practice progress and analytics.
    """
    user = request.user
    
    try:
        listening_progress = ListeningProgress.objects.get(user=user)
        serializer = ListeningProgressSerializer(listening_progress)
        return Response(serializer.data)
    except ListeningProgress.DoesNotExist:
        # Create initial progress record
        listening_progress = ListeningProgress.objects.create(user=user)
        serializer = ListeningProgressSerializer(listening_progress)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_listening_stats(request):
    """
    GET /api/v1/practice/listening/stats/
    
    Get comprehensive listening practice statistics for dashboard.
    """
    user = request.user
    
    # Get basic stats
    total_sessions = ListeningSession.objects.filter(user=user).count()
    completed_sessions = ListeningSession.objects.filter(
        user=user, 
        status='COMPLETED'
    )
    
    # Calculate average score
    if completed_sessions.exists():
        avg_score = completed_sessions.aggregate(
            avg=models.Avg('overall_score')
        )['avg'] or 0
        avg_score = round(avg_score, 1)
    else:
        avg_score = 0
    
    # Get listening progress
    try:
        progress = ListeningProgress.objects.get(user=user)
        current_streak = progress.current_listening_streak
        longest_streak = progress.longest_listening_streak
        total_hours = progress.total_hours_listened
    except ListeningProgress.DoesNotExist:
        current_streak = 0
        longest_streak = 0
        total_hours = 0.0
    
    # Weekly stats
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    week_ago = timezone.now() - timedelta(days=7)
    weekly_sessions = ListeningSession.objects.filter(
        user=user,
        started_at__gte=week_ago
    )
    
    sessions_this_week = weekly_sessions.count()
    
    # Calculate minutes this week
    minutes_this_week = 0
    for session in weekly_sessions:
        if session.total_duration:
            minutes_this_week += session.total_duration.total_seconds() / 60
    
    # Improvement trend (simplified)
    recent_sessions = completed_sessions.order_by('-completed_at')[:5]
    if recent_sessions.count() >= 3:
        recent_avg = sum(s.overall_score for s in recent_sessions[:3]) / 3
        older_avg = sum(s.overall_score for s in recent_sessions[-3:]) / 3
        
        if recent_avg > older_avg + 5:
            improvement_trend = 'up'
        elif recent_avg < older_avg - 5:
            improvement_trend = 'down'
        else:
            improvement_trend = 'stable'
    else:
        improvement_trend = 'stable'
    
    # Favorite accent and comfortable speed
    favorite_accent = 'AMERICAN'  # Default
    comfortable_speed = '1.0x'   # Default
    
    if hasattr(user, 'listening_progress'):
        progress = user.listening_progress
        # Find most practiced accent
        accent_counts = {
            'american': progress.american_sessions,
            'british': progress.british_sessions,
            'other': progress.other_accents_sessions
        }
        favorite_accent = max(accent_counts.items(), key=lambda x: x[1])[0].upper()
        
        # Get comfortable speed
        if progress.speeds_comfort_level:
            comfortable_speeds = [
                speed for speed, comfort in progress.speeds_comfort_level.items()
                if comfort >= 80  # High comfort threshold
            ]
            if comfortable_speeds:
                comfortable_speed = f"{max(comfortable_speeds)}x"
    
    stats = {
        'total_sessions': total_sessions,
        'total_hours': round(total_hours, 1),
        'average_score': avg_score,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'sessions_this_week': sessions_this_week,
        'minutes_this_week': round(minutes_this_week, 1),
        'improvement_trend': improvement_trend,
        'favorite_accent': favorite_accent,
        'comfortable_speed': comfortable_speed,
        'strong_areas': ['Comprehension', 'Vocabulary'],  # Simplified
        'improvement_areas': ['Speed Adaptation', 'Accent Recognition']  # Simplified
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@listening_required(3)  # 3 minutes consumed when completing  
def complete_listening_session(request, session_id):
    """
    POST /api/v1/practice/listening/sessions/{session_id}/complete/
    
    Complete a listening practice session and calculate final scores.
    """
    session = get_object_or_404(
        ListeningSession,
        id=session_id,
        user=request.user
    )
    
    if session.status == 'COMPLETED':
        return Response({'error': 'Session already completed'})
    
    # Calculate final scores based on attempts
    attempts = session.attempts.all()
    
    if attempts.exists():
        # Comprehension score
        correct_attempts = attempts.filter(is_correct=True).count()
        total_attempts = attempts.count()
        comprehension_score = (correct_attempts / total_attempts) * 100
        
        # Accuracy score (including partial credits)
        total_partial_credit = sum(attempt.partial_credit for attempt in attempts)
        accuracy_score = (total_partial_credit / total_attempts) * 100
        
        # Vocabulary score (simplified)
        vocab_attempts = attempts.filter(attempt_type='VOCABULARY_IDENTIFICATION')
        if vocab_attempts.exists():
            vocab_correct = vocab_attempts.filter(is_correct=True).count()
            vocabulary_score = (vocab_correct / vocab_attempts.count()) * 100
        else:
            vocabulary_score = comprehension_score  # Use comprehension as fallback
        
        # Overall score
        overall_score = (comprehension_score * 0.5 + 
                        accuracy_score * 0.3 + 
                        vocabulary_score * 0.2)
        
        # Update session
        session.comprehension_score = round(comprehension_score, 1)
        session.accuracy_score = round(accuracy_score, 1)
        session.vocabulary_score = round(vocabulary_score, 1)
        session.overall_score = round(overall_score, 1)
        session.is_passed = overall_score >= session.exercise.minimum_score
        session.status = 'COMPLETED'
        session.completed_at = timezone.now()
        
        # Calculate total duration
        if session.started_at:
            session.total_duration = session.completed_at - session.started_at
        
        session.save()
        
        # Update user listening progress
        listening_progress, created = ListeningProgress.objects.get_or_create(
            user=request.user
        )
        
        # Update statistics
        listening_progress.total_sessions += 1
        if session.total_duration:
            listening_progress.total_hours_listened += session.total_duration.total_seconds() / 3600
        
        # Update average scores
        all_sessions = ListeningSession.objects.filter(
            user=request.user,
            status='COMPLETED'
        )
        
        if all_sessions.exists():
            listening_progress.avg_comprehension_score = round(
                all_sessions.aggregate(avg=models.Avg('comprehension_score'))['avg'] or 0, 1
            )
            listening_progress.overall_listening_score = round(
                all_sessions.aggregate(avg=models.Avg('overall_score'))['avg'] or 0, 1
            )
        
        listening_progress.last_session_date = timezone.now()
        listening_progress.save()
        
        # Award points if passed
        if session.is_passed:
            user_progress = UserProgress.objects.get(user=request.user)
            user_progress.add_points(session.exercise.points_reward)
    
    serializer = ListeningSessionSerializer(session)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_listening_comprehension(request):
    """
    POST /api/v1/practice/listening/analyze/
    
    Analyze user's listening comprehension and provide feedback.
    """
    user_answers = request.data.get('user_answers', [])
    correct_answers = request.data.get('correct_answers', [])
    exercise_id = request.data.get('exercise_id')
    
    if not all([user_answers, correct_answers, exercise_id]):
        return Response(
            {'error': 'user_answers, correct_answers, and exercise_id are required'},
            status=status_module.HTTP_400_BAD_REQUEST
        )
    
    try:
        exercise = ListeningExercise.objects.get(id=exercise_id)
    except ListeningExercise.DoesNotExist:
        return Response(
            {'error': 'Exercise not found'},
            status=status_module.HTTP_404_NOT_FOUND
        )
    
    # Simple analysis (in production, use AI for better analysis)
    analysis_results = {
        'overall_score': 0,
        'comprehension_score': 0,
        'accuracy_score': 0,
        'vocabulary_score': 0,
        'speed_adaptation_score': 0,
        'user_answers': user_answers,
        'correct_answers': correct_answers,
        'answer_analysis': [],
        'vocabulary_gaps': [],
        'comprehension_patterns': [],
        'feedback_text': '',
        'improvement_suggestions': [],
        'recommended_exercises': []
    }
    
    # Calculate basic scores
    total_questions = len(correct_answers)
    correct_count = 0
    
    for i, (user_ans, correct_ans) in enumerate(zip(user_answers, correct_answers)):
        is_correct = user_ans.lower().strip() == correct_ans.lower().strip()
        similarity = 0.8 if is_correct else 0.3  # Simplified similarity
        
        if is_correct:
            correct_count += 1
        
        analysis_results['answer_analysis'].append({
            'question_index': i,
            'user_answer': user_ans,
            'correct_answer': correct_ans,
            'is_correct': is_correct,
            'similarity_score': similarity
        })
    
    # Calculate scores
    comprehension_score = (correct_count / total_questions) * 100
    analysis_results['comprehension_score'] = round(comprehension_score, 1)
    analysis_results['accuracy_score'] = round(comprehension_score, 1)  # Simplified
    analysis_results['vocabulary_score'] = round(comprehension_score * 0.9, 1)  # Slightly lower
    analysis_results['speed_adaptation_score'] = round(comprehension_score * 1.1, 1)  # Slightly higher
    analysis_results['overall_score'] = round(comprehension_score, 1)
    
    # Generate feedback
    if comprehension_score >= 85:
        analysis_results['feedback_text'] = "Excellent comprehension! Your listening skills are very strong."
        analysis_results['improvement_suggestions'] = [
            "Try more advanced listening exercises",
            "Practice with different accents",
            "Challenge yourself with faster speech rates"
        ]
    elif comprehension_score >= 70:
        analysis_results['feedback_text'] = "Good comprehension with room for improvement."
        analysis_results['improvement_suggestions'] = [
            "Focus on key vocabulary",
            "Practice active listening techniques",
            "Review difficult audio segments multiple times"
        ]
    else:
        analysis_results['feedback_text'] = "Keep practicing! Your listening skills will improve with consistent effort."
        analysis_results['improvement_suggestions'] = [
            "Start with slower speech rates",
            "Focus on basic vocabulary",
            "Use transcripts to check understanding"
        ]
    
    # Recommended exercises
    analysis_results['recommended_exercises'] = [
        f"{exercise.difficulty} level exercises",
        f"{exercise.accent_type} accent practice",
        "Vocabulary building exercises"
    ]
    
    return Response(analysis_results)


# =============================================================================
# AI TRANSLATION ENDPOINTS - Intelligent translation validation
# =============================================================================

class AITranslationValidationView(APIView):
    """
    POST /api/v1/practice/validate-ai-translation/
    
    Validate user translation using AI analysis with detailed feedback
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate translation using AI with intelligent scoring"""
        import asyncio
        from .services.ai_translation import AITranslationValidator
        
        # Extract request data
        source_text = request.data.get('source_text', '').strip()
        user_translation = request.data.get('user_translation', '').strip()
        challenge_id = request.data.get('challenge_id')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        
        # Validate required fields
        if not source_text or not user_translation:
            return Response(
                {'error': 'source_text and user_translation are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Validate challenge exists if provided
        challenge = None
        if challenge_id:
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'}, 
                    status=status_module.HTTP_404_NOT_FOUND
                )
        
        # Get user progress for hearts/points management
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        # Check if this is practice mode (challenge already completed)
        is_practice = False
        existing_progress = None
        if challenge:
            existing_progress = ChallengeProgress.objects.filter(
                user=request.user,
                challenge=challenge
            ).first()
            is_practice = existing_progress is not None
        
        # Check hearts for new challenges
        if not is_practice and user_progress.hearts == 0:
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate translation using AI
            validator = AITranslationValidator()
            
            # Run async validation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    validator.validate_translation(
                        source_text=source_text,
                        user_translation=user_translation,
                        difficulty_level=difficulty_level
                    )
                )
            finally:
                loop.close()
            
            # Process results and update progress
            response_data = {
                'success': True,
                'ai_validation': {
                    'semantic_score': result.semantic_score,
                    'fluency_score': result.fluency_score,
                    'fidelity_score': result.fidelity_score,
                    'overall_score': result.overall_score,
                    'is_acceptable': result.is_acceptable,
                    'partial_credit': result.partial_credit
                },
                'feedback': {
                    'message': result.feedback,
                    'explanation': result.explanation,
                    'suggestions': result.suggestions
                },
                'user_answer': user_translation,
                'source_text': source_text
            }
            
            # Update challenge progress if challenge provided
            if challenge and result.is_acceptable:
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
                
                response_data['challenge_progress'] = {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                }
            
            # Update user progress based on AI result
            if result.is_acceptable:
                if is_practice:
                    # Practice mode: restore hearts and add points
                    user_progress.add_hearts(1)
                else:
                    # New challenge: just add points
                    pass
                
                # Add points based on AI scoring
                points_earned = result.partial_credit
                user_progress.add_points(points_earned)
                
                response_data['points_earned'] = points_earned
            else:
                # Incorrect translation: reduce hearts if not practice
                if not is_practice and user_progress.hearts > 0:
                    user_progress.reduce_hearts()
                
                response_data['points_earned'] = 0
            
            # Add current user progress to response
            response_data['user_progress'] = {
                'hearts': user_progress.hearts,
                'points': user_progress.points
            }
            
            return Response(response_data, status=status_module.HTTP_200_OK)
            
        except Exception as e:
            print(f"AI Translation validation error: {e}")
            return Response(
                {'error': 'Translation validation failed', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateTranslationSuggestionsView(APIView):
    """
    POST /api/v1/practice/generate-translation-suggestions/
    
    Generate multiple correct translation alternatives for teachers
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate translation alternatives using AI"""
        import asyncio
        from .services.ai_translation import AITranslationValidator
        
        source_text = request.data.get('source_text', '').strip()
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        count = min(int(request.data.get('count', 3)), 5)  # Limit to 5 suggestions
        
        if not source_text:
            return Response(
                {'error': 'source_text is required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            validator = AITranslationValidator()
            
            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                suggestions = loop.run_until_complete(
                    validator.generate_translation_suggestions(
                        source_text=source_text,
                        difficulty_level=difficulty_level,
                        count=count
                    )
                )
            finally:
                loop.close()
            
            return Response({
                'success': True,
                'source_text': source_text,
                'suggestions': suggestions,
                'difficulty_level': difficulty_level
            })
            
        except Exception as e:
            print(f"Translation suggestions error: {e}")
            return Response(
                {'error': 'Failed to generate suggestions', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateTranslationExerciseView(APIView):
    """
    POST /api/v1/practice/generate-translation-exercise/
    
    Generate complete translation exercise with AI
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate a complete translation exercise"""
        import asyncio
        from .services.ai_translation import AITranslationValidator
        
        topic = request.data.get('topic', 'general conversation')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        exercise_type = request.data.get('exercise_type', 'sentence')
        
        try:
            validator = AITranslationValidator()
            
            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                exercise_data = loop.run_until_complete(
                    validator.generate_translation_exercise(
                        topic=topic,
                        difficulty_level=difficulty_level,
                        exercise_type=exercise_type
                    )
                )
            finally:
                loop.close()
            
            return Response({
                'success': True,
                'exercise': exercise_data,
                'generated_at': timezone.now(),
                'parameters': {
                    'topic': topic,
                    'difficulty_level': difficulty_level,
                    'exercise_type': exercise_type
                }
            })
            
        except Exception as e:
            print(f"Exercise generation error: {e}")
            return Response(
                {'error': 'Failed to generate exercise', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# AI PRONUNCIATION ENDPOINTS - Intelligent pronunciation analysis
# =============================================================================

class AIPronunciationAnalysisView(APIView):
    """
    POST /api/v1/practice/analyze-ai-pronunciation/
    
    Analyze student pronunciation using AI (Whisper + GPT-4)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Analyze pronunciation using AI with detailed feedback"""
        import asyncio
        import io
        from .services.ai_pronunciation import AIPronunciationAnalyzer
        
        # Extract request data
        audio_file = request.FILES.get('audio')
        expected_text = request.data.get('expected_text', '').strip()
        challenge_id = request.data.get('challenge_id')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        
        # Validate required fields
        if not audio_file or not expected_text:
            return Response(
                {'error': 'audio file and expected_text are required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        # Validate challenge exists if provided
        challenge = None
        if challenge_id:
            try:
                challenge = PracticeChallenge.objects.get(id=challenge_id)
            except PracticeChallenge.DoesNotExist:
                return Response(
                    {'error': 'Challenge not found'}, 
                    status=status_module.HTTP_404_NOT_FOUND
                )
        
        # Get user progress for hearts/points management
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        # Check if this is practice mode
        is_practice = False
        existing_progress = None
        if challenge:
            existing_progress = ChallengeProgress.objects.filter(
                user=request.user,
                challenge=challenge
            ).first()
            is_practice = existing_progress is not None
        
        # Check hearts for new challenges
        if not is_practice and user_progress.hearts == 0:
            return Response(
                {'error': 'hearts', 'message': 'No hearts remaining'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Convert uploaded file to BytesIO
            audio_bytes = io.BytesIO(audio_file.read())
            audio_bytes.name = audio_file.name
            
            # Analyze pronunciation using AI
            analyzer = AIPronunciationAnalyzer()
            
            # Run async analysis in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    analyzer.analyze_pronunciation(
                        audio_file=audio_bytes,
                        expected_text=expected_text,
                        difficulty_level=difficulty_level
                    )
                )
            finally:
                loop.close()
            
            # Process results and update progress
            response_data = {
                'success': True,
                'ai_analysis': {
                    'transcribed_text': result.transcribed_text,
                    'expected_text': result.expected_text,
                    'pronunciation_score': result.pronunciation_score,
                    'fluency_score': result.fluency_score,
                    'clarity_score': result.clarity_score,
                    'overall_score': result.overall_score,
                    'is_acceptable': result.is_acceptable,
                    'partial_credit': result.partial_credit,
                    'confidence_level': result.confidence_level
                },
                'feedback': {
                    'message': result.feedback,
                    'problematic_words': result.problematic_words,
                    'suggestions': result.suggestions
                }
            }
            
            # Update challenge progress if challenge provided
            if challenge and result.is_acceptable:
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
                
                response_data['challenge_progress'] = {
                    'id': str(progress.id),
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                }
            
            # Update user progress based on AI result
            if result.is_acceptable:
                if is_practice:
                    # Practice mode: restore hearts and add points
                    user_progress.add_hearts(1)
                else:
                    # New challenge: just add points
                    pass
                
                # Add points based on AI scoring
                points_earned = result.partial_credit
                user_progress.add_points(points_earned)
                
                response_data['points_earned'] = points_earned
            else:
                # Incorrect pronunciation: reduce hearts if not practice
                if not is_practice and user_progress.hearts > 0:
                    user_progress.reduce_hearts()
                
                response_data['points_earned'] = 0
            
            # Add current user progress to response
            response_data['user_progress'] = {
                'hearts': user_progress.hearts,
                'points': user_progress.points
            }
            
            return Response(response_data, status=status_module.HTTP_200_OK)
            
        except Exception as e:
            print(f"AI Pronunciation analysis error: {e}")
            return Response(
                {'error': 'Pronunciation analysis failed', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GeneratePronunciationExerciseView(APIView):
    """
    POST /api/v1/practice/generate-pronunciation-exercise/
    
    Generate pronunciation exercise with AI
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate pronunciation exercise using AI"""
        import asyncio
        from .services.ai_pronunciation import AIPronunciationAnalyzer
        
        topic = request.data.get('topic', 'daily conversation')
        difficulty_level = request.data.get('difficulty_level', 'intermediate')
        exercise_type = request.data.get('exercise_type', 'sentence')
        
        try:
            analyzer = AIPronunciationAnalyzer()
            
            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                exercise_data = loop.run_until_complete(
                    analyzer.generate_pronunciation_exercise(
                        topic=topic,
                        difficulty_level=difficulty_level,
                        exercise_type=exercise_type
                    )
                )
            finally:
                loop.close()
            
            return Response({
                'success': True,
                'exercise': exercise_data,
                'generated_at': timezone.now(),
                'parameters': {
                    'topic': topic,
                    'difficulty_level': difficulty_level,
                    'exercise_type': exercise_type
                }
            })
            
        except Exception as e:
            print(f"Pronunciation exercise generation error: {e}")
            return Response(
                {'error': 'Failed to generate pronunciation exercise', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateReferenceAudioView(APIView):
    """
    POST /api/v1/practice/generate-reference-audio/
    
    Generate reference audio pronunciation using TTS
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate reference audio for pronunciation practice"""
        import asyncio
        from django.http import HttpResponse
        from .services.ai_pronunciation import AIPronunciationAnalyzer
        
        text = request.data.get('text', '').strip()
        voice = request.data.get('voice', 'alloy')  # alloy, echo, fable, onyx, nova, shimmer
        
        if not text:
            return Response(
                {'error': 'text is required'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        try:
            analyzer = AIPronunciationAnalyzer()
            
            # Run async operation in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_bytes = loop.run_until_complete(
                    analyzer.generate_reference_audio(text=text, voice=voice)
                )
            finally:
                loop.close()
            
            if audio_bytes:
                # Return audio file directly
                response = HttpResponse(audio_bytes, content_type='audio/mpeg')
                response['Content-Disposition'] = f'attachment; filename="reference_{hash(text)}.mp3"'
                return response
            else:
                return Response(
                    {'error': 'Failed to generate audio'}, 
                    status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            print(f"Reference audio generation error: {e}")
            return Response(
                {'error': 'Failed to generate reference audio', 'details': str(e)}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========================================================================
# 🆕 COURSE-SPECIFIC PRACTICE ENDPOINTS - Práticas contextualizadas por curso
# ========================================================================

class CourseSpeakingExercisesView(APIView):
    """
    GET /api/v1/practice/courses/{course_id}/speaking/
    
    Exercícios de speaking específicos para um curso
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Lista exercícios de speaking para um curso específico"""
        try:
            from apps.courses.models import Course
            course = Course.objects.get(id=course_id, course_type='practice')
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso não encontrado'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )
        
        # Buscar exercícios específicos do curso
        exercises = SpeakingExercise.objects.filter(
            course=course,
            is_course_specific=True,
            is_active=True
        ).order_by('difficulty', 'created_at')
        
        # Se não há exercícios específicos, gera automaticamente
        if not exercises.exists():
            exercises = self.generate_course_exercises(course, request.user)
        
        from .serializers import SpeakingExerciseSerializer
        serializer = SpeakingExerciseSerializer(exercises, many=True)
        
        return Response({
            'message': f'Exercícios de speaking para {course.title}',
            'course': {
                'id': str(course.id),
                'title': course.title,
                'level': course.level
            },
            'exercises': serializer.data
        })
    
    def generate_course_exercises(self, course, user):
        """Gera exercícios de speaking baseados no conteúdo do curso"""
        exercises = []
        
        # Get course lessons for context
        practice_units = course.practice_units.all()[:3]  # Primeiras 3 unidades
        
        for unit in practice_units:
            lessons = unit.lessons.all()[:2]  # Primeiras 2 lições por unidade
            
            for lesson in lessons:
                # Gerar exercício de pronúncia
                pronunciation_exercise = SpeakingExercise.objects.create(
                    course=course,
                    is_course_specific=True,
                    auto_generated=True,
                    title=f"Pronúncia: {lesson.title}",
                    description=f"Pratique a pronúncia do vocabulário da lição '{lesson.title}'",
                    exercise_type='PRONUNCIATION',
                    difficulty=course.level.upper(),
                    lesson_context=lesson.title,
                    target_text=f"Vocabulary from {lesson.title}: pronunciation practice",
                    vocabulary_words=["hello", "world", "practice"],  # Seria extraído do conteúdo real
                    created_by=user
                )
                exercises.append(pronunciation_exercise)
                
                # Gerar exercício de conversação
                conversation_exercise = SpeakingExercise.objects.create(
                    course=course,
                    is_course_specific=True,
                    auto_generated=True,
                    title=f"Conversação: {lesson.title}",
                    description=f"Pratique conversação baseada na lição '{lesson.title}'",
                    exercise_type='CONVERSATION',
                    difficulty=course.level.upper(),
                    lesson_context=lesson.title,
                    conversation_prompt=f"Let's practice conversation about the topic: {lesson.title}",
                    vocabulary_words=["conversation", "practice", "topic"],
                    created_by=user
                )
                exercises.append(conversation_exercise)
        
        return exercises


class CourseListeningExercisesView(APIView):
    """
    GET /api/v1/practice/courses/{course_id}/listening/
    
    Exercícios de listening específicos para um curso
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Lista exercícios de listening para um curso específico"""
        try:
            from apps.courses.models import Course
            course = Course.objects.get(id=course_id, course_type='practice')
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso não encontrado'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )
        
        # Buscar exercícios específicos do curso
        exercises = ListeningExercise.objects.filter(
            course=course,
            is_course_specific=True,
            is_active=True
        ).order_by('difficulty', 'created_at')
        
        # Se não há exercícios específicos, gera automaticamente
        if not exercises.exists():
            exercises = self.generate_course_exercises(course, request.user)
        
        from .serializers import ListeningExerciseSerializer
        serializer = ListeningExerciseSerializer(exercises, many=True)
        
        return Response({
            'message': f'Exercícios de listening para {course.title}',
            'course': {
                'id': str(course.id),
                'title': course.title,
                'level': course.level
            },
            'exercises': serializer.data
        })
    
    def generate_course_exercises(self, course, user):
        """Gera exercícios de listening baseados no conteúdo do curso"""
        exercises = []
        
        # Get course lessons for context
        practice_units = course.practice_units.all()[:3]  # Primeiras 3 unidades
        
        for unit in practice_units:
            lessons = unit.lessons.all()[:2]  # Primeiras 2 lições por unidade
            
            for lesson in lessons:
                # Gerar exercício de compreensão auditiva
                comprehension_exercise = ListeningExercise.objects.create(
                    course=course,
                    is_course_specific=True,
                    auto_generated=True,
                    title=f"Compreensão: {lesson.title}",
                    description=f"Pratique compreensão auditiva com conteúdo da lição '{lesson.title}'",
                    exercise_type='AUDIO_COMPREHENSION',
                    difficulty=course.level.upper(),
                    lesson_context=lesson.title,
                    audio_url="https://example.com/audio/sample.mp3",  # Seria gerado dinamicamente
                    audio_duration="0:02:00",
                    transcript=f"Audio content for lesson: {lesson.title}",
                    questions=[
                        {"question": "What is the main topic?", "type": "multiple_choice"},
                        {"question": "What words did you hear?", "type": "text_input"}
                    ],
                    correct_answers=["topic", "words"],
                    created_by=user
                )
                exercises.append(comprehension_exercise)
        
        return exercises


class CoursePracticeProgressView(APIView):
    """
    GET /api/v1/practice/courses/{course_id}/progress/
    
    Progresso das práticas específicas de um curso
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Retorna progresso das práticas de um curso específico"""
        try:
            from apps.courses.models import Course, UserCourseProgress
            course = Course.objects.get(id=course_id, course_type='practice')
            
            # Buscar progresso do usuário no curso
            user_progress, created = UserCourseProgress.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={'enrollmentDate': timezone.now()}
            )
            
            # Buscar exercícios específicos do curso
            speaking_exercises = SpeakingExercise.objects.filter(
                course=course, is_course_specific=True
            ).count()
            
            listening_exercises = ListeningExercise.objects.filter(
                course=course, is_course_specific=True
            ).count()
            
            practice_summary = user_progress.get_practice_summary()
            
            return Response({
                'message': f'Progresso das práticas para {course.title}',
                'course': {
                    'id': str(course.id),
                    'title': course.title,
                    'level': course.level
                },
                'progress': {
                    'overall_with_practices': user_progress.get_overall_progress_with_practices(),
                    'main_progress': user_progress.overallProgress,
                    'speaking': {
                        **practice_summary['speaking'],
                        'available_exercises': speaking_exercises
                    },
                    'listening': {
                        **practice_summary['listening'],
                        'available_exercises': listening_exercises
                    }
                }
            })
            
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso não encontrado'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )


# ============================================================================
# TEACHER ACHIEVEMENT MANAGEMENT VIEWS
# ============================================================================

class TeacherAchievementListCreateView(generics.ListCreateAPIView):
    """
    GET/POST /api/v1/practice/teacher/achievements/
    
    List all achievements or create new achievement (Teacher only).
    """
    queryset = Achievement.objects.all().order_by('category', 'order')
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'rarity', 'is_active']
    
    def get_queryset(self):
        """Filter achievements with additional stats"""
        queryset = super().get_queryset()
        
        # Add unlock count annotation
        queryset = queryset.annotate(
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        )
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['include_stats'] = True
        return context


class TeacherAchievementDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/teacher/achievements/{id}/
    
    Retrieve, update or delete specific achievement (Teacher only).
    """
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Add unlock count annotation"""
        return super().get_queryset().annotate(
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_achievement_stats(request):
    """
    GET /api/v1/practice/teacher/achievements/stats/
    
    Get achievement statistics for teacher dashboard.
    """
    try:
        total_achievements = Achievement.objects.count()
        active_achievements = Achievement.objects.filter(is_active=True).count()
        inactive_achievements = total_achievements - active_achievements
        
        # Total unlocks across all achievements
        total_unlocked = UserAchievement.objects.filter(is_unlocked=True).count()
        
        # Achievements by category
        category_stats = Achievement.objects.values('category').annotate(
            count=models.Count('id'),
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        ).order_by('category')
        
        # Achievements by rarity
        rarity_stats = Achievement.objects.values('rarity').annotate(
            count=models.Count('id'),
            unlocked_count=models.Count(
                'user_achievements',
                filter=models.Q(user_achievements__is_unlocked=True)
            )
        ).order_by('rarity')
        
        # Recent unlocks (last 7 days)
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_unlocks = UserAchievement.objects.filter(
            is_unlocked=True,
            unlocked_at__gte=recent_date
        ).count()
        
        return Response({
            'total_achievements': total_achievements,
            'active_achievements': active_achievements,
            'inactive_achievements': inactive_achievements,
            'total_unlocked': total_unlocked,
            'recent_unlocks': recent_unlocks,
            'category_breakdown': list(category_stats),
            'rarity_breakdown': list(rarity_stats)
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar estatísticas: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_achievement_status(request, achievement_id):
    """
    POST /api/v1/practice/teacher/achievements/{id}/toggle-status/
    
    Toggle achievement active/inactive status.
    """
    try:
        achievement = get_object_or_404(Achievement, id=achievement_id)
        achievement.is_active = not achievement.is_active
        achievement.save()
        
        return Response({
            'message': f'Conquista {"ativada" if achievement.is_active else "desativada"} com sucesso',
            'is_active': achievement.is_active
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao alterar status: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_achievements(request):
    """
    POST /api/v1/practice/teacher/achievements/bulk-update/
    
    Bulk update achievement properties (activate/deactivate multiple, reorder, etc.).
    """
    try:
        action = request.data.get('action')
        achievement_ids = request.data.get('achievement_ids', [])
        
        if not action or not achievement_ids:
            return Response(
                {'error': 'Ação e IDs das conquistas são obrigatórios'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        achievements = Achievement.objects.filter(id__in=achievement_ids)
        
        if action == 'activate':
            achievements.update(is_active=True)
            message = f'{achievements.count()} conquistas ativadas'
            
        elif action == 'deactivate':
            achievements.update(is_active=False)
            message = f'{achievements.count()} conquistas desativadas'
            
        elif action == 'delete':
            count = achievements.count()
            achievements.delete()
            message = f'{count} conquistas removidas'
            
        elif action == 'reorder':
            # Update order based on provided order list
            order_data = request.data.get('order_data', [])
            for item in order_data:
                Achievement.objects.filter(id=item['id']).update(order=item['order'])
            message = 'Ordem das conquistas atualizada'
            
        else:
            return Response(
                {'error': 'Ação inválida'}, 
                status=status_module.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': message})
        
    except Exception as e:
        return Response(
            {'error': f'Erro na operação em lote: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def achievement_unlock_analytics(request, achievement_id):
    """
    GET /api/v1/practice/teacher/achievements/{id}/analytics/
    
    Get detailed analytics for specific achievement (unlock trends, user stats, etc.).
    """
    try:
        achievement = get_object_or_404(Achievement, id=achievement_id)
        
        # Basic unlock stats
        total_unlocks = UserAchievement.objects.filter(
            achievement=achievement, 
            is_unlocked=True
        ).count()
        
        # Unlock timeline (last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        unlock_timeline = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=True,
            unlocked_at__gte=thirty_days_ago
        ).extra(
            select={'day': 'date(unlocked_at)'}
        ).values('day').annotate(
            count=models.Count('id')
        ).order_by('day')
        
        # Users in progress
        users_in_progress = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=False,
            current_progress__gt=0
        ).count()
        
        # Average time to unlock (for unlocked achievements)
        avg_progress = UserAchievement.objects.filter(
            achievement=achievement,
            is_unlocked=False
        ).aggregate(
            avg_progress=models.Avg('current_progress')
        )
        
        return Response({
            'achievement': {
                'id': str(achievement.id),
                'title': achievement.title,
                'description': achievement.description,
                'category': achievement.category,
                'rarity': achievement.rarity,
                'requirement_target': achievement.requirement_target
            },
            'stats': {
                'total_unlocks': total_unlocks,
                'users_in_progress': users_in_progress,
                'average_progress': avg_progress['avg_progress'] or 0,
                'unlock_timeline': list(unlock_timeline)
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar analytics: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# STUDENT ACHIEVEMENT VIEWS - Public achievement endpoints for students
# ============================================================================

class StudentAchievementListView(generics.ListAPIView):
    """
    GET /api/v1/practice/achievements/
    
    List all achievements with user progress (Student view).
    """
    serializer_class = UserAchievementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['achievement__category', 'achievement__rarity', 'is_unlocked']
    
    def get_queryset(self):
        """Get user achievements or create them if they don't exist"""
        user = self.request.user
        
        # Get all active achievements
        all_achievements = Achievement.objects.filter(is_active=True)
        
        # Create UserAchievement records for any missing achievements
        for achievement in all_achievements:
            UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={
                    'current_progress': 0,
                    'is_unlocked': False
                }
            )
        
        # Return all user achievements
        return UserAchievement.objects.filter(
            user=user,
            achievement__is_active=True
        ).select_related('achievement').order_by(
            'achievement__category', 'achievement__order'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_achievement_stats(request):
    """
    GET /api/v1/practice/achievements/stats/
    
    Get achievement statistics for student dashboard.
    """
    try:
        user = request.user
        
        # Get user achievements
        user_achievements = UserAchievement.objects.filter(user=user)
        unlocked_achievements = user_achievements.filter(is_unlocked=True)
        
        total_available = Achievement.objects.filter(is_active=True).count()
        total_unlocked = unlocked_achievements.count()
        total_points = sum(ua.achievement.points for ua in unlocked_achievements)
        
        # Count rare achievements (epic and legendary)
        rare_achievements = unlocked_achievements.filter(
            achievement__rarity__in=['epic', 'legendary']
        ).count()
        
        # Recent unlocks (last 7 days)
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_unlocked = unlocked_achievements.filter(
            unlocked_at__gte=recent_date
        ).count()
        
        return Response({
            'totalUnlocked': total_unlocked,
            'totalAvailable': total_available,
            'totalPoints': total_points,
            'rareAchievements': rare_achievements,
            'recentUnlocked': recent_unlocked
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar estatísticas: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_achievement_categories(request):
    """
    GET /api/v1/practice/achievements/categories/
    
    Get achievement categories with user progress.
    """
    try:
        user = request.user
        
        # Get category stats
        categories = AchievementCategory.objects.filter(is_active=True).order_by('order')
        
        category_data = []
        for category in categories:
            # Count achievements in this category
            total_in_category = Achievement.objects.filter(
                category=category.name, 
                is_active=True
            ).count()
            
            # Count unlocked by user
            unlocked_in_category = UserAchievement.objects.filter(
                user=user,
                achievement__category=category.name,
                achievement__is_active=True,
                is_unlocked=True
            ).count()
            
            category_data.append({
                'name': category.name,
                'display_name': category.display_name,
                'description': category.description,
                'icon_class': category.icon_class,
                'color': category.color,
                'order': category.order,
                'achievement_count': total_in_category,
                'unlocked_count': unlocked_in_category
            })
        
        return Response(category_data)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar categorias: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_achievement_notifications(request):
    """
    GET /api/v1/practice/achievements/notifications/
    
    Get unread achievement notifications for user.
    """
    try:
        user = request.user
        
        notifications = AchievementNotification.objects.filter(
            user=user,
            is_read=False
        ).select_related('achievement').order_by('-created_at')[:10]
        
        serializer = AchievementNotificationSerializer(
            notifications, 
            many=True,
            context={'request': request}
        )
        
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao buscar notificações: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    POST /api/v1/practice/achievements/notifications/{id}/read/
    
    Mark achievement notification as read.
    """
    try:
        notification = get_object_or_404(
            AchievementNotification,
            id=notification_id,
            user=request.user
        )
        
        notification.is_read = True
        notification.save()
        
        return Response({'message': 'Notificação marcada como lida'})
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao marcar notificação: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_achievement_celebrated(request, achievement_id):
    """
    POST /api/v1/practice/achievements/{id}/celebrate/
    
    Mark achievement as celebrated (popup shown).
    """
    try:
        # Find the notification for this achievement
        notification = AchievementNotification.objects.filter(
            user=request.user,
            achievement_id=achievement_id,
            is_celebrated=False
        ).first()
        
        if notification:
            notification.is_celebrated = True
            notification.save()
        
        return Response({'message': 'Conquista marcada como celebrada'})
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao marcar celebração: {str(e)}'}, 
            status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# TEACHER LEADERBOARD VIEWS - Analytics and management for teachers
# ============================================================================




class TeacherCompetitionsView(generics.ListCreateAPIView):
    """
    GET/POST /api/v1/practice/teacher/leaderboard/competitions/
    
    List teacher competitions or create new ones.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get competitions relevant to teacher"""
        status_filter = self.request.GET.get('status', 'all')
        
        queryset = Competition.objects.all().order_by('-created_at')
        
        if status_filter != 'all':
            if status_filter == 'active':
                queryset = queryset.filter(status='active', end_date__gte=timezone.now())
            elif status_filter == 'finished':
                queryset = queryset.filter(end_date__lt=timezone.now())
        
        return queryset
    
    def list(self, request):
        """List competitions with teacher-specific data"""
        try:
            competitions = self.get_queryset()
            
            competitions_data = []
            for comp in competitions:
                # Get participation count
                participants_count = CompetitionParticipant.objects.filter(competition=comp).count()
                
                # Determine status
                now = timezone.now()
                if comp.start_date > now:
                    status = 'upcoming'
                elif comp.end_date < now:
                    status = 'finished'
                else:
                    status = 'active'
                
                competitions_data.append({
                    'id': str(comp.id),
                    'title': comp.title,
                    'description': comp.description,
                    'type': comp.type,
                    'status': status,
                    'createdBy': 'Teacher',  # Mock
                    'participants': participants_count,
                    'maxParticipants': comp.max_participants,
                    'startDate': comp.start_date.strftime('%Y-%m-%d'),
                    'endDate': comp.end_date.strftime('%Y-%m-%d'),
                    'prize': comp.first_place_prize or 'Badge especial',
                    'targetMetric': 'points',  # Mock
                    'targetValue': 1000,  # Mock
                    'created_at': comp.created_at.isoformat(),
                })
            
            return Response(competitions_data)
            
        except Exception as e:
            return Response(
                {'error': f'Erro ao buscar competições: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request):
        """Create new competition"""
        try:
            data = request.data
            
            # Calculate end date based on type and duration
            start_date = timezone.now()
            if data.get('type') == 'weekly':
                end_date = start_date + timezone.timedelta(days=7)
            elif data.get('type') == 'monthly':
                end_date = start_date + timezone.timedelta(days=30)
            else:
                duration = int(data.get('duration', 7))
                end_date = start_date + timezone.timedelta(days=duration)
            
            competition = Competition.objects.create(
                title=data['title'],
                description=data.get('description', ''),
                type=data.get('type', 'custom'),
                start_date=start_date,
                end_date=end_date,
                first_place_prize=data.get('prize', 'Badge especial + 500 pontos'),
                max_participants=data.get('maxParticipants'),
                status='active'
            )
            
            return Response({
                'id': str(competition.id),
                'title': competition.title,
                'description': competition.description,
                'type': competition.type,
                'status': 'active',
                'participants': 0,
                'startDate': competition.start_date.strftime('%Y-%m-%d'),
                'endDate': competition.end_date.strftime('%Y-%m-%d'),
                'prize': competition.first_place_prize,
                'created_at': competition.created_at.isoformat(),
            }, status=status_module.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Erro ao criar competição: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeacherCompetitionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/v1/practice/teacher/leaderboard/competitions/{id}/
    
    Manage specific competition.
    """
    permission_classes = [IsAuthenticated]
    queryset = Competition.objects.all()
    
    def retrieve(self, request, pk=None):
        """Get competition details"""
        try:
            competition = self.get_object()
            participants_count = CompetitionParticipant.objects.filter(competition=competition).count()
            
            # Determine status
            now = timezone.now()
            if competition.start_date > now:
                status = 'upcoming'
            elif competition.end_date < now:
                status = 'finished'
            else:
                status = 'active'
            
            return Response({
                'id': str(competition.id),
                'title': competition.title,
                'description': competition.description,
                'type': competition.type,
                'status': status,
                'participants': participants_count,
                'maxParticipants': competition.max_participants,
                'startDate': competition.start_date.strftime('%Y-%m-%d'),
                'endDate': competition.end_date.strftime('%Y-%m-%d'),
                'prize': competition.first_place_prize or 'Badge especial',
                'created_at': competition.created_at.isoformat(),
            })
            
        except Competition.DoesNotExist:
            return Response(
                {'error': 'Competição não encontrada'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )
    
    def update(self, request, pk=None):
        """Update competition"""
        try:
            competition = self.get_object()
            data = request.data
            
            # Update fields
            if 'title' in data:
                competition.title = data['title']
            if 'description' in data:
                competition.description = data['description']
            if 'prize' in data:
                competition.first_place_prize = data['prize']
            
            competition.save()
            
            return Response({'message': 'Competição atualizada com sucesso'})
            
        except Competition.DoesNotExist:
            return Response(
                {'error': 'Competição não encontrada'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request, pk=None):
        """Delete competition"""
        try:
            competition = self.get_object()
            
            # Only allow deletion if not started or no participants
            participants_count = CompetitionParticipant.objects.filter(competition=competition).count()
            if participants_count > 0 and competition.start_date <= timezone.now():
                return Response(
                    {'error': 'Não é possível deletar competição com participantes ativa'}, 
                    status=status_module.HTTP_400_BAD_REQUEST
                )
            
            competition.delete()
            return Response({'message': 'Competição deletada com sucesso'})
            
        except Competition.DoesNotExist:
            return Response(
                {'error': 'Competição não encontrada'}, 
                status=status_module.HTTP_404_NOT_FOUND
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_competition_analytics(request, competition_id):
    """
    GET /api/v1/practice/teacher/leaderboard/competitions/{id}/analytics/
    
    Get detailed analytics for a specific competition.
    """
    try:
        competition = Competition.objects.get(id=competition_id)
        participants = CompetitionParticipant.objects.filter(competition=competition)
        
        # Mock analytics data
        analytics = {
            'competitionId': str(competition_id),
            'participationRate': 67.5,
            'averageProgress': 45.2,
            'progressChart': [
                {'date': '2024-01-15', 'participants': 8, 'averageProgress': 10},
                {'date': '2024-01-16', 'participants': 12, 'averageProgress': 25},
                {'date': '2024-01-17', 'participants': 15, 'averageProgress': 35},
                {'date': '2024-01-18', 'participants': 18, 'averageProgress': 45},
            ],
            'engagementMetrics': {
                'dailyActiveParticipants': 14,
                'dropoffRate': 8.3,
                'completionRate': 45.2
            }
        }
        
        return Response(analytics)
        
    except Competition.DoesNotExist:
        return Response(
            {'error': 'Competição não encontrada'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_student_engagement_details(request, student_id):
    """
    GET /api/v1/practice/teacher/leaderboard/students/{id}/details/
    
    Get detailed engagement information for a specific student.
    """
    try:
        from apps.users.models import User
        student = User.objects.get(id=student_id, role='student')
        
        # Get user progress and streak
        user_progress, _ = UserProgress.objects.get_or_create(
            user=student,
            defaults={'points': 0, 'hearts': 5}
        )
        streak, _ = UserStreak.objects.get_or_create(
            user=student,
            defaults={'current_streak': 0}
        )
        
        # Mock detailed data
        details = {
            'student': {
                'id': str(student.id),
                'name': student.name,
                'points': user_progress.points,
                'streak': streak.current_streak,
                'league': 'silver',
                'engagementScore': 85
            },
            'weeklyProgress': [
                {'date': '2024-01-15', 'points': 150, 'lessons': 3, 'streak': 5},
                {'date': '2024-01-16', 'points': 200, 'lessons': 4, 'streak': 6},
                {'date': '2024-01-17', 'points': 180, 'lessons': 3, 'streak': 7},
            ],
            'competitionHistory': [
                {'competition': 'Desafio Semanal', 'rank': 3, 'completed': True, 'progress': 100},
                {'competition': 'Maratona de Lições', 'rank': 5, 'completed': False, 'progress': 67},
            ],
            'achievements': [
                {'title': 'Primeiro Passo', 'unlockedAt': '2024-01-10', 'points': 10},
                {'title': 'Sequência Iniciante', 'unlockedAt': '2024-01-12', 'points': 15},
            ]
        }
        
        return Response(details)
        
    except User.DoesNotExist:
        return Response(
            {'error': 'Estudante não encontrado'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_enroll_students_in_competition(request, competition_id):
    """
    POST /api/v1/practice/teacher/leaderboard/competitions/{id}/enroll/
    
    Bulk enroll students in a competition.
    """
    try:
        competition = Competition.objects.get(id=competition_id)
        student_ids = request.data.get('student_ids', [])
        
        enrolled_count = 0
        for student_id in student_ids:
            try:
                from apps.users.models import User
                student = User.objects.get(id=student_id, role='student')
                
                # Create participation record if doesn't exist
                participant, created = CompetitionParticipant.objects.get_or_create(
                    competition=competition,
                    user=student,
                    defaults={'points_earned': 0}
                )
                
                if created:
                    enrolled_count += 1
                    
            except User.DoesNotExist:
                continue
        
        return Response({
            'enrolled': enrolled_count,
            'message': f'{enrolled_count} estudantes inscritos na competição'
        })
        
    except Competition.DoesNotExist:
        return Response(
            {'error': 'Competição não encontrada'}, 
            status=status_module.HTTP_404_NOT_FOUND
        )


# =============================================================================
# TEACHER LEADERBOARD VIEWS - Class rankings and competition management
# =============================================================================

class TeacherClassRankingsView(APIView):
    """
    GET /api/v1/practice/teacher/leaderboard/rankings/
    
    Get student rankings for teacher's classes
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from apps.users.models import User
            from django.db.models import Sum, Count, Avg, Q
            from datetime import datetime, timedelta
            
            # Get time range parameter
            time_range = request.GET.get('time_range', 'week')
            course_id = request.GET.get('course_id', None)
            
            # Calculate date filter based on time range
            now = timezone.now()
            if time_range == 'week':
                date_filter = now - timedelta(days=7)
            elif time_range == 'month':
                date_filter = now - timedelta(days=30)
            else:
                date_filter = None
            
            # Get all students with their progress
            students = User.objects.filter(role='student')
            
            rankings = []
            for student in students:
                # Get user progress
                try:
                    progress = UserProgress.objects.get(user=student)
                    
                    # Calculate points based on time range
                    if date_filter:
                        # Count completed challenges in time range (10 points each)
                        recent_completed = ChallengeProgress.objects.filter(
                            user=student,
                            completed=True,
                            completed_at__gte=date_filter
                        ).count()
                        points = recent_completed * 10  # 10 points per challenge
                    else:
                        points = progress.points
                    
                    # Get streak
                    try:
                        user_streak = UserStreak.objects.get(user=student)
                        streak = user_streak.current_streak
                    except UserStreak.DoesNotExist:
                        streak = 0
                    
                    # Calculate league based on points
                    if points >= 2000:
                        league = 'gold'
                    elif points >= 1000:
                        league = 'silver'
                    elif points >= 500:
                        league = 'bronze'
                    else:
                        league = 'bronze'
                    
                    # Get completed lessons count
                    completed_lessons = ChallengeProgress.objects.filter(
                        user=student,
                        completed=True
                    ).values('challenge__lesson').distinct().count()
                    
                    # Calculate weekly points
                    week_ago = now - timedelta(days=7)
                    weekly_completed = ChallengeProgress.objects.filter(
                        user=student,
                        completed=True,
                        completed_at__gte=week_ago
                    ).count()
                    weekly_points = weekly_completed * 10  # 10 points per challenge
                    
                    # Calculate monthly points
                    month_ago = now - timedelta(days=30)
                    monthly_completed = ChallengeProgress.objects.filter(
                        user=student,
                        completed=True,
                        completed_at__gte=month_ago
                    ).count()
                    monthly_points = monthly_completed * 10  # 10 points per challenge
                    
                    # Get last activity
                    last_activity = ChallengeProgress.objects.filter(
                        user=student
                    ).order_by('-completed_at').first()
                    
                    if last_activity:
                        time_diff = now - last_activity.completed_at
                        if time_diff.total_seconds() < 3600:  # Less than 1 hour
                            last_activity_str = f"{int(time_diff.total_seconds() / 60)} minutes ago"
                        elif time_diff.days == 0:
                            last_activity_str = f"{int(time_diff.total_seconds() / 3600)} hours ago"
                        else:
                            last_activity_str = f"{time_diff.days} days ago"
                    else:
                        last_activity_str = "Never"
                    
                    rankings.append({
                        'id': str(student.id),
                        'name': student.name,
                        'username': student.email,
                        'points': points,
                        'streak': streak,
                        'league': league,
                        'weeklyPoints': weekly_points,
                        'monthlyPoints': monthly_points,
                        'completedLessons': completed_lessons,
                        'totalLessons': 100,  # This should be calculated based on available lessons
                        'change': 'same',  # This would require historical data
                        'changeAmount': 0,
                        'lastActivity': last_activity_str,
                        'engagementScore': min(100, (weekly_points / 10) + (streak * 2))
                    })
                
                except UserProgress.DoesNotExist:
                    # Create default progress for user
                    UserProgress.objects.create(user=student)
                    rankings.append({
                        'id': str(student.id),
                        'name': student.name,
                        'username': student.email,
                        'points': 0,
                        'streak': 0,
                        'league': 'bronze',
                        'weeklyPoints': 0,
                        'monthlyPoints': 0,
                        'completedLessons': 0,
                        'totalLessons': 100,
                        'change': 'new',
                        'changeAmount': 0,
                        'lastActivity': "Never",
                        'engagementScore': 0
                    })
            
            # Sort by points descending and add ranks
            rankings.sort(key=lambda x: x['points'], reverse=True)
            for i, ranking in enumerate(rankings):
                ranking['rank'] = i + 1
            
            return Response(rankings)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get rankings: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TeacherLeaderboardStatsView(APIView):
    """
    GET /api/v1/practice/teacher/leaderboard/stats/
    
    Get comprehensive teacher leaderboard statistics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from apps.users.models import User
            from django.db.models import Sum, Count, Avg, Q
            from datetime import datetime, timedelta
            
            # Get time range parameter
            time_range = request.GET.get('time_range', 'week')
            
            # Calculate date filter
            now = timezone.now()
            if time_range == 'week':
                date_filter = now - timedelta(days=7)
            elif time_range == 'month':
                date_filter = now - timedelta(days=30)
            else:
                date_filter = None
            
            # Get all students
            students = User.objects.filter(role='student')
            total_students = students.count()
            
            # Count active students (those who have activity in the time range)
            if date_filter:
                active_students = students.filter(
                    challenge_progress__completed_at__gte=date_filter
                ).distinct().count()
            else:
                active_students = students.filter(
                    challenge_progress__isnull=False
                ).distinct().count()
            
            # Calculate average points from UserProgress
            avg_points = UserProgress.objects.aggregate(
                avg=Avg('points')
            )['avg'] or 0
            
            # Calculate average streak from UserStreak model
            avg_streak = UserStreak.objects.aggregate(
                avg=Avg('current_streak')
            )['avg'] or 0
            
            # Count competitions
            active_competitions = Competition.objects.filter(
                end_date__gte=now,
                start_date__lte=now
            ).count()
            
            completed_competitions = Competition.objects.filter(
                end_date__lt=now
            ).count()
            
            # Calculate engagement rate
            engagement_rate = (active_students / total_students * 100) if total_students > 0 else 0
            
            # League distribution
            league_distribution = {
                'bronze': 0,
                'silver': 0,
                'gold': 0,
                'diamond': 0
            }
            
            for student in students:
                try:
                    progress = UserProgress.objects.get(user=student)
                    points = progress.points
                    if points >= 2000:
                        league_distribution['gold'] += 1
                    elif points >= 1000:
                        league_distribution['silver'] += 1
                    else:
                        league_distribution['bronze'] += 1
                except UserProgress.DoesNotExist:
                    league_distribution['bronze'] += 1
            
            # Weekly activity (simplified)
            weekly_activity = []
            for i in range(7):
                day = now - timedelta(days=i)
                day_name = day.strftime('%a')
                
                activity = ChallengeProgress.objects.filter(
                    completed_at__date=day.date()
                ).aggregate(
                    active_students=Count('user', distinct=True),
                    lessons_completed=Count('challenge__lesson', distinct=True)
                )
                
                weekly_activity.append({
                    'day': day_name,
                    'activeStudents': activity['active_students'] or 0,
                    'pointsEarned': 0,  # Points are tracked in UserProgress, not per challenge
                    'lessonsCompleted': activity['lessons_completed'] or 0
                })
            
            weekly_activity.reverse()  # Show in chronological order
            
            stats = {
                'totalStudents': total_students,
                'activeStudents': active_students,
                'averagePoints': avg_points,
                'averageStreak': avg_streak,
                'activeCompetitions': active_competitions,
                'completedCompetitions': completed_competitions,
                'engagementRate': engagement_rate,
                'leagueDistribution': league_distribution,
                'weeklyActivity': weekly_activity,
                'topPerformers': [],  # Would need more complex query
                'strugglingStudents': []  # Would need more complex query
            }
            
            return Response(stats)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get stats: {str(e)}'}, 
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# FRONTEND COMPATIBILITY VIEWS - Match expected frontend endpoint behavior
# ============================================================================

class UnitsListView(generics.ListAPIView):
    """
    GET /api/v1/practice/units/?course={courseId}
    
    List all practice units for a specific course (frontend compatibility).
    Expected query parameter: course (course UUID)
    """
    serializer_class = PracticeUnitSerializer
    permission_classes = []  # Temporarily removed for frontend compatibility
    authentication_classes = []  # Disable authentication completely
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course']
    
    def get_queryset(self):
        return PracticeUnit.objects.all().prefetch_related(
            'lessons__challenges__options'
        ).order_by('order')


class LessonsListView(generics.ListAPIView):
    """
    GET /api/v1/practice/lessons/?unit={unitId}
    
    List all practice lessons for a specific unit (frontend compatibility).
    Expected query parameter: unit (unit UUID)
    """
    serializer_class = PracticeLessonSerializer
    permission_classes = []  # Temporarily removed for frontend compatibility
    authentication_classes = []  # Disable authentication completely
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['unit']
    
    def get_queryset(self):
        return PracticeLesson.objects.all().prefetch_related(
            'challenges__options'
        ).order_by('order')


class ChallengesListView(generics.ListAPIView):
    """
    GET /api/v1/practice/challenges/?lesson={lessonId}
    
    List all practice challenges for a specific lesson (frontend compatibility).
    Expected query parameter: lesson (lesson UUID)
    """
    serializer_class = PracticeChallengeSerializer
    permission_classes = []  # Temporarily removed for frontend compatibility
    authentication_classes = []  # Disable authentication completely
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['lesson']
    
    def get_queryset(self):
        return PracticeChallenge.objects.all().prefetch_related(
            'options'
        ).order_by('order')


# Test function for units endpoint without authentication
@api_view(['GET'])
@permission_classes([])
def units_list_test(request):
    """Test function to verify units endpoint is working"""
    course_id = request.GET.get('course')
    
    if course_id:
        units = PracticeUnit.objects.filter(course_id=course_id).prefetch_related(
            'lessons__challenges__options'
        ).order_by('order')
    else:
        units = PracticeUnit.objects.all().prefetch_related(
            'lessons__challenges__options'
        ).order_by('order')
    
    serializer = PracticeUnitSerializer(units, many=True, context={'request': request})
    return Response(serializer.data)


def test_units_simple(request):
    """Simple test view using Django's HttpResponse"""
    from django.http import JsonResponse
    import json
    
    course_id = request.GET.get('course')
    
    units = PracticeUnit.objects.filter(course_id=course_id) if course_id else PracticeUnit.objects.all()
    
    units_data = []
    for unit in units:
        units_data.append({
            'id': str(unit.id),
            'title': unit.title,
            'description': unit.description,
            'order': unit.order,
            'course_id': str(unit.course.id),
            'lessons_count': unit.lessons.count()
        })
    
    return JsonResponse({
        'results': units_data,
        'count': len(units_data),
        'message': 'Units retrieved successfully'
    })


def test_lessons_simple(request):
    """Simple test view for lessons using Django's HttpResponse"""
    from django.http import JsonResponse
    
    unit_id = request.GET.get('unit')
    
    lessons = PracticeLesson.objects.filter(unit_id=unit_id) if unit_id else PracticeLesson.objects.all()
    
    lessons_data = []
    for lesson in lessons:
        lessons_data.append({
            'id': str(lesson.id),
            'title': lesson.title,
            'order': lesson.order,
            'unit_id': str(lesson.unit.id),
            'unit_title': lesson.unit.title,
            'challenges_count': lesson.challenges.count()
        })
    
    return JsonResponse({
        'results': lessons_data,
        'count': len(lessons_data),
        'message': 'Lessons retrieved successfully'
    })


def test_challenges_simple(request):
    """Simple test view for challenges using Django's HttpResponse"""
    from django.http import JsonResponse
    
    lesson_id = request.GET.get('lesson')
    
    challenges = PracticeChallenge.objects.filter(lesson_id=lesson_id) if lesson_id else PracticeChallenge.objects.all()
    
    challenges_data = []
    for challenge in challenges:
        # Get challenge options
        options_data = []
        for option in challenge.options.all():
            options_data.append({
                'id': str(option.id),
                'text': option.text,
                'is_correct': option.is_correct,
                'image_url': option.image_url,
                'audio_url': option.audio_url,
                'order': option.order
            })
        
        challenges_data.append({
            'id': str(challenge.id),
            'type': challenge.type,
            'question': challenge.question,
            'order': challenge.order,
            'lesson_id': str(challenge.lesson.id),
            'lesson_title': challenge.lesson.title,
            'options': options_data
        })
    
    return JsonResponse({
        'results': challenges_data,
        'count': len(challenges_data),
        'message': 'Challenges retrieved successfully'
    })


# Main endpoints for frontend compatibility (same as test versions but with proper names)
def units_list_simple(request):
    """Main units endpoint compatible with frontend"""
    return test_units_simple(request)


def lessons_list_simple(request):
    """Main lessons endpoint compatible with frontend"""
    return test_lessons_simple(request)


def challenges_list_simple(request):
    """Main challenges endpoint compatible with frontend"""
    return test_challenges_simple(request)


