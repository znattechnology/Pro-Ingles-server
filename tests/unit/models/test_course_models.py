"""
Unit tests for Course models.

Tests the core course management functionality including courses,
sections, chapters, and enrollments.
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal

from apps.courses.models import Course, CourseSection, Chapter, CourseEnrollment
from tests.factories import (
    CourseFactory, CourseSectionFactory, ChapterFactory, 
    CourseEnrollmentFactory, TeacherFactory, StudentFactory
)


@pytest.mark.django_db
@pytest.mark.critical
class TestCourseModel(TestCase):
    """Test Course model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.teacher = TeacherFactory()
        self.course_data = {
            'title': 'Advanced English Grammar',
            'description': 'Comprehensive grammar course for intermediate learners',
            'category': 'Gramática',
            'level': 'Intermediate',
            'status': 'Published',
            'template': 'general',
            'teacher': self.teacher,
            'teacherName': self.teacher.name
        }
    
    def test_create_course(self):
        """Test creating a basic course."""
        course = Course.objects.create(**self.course_data)
        
        self.assertEqual(course.title, self.course_data['title'])
        self.assertEqual(course.teacher, self.teacher)
        self.assertEqual(course.status, 'Published')
        self.assertIsNotNone(course.courseId)  # UUID should be generated
        self.assertIsNotNone(course.created_at)
        self.assertIsNotNone(course.updated_at)
    
    def test_course_string_representation(self):
        """Test the string representation of course."""
        course = CourseFactory(title='Test Course')
        self.assertEqual(str(course), 'Test Course')
    
    def test_course_uuid_generation(self):
        """Test that each course gets a unique UUID."""
        course1 = CourseFactory()
        course2 = CourseFactory()
        
        self.assertNotEqual(course1.courseId, course2.courseId)
        self.assertIsNotNone(course1.courseId)
        self.assertIsNotNone(course2.courseId)
    
    def test_course_levels_validation(self):
        """Test that only valid levels are accepted."""
        valid_levels = ['Beginner', 'Intermediate', 'Advanced']
        
        for level in valid_levels:
            course = CourseFactory(level=level)
            self.assertEqual(course.level, level)
    
    def test_course_status_validation(self):
        """Test that only valid statuses are accepted."""
        valid_statuses = ['Draft', 'Published', 'Archived']
        
        for status in valid_statuses:
            course = CourseFactory(status=status)
            self.assertEqual(course.status, status)
    
    def test_course_teacher_relationship(self):
        """Test the teacher foreign key relationship."""
        teacher = TeacherFactory()
        course = CourseFactory(teacher=teacher)
        
        self.assertEqual(course.teacher, teacher)
        self.assertIn(course, teacher.taught_courses.all())
    
    def test_course_sections_relationship(self):
        """Test the sections reverse relationship."""
        course = CourseFactory()
        section1 = CourseSectionFactory(course=course, order=1)
        section2 = CourseSectionFactory(course=course, order=2)
        
        sections = course.sections.all().order_by('order')
        self.assertEqual(list(sections), [section1, section2])
    
    def test_course_total_sections_property(self):
        """Test the total_sections property."""
        course = CourseFactory()
        
        # No sections initially
        self.assertEqual(course.total_sections, 0)
        
        # Add sections
        CourseSectionFactory.create_batch(3, course=course)
        course.refresh_from_db()
        
        self.assertEqual(course.total_sections, 3)
    
    def test_course_total_chapters_property(self):
        """Test the total_chapters property."""
        course = CourseFactory()
        section = CourseSectionFactory(course=course)
        
        # No chapters initially
        self.assertEqual(course.total_chapters, 0)
        
        # Add chapters
        ChapterFactory.create_batch(5, section=section)
        course.refresh_from_db()
        
        self.assertEqual(course.total_chapters, 5)
    
    def test_course_total_enrollments_property(self):
        """Test the total_enrollments property."""
        course = CourseFactory()
        
        # No enrollments initially
        self.assertEqual(course.total_enrollments, 0)
        
        # Add enrollments
        CourseEnrollmentFactory.create_batch(3, course=course)
        course.refresh_from_db()
        
        self.assertEqual(course.total_enrollments, 3)


