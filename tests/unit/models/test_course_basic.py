"""
Basic unit tests for Course models.

Tests fundamental course model functionality without complex dependencies.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import TeacherFactory

User = get_user_model()


@pytest.mark.django_db
class TestCourseBasic(TestCase):
    """Test basic Course model functionality."""
    
    def test_create_course_manual(self):
        """Test creating a course manually."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Basic English',
            description='A simple English course',
            teacher=teacher,
            level='Beginner',
            status='Draft'
        )
        
        self.assertEqual(course.title, 'Basic English')
        self.assertEqual(course.teacher, teacher)
        self.assertEqual(course.level, 'Beginner')
        self.assertEqual(course.status, 'Draft')
        self.assertIsNotNone(course.id)
    
    def test_course_string_representation(self):
        """Test course string representation."""
        teacher = TeacherFactory(name='John Teacher')
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher,
            teacherName='John Teacher'
        )
        expected_str = 'Test Course by John Teacher'
        self.assertEqual(str(course), expected_str)
    
    def test_course_auto_populate_teacher_name(self):
        """Test that teacherName is auto-populated."""
        teacher = TeacherFactory(name='Jane Smith')
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher,
            level='Beginner'
        )
        
        self.assertEqual(course.teacherName, 'Jane Smith')
    
    def test_course_access_permissions(self):
        """Test course access permissions."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher,
            status='Published'
        )
        
        # Published course should be accessible by anyone
        student = TeacherFactory()  # Using teacher factory as generic user
        self.assertTrue(course.can_be_accessed_by(student))
        self.assertTrue(course.can_be_accessed_by(teacher))


@pytest.mark.django_db
class TestCourseSectionBasic(TestCase):
    """Test basic CourseSection functionality."""
    
    def test_create_section_manual(self):
        """Test creating a section manually."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Introduction',
            sectionDescription='Basic introduction',
            order=1
        )
        
        self.assertEqual(section.course, course)
        self.assertEqual(section.sectionTitle, 'Introduction')
        self.assertEqual(section.order, 1)
    
    def test_section_string_representation(self):
        """Test section string representation."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='English Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Grammar Basics',
            order=1
        )
        expected_str = 'English Course - Grammar Basics'
        self.assertEqual(str(section), expected_str)


@pytest.mark.django_db 
class TestChapterBasic(TestCase):
    """Test basic Chapter functionality."""
    
    def test_create_text_chapter_manual(self):
        """Test creating a text chapter manually."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        
        chapter = Chapter.objects.create(
            section=section,
            title='Introduction to Verbs',
            content='Verbs are action words...',
            type='Text',
            order=1
        )
        
        self.assertEqual(chapter.title, 'Introduction to Verbs')
        self.assertEqual(chapter.type, 'Text')
        self.assertEqual(chapter.section, section)
    
    def test_chapter_string_representation(self):
        """Test chapter string representation."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='English Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Grammar',
            order=1
        )
        chapter = Chapter.objects.create(
            section=section,
            title='Verbs',
            content='Test content',
            type='Text',
            order=1
        )
        
        expected_str = 'English Course - Grammar - Verbs'
        self.assertEqual(str(chapter), expected_str)
    
    def test_chapter_course_property(self):
        """Test the course property of chapter."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        chapter = Chapter.objects.create(
            section=section,
            title='Test Chapter',
            content='Test content',
            type='Text',
            order=1
        )
        
        self.assertEqual(chapter.course, course)
    
    def test_quiz_chapter_auto_enable(self):
        """Test that quiz chapters auto-enable quiz_enabled."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        chapter = Chapter.objects.create(
            section=section,
            title='Quiz Chapter',
            content='Quiz content',
            type='Quiz',
            order=1
        )
        
        self.assertEqual(chapter.type, 'Quiz')
        self.assertTrue(chapter.quiz_enabled)
    
    def test_exercise_chapter_practice_selection(self):
        """Test that exercise chapters get default practice_selection."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        chapter = Chapter.objects.create(
            section=section,
            title='Exercise Chapter',
            content='Exercise content',
            type='Exercise',
            order=1
        )
        
        self.assertEqual(chapter.type, 'Exercise')
        self.assertIsNotNone(chapter.practice_selection)
        self.assertIn('course_id', chapter.practice_selection)
        self.assertIn('lesson_ids', chapter.practice_selection)


@pytest.mark.django_db
class TestCourseRelationships(TestCase):
    """Test course model relationships."""
    
    def test_course_sections_count(self):
        """Test course total_sections property."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        
        # Initially no sections
        self.assertEqual(course.total_sections, 0)
        
        # Add sections
        CourseSection.objects.create(
            course=course,
            sectionTitle='Section 1',
            order=1
        )
        CourseSection.objects.create(
            course=course,
            sectionTitle='Section 2',
            order=2
        )
        
        self.assertEqual(course.total_sections, 2)
    
    def test_course_chapters_count(self):
        """Test course total_chapters property."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        
        # Initially no chapters
        self.assertEqual(course.total_chapters, 0)
        
        # Add chapters
        Chapter.objects.create(
            section=section,
            title='Chapter 1',
            content='Content 1',
            type='Text',
            order=1
        )
        Chapter.objects.create(
            section=section,
            title='Chapter 2',
            content='Content 2',
            type='Text',
            order=2
        )
        
        self.assertEqual(course.total_chapters, 2)
    
    def test_section_chapters_count(self):
        """Test section total_chapters property."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher
        )
        section = CourseSection.objects.create(
            course=course,
            sectionTitle='Test Section',
            order=1
        )
        
        # Initially no chapters
        self.assertEqual(section.total_chapters, 0)
        
        # Add chapters
        Chapter.objects.create(
            section=section,
            title='Chapter 1',
            content='Content 1',
            type='Text',
            order=1
        )
        
        self.assertEqual(section.total_chapters, 1)