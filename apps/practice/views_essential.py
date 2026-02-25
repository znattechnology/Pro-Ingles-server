"""
Essential Practice Views - Views that are NOT duplicated in the new API structure.

These views remain here because they are:
1. Teacher-specific functionality not in student API
2. Legacy endpoints that still need to work

All other views have been migrated to:
- apps/courses/api/student/practice_courses/views.py
- apps/courses/api/teacher/practice_courses/views.py
"""

import logging
from rest_framework import status as status_module
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course
from .permissions import IsTeacher
from .throttling import CourseCreationThrottle

logger = logging.getLogger(__name__)


class CreateCourseView(APIView):
    """
    POST /api/v1/practice/courses/create/

    Create a new course for practice laboratory.

    SECURITY: Only teachers can create courses.
    Double-checked with permission class and manual validation inside post().
    Rate limited to prevent excessive course creation.
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    throttle_classes = [CourseCreationThrottle]

    def post(self, request):
        """
        DEFENSIVE PROGRAMMING: Create a new course with comprehensive validation
        """
        try:
            # Validate user authentication
            if not request.user or not request.user.is_authenticated:
                logger.warning("SECURITY - Unauthenticated course creation attempt")
                return Response(
                    {'error': 'Authentication required'},
                    status=status_module.HTTP_401_UNAUTHORIZED
                )

            # Validate user role
            user_role = getattr(request.user, 'role', None)
            if user_role != 'teacher':
                logger.warning(f"SECURITY - Non-teacher course creation attempt by user {getattr(request.user, 'id', 'N/A')}")
                return Response(
                    {'error': 'Only teachers can create courses'},
                    status=status_module.HTTP_403_FORBIDDEN
                )

            logger.info(f"CREATING PRACTICE COURSE - User: {request.user}")

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
                level = 'Beginner'

            # Validate status
            status = request.data.get('status', 'Draft').strip()
            valid_statuses = ['Draft', 'Published', 'Archived']
            if status not in valid_statuses:
                status = 'Draft'

            # Validate template
            template = request.data.get('template', 'general').strip()
            valid_templates = ['general', 'oil-gas', 'banking', 'technology', 'executive', 'ai-personal']
            if template not in valid_templates:
                template = 'general'

            # Extract additional teacher and metadata fields
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

            # Create the course
            course = Course.objects.create(
                title=title,
                description=description,
                category=category,
                level=level,
                status=status,
                template=template,
                teacher=request.user,
                teacherName=teacher_name or f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
                course_type='practice',
            )

            logger.info(f"Course created successfully with ID: {course.id}")

            # Prepare response
            response_data = {
                'id': str(course.id),
                'courseId': str(course.id),
                'title': course.title,
                'description': course.description,
                'category': course.category,
                'level': course.level,
                'status': course.status,
                'template': course.template,
                'image': course.image or '',
                'teacher': str(course.teacher.id),
                'teacherId': str(course.teacher.id),
                'teacherName': course.teacherName,
                'teacher_id': teacher_id or str(course.teacher.id),
                'teacher_email': teacher_email or course.teacher.email,
                'teacher_name': teacher_name or course.teacherName,
                'course_type': course.course_type,
                'created_by': created_by or str(request.user.id),
                'language': language or 'pt-BR',
                'difficulty_level': difficulty_level or level,
                'learningObjectives': learning_objectives,
                'targetAudience': target_audience,
                'hearts': hearts,
                'pointsPerChallenge': points_per_challenge,
                'passingScore': passing_score,
                'created_at': course.created_at.isoformat() if course.created_at else None,
                'updated_at': course.updated_at.isoformat() if course.updated_at else None,
            }

            return Response(response_data, status=status_module.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating course: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to create course: {str(e)}'},
                status=status_module.HTTP_500_INTERNAL_SERVER_ERROR
            )