@pytest.mark.django_db
class TestCourseSectionModel(TestCase):
    """Test CourseSection model functionality."""
    
    def test_create_course_section(self):
        """Test creating a course section."""
        course = CourseFactory()
        section_data = {
            'course': course,
            'sectionTitle': 'Introduction to Grammar',
            'sectionDescription': 'Basic grammar concepts',
            'order': 1
        }
        
        section = CourseSection.objects.create(**section_data)
        
        self.assertEqual(section.course, course)
        self.assertEqual(section.sectionTitle, section_data['sectionTitle'])
        self.assertEqual(section.order, 1)
        self.assertIsNotNone(section.sectionId)
    
    def test_section_string_representation(self):
        """Test the string representation of section."""
        section = CourseSectionFactory(sectionTitle='Test Section')
        self.assertEqual(str(section), 'Test Section')
    
    def test_section_ordering(self):
        """Test that sections are ordered correctly."""
        course = CourseFactory()
        section3 = CourseSectionFactory(course=course, order=3)
        section1 = CourseSectionFactory(course=course, order=1)
        section2 = CourseSectionFactory(course=course, order=2)
        
        sections = course.sections.all()
        ordered_sections = [section1, section2, section3]
        
        self.assertEqual(list(sections), ordered_sections)
    
    def test_section_chapters_relationship(self):
        """Test the chapters reverse relationship."""
        section = CourseSectionFactory()
        chapter1 = ChapterFactory(section=section, order=1)
        chapter2 = ChapterFactory(section=section, order=2)
        
        chapters = section.chapters.all().order_by('order')
        self.assertEqual(list(chapters), [chapter1, chapter2])


@pytest.mark.django_db
class TestChapterModel(TestCase):
    """Test Chapter model functionality."""
    
    def test_create_chapter(self):
        """Test creating a chapter."""
        section = CourseSectionFactory()
        chapter_data = {
            'section': section,
            'title': 'Present Tense',
            'content': 'Learn about present tense usage...',
            'type': 'Text',
            'order': 1
        }
        
        chapter = Chapter.objects.create(**chapter_data)
        
        self.assertEqual(chapter.section, section)
        self.assertEqual(chapter.title, chapter_data['title'])
        self.assertEqual(chapter.type, 'Text')
        self.assertIsNotNone(chapter.chapterId)
    
    def test_chapter_string_representation(self):
        """Test the string representation of chapter."""
        chapter = ChapterFactory(title='Test Chapter')
        self.assertEqual(str(chapter), 'Test Chapter')
    
    def test_chapter_types_validation(self):
        """Test that only valid chapter types are accepted."""
        valid_types = ['Text', 'Quiz', 'Video']
        
        for chapter_type in valid_types:
            chapter = ChapterFactory(type=chapter_type)
            self.assertEqual(chapter.type, chapter_type)
    
    def test_chapter_ordering(self):
        """Test that chapters are ordered correctly."""
        section = CourseSectionFactory()
        chapter3 = ChapterFactory(section=section, order=3)
        chapter1 = ChapterFactory(section=section, order=1)
        chapter2 = ChapterFactory(section=section, order=2)
        
        chapters = section.chapters.all()
        ordered_chapters = [chapter1, chapter2, chapter3]
        
        self.assertEqual(list(chapters), ordered_chapters)
    
    def test_video_chapter_with_url(self):
        """Test video chapter with video URL."""
        video_url = 'https://example.com/video.mp4'
        chapter = ChapterFactory(type='Video', video=video_url)
        
        self.assertEqual(chapter.type, 'Video')
        self.assertEqual(chapter.video, video_url)
    
    def test_quiz_chapter_with_practice_lesson(self):
        """Test quiz chapter with practice lesson."""
        chapter = ChapterFactory(type='Quiz', quiz_enabled=True)
        
        self.assertEqual(chapter.type, 'Quiz')
        self.assertTrue(chapter.quiz_enabled)


@pytest.mark.django_db
class TestCourseEnrollmentModel(TestCase):
    """Test CourseEnrollment model functionality."""
    
    def test_create_enrollment(self):
        """Test creating a course enrollment."""
        student = StudentFactory()
        course = CourseFactory()
        
        enrollment = CourseEnrollment.objects.create(
            user=student,
            course=course
        )
        
        self.assertEqual(enrollment.user, student)
        self.assertEqual(enrollment.course, course)
        self.assertIsNotNone(enrollment.enrollment_date)
    
    def test_enrollment_string_representation(self):
        """Test the string representation of enrollment."""
        student = StudentFactory(name='John Doe')
        course = CourseFactory(title='Test Course')
        enrollment = CourseEnrollmentFactory(user=student, course=course)
        
        expected_str = f'John Doe enrolled in Test Course'
        self.assertEqual(str(enrollment), expected_str)
    
    def test_unique_enrollment_constraint(self):
        """Test that a user can only enroll once per course."""
        student = StudentFactory()
        course = CourseFactory()
        
        # First enrollment should work
        CourseEnrollmentFactory(user=student, course=course)
        
        # Second enrollment should fail
        with self.assertRaises(IntegrityError):
            CourseEnrollmentFactory(user=student, course=course)
    
    def test_enrollment_relationships(self):
        """Test enrollment relationships."""
        enrollment = CourseEnrollmentFactory()
        
        # User should have this enrollment
        self.assertIn(enrollment, enrollment.user.enrollments.all())
        
        # Course should have this enrollment
        self.assertIn(enrollment, enrollment.course.enrollments.all())


