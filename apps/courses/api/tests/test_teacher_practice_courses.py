"""
Integration tests for Teacher Practice Courses APIs.

Tests teacher access to practice course management including:
- Course CRUD operations (via practice app)
- Authentication and permissions
- Practice-specific features
- Gamification management
"""

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course
from apps.practice.models import PracticeUnit, PracticeLesson, PracticeChallenge
from tests.factories import TeacherFactory, StudentFactory, PracticeCourseFactory


class TeacherPracticeCoursesAPITest(APITestCase):
    """Test teacher practice course API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.other_teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create practice courses
        self.teacher_practice_course = PracticeCourseFactory(teacher=self.teacher, status='Published')
        self.teacher_draft_practice_course = PracticeCourseFactory(teacher=self.teacher, status='Draft')
        self.other_teacher_practice_course = PracticeCourseFactory(teacher=self.other_teacher, status='Published')
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_as_teacher(self):
        """Authenticate client as teacher."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def authenticate_as_student(self):
        """Authenticate client as student."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_teacher_practice_endpoints_redirect_to_practice_app(self):
        """Test that teacher practice course endpoints redirect to practice app."""
        self.authenticate_as_teacher()
        
        # The teacher practice courses URL redirects to practice app
        # Let's test the practice app endpoints directly
        practice_endpoints = [
            '/api/v1/practice/',  # Main practice app endpoint
            '/api/v1/teacher/practice-courses/',  # Redirected endpoint
        ]
        
        for url in practice_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Should not be 404 (endpoint exists)
                self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                                  f"Practice endpoint {url} should exist")
    
    def test_teacher_authentication_required_for_practice_management(self):
        """Test that practice course management requires authentication."""
        # Test without authentication
        response = self.client.get('/api/v1/teacher/practice-courses/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_student_cannot_access_teacher_practice_endpoints(self):
        """Test that students cannot access teacher practice endpoints."""
        self.authenticate_as_student()
        
        teacher_practice_endpoints = [
            '/api/v1/teacher/practice-courses/',
        ]
        
        for url in teacher_practice_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Student should be denied access
                self.assertIn(response.status_code, [
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_404_NOT_FOUND  # Some might return 404 for security
                ])
    
    def test_practice_course_type_separation(self):
        """Test that practice courses are properly separated from video courses."""
        self.authenticate_as_teacher()
        
        # Create a video course for comparison
        video_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Video Course",
            description="A video course",
            course_type='video',
            status='Published'
        )
        
        # Verify course types are different
        self.assertEqual(self.teacher_practice_course.course_type, 'practice')
        self.assertEqual(video_course.course_type, 'video')
        
        # Verify they are stored correctly
        practice_courses = Course.objects.filter(course_type='practice', teacher=self.teacher)
        video_courses = Course.objects.filter(course_type='video', teacher=self.teacher)
        
        self.assertIn(self.teacher_practice_course, practice_courses)
        self.assertNotIn(video_course, practice_courses)
        self.assertIn(video_course, video_courses)
        self.assertNotIn(self.teacher_practice_course, video_courses)


@pytest.mark.django_db
class TeacherPracticeCoursesPermissionsTest(APITestCase):
    """Test permissions and access control for teacher practice courses."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_role_based_access_to_practice_management(self):
        """Test that only teachers can access practice course management."""
        # Test with teacher credentials
        teacher_token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_token}')
        
        response = self.client.get('/api/v1/teacher/practice-courses/')
        # Teacher should have access (not 401/403)
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])
        
        # Test with student credentials
        student_token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {student_token}')
        
        response = self.client.get('/api/v1/teacher/practice-courses/')
        # Student should be denied
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])


@pytest.mark.django_db
class PracticeAppIntegrationTest(APITestCase):
    """Test integration between courses app and practice app."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create a practice course
        self.practice_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Practice Course",
            description="A practice course",
            course_type='practice',
            status='Published'
        )
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_practice_course_exists_in_database(self):
        """Test that practice courses are properly stored."""
        # Verify course exists and has correct type
        self.assertTrue(Course.objects.filter(
            id=self.practice_course.id,
            course_type='practice'
        ).exists())
        
        # Verify course is accessible
        course = Course.objects.get(id=self.practice_course.id)
        self.assertEqual(course.course_type, 'practice')
        self.assertEqual(course.teacher, self.teacher)
    
    def test_practice_units_can_be_created(self):
        """Test that practice units can be created for practice courses."""
        # Create a practice unit
        practice_unit = PracticeUnit.objects.create(
            course=self.practice_course,
            title="Basic Unit",
            description="Basic practice unit",
            order=1
        )
        
        # Verify unit was created correctly
        self.assertEqual(practice_unit.course, self.practice_course)
        self.assertEqual(practice_unit.title, "Basic Unit")
        
        # Verify relationship works
        self.assertIn(practice_unit, self.practice_course.practice_units.all())
    
    def test_practice_lessons_can_be_created(self):
        """Test that practice lessons can be created for practice units."""
        # Create unit first
        practice_unit = PracticeUnit.objects.create(
            course=self.practice_course,
            title="Basic Unit",
            description="Basic practice unit",
            order=1
        )
        
        # Create lesson
        practice_lesson = PracticeLesson.objects.create(
            unit=practice_unit,
            title="Basic Lesson",
            order=1
        )
        
        # Verify lesson was created correctly
        self.assertEqual(practice_lesson.unit, practice_unit)
        self.assertEqual(practice_lesson.title, "Basic Lesson")
        
        # Verify relationship works
        self.assertIn(practice_lesson, practice_unit.lessons.all())
    
    def test_practice_challenges_can_be_created(self):
        """Test that practice challenges can be created for practice lessons."""
        # Create unit and lesson first
        practice_unit = PracticeUnit.objects.create(
            course=self.practice_course,
            title="Basic Unit",
            description="Basic practice unit",
            order=1
        )
        
        practice_lesson = PracticeLesson.objects.create(
            unit=practice_unit,
            title="Basic Lesson",
            order=1
        )
        
        # Create challenge
        practice_challenge = PracticeChallenge.objects.create(
            lesson=practice_lesson,
            type="SELECT",
            question="What is the correct answer?",
            order=1
        )
        
        # Verify challenge was created correctly
        self.assertEqual(practice_challenge.lesson, practice_lesson)
        self.assertEqual(practice_challenge.type, "SELECT")
        
        # Verify relationship works
        self.assertIn(practice_challenge, practice_lesson.challenges.all())


@pytest.mark.django_db
class PracticeCoursesEndpointsTest(APITestCase):
    """Test that practice course endpoints exist and are accessible."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_practice_app_endpoints_exist(self):
        """Test that practice app endpoints exist."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test main practice endpoints
        practice_endpoints = [
            '/api/v1/practice/',
            '/api/v1/teacher/practice-courses/',
        ]
        
        for url in practice_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Should exist (not 404)
                self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                                  f"Practice endpoint {url} should exist")
                
                # Should be accessible to authenticated teachers
                self.assertNotIn(response.status_code, [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN
                ])
    
    def test_practice_course_management_flow(self):
        """Test basic practice course management flow."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create a practice course
        practice_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Test Practice Course",
            description="A test practice course",
            course_type='practice',
            status='Draft'
        )
        
        # Verify course was created
        self.assertTrue(Course.objects.filter(
            id=practice_course.id,
            course_type='practice',
            teacher=self.teacher
        ).exists())
        
        # Test that we can access practice endpoints
        response = self.client.get('/api/v1/practice/')
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)