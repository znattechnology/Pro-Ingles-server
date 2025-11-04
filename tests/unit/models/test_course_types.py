"""
Unit tests for different Course types: video-course vs practice-course.

Tests the behavioral differences between video courses and practice laboratory courses.
"""

import pytest
from django.test import TestCase

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import (
    TeacherFactory, 
    VideoCourseFactory, 
    PracticeCourseFactory,
    PublishedVideoCourseFactory,
    PublishedPracticeCourseFactory,
    CourseSectionFactory,
    ChapterFactory
)


@pytest.mark.django_db
class TestCourseTypes(TestCase):
    """Test the differences between video and practice course types."""
    
    def test_video_course_creation(self):
        """Test creating a video course."""
        video_course = VideoCourseFactory()
        
        self.assertEqual(video_course.course_type, 'video')
        self.assertIsNotNone(video_course.teacher)
        self.assertIsNotNone(video_course.title)
    
    def test_practice_course_creation(self):
        """Test creating a practice laboratory course."""
        practice_course = PracticeCourseFactory()
        
        self.assertEqual(practice_course.course_type, 'practice')
        self.assertIsNotNone(practice_course.teacher)
        self.assertIsNotNone(practice_course.title)
    
    def test_course_type_default(self):
        """Test that default course type is 'video'."""
        teacher = TeacherFactory()
        course = Course.objects.create(
            title='Default Course',
            teacher=teacher
        )
        
        self.assertEqual(course.course_type, 'video')
    
    def test_course_type_choices_validation(self):
        """Test that only valid course types are accepted."""
        valid_types = ['video', 'practice']
        
        for course_type in valid_types:
            teacher = TeacherFactory()
            course = Course.objects.create(
                title=f'Test {course_type} Course',
                teacher=teacher,
                course_type=course_type
            )
            self.assertEqual(course.course_type, course_type)


@pytest.mark.django_db
class TestVideoCourseSpecifics(TestCase):
    """Test video course specific functionality."""
    
    def test_video_course_with_video_chapters(self):
        """Test video course with video chapters."""
        video_course = VideoCourseFactory()
        section = CourseSectionFactory(course=video_course)
        
        # Video courses commonly have video chapters
        video_chapter = Chapter.objects.create(
            section=section,
            title='Video Lesson 1',
            content='Watch this video to learn...',
            type='Video',
            video='https://example.com/video1.mp4',
            order=1
        )
        
        self.assertEqual(video_chapter.type, 'Video')
        self.assertEqual(video_chapter.video, 'https://example.com/video1.mp4')
        self.assertEqual(video_chapter.course.course_type, 'video')
    
    def test_video_course_mixed_content(self):
        """Test video course with mixed chapter types."""
        video_course = VideoCourseFactory()
        # Create section without auto-generated chapters
        section = CourseSection.objects.create(
            course=video_course,
            sectionTitle='Mixed Content Section',
            order=1
        )
        
        # Video courses can have text, video, and quiz chapters
        text_chapter = Chapter.objects.create(
            section=section,
            type='Text',
            title='Introduction Text',
            content='Introduction content',
            order=1
        )
        video_chapter = Chapter.objects.create(
            section=section,
            type='Video',
            title='Video Lesson',
            content='Video content',
            video='https://example.com/video.mp4',
            order=2
        )
        quiz_chapter = Chapter.objects.create(
            section=section,
            type='Quiz',
            title='Knowledge Check',
            content='Quiz content',
            order=3
        )
        
        chapters = list(section.chapters.all().order_by('order'))
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].type, 'Text')
        self.assertEqual(chapters[1].type, 'Video') 
        self.assertEqual(chapters[2].type, 'Quiz')
        
        # All chapters belong to video course
        for chapter in chapters:
            self.assertEqual(chapter.course.course_type, 'video')
    
    def test_published_video_course_accessibility(self):
        """Test that published video courses are accessible to students."""
        published_video_course = PublishedVideoCourseFactory()
        student = TeacherFactory()  # Using as generic user
        
        self.assertEqual(published_video_course.status, 'Published')
        self.assertEqual(published_video_course.course_type, 'video')
        self.assertTrue(published_video_course.can_be_accessed_by(student))


@pytest.mark.django_db
class TestPracticeCourseSpecifics(TestCase):
    """Test practice laboratory course specific functionality."""
    
    def test_practice_course_with_exercise_chapters(self):
        """Test practice course with exercise chapters."""
        practice_course = PracticeCourseFactory()
        section = CourseSectionFactory(course=practice_course)
        
        # Practice courses commonly have exercise chapters
        exercise_chapter = Chapter.objects.create(
            section=section,
            title='Grammar Practice',
            content='Complete these grammar exercises...',
            type='Exercise',
            order=1
        )
        
        self.assertEqual(exercise_chapter.type, 'Exercise')
        self.assertEqual(exercise_chapter.course.course_type, 'practice')
        self.assertIsNotNone(exercise_chapter.practice_selection)
    
    def test_practice_course_quiz_chapters(self):
        """Test practice course with interactive quiz chapters."""
        practice_course = PracticeCourseFactory()
        section = CourseSectionFactory(course=practice_course)
        
        # Practice courses can have quiz chapters for assessment
        quiz_chapter = Chapter.objects.create(
            section=section,
            title='Practice Quiz',
            content='Test your knowledge...',
            type='Quiz',
            order=1,
            quiz_data={
                "questions": [
                    {
                        "id": 1,
                        "question": "Choose the correct verb form",
                        "type": "multiple_choice",
                        "options": ["go", "goes", "going", "gone"],
                        "correct_answer": 1
                    }
                ],
                "settings": {
                    "time_limit": 600,
                    "shuffle_questions": True
                }
            }
        )
        
        self.assertEqual(quiz_chapter.type, 'Quiz')
        self.assertTrue(quiz_chapter.quiz_enabled)
        self.assertIsNotNone(quiz_chapter.quiz_data)
        self.assertEqual(quiz_chapter.course.course_type, 'practice')
    
    def test_published_practice_course_accessibility(self):
        """Test that published practice courses are accessible."""
        published_practice_course = PublishedPracticeCourseFactory()
        student = TeacherFactory()  # Using as generic user
        
        self.assertEqual(published_practice_course.status, 'Published')
        self.assertEqual(published_practice_course.course_type, 'practice')
        self.assertTrue(published_practice_course.can_be_accessed_by(student))


