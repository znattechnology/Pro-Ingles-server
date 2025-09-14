"""
Serializers for the ProEnglish course management system.

This module contains all serializers for course-related models,
following the same structure and response format as the Express API.
"""

from rest_framework import serializers
from .models import (
    Course, CourseSection, Chapter, ChapterComment,
    CourseEnrollment, Transaction, UserCourseProgress, ChapterProgress,
    ChapterResource, ChapterQuiz, StudentQuizAttempt
)
from apps.users.serializers import UserProfileSerializer


class ChapterCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for chapter comments - matches Express comments structure.
    Optimized with selective fields to avoid N+1 queries.
    """
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = ChapterComment
        fields = [
            'commentId', 'text', 'timestamp', 'user', 'user_name'
        ]
        read_only_fields = ['commentId', 'timestamp', 'user_name']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    @classmethod
    def optimize_queryset(cls, queryset):
        """Optimize queryset with select_related for performance."""
        return queryset.select_related('user').order_by('-timestamp')


class ChapterSerializer(serializers.ModelSerializer):
    """
    Serializer for chapters - matches Express chapter structure.
    Optimized for performance with conditional field loading.
    """
    comments = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = [
            'chapterId', 'title', 'content', 'type', 'video', 
            'order', 'comments', 'created_at'
        ]
        read_only_fields = ['chapterId', 'created_at']
    
    def __init__(self, *args, **kwargs):
        # Allow conditional field inclusion via context
        include_comments = kwargs.get('context', {}).get('include_comments', True)
        if not include_comments:
            self.fields.pop('comments', None)
        super().__init__(*args, **kwargs)
    
    def get_comments(self, obj):
        """Get comments with optimized query."""
        if not hasattr(obj, '_prefetched_comments'):
            # If not prefetched, return empty list to avoid N+1
            return []
        
        comments = ChapterCommentSerializer.optimize_queryset(
            obj.comments.all()
        )
        return ChapterCommentSerializer(comments, many=True).data


class ChapterCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating chapters without nested data.
    """
    
    class Meta:
        model = Chapter
        fields = [
            'title', 'content', 'type', 'video', 'order'
        ]


class CourseSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for course sections - matches Express sections structure.
    Optimized with conditional chapter loading.
    """
    chapters = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSection
        fields = [
            'sectionId', 'sectionTitle', 'sectionDescription', 
            'order', 'chapters', 'created_at'
        ]
        read_only_fields = ['sectionId', 'created_at']
    
    def __init__(self, *args, **kwargs):
        # Allow conditional chapter inclusion via context
        include_chapters = kwargs.get('context', {}).get('include_chapters', True)
        if not include_chapters:
            self.fields.pop('chapters', None)
        super().__init__(*args, **kwargs)
    
    def get_chapters(self, obj):
        """Get chapters with optimized query."""
        if not hasattr(obj, '_prefetched_chapters'):
            # If not prefetched, return empty list to avoid N+1
            return []
        
        context = self.context.copy()
        context['include_comments'] = context.get('include_chapter_comments', False)
        
        return ChapterSerializer(
            obj.chapters.all().order_by('order'),
            many=True,
            context=context
        ).data


class CourseSectionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating sections without nested data.
    """
    
    class Meta:
        model = CourseSection
        fields = [
            'sectionTitle', 'sectionDescription', 'order'
        ]


