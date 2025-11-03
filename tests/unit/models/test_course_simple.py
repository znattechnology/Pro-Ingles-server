"""
Simple unit tests for Course models.

Tests basic course functionality without complex dependencies.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import CourseFactory, TeacherFactory

User = get_user_model()


@pytest.mark.django_db
class TestCourseModelBasic(TestCase):
    """Test basic Course model functionality."""
    
    def test_create_simple_course(self):
        """Test creating a basic course."""
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
        """Test the string representation of course."""
        course = CourseFactory(title='Test Course', teacherName='John Teacher')
        expected_str = 'Test Course by John Teacher'
        self.assertEqual(str(course), expected_str)
    
    def test_course_factory_basic(self):
        """Test CourseFactory creates valid courses."""
        course = CourseFactory()
        
        self.assertIsNotNone(course.title)
        self.assertIsNotNone(course.teacher)
        self.assertIsNotNone(course.teacherName)
        self.assertIn(course.level, ['Beginner', 'Intermediate', 'Advanced'])
    
    def test_course_auto_populate_teacher_name(self):
        """Test that teacherName is auto-populated from teacher."""
        teacher = TeacherFactory(name='Jane Smith')
        course = Course.objects.create(
            title='Test Course',
            teacher=teacher,
            level='Beginner'
        )
        
        self.assertEqual(course.teacherName, 'Jane Smith')


@pytest.mark.django_db
class TestCourseSectionBasic(TestCase):
    """Test basic CourseSection functionality."""
    
    def test_create_course_section(self):
        """Test creating a course section."""
        course = CourseFactory()
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
        """Test the string representation of section."""
        course = CourseFactory(title='English Course')
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
    
    def test_create_text_chapter(self):
        """Test creating a text chapter."""
        course = CourseFactory()
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
        """Test the string representation of chapter."""
        course = CourseFactory(title='English Course')
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
        course = CourseFactory()
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


@pytest.mark.django_db
class TestCourseFactoryBatch(TestCase):
    """Test course factory batch operations."""
    
    def test_create_multiple_courses(self):
        """Test creating multiple courses with factories."""
        courses = CourseFactory.create_batch(3)
        
        self.assertEqual(len(courses), 3)
        
        # All should have unique titles
        titles = [course.title for course in courses]
        self.assertEqual(len(titles), len(set(titles)))
    
    def test_factory_with_custom_data(self):
        """Test factories with custom data."""
        custom_title = 'Custom Course Title'
        course = CourseFactory(title=custom_title, level='Advanced')
        
        self.assertEqual(course.title, custom_title)
        self.assertEqual(course.level, 'Advanced')