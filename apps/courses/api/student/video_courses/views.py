"""
Views for the ProEnglish course management system - Student Video Courses API.

This module contains all API views for student video course-related operations,
maintaining the same endpoints and response format as the Express API.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q

from django.db.models import Count, Avg


# =============================================================================
# SECURITY MIXIN - Enrollment Verification
# =============================================================================

class EnrollmentRequiredMixin:
    """
    Mixin that requires user to be enrolled in the course to access content.

    SECURITY: This mixin prevents unauthorized access to paid course content.
    Apply to views that expose course content (chapters, quizzes, resources).

    The mixin checks:
    1. User is authenticated
    2. User has an active and non-expired enrollment in the course
    3. User has the required subscription level for premium courses

    To use, add this mixin BEFORE the base class:
        class MyView(EnrollmentRequiredMixin, generics.RetrieveAPIView):
            ...
    """

    def check_enrollment(self, course):
        """
        Check if the current user is enrolled in the course and has proper subscription.

        SECURITY: Uses atomic check to prevent race conditions.

        Args:
            course: The Course model instance

        Raises:
            PermissionDenied: If user is not enrolled or doesn't have proper subscription
        """
        from django.utils import timezone

        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Autenticação necessária para aceder a este conteúdo.")

        # SECURITY: Atomic check for enrollment with expiration validation
        from ....models import CourseEnrollment
        try:
            enrollment = CourseEnrollment.objects.select_for_update().get(
                user=user,
                course=course,
                is_active=True
            )

            # Check if enrollment has expired
            if enrollment.expires_at and timezone.now() > enrollment.expires_at:
                raise PermissionDenied(
                    "A sua matrícula neste curso expirou. Renove para continuar a aceder."
                )

        except CourseEnrollment.DoesNotExist:
            raise PermissionDenied(
                "Precisa estar inscrito neste curso para aceder a este conteúdo."
            )

        # SECURITY: Check subscription access for non-free courses
        # This is checked AFTER enrollment to prevent information leakage
        if not course.user_has_access(user):
            access_messages = {
                'premium': 'Este curso requer um plano Premium ou superior. A sua subscrição pode ter expirado.',
                'premium_plus': 'Este curso é exclusivo para assinantes Premium Plus.',
            }
            message = access_messages.get(
                course.access_level,
                'Não tem permissão para aceder a este conteúdo.'
            )
            raise PermissionDenied(message)

    def get_course_from_chapter(self, chapter):
        """Extract course from chapter object."""
        return chapter.section.course

    def get_course_from_quiz(self, quiz):
        """Extract course from quiz object."""
        return quiz.chapter.section.course

    def get_course_from_resource(self, resource):
        """Extract course from resource object."""
        return resource.chapter.section.course


class SubscriptionAccessMixin:
    """
    Mixin that checks subscription access for course content without requiring enrollment.

    SECURITY: This mixin is for views that list content (sections, chapters).
    For free courses: allows unauthenticated access
    For premium courses: requires authentication and valid subscription

    Unlike EnrollmentRequiredMixin, this doesn't require enrollment, just subscription.
    Use this for browsing course structure (sections, chapter lists).
    Use EnrollmentRequiredMixin for accessing actual content (chapter details, videos).
    """

    def check_subscription_access(self, course):
        """
        Check if the current user has subscription access to the course.

        Args:
            course: The Course model instance

        Returns:
            bool: True if user has access, False otherwise

        Raises:
            PermissionDenied: If premium course and user lacks subscription
        """
        # Free courses are accessible to everyone
        if course.access_level == 'free':
            return True

        user = self.request.user

        # Premium courses require authentication
        if not user.is_authenticated:
            raise PermissionDenied(
                "Este curso requer uma subscrição. Faça login para verificar seu acesso."
            )

        # Check subscription access
        if not course.user_has_access(user):
            access_messages = {
                'premium': 'Este curso requer um plano Premium ou superior.',
                'premium_plus': 'Este curso é exclusivo para assinantes Premium Plus.',
            }
            message = access_messages.get(
                course.access_level,
                'Não tem a subscrição necessária para aceder a este conteúdo.'
            )
            raise PermissionDenied(message)

        return True


from ....models import (
    Course, CourseSection, Chapter, ChapterComment,
    CourseEnrollment, Transaction, UserCourseProgress, ChapterProgress,
    ChapterResource, ChapterQuiz, StudentQuizAttempt,
    CourseWishlist, CourseReview, StudentNote, StudentBookmark, CourseCertificate
)
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateSerializer, CourseUpdateSerializer,
    CourseSectionSerializer, CourseSectionCreateSerializer,
    ChapterSerializer, ChapterCreateSerializer, ChapterCommentSerializer,
    TransactionSerializer, TransactionCreateSerializer,
    UserCourseProgressSerializer, UserCourseProgressUpdateSerializer,
    ChapterProgressSerializer, CourseEnrollmentSerializer,
    ChapterResourceSerializer, ChapterResourceCreateSerializer,
    ChapterQuizSerializer, ChapterQuizCreateSerializer,
    StudentQuizAttemptSerializer, StudentQuizAttemptCreateSerializer,
    CourseWishlistSerializer, CourseReviewSerializer, StudentNoteSerializer,
    StudentBookmarkSerializer, CourseCertificateSerializer
)
from ....pagination import (
    CourseListPagination, TransactionListPagination, CommentListPagination,
    QuizAttemptPagination, StandardResultsSetPagination, optimize_paginated_queryset
)


class CourseListView(generics.ListAPIView):
    """
    List published video courses for students.

    GET /api/v1/student/video-courses/ - List all published video courses

    Query Parameters for GET:
    - category: Filter by category ('all' for no filter)
    - access_level: Filter by access level ('free', 'premium', 'premium_plus', 'all')
    - is_featured: Filter by featured status ('true', 'false')
    - level: Filter by course difficulty level ('Beginner', 'Intermediate', 'Advanced')
    - ordering: Sort order (-created_at, title, level, -is_featured)
    - include_description: Include description field (default: true)
    - include_enrollment_count: Include enrollment count (default: false)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 12, max: 50)
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = CourseListPagination

    def get_queryset(self):
        # Students see only published VIDEO courses
        queryset = Course.objects.filter(status='Published', course_type='video')

        # Apply category filter
        category = self.request.query_params.get('category')
        if category and category != 'all':
            queryset = queryset.filter(category=category)

        # Apply access_level filter
        access_level = self.request.query_params.get('access_level')
        if access_level and access_level != 'all':
            valid_levels = ['free', 'premium', 'premium_plus']
            if access_level in valid_levels:
                queryset = queryset.filter(access_level=access_level)

        # Apply is_featured filter
        is_featured = self.request.query_params.get('is_featured')
        if is_featured == 'true':
            queryset = queryset.filter(is_featured=True)
        elif is_featured == 'false':
            queryset = queryset.filter(is_featured=False)

        # Apply level filter
        level = self.request.query_params.get('level')
        if level:
            valid_levels = ['Beginner', 'Intermediate', 'Advanced']
            if level in valid_levels:
                queryset = queryset.filter(level=level)

        # Use optimized queryset from serializer
        include_enrollment_count = self.request.query_params.get('include_enrollment_count', 'false').lower() == 'true'
        queryset = CourseListSerializer.optimize_queryset(
            queryset,
            include_enrollment_count=include_enrollment_count
        )

        # Apply ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        return queryset.order_by(ordering)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Get context for serialization
        context = {'request': request}
        context['include_description'] = request.query_params.get('include_description', 'true').lower() == 'true'
        context['include_enrollment_count'] = request.query_params.get('include_enrollment_count', 'false').lower() == 'true'

        # Paginate queryset
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            response = self.get_paginated_response(serializer.data)
            # Add custom message to paginated response
            response.data['message'] = 'Cursos recuperados com sucesso'
            return response

        # Fallback without pagination (shouldn't happen with pagination_class set)
        serializer = self.get_serializer(queryset, many=True, context=context)

        return Response({
            'message': 'Cursos recuperados com sucesso',
            'data': serializer.data
        })