class CourseListSerializer(serializers.ModelSerializer):
    """
    Serializer for course list view - lighter version without nested data.
    Optimized for performance with selective fields.
    """
    teacherId = serializers.CharField(source='teacher.id', read_only=True)
    total_enrollments = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'courseId', 'title', 'description', 'category', 'image',
            'price', 'level', 'status', 'template', 'teacher', 'teacherId', 'teacherName', 
            'total_enrollments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'courseId', 'teacher', 'teacherId', 'teacherName', 'total_enrollments',
            'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        # Remove heavy fields if not needed
        context = kwargs.get('context', {})
        fields_to_remove = []
        
        if not context.get('include_description', True):
            fields_to_remove.append('description')
        if not context.get('include_enrollment_count', False):
            fields_to_remove.append('total_enrollments')
        
        super().__init__(*args, **kwargs)
        
        for field_name in fields_to_remove:
            self.fields.pop(field_name, None)
    
    def get_total_enrollments(self, obj):
        """Get enrollment count efficiently."""
        if hasattr(obj, '_enrollment_count'):
            return obj._enrollment_count
        return getattr(obj, 'total_enrollments', 0)
    
    @classmethod
    def optimize_queryset(cls, queryset, include_enrollment_count=False):
        """Optimize queryset for list view."""
        queryset = queryset.select_related('teacher')
        
        if include_enrollment_count:
            from django.db.models import Count
            queryset = queryset.annotate(
                _enrollment_count=Count('enrollments')
            )
        
        return queryset


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for course detail view - matches Express Course response structure.
    Optimized with conditional loading and efficient queries.
    """
    teacherId = serializers.CharField(source='teacher.id', read_only=True)
    sections = serializers.SerializerMethodField()
    enrollments = serializers.SerializerMethodField()
    total_sections = serializers.SerializerMethodField()
    total_chapters = serializers.SerializerMethodField()
    total_enrollments = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'courseId', 'title', 'description', 'category', 'image',
            'price', 'level', 'status', 'template', 'teacher', 'teacherId', 'teacherName',
            'sections', 'enrollments', 'total_sections', 'total_chapters',
            'total_enrollments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'courseId', 'teacher', 'teacherId', 'teacherName', 'sections', 'enrollments',
            'total_sections', 'total_chapters', 'total_enrollments',
            'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        # Allow conditional field inclusion
        context = kwargs.get('context', {})
        fields_to_remove = []
        
        if not context.get('include_sections', True):
            fields_to_remove.append('sections')
        if not context.get('include_enrollments', True):
            fields_to_remove.append('enrollments')
        
        super().__init__(*args, **kwargs)
        
        for field_name in fields_to_remove:
            self.fields.pop(field_name, None)
    
    def get_sections(self, obj):
        """Get sections with optimized query."""
        if not hasattr(obj, '_prefetched_sections'):
            return []
        
        context = self.context.copy()
        context['include_chapters'] = context.get('include_chapters', True)
        context['include_chapter_comments'] = context.get('include_chapter_comments', False)
        
        return CourseSectionSerializer(
            obj.sections.all().order_by('order'),
            many=True,
            context=context
        ).data
    
    def get_enrollments(self, obj):
        """
        Return enrollments in the same format as Express - array of userId objects.
        Optimized to avoid N+1 queries.
        """
        if hasattr(obj, '_prefetched_enrollments'):
            return [{'userId': str(enrollment.user.id)} 
                   for enrollment in obj.enrollments.all()]
        return []
    
    def get_total_sections(self, obj):
        """Get total sections count efficiently."""
        if hasattr(obj, '_sections_count'):
            return obj._sections_count
        return getattr(obj, 'total_sections', 0)
    
    def get_total_chapters(self, obj):
        """Get total chapters count efficiently."""
        if hasattr(obj, '_chapters_count'):
            return obj._chapters_count
        return getattr(obj, 'total_chapters', 0)
    
    def get_total_enrollments(self, obj):
        """Get total enrollments count efficiently."""
        if hasattr(obj, '_enrollments_count'):
            return obj._enrollments_count
        return getattr(obj, 'total_enrollments', 0)
    
    @classmethod
    def optimize_queryset(cls, queryset, include_sections=True, include_enrollments=True):
        """Optimize queryset for detail view."""
        from django.db.models import Count
        
        # Always select related teacher
        queryset = queryset.select_related('teacher')
        
        # Add counts as annotations to avoid property calculations
        queryset = queryset.annotate(
            _sections_count=Count('sections', distinct=True),
            _chapters_count=Count('sections__chapters', distinct=True),
            _enrollments_count=Count('enrollments', distinct=True)
        )
        
        # Prefetch related objects if needed
        prefetch_list = []
        
        if include_sections:
            prefetch_list.extend([
                'sections',
                'sections__chapters',
                'sections__chapters__comments__user'
            ])
        
        if include_enrollments:
            prefetch_list.append('enrollments__user')
        
        if prefetch_list:
            from django.db.models import Prefetch
            queryset = queryset.prefetch_related(*prefetch_list)
        
        return queryset


class CourseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating courses.
    """
    
    # Make fields optional to allow creating course with minimal data
    title = serializers.CharField(required=False, default="Novo Curso")
    description = serializers.CharField(required=False, default="")
    category = serializers.CharField(required=False, default="Inglês Geral")
    level = serializers.CharField(required=False, default="Beginner")
    status = serializers.CharField(required=False, default="Draft")
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    template = serializers.CharField(required=False, default="general")
    
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'category', 'image',
            'price', 'level', 'status', 'template'
        ]
    
    def create(self, validated_data):
        # Set teacher and teacherName from authenticated user
        user = self.context['request'].user
        validated_data['teacher'] = user
        validated_data['teacherName'] = user.name or f"Professor {user.email}"
        
        # Set default values if not provided
        if 'title' not in validated_data or not validated_data['title']:
            validated_data['title'] = "Novo Curso"
        
        return super().create(validated_data)


class CourseUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating courses.
    """
    
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'category', 'image',
            'price', 'level', 'status', 'template'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for transactions - matches Express Transaction structure.
    """
    user_name = serializers.CharField(source='user.name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transactionId', 'user', 'user_name', 'course', 'course_title',
            'dateTime', 'amount', 'paymentProvider', 'created_at'
        ]
        read_only_fields = ['id', 'user_name', 'course_title', 'dateTime', 'created_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating transactions during course purchase.
    """
    courseId = serializers.UUIDField(source='course.id', write_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'transactionId', 'courseId', 'amount', 'paymentProvider'
        ]
    
    def create(self, validated_data):
        course_data = validated_data.pop('course')
        course = Course.objects.get(id=course_data['id'])
        
        validated_data['user'] = self.context['request'].user
        validated_data['course'] = course
        
        return super().create(validated_data)


class ChapterProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for chapter progress - matches Express chapter completion structure.
    """
    chapterId = serializers.CharField(source='chapter.id', read_only=True)
    
    class Meta:
        model = ChapterProgress
        fields = ['chapterId', 'completed', 'completed_at']
        read_only_fields = ['completed_at']


class UserCourseProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for user course progress - matches Express UserCourseProgress structure.
    """
    courseId = serializers.CharField(source='course.id', read_only=True)
    userId = serializers.CharField(source='user.id', read_only=True)
    sections = serializers.SerializerMethodField()
    
    class Meta:
        model = UserCourseProgress
        fields = [
            'userId', 'courseId', 'enrollmentDate', 'overallProgress',
            'sections', 'lastAccessedTimestamp'
        ]
        read_only_fields = ['userId', 'courseId', 'lastAccessedTimestamp']
    
    def get_sections(self, obj):
        """
        Return progress in the same nested structure as Express:
        sections: [{ sectionId, chapters: [{ chapterId, completed }] }]
        """
        sections_data = []
        
        # Get all sections for this course
        for section in obj.course.sections.all():
            section_data = {
                'sectionId': str(section.id),
                'chapters': []
            }
            
            # Get progress for each chapter in this section
            for chapter in section.chapters.all():
                try:
                    progress = obj.chapter_progress.get(chapter=chapter)
                    chapter_data = {
                        'chapterId': str(chapter.id),
                        'completed': progress.completed
                    }
                except ChapterProgress.DoesNotExist:
                    chapter_data = {
                        'chapterId': str(chapter.id),
                        'completed': False
                    }
                
                section_data['chapters'].append(chapter_data)
            
            sections_data.append(section_data)
        
        return sections_data


class UserCourseProgressUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user course progress.
    Accepts the same nested structure as Express.
    """
    sections = serializers.ListField(child=serializers.DictField())
    
    def update(self, instance, validated_data):
        sections_data = validated_data.get('sections', [])
        
        # Update progress for each chapter
        for section_data in sections_data:
            section_id = section_data.get('sectionId')
            chapters_data = section_data.get('chapters', [])
            
            for chapter_data in chapters_data:
                chapter_id = chapter_data.get('chapterId')
                completed = chapter_data.get('completed', False)
                
                try:
                    chapter = Chapter.objects.get(id=chapter_id)
                    progress, created = ChapterProgress.objects.get_or_create(
                        user_progress=instance,
                        chapter=chapter,
                        defaults={'completed': completed}
                    )
                    if not created:
                        progress.completed = completed
                        progress.save()
                        
                except Chapter.DoesNotExist:
                    continue
        
        # Recalculate overall progress
        total_chapters = instance.course.total_chapters
        if total_chapters > 0:
            completed_chapters = instance.chapter_progress.filter(completed=True).count()
            instance.overallProgress = (completed_chapters / total_chapters) * 100
        else:
            instance.overallProgress = 0
        
        instance.save()
        return instance


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for course enrollments.
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = CourseEnrollment
        fields = [
            'id', 'user', 'user_name', 'course', 'course_title', 
            'enrollment_date', 'created_at'
        ]
        read_only_fields = ['id', 'user_name', 'course_title', 'enrollment_date', 'created_at']


# =============================================================================
# 🆕 PHASE 1 BRIDGE SERIALIZERS - Chapter Enhancement API
# =============================================================================

class ChapterResourceSerializer(serializers.ModelSerializer):
    """
    Serializer for chapter resources - PDFs, links, videos, etc.
    """
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ChapterResource
        fields = [
            'id', 'title', 'description', 'resource_type', 'file', 'external_url',
            'file_size', 'download_count', 'order', 'is_featured',
            'created_by', 'created_by_name', 'file_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'download_count', 'created_by', 'created_by_name', 
            'file_url', 'created_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Return appropriate URL for the resource"""
        if obj.file:
            return self.context['request'].build_absolute_uri(obj.file.url) if self.context.get('request') else obj.file.url
        elif obj.external_url:
            return obj.external_url
        return None
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ChapterResourceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating chapter resources.
    """
    
    class Meta:
        model = ChapterResource
        fields = [
            'title', 'description', 'resource_type', 'file', 'external_url',
            'order', 'is_featured'
        ]
    
    def validate(self, data):
        """Ensure either file or external_url is provided"""
        if not data.get('file') and not data.get('external_url'):
            raise serializers.ValidationError(
                "Either 'file' or 'external_url' must be provided"
            )
        return data


class ChapterQuizSerializer(serializers.ModelSerializer):
    """
    Serializer for chapter quizzes - bridges to Practice Lab system.
    """
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    practice_lesson_title = serializers.CharField(source='practice_lesson.title', read_only=True, allow_null=True)
    
    class Meta:
        model = ChapterQuiz
        fields = [
            'id', 'chapter', 'chapter_title', 'practice_lesson', 'practice_lesson_title',
            'title', 'description', 'points_reward', 'hearts_cost', 'passing_score',
            'time_limit', 'max_attempts', 'total_attempts', 'total_completions',
            'average_score', 'completion_rate', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'chapter_title', 'practice_lesson_title', 'total_attempts',
            'total_completions', 'average_score', 'completion_rate',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ChapterQuizCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating chapter quizzes.
    """
    
    class Meta:
        model = ChapterQuiz
        fields = [
            'practice_lesson', 'title', 'description', 'points_reward',
            'hearts_cost', 'passing_score', 'time_limit', 'max_attempts', 'is_active'
        ]


class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer for student quiz attempts.
    """
    student_name = serializers.CharField(source='student.name', read_only=True)
    quiz_title = serializers.CharField(source='chapter_quiz.title', read_only=True)
    chapter_title = serializers.CharField(source='chapter_quiz.chapter.title', read_only=True)
    score_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = StudentQuizAttempt
        fields = [
            'id', 'student', 'student_name', 'chapter_quiz', 'quiz_title', 'chapter_title',
            'score', 'max_score', 'score_percentage', 'time_taken', 'hearts_lost',
            'points_earned', 'is_completed', 'is_passed', 'attempt_number',
            'completed_at', 'practice_progress', 'created_at'
        ]
        read_only_fields = [
            'id', 'student', 'student_name', 'quiz_title', 'chapter_title',
            'score_percentage', 'attempt_number', 'created_at'
        ]


class StudentQuizAttemptCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating student quiz attempts.
    """
    
    class Meta:
        model = StudentQuizAttempt
        fields = [
            'chapter_quiz', 'score', 'max_score', 'time_taken', 'hearts_lost',
            'points_earned', 'is_completed', 'is_passed', 'practice_progress'
        ]
    
    def create(self, validated_data):
        # Set student from request user
        validated_data['student'] = self.context['request'].user
        
        # Calculate attempt number
        chapter_quiz = validated_data['chapter_quiz']
        existing_attempts = StudentQuizAttempt.objects.filter(
            student=validated_data['student'],
            chapter_quiz=chapter_quiz
        ).count()
        validated_data['attempt_number'] = existing_attempts + 1
        
        # Set completion timestamp if completed
        if validated_data.get('is_completed', False):
            from django.utils import timezone
            validated_data['completed_at'] = timezone.now()
        
        return super().create(validated_data)