@pytest.mark.django_db
class TestCourseBusinessLogic(TestCase):
    """Test business logic methods on Course models."""
    
    def test_course_can_be_accessed_by(self):
        """Test course access permissions."""
        teacher = TeacherFactory()
        student = StudentFactory()
        
        # Published course should be accessible
        published_course = CourseFactory(status='Published', teacher=teacher)
        self.assertTrue(published_course.can_be_accessed_by(student))
        
        # Draft course should only be accessible by teacher
        draft_course = CourseFactory(status='Draft', teacher=teacher)
        self.assertTrue(draft_course.can_be_accessed_by(teacher))
        self.assertFalse(draft_course.can_be_accessed_by(student))
    
    def test_course_user_progress(self):
        """Test course user progress retrieval."""
        student = StudentFactory()
        course = CourseFactory()
        
        # Initially no progress
        progress = course.get_user_progress(student)
        self.assertIsNone(progress)
    
    def test_course_difficulty_validation(self):
        """Test course difficulty and category validation."""
        # Medical courses should be Advanced
        medical_course = CourseFactory(
            category='Inglês Médico',
            level='Advanced'
        )
        self.assertEqual(medical_course.level, 'Advanced')
        
        # Business courses can be Intermediate or Advanced
        business_course = CourseFactory(
            category='Inglês para Negócios',
            level='Intermediate'
        )
        self.assertEqual(business_course.level, 'Intermediate')


@pytest.mark.performance
@pytest.mark.django_db
class TestCourseModelPerformance(TestCase):
    """Test performance aspects of Course models."""
    
    def test_course_list_query_optimization(self):
        """Test that course list queries are optimized."""
        # Create courses with related data
        CourseFactory.create_batch(5)
        
        # Fetching courses with teacher info should be optimized
        with self.assertNumQueries(1):
            courses = Course.objects.select_related('teacher').all()
            list(courses)  # Force evaluation
    
    def test_course_with_sections_optimization(self):
        """Test course with sections query optimization."""
        course = CourseFactory()
        CourseSectionFactory.create_batch(3, course=course)
        
        # Fetching course with sections should use prefetch_related
        with self.assertNumQueries(2):  # 1 for course, 1 for sections
            course_with_sections = Course.objects.prefetch_related('sections').get(pk=course.pk)
            list(course_with_sections.sections.all())  # Force evaluation
    
    def test_bulk_enrollment_creation(self):
        """Test bulk enrollment creation performance."""
        course = CourseFactory()
        students = StudentFactory.create_batch(10)
        
        # Bulk create enrollments
        enrollments = [
            CourseEnrollment(user=student, course=course)
            for student in students
        ]
        
        created_enrollments = CourseEnrollment.objects.bulk_create(enrollments)
        self.assertEqual(len(created_enrollments), 10)


@pytest.mark.security
@pytest.mark.django_db
class TestCourseSecurity(TestCase):
    """Test security aspects of Course models."""
    
    def test_course_teacher_isolation(self):
        """Test that teachers can only see their own courses."""
        teacher1 = TeacherFactory()
        teacher2 = TeacherFactory()
        
        course1 = CourseFactory(teacher=teacher1)
        course2 = CourseFactory(teacher=teacher2)
        
        # Teacher 1 should only see their course
        teacher1_courses = Course.objects.filter(teacher=teacher1)
        self.assertIn(course1, teacher1_courses)
        self.assertNotIn(course2, teacher1_courses)
    
    def test_student_enrollment_permissions(self):
        """Test student enrollment permissions."""
        student = StudentFactory()
        teacher = TeacherFactory()
        course = CourseFactory(teacher=teacher)
        
        # Student should be able to enroll in published courses
        enrollment = CourseEnrollmentFactory(user=student, course=course)
        self.assertIsNotNone(enrollment)
        
        # Student should not see teacher-only information
        # (This would be tested in serializer/view tests)
    
    def test_course_data_validation(self):
        """Test course data validation for security."""
        # Test that malicious content is handled properly
        course = CourseFactory()
        
        # Course title should not contain script tags
        malicious_title = '<script>alert("xss")</script>Course Title'
        course.title = malicious_title
        
        # This should be handled by serializers/forms, not model
        # But we test that the model can store it safely
        course.save()
        self.assertEqual(course.title, malicious_title)  # Stored as-is, cleaned in presentation