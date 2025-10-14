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
from django.db import transaction
from django.db.models import Q

from ....models import (
    Course, CourseSection, Chapter, ChapterComment,
    CourseEnrollment, Transaction, UserCourseProgress, ChapterProgress,
    ChapterResource, ChapterQuiz, StudentQuizAttempt
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
    StudentQuizAttemptSerializer, StudentQuizAttemptCreateSerializer
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
    - ordering: Sort order (-created_at, title, level)
    - include_description: Include description field (default: true)
    - include_enrollment_count: Include enrollment count (default: false)
    """
    serializer_class = CourseListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # Disable pagination
    
    def get_queryset(self):
        # Students see only published VIDEO courses
        queryset = Course.objects.filter(status='Published', course_type='video')
        
        # Apply category filter
        category = self.request.query_params.get('category')
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
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
        
        # Serialize without pagination
        serializer = self.get_serializer(queryset, many=True, context=context)
        
        return Response({
            'message': 'Cursos recuperados com sucesso',
            'data': serializer.data
        })


class CourseDetailView(generics.RetrieveAPIView):
    """
    Retrieve course details for students.
    
    GET /api/v1/student/video-courses/{id}/ - Get course details
    """
    queryset = Course.objects.filter(status='Published', course_type='video')
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'courseId'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Get fresh instance with optimizations based on query parameters
        include_sections = request.query_params.get('include_sections', 'true').lower() == 'true'
        include_enrollments = request.query_params.get('include_enrollments', 'true').lower() == 'true'
        include_chapters = request.query_params.get('include_chapters', 'true').lower() == 'true'
        include_comments = request.query_params.get('include_chapter_comments', 'false').lower() == 'true'
        
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
        
        serializer = self.get_serializer(instance, context=context)
        
        return Response({
            'message': 'Curso recuperado com sucesso',
            'data': serializer.data
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_transaction(request):
    """
    Create transaction and enroll user in course.
    
    POST /api/v1/courses/transactions/create/
    
    Maps to Express: POST /transactions
    """
    serializer = TransactionCreateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    with transaction.atomic():
        # Create transaction
        new_transaction = serializer.save()
        
        # Create enrollment
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
    enrollments = CourseEnrollment.objects.filter(user=user).select_related('course')
    courses = [enrollment.course for enrollment in enrollments 
              if enrollment.course.course_type == 'video' and enrollment.course.status == 'Published']
    
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

class CourseSectionListView(generics.ListAPIView):
    """
    List sections for a published course.
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


class CourseSectionDetailView(generics.RetrieveAPIView):
    """
    Retrieve a course section details.
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


# Chapter Views (Read-only for students)

class ChapterListView(generics.ListAPIView):
    """
    List chapters for a section.
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


class ChapterDetailView(generics.RetrieveAPIView):
    """
    Retrieve chapter details.
    """
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'chapterId'
    
    def get_queryset(self):
        return Chapter.objects.filter(
            section__course__status='Published',
            section__course__course_type='video'
        ).select_related('section', 'section__course')


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

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_stripe_payment_intent(request):
    """
    Create Stripe payment intent.
    
    POST /api/v1/courses/payments/stripe/intent/
    
    Maps to Express: POST /transactions/stripe-payment-intent
    """
    amount = request.data.get('amount', 0)
    
    if not amount or amount <= 0:
        amount = 50  # Default minimum amount
    
    try:
        import stripe
        from django.conf import settings
        
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        
        if not stripe.api_key:
            return Response({
                'error': 'Stripe não configurado'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='eur',
            automatic_payment_methods={'enabled': True}
        )
        
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
        return Response({
            'error': f'Erro ao criar intenção de pagamento: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# 🆕 PHASE 1 BRIDGE ENDPOINTS - Chapter Enhancement API
# =============================================================================

class ChapterResourceListView(generics.ListAPIView):
    """
    List resources for a chapter (read-only for students).
    
    GET /api/v1/student/video-courses/chapters/{chapterId}/resources/
    
    Query Parameters for GET:
    - page: Page number (default: 1)  
    - page_size: Items per page (default: 20, max: 100)
    - ordering: Sort order (order, -created_at, resource_type)
    """
    serializer_class = ChapterResourceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        queryset = ChapterResource.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video'
        )
        queryset = queryset.select_related('chapter', 'created_by')
        return optimize_paginated_queryset(queryset, self.request, 'order')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Recursos do capítulo recuperados com sucesso',
            'data': serializer.data
        })


class ChapterResourceDetailView(generics.RetrieveAPIView):
    """
    Retrieve a chapter resource (read-only for students).
    
    GET /api/v1/student/video-courses/chapters/{chapterId}/resources/{resourceId}/
    """
    serializer_class = ChapterResourceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'resourceId'
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterResource.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video'
        )
    
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


class ChapterQuizListView(generics.ListAPIView):
    """
    Get quiz for a chapter (read-only for students).
    
    GET /api/v1/student/video-courses/chapters/{chapterId}/quiz/
    """
    serializer_class = ChapterQuizSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video',
            is_active=True
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        if not queryset.exists():
            return Response({
                'message': 'Nenhum quiz encontrado para este capítulo',
                'data': None
            })
        
        # Should be only one quiz per chapter
        quiz = queryset.first()
        serializer = self.get_serializer(quiz)
        
        return Response({
            'message': 'Quiz do capítulo recuperado com sucesso',
            'data': serializer.data
        })


class ChapterQuizDetailView(generics.RetrieveAPIView):
    """
    Retrieve a chapter quiz (read-only for students).
    
    GET /api/v1/student/video-courses/chapters/{chapterId}/quiz/{quizId}/
    """
    serializer_class = ChapterQuizSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'quizId'
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(
            chapter__id=chapter_id,
            chapter__section__course__status='Published',
            chapter__section__course__course_type='video',
            is_active=True
        )
    
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
        
        # Get the chapter quiz
        try:
            chapter_quiz = ChapterQuiz.objects.get(chapter__id=chapter_id)
        except ChapterQuiz.DoesNotExist:
            return StudentQuizAttempt.objects.none()
        
        # Students see only their attempts, teachers see all attempts
        if self.request.user.role == 'teacher' and chapter_quiz.chapter.section.course.teacher == self.request.user:
            return StudentQuizAttempt.objects.filter(chapter_quiz=chapter_quiz).order_by('-created_at')
        else:
            return StudentQuizAttempt.objects.filter(
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