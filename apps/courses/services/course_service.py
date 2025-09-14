"""
Course management service.

This service handles all business logic related to course creation,
management, publishing, and organization.
"""

from typing import Dict, List, Optional, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .base_service import BaseService, BusinessLogicError, PermissionError, NotFoundError
from apps.courses.models import Course, CourseSection, Chapter, ChapterComment


class CourseService(BaseService):
    """
    Service for managing courses, sections, and chapters.
    
    Provides business logic for:
    - Course creation and management
    - Section and chapter organization
    - Publishing workflow
    - Access control and permissions
    """
    
    def create_course(self, course_data: Dict[str, Any]) -> Course:
        """
        Create a new course with validation and business rules.
        
        Args:
            course_data: Dictionary containing course information
            
        Returns:
            Created Course instance
            
        Raises:
            PermissionError: If user is not a teacher
            ValidationError: If course data is invalid
        """
        self.require_user()
        self.require_permission(
            self.user.role == 'teacher',
            "Only teachers can create courses"
        )
        
        # Validate required fields
        self.validate_data(course_data, ['title'])
        
        # Apply business rules
        course_data = self._apply_course_creation_rules(course_data)
        
        try:
            with transaction.atomic():
                # Create the course
                course = Course.objects.create(
                    teacher=self.user,
                    teacherName=self.user.name,
                    **course_data
                )
                
                # Create initial section if specified
                if course_data.get('create_initial_section', True):
                    self.create_section(course, {
                        'sectionTitle': 'Introduction',
                        'sectionDescription': 'Welcome to the course',
                        'order': 1
                    })
                
                self.log_action(
                    "Course created", 
                    f"Course: {course.title} (ID: {course.id})"
                )
                
                # Track event for analytics
                self.track_event('course_created', {
                    'course_id': str(course.id),
                    'title': course.title,
                    'category': course.category,
                    'level': course.level
                })
                
                return course
                
        except Exception as e:
            self.log_action("Course creation failed", str(e), "error")
            raise BusinessLogicError(f"Failed to create course: {str(e)}")
    
    def update_course(self, course_id: str, course_data: Dict[str, Any]) -> Course:
        """
        Update an existing course with business rule validation.
        
        Args:
            course_id: ID of the course to update
            course_data: Updated course data
            
        Returns:
            Updated Course instance
        """
        course = self._get_course_with_permission(course_id, 'edit')
        
        # Apply business rules for updates
        course_data = self._apply_course_update_rules(course, course_data)
        
        try:
            with transaction.atomic():
                # Update course fields
                for field, value in course_data.items():
                    if hasattr(course, field):
                        setattr(course, field, value)
                
                course.save()
                
                self.log_action(
                    "Course updated",
                    f"Course: {course.title} (ID: {course.id})"
                )
                
                # Invalidate related caches
                self.invalidate_cache(f"course:{course.id}:*")
                
                return course
                
        except Exception as e:
            self.log_action("Course update failed", str(e), "error")
            raise BusinessLogicError(f"Failed to update course: {str(e)}")
    
    def publish_course(self, course_id: str) -> Course:
        """
        Publish a course after validation checks.
        
        Args:
            course_id: ID of the course to publish
            
        Returns:
            Published Course instance
        """
        course = self._get_course_with_permission(course_id, 'edit')
        
        # Validate course is ready for publishing
        self._validate_course_for_publishing(course)
        
        try:
            with transaction.atomic():
                course.status = 'Published'
                course.save()
                
                self.log_action(
                    "Course published",
                    f"Course: {course.title} (ID: {course.id})"
                )
                
                # Send notifications to followers/interested users
                self._notify_course_published(course)
                
                # Track publishing event
                self.track_event('course_published', {
                    'course_id': str(course.id),
                    'title': course.title,
                    'teacher_id': str(course.teacher.id)
                })
                
                return course
                
        except Exception as e:
            self.log_action("Course publishing failed", str(e), "error")
            raise BusinessLogicError(f"Failed to publish course: {str(e)}")
    
    def create_section(self, course: Course, section_data: Dict[str, Any]) -> CourseSection:
        """
        Create a new section within a course.
        
        Args:
            course: Course to add the section to
            section_data: Section information
            
        Returns:
            Created CourseSection instance
        """
        self.require_permission(
            course.teacher == self.user,
            "Only the course teacher can add sections"
        )
        
        # Validate required fields
        self.validate_data(section_data, ['sectionTitle'])
        
        # Set default order if not provided
        if 'order' not in section_data:
            last_section = course.sections.order_by('-order').first()
            section_data['order'] = (last_section.order + 1) if last_section else 1
        
        try:
            section = CourseSection.objects.create(
                course=course,
                **section_data
            )
            
            self.log_action(
                "Section created",
                f"Section: {section.sectionTitle} in {course.title}"
            )
            
            return section
            
        except Exception as e:
            raise BusinessLogicError(f"Failed to create section: {str(e)}")
    
    def create_chapter(self, section: CourseSection, chapter_data: Dict[str, Any]) -> Chapter:
        """
        Create a new chapter within a section.
        
        Args:
            section: Section to add the chapter to
            chapter_data: Chapter information
            
        Returns:
            Created Chapter instance
        """
        self.require_permission(
            section.course.teacher == self.user,
            "Only the course teacher can add chapters"
        )
        
        # Validate required fields
        self.validate_data(chapter_data, ['title', 'content', 'type'])
        
        # Set default order if not provided
        if 'order' not in chapter_data:
            last_chapter = section.chapters.order_by('-order').first()
            chapter_data['order'] = (last_chapter.order + 1) if last_chapter else 1
        
        try:
            chapter = Chapter.objects.create(
                section=section,
                **chapter_data
            )
            
            self.log_action(
                "Chapter created",
                f"Chapter: {chapter.title} in {section.course.title}"
            )
            
            return chapter
            
        except Exception as e:
            raise BusinessLogicError(f"Failed to create chapter: {str(e)}")
    
    def reorder_sections(self, course_id: str, section_orders: List[Dict[str, Any]]) -> List[CourseSection]:
        """
        Reorder sections within a course.
        
        Args:
            course_id: ID of the course
            section_orders: List of {'section_id': str, 'order': int}
            
        Returns:
            List of reordered sections
        """
        course = self._get_course_with_permission(course_id, 'edit')
        
        try:
            with transaction.atomic():
                sections = []
                for order_data in section_orders:
                    section = CourseSection.objects.get(
                        id=order_data['section_id'],
                        course=course
                    )
                    section.order = order_data['order']
                    section.save()
                    sections.append(section)
                
                self.log_action(
                    "Sections reordered",
                    f"Course: {course.title}, Sections: {len(sections)}"
                )
                
                return sections
                
        except Exception as e:
            raise BusinessLogicError(f"Failed to reorder sections: {str(e)}")
    
    def delete_course(self, course_id: str) -> bool:
        """
        Delete a course with proper validation and cleanup.
        
        Args:
            course_id: ID of the course to delete
            
        Returns:
            True if deletion was successful
        """
        course = self._get_course_with_permission(course_id, 'delete')
        
        # Check if course can be safely deleted
        self._validate_course_for_deletion(course)
        
        try:
            with transaction.atomic():
                course_title = course.title
                course.delete()
                
                self.log_action(
                    "Course deleted",
                    f"Course: {course_title} (ID: {course_id})"
                )
                
                # Invalidate related caches
                self.invalidate_cache(f"course:{course_id}:*")
                
                return True
                
        except Exception as e:
            self.log_action("Course deletion failed", str(e), "error")
            raise BusinessLogicError(f"Failed to delete course: {str(e)}")
    
    def get_course_analytics(self, course_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a course.
        
        Args:
            course_id: ID of the course
            
        Returns:
            Dictionary with course analytics
        """
        course = self._get_course_with_permission(course_id, 'view')
        
        # Check cache first
        cache_key = self.cache_key('course_analytics', course_id)
        cached_analytics = self.get_from_cache(cache_key)
        if cached_analytics:
            return cached_analytics
        
        analytics = {
            'course_id': course_id,
            'title': course.title,
            'status': course.status,
            'created_at': course.created_at,
            'total_sections': course.total_sections,
            'total_chapters': course.total_chapters,
            'total_enrollments': course.total_enrollments,
            'completion_rate': self._calculate_completion_rate(course),
            'average_progress': self._calculate_average_progress(course),
            'engagement_metrics': self._get_engagement_metrics(course),
        }
        
        # Cache for 15 minutes
        self.set_cache(cache_key, analytics, 900)
        
        return analytics
    
    def _get_course_with_permission(self, course_id: str, action: str) -> Course:
        """Get course with permission validation."""
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise NotFoundError(f"Course with ID {course_id} not found")
        
        if action in ['edit', 'delete']:
            self.require_permission(
                course.teacher == self.user,
                f"Only the course teacher can {action} this course"
            )
        elif action == 'view' and course.status == 'Draft':
            self.require_permission(
                course.teacher == self.user,
                "Only the teacher can view draft courses"
            )
        
        return course
    
    def _apply_course_creation_rules(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules for course creation."""
        # Set default values
        defaults = {
            'status': 'Draft',
            'level': 'Beginner',
            'category': 'Inglês Geral',
            'price': 0,
            'template': 'general'
        }
        
        for key, value in defaults.items():
            if key not in course_data:
                course_data[key] = value
        
        # Validate price
        if course_data.get('price', 0) < 0:
            raise ValidationError("Course price cannot be negative")
        
        return course_data
    
    def _apply_course_update_rules(self, course: Course, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply business rules for course updates."""
        # Don't allow changing teacher
        if 'teacher' in update_data:
            del update_data['teacher']
        
        # If course is published, restrict certain changes
        if course.status == 'Published':
            restricted_fields = ['price']  # Price changes need special handling
            for field in restricted_fields:
                if field in update_data and update_data[field] != getattr(course, field):
                    self.log_action(
                        "Restricted field update attempt",
                        f"Field: {field}, Course: {course.title}",
                        "warning"
                    )
        
        return update_data
    
    def _validate_course_for_publishing(self, course: Course):
        """Validate that a course is ready for publishing."""
        errors = []
        
        # Must have at least one section
        if not course.sections.exists():
            errors.append("Course must have at least one section")
        
        # Must have at least one chapter
        if course.total_chapters == 0:
            errors.append("Course must have at least one chapter")
        
        # Must have description
        if not course.description.strip():
            errors.append("Course must have a description")
        
        if errors:
            raise ValidationError("Course cannot be published: " + "; ".join(errors))
    
    def _validate_course_for_deletion(self, course: Course):
        """Validate that a course can be safely deleted."""
        # Check if there are active enrollments
        if course.enrollments.filter(is_active=True).exists():
            raise BusinessLogicError(
                "Cannot delete course with active enrollments. "
                "Please contact support for assistance."
            )
    
    def _notify_course_published(self, course: Course):
        """Send notifications when a course is published."""
        # This would integrate with a notification system
        # For now, just log the intent
        self.log_action(
            "Publishing notifications sent",
            f"Course: {course.title}"
        )
    
    def _calculate_completion_rate(self, course: Course) -> float:
        """Calculate course completion rate."""
        total_enrollments = course.enrollments.count()
        if total_enrollments == 0:
            return 0.0
        
        completed_enrollments = course.user_progress.filter(
            overallProgress__gte=100.0
        ).count()
        
        return round((completed_enrollments / total_enrollments) * 100, 2)
    
    def _calculate_average_progress(self, course: Course) -> float:
        """Calculate average progress across all students."""
        from django.db.models import Avg
        
        result = course.user_progress.aggregate(avg_progress=Avg('overallProgress'))
        return round(result.get('avg_progress') or 0.0, 2)
    
    def _get_engagement_metrics(self, course: Course) -> Dict[str, Any]:
        """Get engagement metrics for the course."""
        from django.db.models import Count, Avg
        from datetime import timedelta
        
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        return {
            'recent_activity': course.user_progress.filter(
                lastAccessedTimestamp__gte=week_ago
            ).count(),
            'average_time_spent': 0,  # Would need time tracking implementation
            'comment_count': ChapterComment.objects.filter(
                chapter__section__course=course
            ).count(),
            'engagement_score': 85  # Placeholder - would calculate based on various factors
        }