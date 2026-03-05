"""
Views for the ProEnglish course management system.

This module contains all API views for course-related operations,
maintaining the same endpoints and response format as the Express API.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from apps.courses.api.teacher.decorators import teacher_required, course_owner_required
from rest_framework.views import APIView
from django.db import models, transaction
from django.db.models import Q

from apps.courses.models import (
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
from apps.courses.pagination import (
    CourseListPagination, TransactionListPagination, CommentListPagination,
    QuizAttemptPagination, StandardResultsSetPagination, optimize_paginated_queryset
)


class CourseListCreateView(generics.ListCreateAPIView):
    """
    List courses or create new course.
    
    GET /api/v1/courses/ - List all published courses (public)
    POST /api/v1/courses/ - Create new course (teachers only)
    
    Maps to Express: GET /courses and POST /courses
    
    Query Parameters for GET:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 12, max: 100)
    - category: Filter by category ('all' for no filter)
    - ordering: Sort order (-created_at, title, price, level)
    - include_description: Include description field (default: true)
    - include_enrollment_count: Include enrollment count (default: false)
    """
    serializer_class = CourseListSerializer
    pagination_class = CourseListPagination
    
    def get_permissions(self):
        # Teacher endpoint requires authentication AND teacher role
        return [permissions.IsAuthenticated()]
    
    def check_teacher_permission(self):
        """Check if user is a teacher, raise PermissionDenied if not."""
        if not self.request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("Authentication required")
        
        if getattr(self.request.user, 'role', None) != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas professores podem acessar este endpoint")
    
    def get_queryset(self):
        # Teacher endpoints require teacher role
        self.check_teacher_permission()
        
        # Teachers see only their own VIDEO courses (Draft + Published)
        queryset = Course.objects.filter(teacher=self.request.user, course_type='video')
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🎥 VIDEO TEACHER - Found {queryset.count()} video courses for teacher {self.request.user.email}")
        
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
        
        return optimize_paginated_queryset(queryset, self.request, '-created_at')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseCreateSerializer
        return CourseListSerializer
    
    def perform_create(self, serializer):
        # Check if user is a teacher
        if self.request.user.role != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas professores podem criar cursos")
        
        # Ensure video courses are created with course_type='video'
        serializer.save(teacher=self.request.user, course_type='video')
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        
        # Return course with full details
        response_serializer = CourseDetailSerializer(course, context={'request': request})
        
        return Response({
            'message': 'Curso criado com sucesso',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Teacher course management - return all courses without pagination
        context = {'request': request}
        context['include_description'] = request.query_params.get('include_description', 'true').lower() == 'true'
        context['include_enrollment_count'] = request.query_params.get('include_enrollment_count', 'false').lower() == 'true'
        
        serializer = self.get_serializer(queryset, many=True, context=context)
        
        return Response({
            'message': 'Cursos recuperados com sucesso',
            'data': serializer.data
        })


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a course.
    
    GET /api/v1/courses/{id}/ - Get course details (public)
    PUT /api/v1/courses/{id}/ - Update course (teacher only)
    DELETE /api/v1/courses/{id}/ - Delete course (teacher only)
    
    Maps to Express: GET/PUT/DELETE /courses/:id
    """
    # Base queryset - optimization handled by serializer
    queryset = Course.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'courseId'
    
    def get_permissions(self):
        # Teacher endpoints require authentication for ALL methods
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CourseUpdateSerializer
        return CourseDetailSerializer
    
    def check_object_permissions(self, request, obj):
        # For teacher endpoints, check teacher role first
        if getattr(request.user, 'role', None) != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas professores podem acessar este endpoint")
        
        # For all operations, verify ownership
        if obj.teacher != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor proprietário pode acessar este curso")
    
    def retrieve(self, request, *args, **kwargs):
        # Get base queryset and apply optimizations
        instance = self.get_object()
        
        # Get fresh instance with optimizations based on query parameters
        include_sections = request.query_params.get('include_sections', 'true').lower() == 'true'
        include_enrollments = request.query_params.get('include_enrollments', 'true').lower() == 'true'
        include_chapters = request.query_params.get('include_chapters', 'true').lower() == 'true'
        include_comments = request.query_params.get('include_chapter_comments', 'false').lower() == 'true'
        
        # Re-fetch with optimizations
        optimized_queryset = CourseDetailSerializer.optimize_queryset(
            Course.objects.filter(id=instance.id),
            include_sections=include_sections,
            include_enrollments=include_enrollments
        )
        instance = optimized_queryset.first()
        
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
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        
        # Return updated course with full details
        response_serializer = CourseDetailSerializer(course, context={'request': request})
        
        return Response({
            'message': 'Curso atualizado com sucesso',
            'data': response_serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        course_title = instance.title
        self.perform_destroy(instance)
        
        return Response({
            'message': f'Curso "{course_title}" deletado com sucesso'
        }, status=status.HTTP_200_OK)


# Transaction creation moved to student API


class TransactionListView(generics.ListAPIView):
    """
    List transactions for teacher's courses (analytics).
    
    GET /api/v1/teacher/video-courses/transactions/
    
    Teachers can see transactions for their courses to track sales.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 15, max: 50)
    - courseId: Filter by specific course
    - ordering: Sort order (-dateTime, amount, paymentProvider)
    """
    serializer_class = TransactionSerializer
    pagination_class = TransactionListPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def check_teacher_permission(self):
        """Check if user is a teacher, raise PermissionDenied if not."""
        if not self.request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("Authentication required")
        
        if getattr(self.request.user, 'role', None) != 'teacher':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas professores podem acessar este endpoint")
    
    def get_queryset(self):
        # Check teacher permission
        self.check_teacher_permission()
        
        # Get transactions for teacher's video courses only
        course_id = self.request.query_params.get('courseId')
        
        if course_id:
            # Filter by specific course if provided (must be teacher's course)
            queryset = Transaction.objects.filter(
                course_id=course_id,
                course__teacher=self.request.user,
                course__course_type='video'
            )
        else:
            # All transactions for teacher's video courses
            queryset = Transaction.objects.filter(
                course__teacher=self.request.user,
                course__course_type='video'
            )
        
        # Optimize queries
        queryset = queryset.select_related('user', 'course')
        
        return optimize_paginated_queryset(queryset, self.request, '-dateTime')
    
    def list(self, request, *args, **kwargs):
        """Add transaction summary to response context for teacher analytics."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate summary for teacher's course sales
        from django.db.models import Sum, Count
        summary = queryset.aggregate(
            total_revenue=Sum('amount'),
            total_sales=Count('id')
        )
        
        # Add summary to request for pagination response
        request.transaction_summary = {
            'total_revenue': summary['total_revenue'] or 0,
            'total_sales': summary['total_sales'] or 0
        }
        
        return super().list(request, *args, **kwargs)


# User enrolled courses moved to student API


# User course progress moved to student API


# Update user course progress moved to student API


# Course Section Management Views

class CourseSectionListCreateView(generics.ListCreateAPIView):
    """
    List sections for a course or create new section.
    """
    serializer_class = CourseSectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        course_id = self.kwargs['courseId']
        include_comments = self.request.query_params.get('include_comments', 'false').lower() == 'true'
        
        queryset = CourseSection.objects.filter(course__id=course_id)
        
        # Optimize based on requirements
        if include_comments:
            queryset = queryset.prefetch_related('chapters__comments__user')
        else:
            queryset = queryset.prefetch_related('chapters')
        
        return queryset.order_by('order')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseSectionCreateSerializer
        return CourseSectionSerializer
    
    def perform_create(self, serializer):
        course_id = self.kwargs['courseId']
        course = get_object_or_404(Course, id=course_id)

        # Check if user owns this course
        if course.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode adicionar seções")

        # Auto-set order to next available position if not provided
        if not serializer.validated_data.get('order'):
            max_order = CourseSection.objects.filter(course=course).aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            serializer.save(course=course, order=max_order + 1)
        else:
            serializer.save(course=course)


class CourseSectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a course section.
    """
    # Base queryset - optimization handled by views and serializers
    queryset = CourseSection.objects.select_related('course', 'course__teacher')
    serializer_class = CourseSectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'sectionId'
    
    def check_object_permissions(self, request, obj):
        if obj.course.teacher != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode editar seções")


# Chapter Management Views

class ChapterListCreateView(generics.ListCreateAPIView):
    """
    List chapters for a section or create new chapter.
    """
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        section_id = self.kwargs['sectionId']
        return Chapter.objects.filter(section__id=section_id).order_by('order')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChapterCreateSerializer
        return ChapterSerializer
    
    def perform_create(self, serializer):
        section_id = self.kwargs['sectionId']
        section = get_object_or_404(CourseSection, id=section_id)

        # Check if user owns this course
        if section.course.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode adicionar capítulos")

        # Auto-set order to next available position if not provided
        if not serializer.validated_data.get('order'):
            max_order = Chapter.objects.filter(section=section).aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            serializer.save(section=section, order=max_order + 1)
        else:
            serializer.save(section=section)


class ChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a chapter.
    """
    # Base queryset - selective optimization in views
    queryset = Chapter.objects.select_related(
        'section', 
        'section__course', 
        'section__course__teacher'
    )
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'chapterId'
    
    def check_object_permissions(self, request, obj):
        if obj.section.course.teacher != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode editar capítulos")


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

# Stripe payment intent moved to student API


# =============================================================================
# AWS S3 VIDEO UPLOAD ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@teacher_required
@course_owner_required
def get_upload_video_url(request, courseId, sectionId, chapterId):
    """
    Generate presigned URL for video upload to S3.
    
    POST /api/v1/courses/{courseId}/sections/{sectionId}/chapters/{chapterId}/get-upload-url/
    
    Maps to Express: POST /:courseId/sections/:sectionId/chapters/:chapterId/get-upload-url
    """
    # Debug logging
    print(f"🔍 Django DEBUG - Request data: {request.data}")
    print(f"🔍 Django DEBUG - Content type: {request.content_type}")
    print(f"🔍 Django DEBUG - Method: {request.method}")
    
    # Try both camelCase and snake_case (RTK Query may be converting)
    fileName = request.data.get('fileName')
    if not fileName:
        fileName = request.data.get('file_name')
    
    fileType = request.data.get('fileType') 
    if not fileType:
        fileType = request.data.get('file_type')
    
    print(f"🔍 Django DEBUG - Extracted fileName: '{fileName}', fileType: '{fileType}'")
    
    if not fileName or not fileType:
        return Response({
            'message': 'O nome e o tipo do ficheiro são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Course ownership is already verified by @course_owner_required decorator
        course = get_object_or_404(Course, id=courseId)
        
        import boto3
        import uuid
        from django.conf import settings
        from botocore.exceptions import ClientError
        
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            return Response({
                'error': 'Configuração S3 incompleta'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Generate unique ID and S3 key (same pattern as Express)
        unique_id = str(uuid.uuid4())
        s3_key = f'videos/{unique_id}/{fileName}'
        
        # Generate presigned URL for PUT operation
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': fileType,
            },
            ExpiresIn=3600  # 1 hour expiration
        )
        
        # Generate final video URL (using CloudFront if available)
        if settings.AWS_CLOUDFRONT_DOMAIN:
            video_url = f"{settings.AWS_CLOUDFRONT_DOMAIN}/videos/{unique_id}/{fileName}"
        else:
            video_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/videos/{unique_id}/{fileName}"
        
        return Response({
            'message': 'URL de upload gerado com sucesso',
            'data': {
                'uploadUrl': upload_url,
                'videoUrl': video_url
            }
        })
        
    except ClientError as e:
        return Response({
            'error': f'Erro S3: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except ImportError:
        return Response({
            'error': 'Biblioteca boto3 não instalada'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': f'Erro ao gerar URL de upload: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@teacher_required
@course_owner_required
def get_resource_upload_url(request, courseId, sectionId, chapterId):
    """
    Generate presigned URL for resource upload to S3.
    
    POST /api/v1/courses/{courseId}/sections/{sectionId}/chapters/{chapterId}/get-resource-upload-url/
    """
    # Debug logging
    print(f"🔍 Django DEBUG - Resource upload request data: {request.data}")
    print(f"🔍 Django DEBUG - Content type: {request.content_type}")
    print(f"🔍 Django DEBUG - Method: {request.method}")
    
    # Try both camelCase and snake_case (RTK Query may be converting)
    fileName = request.data.get('fileName')
    if not fileName:
        fileName = request.data.get('file_name')
    
    fileType = request.data.get('fileType') 
    if not fileType:
        fileType = request.data.get('file_type')
    
    resourceType = request.data.get('resourceType', 'PDF')
    if not resourceType:
        resourceType = request.data.get('resource_type', 'PDF')
        
    print(f"🔍 Django DEBUG - Extracted fileName: '{fileName}', fileType: '{fileType}', resourceType: '{resourceType}'")
    
    if not fileName or not fileType:
        return Response({
            'message': 'O nome e o tipo do ficheiro são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Course ownership is already verified by @course_owner_required decorator
        course = get_object_or_404(Course, id=courseId)
        
        import boto3
        import uuid
        from django.conf import settings
        from botocore.exceptions import ClientError
        
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            return Response({
                'error': 'Configuração S3 incompleta'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Generate unique ID and S3 key based on resource type
        unique_id = str(uuid.uuid4())
        
        # Determine folder based on resource type
        resource_folder_map = {
            'PDF': 'documents',
            'AUDIO': 'audio', 
            'VIDEO': 'videos',
            'IMAGE': 'images',
            'CODE': 'code',
            'WORKSHEET': 'worksheets'
        }
        folder = resource_folder_map.get(resourceType, 'resources')
        
        s3_key = f'chapter_resources/{folder}/{unique_id}/{fileName}'
        
        # Generate presigned URL for PUT operation
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': fileType,
            },
            ExpiresIn=3600  # 1 hour expiration
        )
        
        # Generate final resource URL (using CloudFront if available)
        if settings.AWS_CLOUDFRONT_DOMAIN:
            resource_url = f"{settings.AWS_CLOUDFRONT_DOMAIN}/chapter_resources/{folder}/{unique_id}/{fileName}"
        else:
            resource_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/chapter_resources/{folder}/{unique_id}/{fileName}"
        
        return Response({
            'message': 'URL de upload de recurso gerado com sucesso',
            'data': {
                'uploadUrl': upload_url,
                'resourceUrl': resource_url,
                'resourceType': resourceType
            }
        })
        
    except ClientError as e:
        return Response({
            'error': f'Erro S3: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except ImportError:
        return Response({
            'error': 'Biblioteca boto3 não instalada'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': f'Erro ao gerar URL de upload de recurso: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@teacher_required
@course_owner_required
def upload_course_image(request, courseId):
    """
    Upload course cover image to S3.
    
    POST /api/v1/courses/{courseId}/upload-image/
    
    Handles image upload similar to Express multer approach but with S3 storage
    """
    print(f"🖼️ Upload image request for course: {courseId}")
    print(f"   User: {request.user}")
    print(f"   Files in request: {list(request.FILES.keys())}")
    
    if 'image' not in request.FILES:
        print("❌ No image file in request")
        return Response({
            'message': 'Nenhuma imagem fornecida'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        print("📝 Step 1: Verify course ownership")
        # Course ownership is already verified by @course_owner_required decorator
        course = get_object_or_404(Course, id=courseId)
        print(f"   Found course: {course.title}")
        print(f"   Course teacher: {course.teacher}")
        print(f"   Request user: {request.user}")
        
        print("📝 Step 2: Get image file")
        image_file = request.FILES['image']
        print(f"   Image file: {image_file.name}")
        print(f"   Content type: {image_file.content_type}")
        print(f"   Size: {image_file.size} bytes")
        
        print("📝 Step 3: Validate image file")
        # Validate image file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            print(f"❌ Invalid file type: {image_file.content_type}")
            return Response({
                'message': 'Tipo de arquivo não suportado. Use JPG, PNG ou WebP.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check file size (max 2MB)
        if image_file.size > 2 * 1024 * 1024:
            print(f"❌ File too large: {image_file.size} bytes")
            return Response({
                'message': 'Arquivo muito grande. Máximo 2MB.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print("📝 Step 4: Import libraries and check settings")
        import boto3
        import uuid
        from django.conf import settings
        from botocore.exceptions import ClientError
        
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            print("❌ S3 configuration incomplete")
            return Response({
                'error': 'Configuração S3 incompleta'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        print("📝 Step 5: Create S3 client")
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        print("✅ S3 client created successfully")
        
        print("📝 Step 6: Generate filename and upload to S3")
        # Generate unique filename
        file_extension = image_file.name.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        s3_key = f'courses/images/{unique_filename}'
        
        print(f"   Generated filename: {unique_filename}")
        print(f"   S3 key: {s3_key}")
        
        # Upload file to S3
        print("📤 Uploading to S3...")
        s3_client.upload_fileobj(
            image_file,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': image_file.content_type,
                'CacheControl': 'max-age=86400'
            }
        )
        print("✅ Upload to S3 successful")
        
        # Generate final image URL
        if settings.AWS_CLOUDFRONT_DOMAIN:
            image_url = f"{settings.AWS_CLOUDFRONT_DOMAIN}/courses/images/{unique_filename}"
        else:
            image_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/courses/images/{unique_filename}"
        
        # Delete old image if exists
        if course.image:
            try:
                # Extract key from old URL
                old_key = course.image.split('/')[-2:]  # Get last 2 parts: ['images', 'filename.jpg']
                if len(old_key) == 2 and old_key[0] == 'images':
                    old_s3_key = f'courses/images/{old_key[1]}'
                    s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=old_s3_key)
            except Exception as e:
                # Log but don't fail the request
                print(f"Failed to delete old image: {e}")
        
        # Update course with new image URL
        course.image = image_url
        course.save()
        
        return Response({
            'message': 'Imagem do curso atualizada com sucesso',
            'data': {
                'imageUrl': image_url,
                'course': CourseDetailSerializer(course, context={'request': request}).data
            }
        })
        
    except ClientError as e:
        return Response({
            'error': f'Erro S3: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except ImportError:
        return Response({
            'error': 'Biblioteca boto3 não instalada'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': f'Erro ao fazer upload da imagem: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@teacher_required
@course_owner_required
def get_course_image_upload_url(request, courseId):
    """
    Generate presigned URL for course image upload to S3.

    POST /api/v1/teacher/video-courses/{courseId}/get-image-upload-url/

    Similar to video upload but for course cover images.
    Uses decorators for proper authentication and ownership verification.
    """
    print(f"🖼️ Course image upload URL request for course: {courseId}")
    print(f"   Request data: {request.data}")
    print(f"   User: {request.user}")

    # Get file details
    fileName = request.data.get('fileName') or request.data.get('file_name')
    fileType = request.data.get('fileType') or request.data.get('file_type')

    if not fileName or not fileType:
        return Response({
            'error': 'O nome e o tipo do ficheiro são obrigatórios'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate image file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if fileType not in allowed_types:
        return Response({
            'error': 'Tipo de arquivo não suportado. Use JPG, PNG ou WebP.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Course ownership is already verified by @course_owner_required decorator
        course = get_object_or_404(Course, id=courseId)
        print(f"   Found course: {course.title}")

        import boto3
        import uuid
        from django.conf import settings
        from botocore.exceptions import ClientError

        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_STORAGE_BUCKET_NAME]):
            print("❌ S3 configuration incomplete")
            return Response({
                'error': 'Configuração S3 incompleta no servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # Generate unique filename and S3 key
        file_extension = fileName.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        s3_key = f'courses/images/{unique_filename}'

        print(f"   Generated S3 key: {s3_key}")

        # Generate presigned URL for PUT operation
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key,
                'ContentType': fileType,
                'CacheControl': 'max-age=86400'
            },
            ExpiresIn=3600  # 1 hour expiration
        )

        # Generate final image URL (using CloudFront if available)
        if getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', ''):
            image_url = f"{settings.AWS_CLOUDFRONT_DOMAIN}/courses/images/{unique_filename}"
        else:
            image_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/courses/images/{unique_filename}"

        print(f"✅ Generated presigned URL successfully")

        return Response({
            'message': 'URL de upload de imagem gerado com sucesso',
            'data': {
                'uploadUrl': upload_url,
                'imageUrl': image_url
            }
        })

    except ClientError as e:
        print(f"❌ S3 ClientError: {str(e)}")
        return Response({
            'error': f'Erro S3: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        import traceback
        print(f"❌ Exception: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return Response({
            'error': f'Erro ao gerar URL de upload de imagem: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
@teacher_required
@course_owner_required
def update_course_image_url(request, courseId):
    """
    Update course image URL in database after successful S3 upload.

    PUT /api/v1/teacher/video-courses/{courseId}/update-image-url/
    """
    print(f"🖼️ Update course image URL for course: {courseId}")

    image_url = request.data.get('imageUrl') or request.data.get('image_url')

    if not image_url:
        return Response({
            'error': 'URL da imagem é obrigatório'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Course ownership is already verified by @course_owner_required decorator
        course = get_object_or_404(Course, id=courseId)

        # Update course image
        course.image = image_url
        course.save()

        print(f"✅ Course image updated: {image_url}")

        return Response({
            'message': 'Imagem do curso atualizada com sucesso',
            'data': {
                'imageUrl': image_url
            }
        })

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return Response({
            'error': f'Erro ao atualizar imagem do curso: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# 🆕 PHASE 1 BRIDGE ENDPOINTS - Chapter Enhancement API
# =============================================================================

class ChapterResourceListCreateView(generics.ListCreateAPIView):
    """
    List resources for a chapter or create new resource.
    
    GET /api/v1/courses/chapters/{chapterId}/resources/
    POST /api/v1/courses/chapters/{chapterId}/resources/
    
    Query Parameters for GET:
    - page: Page number (default: 1)  
    - page_size: Items per page (default: 20, max: 100)
    - ordering: Sort order (order, -created_at, resource_type)
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        queryset = ChapterResource.objects.filter(chapter__id=chapter_id)
        queryset = queryset.select_related('chapter', 'created_by')
        return optimize_paginated_queryset(queryset, self.request, 'order')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChapterResourceCreateSerializer
        return ChapterResourceSerializer
    
    def perform_create(self, serializer):
        chapter_id = self.kwargs['chapterId']
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # Check if user owns this course
        if chapter.section.course.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode adicionar recursos")
        
        serializer.save(chapter=chapter)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Recursos do capítulo recuperados com sucesso',
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()
        
        response_serializer = ChapterResourceSerializer(resource, context={'request': request})
        
        return Response({
            'message': 'Recurso criado com sucesso',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class ChapterResourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a chapter resource.
    
    GET /api/v1/courses/chapters/{chapterId}/resources/{resourceId}/
    PUT /api/v1/courses/chapters/{chapterId}/resources/{resourceId}/
    DELETE /api/v1/courses/chapters/{chapterId}/resources/{resourceId}/
    """
    serializer_class = ChapterResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'resourceId'
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterResource.objects.filter(chapter__id=chapter_id)
    
    def check_object_permissions(self, request, obj):
        if obj.chapter.section.course.teacher != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode editar recursos")
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Increment download count for GET requests (except teacher)
        if instance.chapter.section.course.teacher != request.user:
            instance.download_count += 1
            instance.save(update_fields=['download_count'])
        
        serializer = self.get_serializer(instance)
        
        return Response({
            'message': 'Recurso recuperado com sucesso',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()
        
        return Response({
            'message': 'Recurso atualizado com sucesso',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        resource_title = instance.title
        self.perform_destroy(instance)
        
        return Response({
            'message': f'Recurso "{resource_title}" deletado com sucesso'
        }, status=status.HTTP_200_OK)


class ChapterQuizListCreateView(generics.ListCreateAPIView):
    """
    Get quiz for a chapter or create new quiz.
    
    GET /api/v1/courses/chapters/{chapterId}/quiz/
    POST /api/v1/courses/chapters/{chapterId}/quiz/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(chapter__id=chapter_id)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChapterQuizCreateSerializer
        return ChapterQuizSerializer
    
    def perform_create(self, serializer):
        chapter_id = self.kwargs['chapterId']
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # Check if user owns this course
        if chapter.section.course.teacher != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode criar quizzes")
        
        # Check if quiz already exists for this chapter
        if ChapterQuiz.objects.filter(chapter=chapter).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Este capítulo já possui um quiz")
        
        serializer.save(chapter=chapter)
        
        # Enable quiz in chapter
        chapter.quiz_enabled = True
        chapter.save(update_fields=['quiz_enabled'])
    
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
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save()
        
        response_serializer = ChapterQuizSerializer(quiz, context={'request': request})
        
        return Response({
            'message': 'Quiz criado com sucesso',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class ChapterQuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a chapter quiz.
    
    GET /api/v1/courses/chapters/{chapterId}/quiz/{quizId}/
    PUT /api/v1/courses/chapters/{chapterId}/quiz/{quizId}/
    DELETE /api/v1/courses/chapters/{chapterId}/quiz/{quizId}/
    """
    serializer_class = ChapterQuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'quizId'
    
    def get_queryset(self):
        chapter_id = self.kwargs['chapterId']
        return ChapterQuiz.objects.filter(chapter__id=chapter_id)
    
    def check_object_permissions(self, request, obj):
        if obj.chapter.section.course.teacher != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Apenas o professor pode editar quizzes")
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'message': 'Quiz recuperado com sucesso',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save()
        
        return Response({
            'message': 'Quiz atualizado com sucesso',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        quiz_title = instance.title
        chapter = instance.chapter
        
        self.perform_destroy(instance)
        
        # Disable quiz in chapter
        chapter.quiz_enabled = False
        chapter.save(update_fields=['quiz_enabled'])
        
        return Response({
            'message': f'Quiz "{quiz_title}" deletado com sucesso'
        }, status=status.HTTP_200_OK)


# Student quiz attempts moved to student API


# Student quiz summary moved to student API