class CourseDetailView(generics.RetrieveAPIView):
    """
    Retrieve course details for students.

    GET /api/v1/student/video-courses/{id}/ - Get course details

    SECURITY: For premium courses, unauthenticated users and users without
    subscription only see limited preview (section titles, no chapter details).
    """
    queryset = Course.objects.filter(status='Published', course_type='video')
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'courseId'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # SECURITY: Check if user has access to this course
        user = request.user
        user_has_access = False

        if user and user.is_authenticated:
            user_has_access = instance.user_has_access(user)
        else:
            # Unauthenticated users only have access to free courses
            user_has_access = instance.access_level == 'free'

        # Get fresh instance with optimizations based on query parameters
        include_sections = request.query_params.get('include_sections', 'true').lower() == 'true'
        include_enrollments = request.query_params.get('include_enrollments', 'true').lower() == 'true'
        include_chapters = request.query_params.get('include_chapters', 'true').lower() == 'true'
        include_comments = request.query_params.get('include_chapter_comments', 'false').lower() == 'true'

        # SECURITY: Limit content for users without subscription access
        if not user_has_access and instance.access_level != 'free':
            # Show only basic course info and section titles (no chapters)
            include_chapters = False
            include_comments = False

        # Re-fetch with optimizations
        optimized_queryset = CourseDetailSerializer.optimize_queryset(
            Course.objects.filter(id=instance.id, status='Published', course_type='video'),
            include_sections=include_sections,
            include_enrollments=include_enrollments
        )
        instance = optimized_queryset.first()

        if not instance:
            from rest_framework.exceptions import NotFound
            raise NotFound("Curso não encontrado ou não está publicado")

        # Set prefetch flags for serializer
        if include_sections:
            instance._prefetched_sections = True
            # Also set prefetch flags for chapters in each section
            if include_chapters:
                for section in instance.sections.all():
                    section._prefetched_chapters = True
        if include_enrollments:
            instance._prefetched_enrollments = True

        # Prepare context
        context = {'request': request}
        context['include_sections'] = include_sections
        context['include_enrollments'] = include_enrollments
        context['include_chapters'] = include_chapters
        context['include_chapter_comments'] = include_comments
        context['user_has_subscription_access'] = user_has_access

        serializer = self.get_serializer(instance, context=context)

        # Add access information to response
        response_data = {
            'message': 'Curso recuperado com sucesso',
            'data': serializer.data,
            'access_info': {
                'has_access': user_has_access,
                'access_level': instance.access_level,
                'access_level_display': instance.access_level_display,
                'content_limited': not user_has_access and instance.access_level != 'free'
            }
        }

        return Response(response_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_transaction(request):
    """
    Create transaction and enroll user in course.

    POST /api/v1/courses/transactions/create/

    Maps to Express: POST /transactions

    SECURITY: Verifies user has required subscription before enrollment.
    """
    serializer = TransactionCreateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    # SECURITY FIX: Get course and verify subscription access BEFORE enrollment
    course_id = request.data.get('courseId')
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
            # Check if user has subscription access for non-free courses
            if not course.user_has_access(request.user):
                access_messages = {
                    'premium': 'Este curso requer um plano Premium ou superior.',
                    'premium_plus': 'Este curso é exclusivo para assinantes Premium Plus.',
                }
                message = access_messages.get(
                    course.access_level,
                    'Não tem a subscrição necessária para aceder a este curso.'
                )
                return Response({
                    'error': 'Acesso negado',
                    'message': message,
                    'code': 'SUBSCRIPTION_REQUIRED',
                    'required_plan': course.access_level,
                    'upgrade_required': True
                }, status=status.HTTP_403_FORBIDDEN)
        except Course.DoesNotExist:
            return Response({
                'error': 'Curso não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        # Create transaction
        new_transaction = serializer.save()

        # Create enrollment (user already verified to have access)
        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=request.user,
            course=new_transaction.course
        )
        
        # Create initial progress record
        progress, created = UserCourseProgress.objects.get_or_create(
            user=request.user,
            course=new_transaction.course,
            defaults={
                'enrollmentDate': timezone.now(),
                'overallProgress': 0.0
            }
        )
        
        # Create chapter progress records for all chapters
        for section in new_transaction.course.sections.all():
            for chapter in section.chapters.all():
                ChapterProgress.objects.get_or_create(
                    user_progress=progress,
                    chapter=chapter,
                    defaults={'completed': False}
                )
    
    return Response({
        'message': 'Curso adquirido com sucesso',
        'data': {
            'transaction': TransactionSerializer(new_transaction).data,
            'courseProgress': UserCourseProgressSerializer(progress).data
        }
    }, status=status.HTTP_201_CREATED)


class TransactionListView(generics.ListAPIView):
    """
    List transactions for the authenticated user or all (for admins).
    
    GET /api/v1/courses/transactions/
    
    Maps to Express: GET /transactions
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 15, max: 50)
    - userId: Filter by user ID (admin only)
    - ordering: Sort order (-dateTime, amount, paymentProvider)
    """
    serializer_class = TransactionSerializer
    pagination_class = TransactionListPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.request.query_params.get('userId')
        
        if user_id and self.request.user.role == 'admin':
            # Admin can view transactions for specific user
            queryset = Transaction.objects.filter(user_id=user_id)
        elif user_id and str(self.request.user.id) == user_id:
            # User can view their own transactions
            queryset = Transaction.objects.filter(user=self.request.user)
        else:
            # Regular users see only their own transactions
            queryset = Transaction.objects.filter(user=self.request.user)
        
        # Optimize queries
        queryset = queryset.select_related('user', 'course')
        
        return optimize_paginated_queryset(queryset, self.request, '-dateTime')
    
    def list(self, request, *args, **kwargs):
        """Add transaction summary to response context."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate summary for current user's transactions
        from django.db.models import Sum, Count
        summary = queryset.aggregate(
            total_amount=Sum('amount'),
            total_transactions=Count('id')
        )
        
        # Add summary to request for pagination response
        request.transaction_summary = {
            'total_spent': summary['total_amount'] or 0,
            'total_transactions': summary['total_transactions'] or 0
        }
        
        return super().list(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_enrolled_courses(request, userId):
    """
    Get courses user is enrolled in.
    
    GET /api/v1/courses/users/{userId}/enrolled/
    
    Maps to Express: GET /users/course-progress/:userId
    """
    # userId is already a UUID object from Django URL converter
    # Check if user can access this data - direct UUID comparison
    if request.user.id != userId and request.user.role != 'admin':
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Acesso negado")
    
    try:
        from apps.users.models import User
        user = User.objects.get(id=userId)
    except User.DoesNotExist:
        return Response({'error': 'Usuário não encontrado'}, status=404)
    
    # Get enrolled courses - only published video courses
    # Optimized: filter at DB level and use select_related for teacher
    enrollments = CourseEnrollment.objects.filter(
        user=user,
        course__course_type='video',
        course__status='Published'
    ).select_related('course', 'course__teacher')

    courses = [enrollment.course for enrollment in enrollments]

    serializer = CourseListSerializer(courses, many=True)
    
    return Response({
        'message': 'Cursos inscritos recuperados com sucesso',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_course_progress(request, userId, courseId):
    """
    Get user progress in a specific course.
    
    GET /api/v1/courses/users/{userId}/progress/{courseId}/
    
    Maps to Express: GET /users/course-progress/:userId/:courseId
    """
    # userId and courseId are already UUID objects from Django URL converter
    # Check if user can access this data
    if request.user.id != userId and request.user.role != 'admin':
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Acesso negado")
    
    try:
        from apps.users.models import User
        user = User.objects.get(id=userId)
        course = Course.objects.get(id=courseId)
        progress = UserCourseProgress.objects.get(user=user, course=course)
    except (User.DoesNotExist, Course.DoesNotExist):
        return Response({'error': 'Usuário ou curso não encontrado'}, status=404)
    except UserCourseProgress.DoesNotExist:
        return Response({'error': 'Progresso do curso não encontrado para este usuário'}, status=404)
    
    serializer = UserCourseProgressSerializer(progress)
    
    return Response({
        'message': 'Progresso do curso recuperado com sucesso',
        'data': serializer.data
    })


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_user_course_progress(request, userId, courseId):
    """
    Update user progress in a specific course.
    
    PUT /api/v1/courses/users/{userId}/progress/{courseId}/
    
    Maps to Express: PUT /users/course-progress/:userId/:courseId
    """
    # userId and courseId are already UUID objects from Django URL converter
    # Check if user can update this data
    if request.user.id != userId:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Acesso negado")
    
    try:
        from apps.users.models import User
        user = User.objects.get(id=userId)
        course = Course.objects.get(id=courseId)
        progress = UserCourseProgress.objects.get(user=user, course=course)
    except (User.DoesNotExist, Course.DoesNotExist):
        return Response({'error': 'Usuário ou curso não encontrado'}, status=404)
    except UserCourseProgress.DoesNotExist:
        # Create progress if it doesn't exist
        progress = UserCourseProgress.objects.create(
            user=user,
            course=course,
            enrollmentDate=timezone.now(),
            overallProgress=0.0
        )
    
    serializer = UserCourseProgressUpdateSerializer(
        progress, 
        data=request.data, 
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    updated_progress = serializer.save()
    
    # Return updated progress
    response_serializer = UserCourseProgressSerializer(updated_progress)
    
    return Response({
        'message': 'Progresso atualizado com sucesso',
        'data': response_serializer.data
    })


# Course Section Views (Read-only for students)

class CourseSectionListView(SubscriptionAccessMixin, generics.ListAPIView):
    """
    List sections for a published course.

    SECURITY: Checks subscription access for premium courses.
    Free courses: accessible to everyone
    Premium courses: requires valid subscription
    """
    serializer_class = CourseSectionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        course_id = self.kwargs['courseId']
        include_comments = self.request.query_params.get('include_comments', 'false').lower() == 'true'

        # Only sections from published video courses
        queryset = CourseSection.objects.filter(
            course__id=course_id,
            course__status='Published',
            course__course_type='video'
        )

        # Optimize based on requirements
        if include_comments:
            queryset = queryset.prefetch_related('chapters__comments__user')
        else:
            queryset = queryset.prefetch_related('chapters')

        return queryset.order_by('order')

    def list(self, request, *args, **kwargs):
        """Override list to check subscription access before returning sections."""
        course_id = self.kwargs['courseId']
        try:
            course = Course.objects.get(id=course_id, status='Published', course_type='video')
        except Course.DoesNotExist:
            return Response({
                'error': 'Curso não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: Check subscription access
        self.check_subscription_access(course)

        return super().list(request, *args, **kwargs)


class CourseSectionDetailView(SubscriptionAccessMixin, generics.RetrieveAPIView):
    """
    Retrieve a course section details.

    SECURITY: Checks subscription access for premium courses.
    """
    serializer_class = CourseSectionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'sectionId'

    def get_queryset(self):
        return CourseSection.objects.filter(
            course__status='Published',
            course__course_type='video'
        ).select_related('course')

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to check subscription access before returning section."""
        instance = self.get_object()
        course = instance.course

        # SECURITY: Check subscription access
        self.check_subscription_access(course)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# Chapter Views (Read-only for students)

class ChapterListView(SubscriptionAccessMixin, generics.ListAPIView):
    """
    List chapters for a section.

    SECURITY: Checks subscription access for premium courses.
    Free courses: accessible to everyone
    Premium courses: requires valid subscription
    """
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        section_id = self.kwargs['sectionId']
        return Chapter.objects.filter(
            section__id=section_id,
            section__course__status='Published',
            section__course__course_type='video'
        ).order_by('order')

    def list(self, request, *args, **kwargs):
        """Override list to check subscription access before returning chapters."""
        section_id = self.kwargs['sectionId']
        try:
            section = CourseSection.objects.select_related('course').get(
                id=section_id,
                course__status='Published',
                course__course_type='video'
            )
        except CourseSection.DoesNotExist:
            return Response({
                'error': 'Secção não encontrada'
            }, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: Check subscription access
        self.check_subscription_access(section.course)

        return super().list(request, *args, **kwargs)


class ChapterDetailView(EnrollmentRequiredMixin, generics.RetrieveAPIView):
    """
    Retrieve chapter details.

    SECURITY: Requires enrollment to access chapter content.
    """
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'chapterId'

    def get_queryset(self):
        return Chapter.objects.filter(
            section__course__status='Published',
            section__course__course_type='video'
        ).select_related('section', 'section__course')

    def get_object(self):
        """Override to check enrollment before returning object."""
        obj = super().get_object()
        course = self.get_course_from_chapter(obj)
        self.check_enrollment(course)
        return obj


# Chapter Comment Views

class ChapterCommentListCreateView(generics.ListCreateAPIView):
    """
    List comments for a chapter or create new comment.
    
    Query Parameters for GET:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 50)
    - ordering: Sort order (-timestamp, user__name)
    """
    serializer_class = ChapterCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CommentListPagination
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        queryset = ChapterComment.objects.filter(chapter__id=chapter_id)
        return ChapterCommentSerializer.optimize_queryset(queryset)
    
    def perform_create(self, serializer):
        chapter_id = self.kwargs['chapterId']
        chapter = get_object_or_404(Chapter, id=chapter_id)
        serializer.save(chapter=chapter)


# Stripe Payment Intent View
# NOTE: This endpoint is for SUBSCRIPTION payments, not individual course purchases.
# The platform uses a subscription model - all courses are included with subscription.

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_payment_intent(request):
    """
    Create Stripe payment intent for subscription.

    POST /api/v1/courses/payments/stripe/intent/

    SECURITY: Amount should be validated against subscription plan prices.
    This is a legacy endpoint - subscription payments should use the subscriptions app.

    Maps to Express: POST /transactions/stripe-payment-intent
    """
    import logging
    logger = logging.getLogger(__name__)

    amount = request.data.get('amount', 0)
    plan_id = request.data.get('plan_id')  # Optional: subscription plan ID

    # Validate amount
    if not amount or amount <= 0:
        return Response({
            'error': 'Valor inválido'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Convert to integer cents if it's a float
    try:
        amount_cents = int(float(amount) * 100) if amount < 1000 else int(amount)
    except (ValueError, TypeError):
        return Response({
            'error': 'Valor inválido'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate amount range (Stripe limits)
    if amount_cents < 50:  # Stripe minimum is €0.50
        return Response({
            'error': 'Valor mínimo é €0.50'
        }, status=status.HTTP_400_BAD_REQUEST)

    if amount_cents > 99999999:  # Max ~€999,999.99
        return Response({
            'error': 'Valor excede o limite permitido'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        import stripe
        from django.conf import settings

        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

        if not stripe.api_key:
            return Response({
                'error': 'Stripe não configurado'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create idempotency key to prevent duplicate payments
        idempotency_key = f"sub_{request.user.id}_{plan_id or 'default'}_{timezone.now().strftime('%Y%m%d%H')}"

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='eur',
            automatic_payment_methods={'enabled': True},
            metadata={
                'user_id': str(request.user.id),
                'plan_id': str(plan_id) if plan_id else '',
                'type': 'subscription'
            },
            idempotency_key=idempotency_key
        )

        logger.info(f"Payment intent created: user={request.user.id}, plan={plan_id}, amount={amount_cents}")

        return Response({
            'message': 'Payment intent criado com sucesso',
            'data': {
                'clientSecret': payment_intent.client_secret
            }
        })

    except ImportError:
        return Response({
            'error': 'Biblioteca Stripe não instalada'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Payment intent error: {str(e)}")
        return Response({
            'error': f'Erro ao criar intenção de pagamento: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# 🆕 PHASE 1 BRIDGE ENDPOINTS - Chapter Enhancement API
# =============================================================================

class ChapterResourceListView(EnrollmentRequiredMixin, generics.ListAPIView):
    """
    List resources for a chapter (read-only for students).

    GET /api/v1/student/video-courses/chapters/{chapterId}/resources/

    Query Parameters for GET:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - ordering: Sort order (order, -created_at, resource_type)

    SECURITY: Requires enrollment to access chapter resources.
    """
    serializer_class = ChapterResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        queryset = ChapterResource.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video'
        )
        queryset = queryset.select_related('chapter', 'chapter__section__course', 'created_by')
        return optimize_paginated_queryset(queryset, self.request, 'order')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Check enrollment using first resource's course (if any)
        if queryset.exists():
            first_resource = queryset.first()
            course = self.get_course_from_resource(first_resource)
            self.check_enrollment(course)

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'message': 'Recursos do capítulo recuperados com sucesso',
            'data': serializer.data
        })


class ChapterResourceDetailView(EnrollmentRequiredMixin, generics.RetrieveAPIView):
    """
    Retrieve a chapter resource (read-only for students).

    GET /api/v1/student/video-courses/chapters/{chapterId}/resources/{resourceId}/

    SECURITY: Requires enrollment to access resource.
    """
    serializer_class = ChapterResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'resourceId'

    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterResource.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video'
        ).select_related('chapter__section__course')

    def get_object(self):
        """Override to check enrollment before returning object."""
        obj = super().get_object()
        course = self.get_course_from_resource(obj)
        self.check_enrollment(course)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Increment download count for students
        instance.download_count += 1
        instance.save(update_fields=['download_count'])

        serializer = self.get_serializer(instance)

        return Response({
            'message': 'Recurso recuperado com sucesso',
            'data': serializer.data
        })


class ChapterQuizListView(EnrollmentRequiredMixin, generics.ListAPIView):
    """
    Get quiz for a chapter (read-only for students).

    GET /api/v1/student/video-courses/chapters/{chapterId}/quiz/

    SECURITY: Requires enrollment to access quiz.
    """
    serializer_class = ChapterQuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video',
            is_active=True
        ).select_related('chapter__section__course')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            return Response({
                'message': 'Nenhum quiz encontrado para este capítulo',
                'data': None
            })

        # Should be only one quiz per chapter
        quiz = queryset.first()

        # Check enrollment
        course = self.get_course_from_quiz(quiz)
        self.check_enrollment(course)

        serializer = self.get_serializer(quiz)

        return Response({
            'message': 'Quiz do capítulo recuperado com sucesso',
            'data': serializer.data
        })


class ChapterQuizDetailView(EnrollmentRequiredMixin, generics.RetrieveAPIView):
    """
    Retrieve a chapter quiz (read-only for students).

    GET /api/v1/student/video-courses/chapters/{chapterId}/quiz/{quizId}/

    SECURITY: Requires enrollment to access quiz details.
    """
    serializer_class = ChapterQuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'quizId'

    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video',
            is_active=True
        ).select_related('chapter__section__course')

    def get_object(self):
        """Override to check enrollment before returning object."""
        obj = super().get_object()
        course = self.get_course_from_quiz(obj)
        self.check_enrollment(course)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'message': 'Quiz recuperado com sucesso',
            'data': serializer.data
        })


class StudentQuizAttemptListCreateView(generics.ListCreateAPIView):
    """
    List quiz attempts for a student or create new attempt.
    
    GET /api/v1/courses/chapters/{chapterId}/quiz/attempts/
    POST /api/v1/courses/chapters/{chapterId}/quiz/attempts/
    
    Query Parameters for GET:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 25, max: 50)
    - ordering: Sort order (-created_at, score, attempt_number)
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = QuizAttemptPagination
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']

        # Get the chapter quiz with optimized query
        try:
            chapter_quiz = ChapterQuiz.objects.select_related(
                'chapter__section__course__teacher'
            ).get(chapter__id=chapter_id)
        except ChapterQuiz.DoesNotExist:
            return StudentQuizAttempt.objects.none()

        # Base queryset with optimized relations to avoid N+1
        base_queryset = StudentQuizAttempt.objects.select_related(
            'student',
            'chapter_quiz',
            'chapter_quiz__chapter'
        )

        # Students see only their attempts, teachers see all attempts
        if self.request.user.role == 'teacher' and chapter_quiz.chapter.section.course.teacher == self.request.user:
            return base_queryset.filter(chapter_quiz=chapter_quiz).order_by('-created_at')
        else:
            return base_queryset.filter(
                chapter_quiz=chapter_quiz,
                student=self.request.user
            ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StudentQuizAttemptCreateSerializer
        return StudentQuizAttemptSerializer
    
    def perform_create(self, serializer):
        chapter_id = self.kwargs['chapterId']
        chapter_quiz = get_object_or_404(ChapterQuiz, chapter__id=chapter_id)
        
        # Check if quiz is active
        if not chapter_quiz.is_active:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Este quiz não está ativo")
        
        # Check if student exceeded max attempts
        student_attempts = StudentQuizAttempt.objects.filter(
            student=self.request.user,
            chapter_quiz=chapter_quiz
        ).count()
        
        if student_attempts >= chapter_quiz.max_attempts:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f"Limite máximo de {chapter_quiz.max_attempts} tentativas excedido")
        
        attempt = serializer.save(chapter_quiz=chapter_quiz)
        
        # Update quiz statistics
        with transaction.atomic():
            chapter_quiz.total_attempts += 1
            
            if attempt.is_completed:
                if attempt.is_passed:
                    chapter_quiz.total_completions += 1
                
                # Update average score
                all_attempts = StudentQuizAttempt.objects.filter(
                    chapter_quiz=chapter_quiz,
                    is_completed=True
                )
                
                if all_attempts.exists():
                    total_score = sum([attempt.score_percentage for attempt in all_attempts])
                    chapter_quiz.average_score = total_score / all_attempts.count()
            
            chapter_quiz.save()
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Tentativas de quiz recuperadas com sucesso',
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()
        
        response_serializer = StudentQuizAttemptSerializer(attempt, context={'request': request})
        
        return Response({
            'message': 'Tentativa de quiz registrada com sucesso',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_student_quiz_summary(request, chapterId):
    """
    Get summary of student's quiz performance for a specific chapter.
    
    GET /api/v1/courses/chapters/{chapterId}/quiz/summary/
    """
    try:
        chapter_quiz = ChapterQuiz.objects.get(chapter__id=chapterId)
    except ChapterQuiz.DoesNotExist:
        return Response({
            'message': 'Quiz não encontrado para este capítulo',
            'data': None
        })
    
    # Get student's attempts
    attempts = StudentQuizAttempt.objects.filter(
        chapter_quiz=chapter_quiz,
        student=request.user
    ).order_by('-created_at')
    
    if not attempts.exists():
        return Response({
            'message': 'Nenhuma tentativa encontrada',
            'data': {
                'quiz_info': ChapterQuizSerializer(chapter_quiz, context={'request': request}).data,
                'attempts_count': 0,
                'best_score': 0,
                'is_passed': False,
                'attempts_remaining': chapter_quiz.max_attempts,
                'last_attempt': None
            }
        })
    
    best_attempt = attempts.filter(is_completed=True).order_by('-score').first()
    last_attempt = attempts.first()
    passed_attempt = attempts.filter(is_passed=True).first()
    
    summary_data = {
        'quiz_info': ChapterQuizSerializer(chapter_quiz, context={'request': request}).data,
        'attempts_count': attempts.count(),
        'best_score': best_attempt.score_percentage if best_attempt else 0,
        'is_passed': bool(passed_attempt),
        'attempts_remaining': max(0, chapter_quiz.max_attempts - attempts.count()),
        'last_attempt': StudentQuizAttemptSerializer(last_attempt, context={'request': request}).data if last_attempt else None,
        'best_attempt': StudentQuizAttemptSerializer(best_attempt, context={'request': request}).data if best_attempt else None
    }
    
    return Response({
        'message': 'Resumo do quiz recuperado com sucesso',
        'data': summary_data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_course_enrollment_status(request, courseId):
    """
    Check if user is enrolled in a specific course and has access.

    GET /api/v1/student/video-courses/{courseId}/enrollment-status/

    Returns:
    - is_enrolled: Whether user is enrolled
    - has_access: Whether user's subscription allows access
    - can_enroll: Whether user can enroll (has required subscription)
    - access_level: Course's required access level
    - access_level_display: Human-readable access level
    """
    try:
        course = Course.objects.get(id=courseId, status='Published', course_type='video')
    except Course.DoesNotExist:
        return Response({
            'error': 'Curso não encontrado ou não está publicado'
        }, status=404)

    # Check if user is enrolled
    is_enrolled = CourseEnrollment.objects.filter(
        user=request.user,
        course=course,
        is_active=True
    ).exists()

    # Check subscription access
    has_access = course.user_has_access(request.user)

    # Get enrollment details if enrolled
    enrollment_data = None
    if is_enrolled:
        try:
            enrollment = CourseEnrollment.objects.get(user=request.user, course=course)
            enrollment_data = {
                'enrolled_at': enrollment.enrollment_date,
                'enrollment_source': getattr(enrollment, 'enrollment_source', 'direct'),
                'is_active': enrollment.is_active
            }
        except CourseEnrollment.DoesNotExist:
            pass

    # Determine if user can enroll (needs proper subscription for non-free courses)
    can_enroll = has_access and not is_enrolled

    # Get subscription info for premium courses
    subscription_info = None
    if not has_access:
        required_plan = 'Premium' if course.access_level == 'premium' else 'Premium Plus'
        subscription_info = {
            'required_plan': required_plan,
            'message': f'Este curso requer o plano {required_plan} ou superior.'
        }

    return Response({
        'message': 'Status de inscrição verificado com sucesso',
        'data': {
            'course_id': str(courseId),
            'course_title': course.title,
            'is_enrolled': is_enrolled,
            'has_access': has_access,
            'can_enroll': can_enroll,
            'access_level': course.access_level,
            'access_level_display': course.access_level_display,
            'is_free': course.is_free,
            'is_premium': course.is_premium,
            'enrollment_details': enrollment_data,
            'subscription_info': subscription_info
        }
    })


# =============================================================================
# COURSE DISCOVERY ENDPOINTS (Featured, Popular, Search)
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_featured_courses(request):
    """
    Get featured video courses.

    GET /api/v1/student/video-courses/featured/

    Query params:
    - limit: Number of courses to return (default: 6, max: 20)
    - access_level: Filter by access level ('free', 'premium', 'premium_plus', 'all')

    Returns courses marked as featured (is_featured=True).
    Falls back to highest enrollment courses if no featured courses exist.
    """
    # SECURITY: Validate and cap limit
    try:
        limit = min(int(request.query_params.get('limit', 6)), 20)
        if limit < 1:
            limit = 6
    except (ValueError, TypeError):
        limit = 6

    # Base query: Published video courses marked as featured
    queryset = Course.objects.filter(
        status='Published',
        course_type='video',
        is_featured=True
    )

    # Apply access_level filter
    access_level = request.query_params.get('access_level')
    if access_level and access_level != 'all':
        valid_levels = ['free', 'premium', 'premium_plus']
        if access_level in valid_levels:
            queryset = queryset.filter(access_level=access_level)

    # Annotate with enrollment count for ordering
    queryset = queryset.annotate(
        enrollment_count=Count('enrollments')
    ).order_by('-enrollment_count')[:limit]

    # Fallback: if no featured courses, get most popular
    if not queryset.exists():
        fallback_queryset = Course.objects.filter(
            status='Published',
            course_type='video'
        )
        # Apply same access_level filter to fallback
        if access_level and access_level != 'all' and access_level in ['free', 'premium', 'premium_plus']:
            fallback_queryset = fallback_queryset.filter(access_level=access_level)

        queryset = fallback_queryset.annotate(
            enrollment_count=Count('enrollments')
        ).order_by('-enrollment_count')[:limit]

    serializer = CourseListSerializer(
        queryset,
        many=True,
        context={'request': request, 'include_enrollment_count': True}
    )

    return Response({
        'message': 'Cursos em destaque recuperados com sucesso',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_popular_courses(request):
    """
    Get popular video courses.

    GET /api/v1/student/video-courses/popular/

    Query params:
    - limit: Number of courses to return (default: 10, max: 50)
    - access_level: Filter by access level ('free', 'premium', 'premium_plus', 'all')
    - category: Filter by category
    """
    # SECURITY: Validate and cap limit to prevent DoS
    try:
        limit = min(int(request.query_params.get('limit', 10)), 50)
        if limit < 1:
            limit = 10
    except (ValueError, TypeError):
        limit = 10

    queryset = Course.objects.filter(
        status='Published',
        course_type='video'
    )

    # Apply access_level filter
    access_level = request.query_params.get('access_level')
    if access_level and access_level != 'all':
        valid_levels = ['free', 'premium', 'premium_plus']
        if access_level in valid_levels:
            queryset = queryset.filter(access_level=access_level)

    # Apply category filter
    category = request.query_params.get('category')
    if category and category != 'all':
        queryset = queryset.filter(category=category)

    courses = queryset.annotate(
        enrollment_count=Count('enrollments'),
        avg_rating=Avg('reviews__rating')
    ).order_by('-enrollment_count', '-avg_rating')[:limit]

    serializer = CourseListSerializer(
        courses,
        many=True,
        context={'request': request, 'include_enrollment_count': True}
    )

    return Response({
        'message': 'Cursos populares recuperados com sucesso',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_courses(request):
    """
    Search video courses.

    GET /api/v1/student/video-courses/search/

    Query params:
    - q: Search query (searches title and description)
    - category: Filter by category
    - level: Filter by level
    - access_level: Filter by access level ('free', 'premium', 'premium_plus')
    - is_featured: Filter by featured status ('true', 'false')
    - limit: Number of results (default: 20, max: 100)

    SECURITY:
    - Query is sanitized to prevent injection attacks
    - Limit is capped to prevent excessive resource usage
    """
    query = request.query_params.get('q', '').strip()
    category = request.query_params.get('category')
    level = request.query_params.get('level')
    access_level = request.query_params.get('access_level')
    is_featured = request.query_params.get('is_featured')

    # SECURITY: Validate and cap limit to prevent DoS
    try:
        limit = min(int(request.query_params.get('limit', 20)), 100)
        if limit < 1:
            limit = 20
    except (ValueError, TypeError):
        limit = 20

    # SECURITY: Cap query length to prevent regex DoS or memory issues
    MAX_QUERY_LENGTH = 100
    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH]

    courses = Course.objects.filter(
        status='Published',
        course_type='video'
    )

    if query:
        # Django's icontains uses parameterized queries - safe from SQL injection
        courses = courses.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    if category and category != 'all':
        courses = courses.filter(category=category)

    if level:
        valid_levels = ['Beginner', 'Intermediate', 'Advanced']
        if level in valid_levels:
            courses = courses.filter(level=level)

    # Apply access_level filter
    if access_level and access_level != 'all':
        valid_access_levels = ['free', 'premium', 'premium_plus']
        if access_level in valid_access_levels:
            courses = courses.filter(access_level=access_level)

    # Apply is_featured filter
    if is_featured == 'true':
        courses = courses.filter(is_featured=True)
    elif is_featured == 'false':
        courses = courses.filter(is_featured=False)

    courses = courses.annotate(
        enrollment_count=Count('enrollments')
    ).order_by('-enrollment_count')[:limit]

    serializer = CourseListSerializer(
        courses,
        many=True,
        context={'request': request}
    )

    return Response({
        'message': 'Pesquisa realizada com sucesso',
        'data': serializer.data,
        'total': courses.count()
    })


# =============================================================================
# WISHLIST ENDPOINTS
# =============================================================================

class WishlistListCreateView(generics.ListCreateAPIView):
    """
    List user's wishlist or add course to wishlist.

    GET /api/v1/student/video-courses/wishlist/
    POST /api/v1/student/video-courses/wishlist/
    """
    serializer_class = CourseWishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseWishlist.objects.filter(
            user=self.request.user
        ).select_related('course').order_by('-added_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Lista de desejos recuperada com sucesso',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Curso adicionado à lista de desejos',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist(request, courseId):
    """
    Remove course from wishlist.

    DELETE /api/v1/student/video-courses/wishlist/{courseId}/
    """
    try:
        wishlist_item = CourseWishlist.objects.get(
            user=request.user,
            course_id=courseId
        )
        wishlist_item.delete()
        return Response({
            'message': 'Curso removido da lista de desejos'
        })
    except CourseWishlist.DoesNotExist:
        return Response({
            'error': 'Curso não encontrado na lista de desejos'
        }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# NOTES ENDPOINTS
# =============================================================================

class NoteListCreateView(generics.ListCreateAPIView):
    """
    List user's notes or create new note.

    GET /api/v1/student/video-courses/notes/
    POST /api/v1/student/video-courses/notes/

    Query params for GET:
    - course_id: Filter by course
    """
    serializer_class = StudentNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = StudentNote.objects.filter(
            user=self.request.user
        ).select_related('course', 'chapter').order_by('-created_at')

        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Notas recuperadas com sucesso',
            'data': serializer.data
        })


class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a note.

    GET/PUT/DELETE /api/v1/student/video-courses/notes/{noteId}/
    """
    serializer_class = StudentNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'noteId'

    def get_queryset(self):
        return StudentNote.objects.filter(user=self.request.user)


# =============================================================================
# BOOKMARKS ENDPOINTS
# =============================================================================

class BookmarkListCreateView(generics.ListCreateAPIView):
    """
    List user's bookmarks or create new bookmark.

    GET /api/v1/student/video-courses/bookmarks/
    POST /api/v1/student/video-courses/bookmarks/

    Query params for GET:
    - course_id: Filter by course
    """
    serializer_class = StudentBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = StudentBookmark.objects.filter(
            user=self.request.user
        ).select_related(
            'chapter', 'chapter__section', 'chapter__section__course'
        ).order_by('-created_at')

        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(chapter__section__course_id=course_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Marcadores recuperados com sucesso',
            'data': serializer.data
        })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_bookmark(request, bookmarkId):
    """
    Delete a bookmark.

    DELETE /api/v1/student/video-courses/bookmarks/{bookmarkId}/
    """
    try:
        bookmark = StudentBookmark.objects.get(id=bookmarkId, user=request.user)
        bookmark.delete()
        return Response({'message': 'Marcador removido com sucesso'})
    except StudentBookmark.DoesNotExist:
        return Response({
            'error': 'Marcador não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# REVIEWS ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_course_reviews(request, courseId):
    """
    Get reviews for a course.

    GET /api/v1/student/video-courses/{courseId}/reviews/

    Query params:
    - page: Page number
    """
    # Optimized: select_related on user to avoid N+1 when serializing user_name/avatar
    reviews = CourseReview.objects.filter(
        course_id=courseId
    ).select_related('user', 'course').order_by('-created_at')

    # Calculate average rating
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0

    serializer = CourseReviewSerializer(reviews, many=True, context={'request': request})

    return Response({
        'message': 'Avaliações recuperadas com sucesso',
        'data': serializer.data,
        'average': round(avg_rating, 1),
        'total': reviews.count()
    })


class ReviewCreateView(generics.CreateAPIView):
    """
    Create a course review.

    POST /api/v1/student/video-courses/reviews/
    """
    serializer_class = CourseReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Check if user already reviewed this course
        course_id = request.data.get('course')
        if CourseReview.objects.filter(user=request.user, course_id=course_id).exists():
            return Response({
                'error': 'Você já avaliou este curso'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Avaliação criada com sucesso',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# CERTIFICATES ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_my_certificates(request):
    """
    Get user's certificates.

    GET /api/v1/student/video-courses/certificates/
    """
    certificates = CourseCertificate.objects.filter(
        user=request.user
    ).select_related('course').order_by('-issued_at')

    serializer = CourseCertificateSerializer(certificates, many=True, context={'request': request})

    return Response({
        'message': 'Certificados recuperados com sucesso',
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_certificate(request, courseId):
    """
    Generate certificate for a completed course.

    POST /api/v1/student/video-courses/{courseId}/generate-certificate/

    Requirements:
    - User must have a subscription plan that includes certificates
    - Course must be completed (100% progress)
    - Student must meet minimum grade requirements for certificate eligibility
    """
    from ....services import GradeCalculatorService
    from apps.subscriptions.models import UserSubscription
    import uuid

    # P2 FIX: Check if user's subscription plan allows certificates
    try:
        subscription = UserSubscription.objects.select_related('plan').get(user=request.user)
        if not subscription.is_active():
            return Response({
                'error': 'Assinatura inativa',
                'code': 'SUBSCRIPTION_INACTIVE',
                'message': 'Você precisa de uma assinatura ativa para gerar certificados.'
            }, status=status.HTTP_403_FORBIDDEN)

        if not subscription.plan.certificates:
            return Response({
                'error': 'Recurso não disponível no seu plano',
                'code': 'CERTIFICATES_NOT_INCLUDED',
                'message': 'Certificados não estão incluídos no seu plano atual. Faça upgrade para Premium ou Premium Plus.',
                'upgrade_required': True,
                'current_plan': subscription.plan.plan_type
            }, status=status.HTTP_403_FORBIDDEN)
    except UserSubscription.DoesNotExist:
        return Response({
            'error': 'Assinatura não encontrada',
            'code': 'NO_SUBSCRIPTION',
            'message': 'Você precisa de uma assinatura para gerar certificados.'
        }, status=status.HTTP_403_FORBIDDEN)

    # Check if user is enrolled and has progress
    try:
        progress = UserCourseProgress.objects.select_related('course').get(
            user=request.user,
            course_id=courseId
        )
    except UserCourseProgress.DoesNotExist:
        return Response({
            'error': 'Você não está inscrito neste curso'
        }, status=status.HTTP_400_BAD_REQUEST)

    course = progress.course

    # Check completion percentage
    if progress.overallProgress < 100.0:
        return Response({
            'error': f'Você precisa completar 100% do curso. Progresso atual: {progress.overallProgress:.1f}%'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if certificate already exists
    existing = CourseCertificate.objects.filter(
        user=request.user,
        course_id=courseId
    ).first()

    if existing:
        serializer = CourseCertificateSerializer(existing, context={'request': request})
        return Response({
            'message': 'Certificado já existe',
            'data': serializer.data
        })

    # Calculate and check grade eligibility
    calculator = GradeCalculatorService(request.user, course)
    grade = calculator.calculate_and_save(change_reason='recalculation')

    if not grade.is_eligible_for_certificate:
        missing_requirements = grade.get_missing_requirements()
        messages = [req['message'] for req in missing_requirements]

        return Response({
            'error': 'Você não atendeu aos requisitos mínimos para o certificado',
            'details': {
                'final_grade': {
                    'percentage': grade.final_grade_percentage,
                    'letter': grade.final_grade_letter,
                },
                'is_eligible': False,
                'missing_requirements': missing_requirements,
                'messages': messages,
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Generate verification code
    verification_code = f"VER-{uuid.uuid4().hex[:8].upper()}"

    # Create certificate with grade information
    certificate = CourseCertificate.objects.create(
        user=request.user,
        course_id=courseId,
        completion_percentage=progress.overallProgress,
        final_grade=grade.final_grade_percentage,
        final_grade_letter=grade.final_grade_letter,
        verification_code=verification_code
    )

    # Generate PDF certificate
    try:
        from ....services.certificate_service import CertificateGenerationService
        pdf_service = CertificateGenerationService(certificate)
        pdf_service.save_certificate()
    except Exception as e:
        # Log but don't fail - certificate record is created, PDF can be generated later
        import logging
        logging.getLogger(__name__).error(f"Error generating PDF: {e}")

    serializer = CourseCertificateSerializer(certificate, context={'request': request})

    return Response({
        'message': 'Certificado gerado com sucesso',
        'data': serializer.data,
        'grade_summary': {
            'final_percentage': grade.final_grade_percentage,
            'final_letter': grade.final_grade_letter,
            'quiz_score': grade.quiz_score,
            'practice_score': grade.practice_score,
            'conversation_score': grade.conversation_score,
        }
    }, status=status.HTTP_201_CREATED)


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_student_video_analytics(request):
    """
    Get student's video learning analytics.

    GET /api/v1/student/video-courses/analytics/
    """
    user = request.user

    # Get enrolled courses count
    total_enrolled = CourseEnrollment.objects.filter(
        user=user,
        course__course_type='video'
    ).count()

    # Get completed courses count
    courses_completed = UserCourseProgress.objects.filter(
        user=user,
        overallProgress__gte=100.0,
        course__course_type='video'
    ).count()

    # Get certificates count
    certificates_earned = CourseCertificate.objects.filter(user=user).count()

    # Calculate average progress
    progress_data = UserCourseProgress.objects.filter(
        user=user,
        course__course_type='video'
    ).aggregate(avg_progress=Avg('overallProgress'))
    average_progress = progress_data['avg_progress'] or 0

    # Calculate total watch time (from chapter progress time_spent)
    total_time = ChapterProgress.objects.filter(
        user_progress__user=user,
        user_progress__course__course_type='video'
    ).aggregate(total=models.Sum('time_spent'))['total'] or 0

    # Get recent activity (last 5 accessed courses)
    recent_courses = UserCourseProgress.objects.filter(
        user=user,
        course__course_type='video'
    ).select_related('course').order_by('-lastAccessedTimestamp')[:5]

    recent_activity = [{
        'course_id': str(p.course.id),
        'course_title': p.course.title,
        'progress': p.overallProgress,
        'last_accessed': p.lastAccessedTimestamp.isoformat()
    } for p in recent_courses]

    return Response({
        'message': 'Analytics recuperados com sucesso',
        'data': {
            'total_courses_enrolled': total_enrolled,
            'courses_completed': courses_completed,
            'total_watch_time': total_time,
            'certificates_earned': certificates_earned,
            'average_progress': round(average_progress, 1),
            'current_streak': 0,  # TODO: Implement streak tracking
            'recent_activity': recent_activity
        }
    })


# =============================================================================
# GRADING ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_course_grade(request, courseId):
    """
    Get student's grade for a specific course.

    GET /api/v1/student/video-courses/{courseId}/grade/

    Returns:
    - Quiz scores and details
    - Practice completion and details
    - Conversation scores (if applicable)
    - Final weighted grade
    - Certificate eligibility status
    """
    from ....services import GradeCalculatorService
    from ....models import StudentCourseGrade

    # Verify enrollment
    try:
        enrollment = CourseEnrollment.objects.select_related('course').get(
            user=request.user,
            course_id=courseId
        )
    except CourseEnrollment.DoesNotExist:
        return Response({
            'error': 'Você não está inscrito neste curso'
        }, status=status.HTTP_404_NOT_FOUND)

    # Calculate and save grades
    calculator = GradeCalculatorService(request.user, enrollment.course)
    grade = calculator.calculate_and_save(change_reason='recalculation')

    # Get missing requirements
    missing_requirements = grade.get_missing_requirements()

    # Build weight info with mode explanation
    weight_info = grade.weight_info or {}
    grading_mode = weight_info.get('mode', 'full')
    active_components = weight_info.get('active_components', [])

    mode_explanation = ''
    if grading_mode == 'simplified':
        mode_explanation = f'Avaliação baseada apenas em: {", ".join(active_components)}'
    elif grading_mode == 'no_content':
        mode_explanation = 'Nenhum componente de avaliação disponível neste curso'
    elif weight_info.get('weights_adjusted'):
        mode_explanation = 'Pesos ajustados automaticamente com base no conteúdo disponível'

    return Response({
        'message': 'Notas recuperadas com sucesso',
        'data': {
            'course': {
                'id': str(enrollment.course.id),
                'title': enrollment.course.title,
                'level': getattr(enrollment.course, 'level', None),
            },
            'grades': {
                'quizzes': {
                    'score': grade.quiz_score,
                    'count': grade.quiz_count,
                    'completed': grade.quiz_completed,
                    'passed': grade.quiz_passed,
                    'details': grade.quiz_details,
                },
                'practice': {
                    'score': grade.practice_score,
                    'count': grade.practice_count,
                    'completed': grade.practice_completed,
                    'details': grade.practice_details,
                },
                'conversation': {
                    'score': grade.conversation_score,
                    'sessions': grade.conversation_sessions,
                    'minutes': grade.conversation_minutes,
                    'required': grade.has_conversation_requirement,
                    'details': grade.conversation_details,
                },
            },
            'final_grade': {
                'percentage': grade.final_grade_percentage,
                'letter': grade.final_grade_letter,
            },
            'weight_info': {
                'quiz_weight': weight_info.get('quiz_weight', 0),
                'practice_weight': weight_info.get('practice_weight', 0),
                'conversation_weight': weight_info.get('conversation_weight', 0),
                'mode': grading_mode,
                'mode_explanation': mode_explanation,
                'active_components': active_components,
                'weights_adjusted': weight_info.get('weights_adjusted', False),
            },
            'certificate_eligibility': {
                'is_eligible': grade.is_eligible_for_certificate,
                'details': grade.eligibility_details,
                'missing_requirements': missing_requirements,
            },
            'last_calculated_at': grade.last_calculated_at.isoformat(),
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_certificate_eligibility(request, courseId):
    """
    Check if student is eligible for a certificate.

    GET /api/v1/student/video-courses/{courseId}/certificate-eligibility/

    Returns a simplified view of certificate eligibility.
    """
    from ....services import GradeCalculatorService
    from ....models import StudentCourseGrade, CourseGradingConfig

    # Verify enrollment
    try:
        enrollment = CourseEnrollment.objects.select_related('course').get(
            user=request.user,
            course_id=courseId
        )
    except CourseEnrollment.DoesNotExist:
        return Response({
            'error': 'Você não está inscrito neste curso'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get or calculate grades
    calculator = GradeCalculatorService(request.user, enrollment.course)
    grade = calculator.calculate_and_save(change_reason='recalculation')

    # Get grading config for requirements display
    try:
        config = enrollment.course.grading_config
    except CourseGradingConfig.DoesNotExist:
        config = None

    # Build requirements list
    requirements = []

    if config:
        requirements.append({
            'name': 'Média mínima em quizzes',
            'required_value': f'{config.min_quiz_average}%',
            'current_value': f'{grade.quiz_score}%',
            'met': grade.quiz_score >= config.min_quiz_average,
        })

        if config.require_all_quizzes_passed:
            requirements.append({
                'name': 'Todos os quizzes aprovados',
                'required_value': f'{grade.quiz_count} quizzes',
                'current_value': f'{grade.quiz_passed} aprovados',
                'met': grade.quiz_passed == grade.quiz_count and grade.quiz_count > 0,
            })

        requirements.append({
            'name': 'Exercícios práticos completados',
            'required_value': f'{config.min_practice_completion}%',
            'current_value': f'{grade.practice_score}%',
            'met': grade.practice_score >= config.min_practice_completion,
        })

        if config.require_conversation_if_available and grade.has_conversation_requirement:
            requirements.append({
                'name': 'Pontuação em conversação',
                'required_value': f'{config.min_conversation_score}%',
                'current_value': f'{grade.conversation_score}%',
                'met': grade.conversation_score >= config.min_conversation_score,
            })

        requirements.append({
            'name': 'Nota final mínima',
            'required_value': f'{config.min_final_grade}%',
            'current_value': f'{grade.final_grade_percentage}%',
            'met': grade.final_grade_percentage >= config.min_final_grade,
        })

    return Response({
        'message': 'Elegibilidade verificada com sucesso',
        'data': {
            'course': {
                'id': str(enrollment.course.id),
                'title': enrollment.course.title,
            },
            'is_eligible': grade.is_eligible_for_certificate,
            'final_grade': {
                'percentage': grade.final_grade_percentage,
                'letter': grade.final_grade_letter,
            },
            'requirements': requirements,
            'can_generate_certificate': grade.is_eligible_for_certificate,
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_grade_history(request, courseId):
    """
    Get grade history for a course.

    GET /api/v1/student/video-courses/{courseId}/grade-history/

    Returns history of grade changes over time.
    """
    from ....models import StudentCourseGrade, GradeHistory

    # Verify enrollment
    try:
        enrollment = CourseEnrollment.objects.select_related('course').get(
            user=request.user,
            course_id=courseId
        )
    except CourseEnrollment.DoesNotExist:
        return Response({
            'error': 'Você não está inscrito neste curso'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get grade record
    try:
        grade = StudentCourseGrade.objects.get(
            user=request.user,
            course_id=courseId
        )
    except StudentCourseGrade.DoesNotExist:
        return Response({
            'message': 'Nenhum histórico de notas encontrado',
            'data': {
                'history': []
            }
        })

    # Get history entries
    history_entries = GradeHistory.objects.filter(
        student_grade=grade
    ).order_by('-created_at')[:20]

    history_data = [{
        'id': str(entry.id),
        'date': entry.created_at.isoformat(),
        'change_reason': entry.change_reason,
        'quiz_score': entry.quiz_score,
        'practice_score': entry.practice_score,
        'conversation_score': entry.conversation_score,
        'final_grade_percentage': entry.final_grade_percentage,
        'final_grade_letter': entry.final_grade_letter,
        'is_eligible': entry.is_eligible,
        'details': entry.change_details,
    } for entry in history_entries]

    return Response({
        'message': 'Histórico recuperado com sucesso',
        'data': {
            'course': {
                'id': str(enrollment.course.id),
                'title': enrollment.course.title,
            },
            'current_grade': {
                'percentage': grade.final_grade_percentage,
                'letter': grade.final_grade_letter,
                'is_eligible': grade.is_eligible_for_certificate,
            },
            'history': history_data
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_student_grades(request):
    """
    Get all grades for the authenticated student across all enrolled courses.

    GET /api/v1/student/video-courses/grades/all/

    Returns:
    - List of all courses with their grades
    - Summary statistics (average grade, total courses, certificates earned)
    - Grade breakdown per course

    Query Parameters:
    - include_details: Include detailed quiz/practice/conversation info (default: true)
    - sort_by: Sort order (grade, title, recent) (default: recent)
    """
    from ....services import GradeCalculatorService
    from ....models import StudentCourseGrade, CourseCertificate

    include_details = request.query_params.get('include_details', 'true').lower() == 'true'
    sort_by = request.query_params.get('sort_by', 'recent')

    # Get all enrollments for the user with optimized queries
    # Include course.teacher for serialization to avoid N+1
    enrollments = CourseEnrollment.objects.filter(
        user=request.user
    ).select_related('course', 'course__teacher').order_by('-enrollment_date')

    # Prefetch existing grades to avoid N+1 queries in the loop
    existing_grades = {
        grade.course_id: grade
        for grade in StudentCourseGrade.objects.filter(
            user=request.user,
            course__in=[e.course_id for e in enrollments]
        )
    }

    if not enrollments.exists():
        return Response({
            'message': 'Nenhum curso encontrado',
            'data': {
                'courses': [],
                'summary': {
                    'total_courses': 0,
                    'courses_with_grades': 0,
                    'average_grade': 0,
                    'certificates_earned': 0,
                    'eligible_for_certificate': 0,
                }
            }
        })

    # Process each enrollment
    courses_grades = []
    total_percentage = 0
    courses_with_grades = 0
    eligible_count = 0

    for enrollment in enrollments:
        course = enrollment.course

        # Use prefetched grade if available, otherwise calculate
        grade = existing_grades.get(course.id)
        if grade is None:
            # Calculate if not exists
            calculator = GradeCalculatorService(request.user, course)
            grade = calculator.calculate_and_save(change_reason='recalculation')

        # Build grade data
        grade_data = {
            'course': {
                'id': str(course.id),
                'title': course.title,
                'thumbnail': course.image if course.image else None,
                'level': getattr(course, 'level', None),
                'category': getattr(course, 'category', None),
            },
            'enrollment': {
                'enrolled_at': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            },
            'final_grade': {
                'percentage': round(grade.final_grade_percentage, 2),
                'letter': grade.final_grade_letter,
            },
            'is_eligible_for_certificate': grade.is_eligible_for_certificate,
            'last_calculated_at': grade.last_calculated_at.isoformat(),
        }

        # Include weight info
        weight_info = grade.weight_info or {}
        grade_data['grading_mode'] = weight_info.get('mode', 'full')
        grade_data['active_components'] = weight_info.get('active_components', [])

        # Include detailed breakdown if requested
        if include_details:
            grade_data['grades'] = {
                'quizzes': {
                    'score': grade.quiz_score,
                    'count': grade.quiz_count,
                    'completed': grade.quiz_completed,
                    'passed': grade.quiz_passed,
                },
                'practice': {
                    'score': grade.practice_score,
                    'count': grade.practice_count,
                    'completed': grade.practice_completed,
                },
                'conversation': {
                    'score': grade.conversation_score,
                    'sessions': grade.conversation_sessions,
                    'minutes': grade.conversation_minutes,
                    'required': grade.has_conversation_requirement,
                },
            }

            # Add missing requirements if not eligible
            if not grade.is_eligible_for_certificate:
                grade_data['missing_requirements'] = grade.get_missing_requirements()

        courses_grades.append(grade_data)

        # Update summary stats
        if grade.final_grade_letter != 'N/A':
            total_percentage += grade.final_grade_percentage
            courses_with_grades += 1

        if grade.is_eligible_for_certificate:
            eligible_count += 1

    # Sort courses
    if sort_by == 'grade':
        courses_grades.sort(key=lambda x: x['final_grade']['percentage'], reverse=True)
    elif sort_by == 'title':
        courses_grades.sort(key=lambda x: x['course']['title'])
    # 'recent' is already sorted by enrolled_at

    # Get certificates count
    certificates_count = CourseCertificate.objects.filter(
        user=request.user
    ).count()

    # Calculate average grade
    average_grade = round(total_percentage / courses_with_grades, 2) if courses_with_grades > 0 else 0

    # Determine overall grade letter
    def get_letter_from_percentage(pct):
        if pct >= 90:
            return 'A'
        elif pct >= 80:
            return 'B'
        elif pct >= 70:
            return 'C'
        elif pct >= 60:
            return 'D'
        elif pct > 0:
            return 'F'
        return 'N/A'

    return Response({
        'message': 'Notas recuperadas com sucesso',
        'data': {
            'courses': courses_grades,
            'summary': {
                'total_courses': len(courses_grades),
                'courses_with_grades': courses_with_grades,
                'average_grade': {
                    'percentage': average_grade,
                    'letter': get_letter_from_percentage(average_grade),
                },
                'certificates_earned': certificates_count,
                'eligible_for_certificate': eligible_count,
            }
        }
    })


# =============================================================================
# CERTIFICATE DOWNLOAD & VERIFICATION ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_certificate(request, certificateId):
    """
    Download certificate PDF.

    GET /api/v1/student/video-courses/certificates/{certificateId}/download/

    Returns the PDF file for download or a URL redirect.
    """
    from django.http import FileResponse, HttpResponseRedirect
    from django.core.files.storage import default_storage

    try:
        certificate = CourseCertificate.objects.get(
            id=certificateId,
            user=request.user
        )
    except CourseCertificate.DoesNotExist:
        return Response({
            'error': 'Certificado não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)

    # If PDF doesn't exist, generate it
    if not certificate.certificate_url:
        try:
            from ....services.certificate_service import CertificateGenerationService
            pdf_service = CertificateGenerationService(certificate)
            pdf_service.save_certificate()
            certificate.refresh_from_db()
        except Exception as e:
            return Response({
                'error': 'Erro ao gerar PDF do certificado',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Build full URL for the certificate
    if certificate.certificate_url.startswith('http'):
        download_url = certificate.certificate_url
    else:
        # For local storage, build full URL
        from django.conf import settings
        base_url = request.build_absolute_uri('/').rstrip('/')
        download_url = f"{base_url}{certificate.certificate_url}"

    # Verify file exists for local storage
    if not certificate.certificate_url.startswith('http'):
        file_path = certificate.certificate_url.replace('/media/', '')
        if not default_storage.exists(file_path):
            # Regenerate if file doesn't exist
            try:
                from ....services.certificate_service import CertificateGenerationService
                pdf_service = CertificateGenerationService(certificate)
                pdf_service.save_certificate()
                certificate.refresh_from_db()
                download_url = f"{base_url}{certificate.certificate_url}"
            except Exception as e:
                return Response({
                    'error': 'Erro ao regenerar PDF do certificado',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'message': 'Certificado disponível para download',
        'download_url': download_url
    })


from rest_framework.throttling import AnonRateThrottle

class CertificateVerificationThrottle(AnonRateThrottle):
    """Rate limit certificate verification to prevent enumeration attacks."""
    rate = '10/minute'  # 10 requests per minute per IP


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_certificate(request, verification_code):
    """
    Public endpoint to verify a certificate's authenticity.

    GET /api/v1/certificates/verify/{verification_code}/

    Returns certificate details if valid, or error if not found.
    This endpoint is public (no authentication required).

    SECURITY:
    - Rate limited to prevent brute-force enumeration
    - Student name is partially masked for privacy
    - Verification attempts are logged
    """
    import logging
    logger = logging.getLogger(__name__)

    # Apply rate limiting manually for function-based view
    throttle = CertificateVerificationThrottle()
    if not throttle.allow_request(request, None):
        logger.warning(f"Certificate verification rate limit exceeded from IP: {_get_client_ip(request)}")
        return Response({
            'error': 'Muitas tentativas de verificação. Tente novamente em 1 minuto.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # Validate verification code format (basic check)
    if not verification_code or len(verification_code) < 8:
        return Response({
            'valid': False,
            'error': 'Código de verificação inválido'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        certificate = CourseCertificate.objects.select_related(
            'user', 'course'
        ).get(verification_code=verification_code)

        # Log successful verification
        logger.info(f"Certificate verified: {certificate.certificate_number} from IP: {_get_client_ip(request)}")

    except CourseCertificate.DoesNotExist:
        # Log failed verification attempt
        logger.warning(f"Invalid certificate verification attempt: {verification_code[:20]}... from IP: {_get_client_ip(request)}")
        return Response({
            'valid': False,
            'error': 'Certificado não encontrado',
            'message': 'O código de verificação fornecido não corresponde a nenhum certificado válido.'
        }, status=status.HTTP_404_NOT_FOUND)

    # SECURITY: Mask student name for privacy (show first name only)
    full_name = certificate.user.name or ''
    if full_name:
        name_parts = full_name.strip().split()
        if len(name_parts) > 1:
            # Show first name + last initial: "João S."
            masked_name = f"{name_parts[0]} {name_parts[-1][0]}."
        else:
            masked_name = name_parts[0] if name_parts else 'Estudante'
    else:
        masked_name = 'Estudante'

    return Response({
        'valid': True,
        'message': 'Certificado válido e autêntico',
        'data': {
            'certificate_number': certificate.certificate_number,
            'student_name': masked_name,  # Privacy: masked name
            'course_title': certificate.course.title,
            'issued_at': certificate.issued_at.isoformat(),
            'final_grade': {
                'percentage': certificate.final_grade,
                'letter': certificate.final_grade_letter,
            },
            'completion_percentage': certificate.completion_percentage,
        }
    })


def _get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_certificate_detail(request, certificateId):
    """
    Get detailed information about a specific certificate.

    GET /api/v1/student/video-courses/certificates/{certificateId}/
    """
    try:
        certificate = CourseCertificate.objects.select_related(
            'course'
        ).get(id=certificateId, user=request.user)
    except CourseCertificate.DoesNotExist:
        return Response({
            'error': 'Certificado não encontrado'
        }, status=status.HTTP_404_NOT_FOUND)

    # Get grade details
    try:
        grade = StudentCourseGrade.objects.get(
            user=request.user,
            course=certificate.course
        )
        grade_breakdown = {
            'quizzes': {
                'score': grade.quiz_score,
                'count': grade.quiz_count,
                'completed': grade.quiz_completed,
            },
            'practice': {
                'score': grade.practice_score,
                'count': grade.practice_count,
                'completed': grade.practice_completed,
            },
            'conversation': {
                'score': grade.conversation_score,
                'sessions': grade.conversation_sessions,
                'minutes': grade.conversation_minutes,
            },
        }
    except StudentCourseGrade.DoesNotExist:
        grade_breakdown = None

    return Response({
        'message': 'Certificado recuperado com sucesso',
        'data': {
            'id': str(certificate.id),
            'certificate_number': certificate.certificate_number,
            'verification_code': certificate.verification_code,
            'course': {
                'id': str(certificate.course.id),
                'title': certificate.course.title,
                'image': certificate.course.image if certificate.course.image else None,
            },
            'issued_at': certificate.issued_at.isoformat(),
            'final_grade': {
                'percentage': certificate.final_grade,
                'letter': certificate.final_grade_letter,
            },
            'completion_percentage': certificate.completion_percentage,
            'certificate_url': certificate.certificate_url,
            'grade_breakdown': grade_breakdown,
        }
    })