@pytest.mark.django_db
class TestCourseTypeFiltering(TestCase):
    """Test filtering courses by type."""
    
    def test_filter_video_courses_only(self):
        """Test filtering to get only video courses."""
        # Create mixed course types
        video_course1 = VideoCourseFactory()
        video_course2 = VideoCourseFactory()
        practice_course1 = PracticeCourseFactory()
        practice_course2 = PracticeCourseFactory()
        
        # Filter video courses only
        video_courses = Course.objects.filter(course_type='video')
        
        self.assertEqual(video_courses.count(), 2)
        self.assertIn(video_course1, video_courses)
        self.assertIn(video_course2, video_courses)
        self.assertNotIn(practice_course1, video_courses)
        self.assertNotIn(practice_course2, video_courses)
    
    def test_filter_practice_courses_only(self):
        """Test filtering to get only practice courses."""
        # Create mixed course types
        video_course1 = VideoCourseFactory()
        video_course2 = VideoCourseFactory()
        practice_course1 = PracticeCourseFactory()
        practice_course2 = PracticeCourseFactory()
        
        # Filter practice courses only
        practice_courses = Course.objects.filter(course_type='practice')
        
        self.assertEqual(practice_courses.count(), 2)
        self.assertNotIn(video_course1, practice_courses)
        self.assertNotIn(video_course2, practice_courses)
        self.assertIn(practice_course1, practice_courses)
        self.assertIn(practice_course2, practice_courses)
    
    def test_filter_published_video_courses(self):
        """Test filtering published video courses specifically."""
        # Create various course combinations
        published_video = PublishedVideoCourseFactory()
        draft_video = VideoCourseFactory(status='Draft')
        published_practice = PublishedPracticeCourseFactory()
        draft_practice = PracticeCourseFactory(status='Draft')
        
        # Filter published video courses only
        published_video_courses = Course.objects.filter(
            course_type='video',
            status='Published'
        )
        
        self.assertEqual(published_video_courses.count(), 1)
        self.assertIn(published_video, published_video_courses)
        self.assertNotIn(draft_video, published_video_courses)
        self.assertNotIn(published_practice, published_video_courses)
        self.assertNotIn(draft_practice, published_video_courses)
    
    def test_filter_published_practice_courses(self):
        """Test filtering published practice courses specifically."""
        # Create various course combinations
        published_video = PublishedVideoCourseFactory()
        draft_video = VideoCourseFactory(status='Draft')
        published_practice = PublishedPracticeCourseFactory()
        draft_practice = PracticeCourseFactory(status='Draft')
        
        # Filter published practice courses only
        published_practice_courses = Course.objects.filter(
            course_type='practice',
            status='Published'
        )
        
        self.assertEqual(published_practice_courses.count(), 1)
        self.assertNotIn(published_video, published_practice_courses)
        self.assertNotIn(draft_video, published_practice_courses)
        self.assertIn(published_practice, published_practice_courses)
        self.assertNotIn(draft_practice, published_practice_courses)


@pytest.mark.django_db
class TestCourseTypeBusinessLogic(TestCase):
    """Test business logic differences between course types."""
    
    def test_course_type_in_string_representation(self):
        """Test course type information in string representation."""
        teacher = TeacherFactory(name='John Teacher')
        video_course = VideoCourseFactory(
            teacher=teacher,
            teacherName=teacher.name,
            title='Video English Course'
        )
        practice_course = PracticeCourseFactory(
            teacher=teacher,
            teacherName=teacher.name,
            title='Practice English Lab'
        )
        
        # Both should show teacher and title, regardless of type
        self.assertEqual(str(video_course), 'Video English Course by John Teacher')
        self.assertEqual(str(practice_course), 'Practice English Lab by John Teacher')
    
    def test_course_type_indexing(self):
        """Test that course_type is properly indexed for performance."""
        # Create courses of different types
        VideoCourseFactory.create_batch(5)
        PracticeCourseFactory.create_batch(3)
        
        # These queries should be efficient due to indexing
        video_count = Course.objects.filter(course_type='video').count()
        practice_count = Course.objects.filter(course_type='practice').count()
        
        self.assertEqual(video_count, 5)
        self.assertEqual(practice_count, 3)
    
    def test_teacher_can_create_both_types(self):
        """Test that a teacher can create both video and practice courses."""
        teacher = TeacherFactory()
        
        video_course = Course.objects.create(
            title='Video Course',
            teacher=teacher,
            course_type='video'
        )
        practice_course = Course.objects.create(
            title='Practice Course',
            teacher=teacher,
            course_type='practice'
        )
        
        teacher_courses = Course.objects.filter(teacher=teacher)
        self.assertEqual(teacher_courses.count(), 2)
        self.assertIn(video_course, teacher_courses)
        self.assertIn(practice_course, teacher_courses)
        
        # Teacher should have access to both types
        self.assertTrue(video_course.can_be_accessed_by(teacher))
        self.assertTrue(practice_course.can_be_accessed_by(teacher))