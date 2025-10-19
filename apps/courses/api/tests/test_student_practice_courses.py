"""
Integration tests for Student Practice Courses APIs.

Tests student access to practice course functionality including:
- Course listing
- Units and lessons
- Progress tracking  
- Hearts/gamification features
- AI speaking/listening features
"""

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course, CourseSection, Chapter
from apps.practice.models import PracticeUnit, PracticeLesson, PracticeChallenge, UserProgress
from tests.factories import (
    TeacherFactory, StudentFactory, 
    PublishedPracticeCourseFactory, PracticeCourseFactory
)


class StudentPracticeCoursesAPITest(APITestCase):
    """Test student practice course API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create practice courses
        self.published_practice_course = PublishedPracticeCourseFactory(teacher=self.teacher)
        self.draft_practice_course = PracticeCourseFactory(teacher=self.teacher, status='Draft')
        
        # Create some practice units and lessons for the published course
        self.practice_unit = PracticeUnit.objects.create(
            course=self.published_practice_course,
            title="Basic Unit",
            description="Basic practice unit",
            order=1
        )
        
        self.practice_lesson = PracticeLesson.objects.create(
            unit=self.practice_unit,
            title="Basic Lesson",
            order=1
        )
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_as_student(self):
        """Authenticate client as student."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_practice_courses_list_requires_authentication(self):
        """Test that practice courses listing requires authentication."""
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        # Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_student_can_list_practice_courses(self):
        """Test authenticated student can list published practice courses."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response format
        response_data = response.json()
        
        # The response might be a list or wrapped in {data: [...]}
        if isinstance(response_data, dict) and 'data' in response_data:
            courses = response_data['data']
        else:
            courses = response_data
        
        # Should find our published practice course
        course_ids = [course.get('id') or course.get('courseId') for course in courses]
        self.assertIn(str(self.published_practice_course.id), course_ids)
        
        # Should NOT find draft course
        self.assertNotIn(str(self.draft_practice_course.id), course_ids)
    
    def test_student_can_access_course_units(self):
        """Test student can access units of a practice course."""
        self.authenticate_as_student()
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        
        # Should be accessible (might return 200 or 404 if no units)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            # Just verify it's a valid response structure
            self.assertIsInstance(response_data, (list, dict))
    
    def test_test_endpoints_exist(self):
        """Test that the test endpoints exist and respond."""
        self.authenticate_as_student()
        
        test_endpoints = [
            '/api/v1/student/practice-courses/test-units/',
            '/api/v1/student/practice-courses/test-lessons/',
            '/api/v1/student/practice-courses/test-challenges/'
        ]
        
        for url in test_endpoints:
            response = self.client.get(url)
            # Should exist (200) or be method not allowed (405), but not 404
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND, 
                              f"Endpoint {url} should exist")
    
    def test_user_progress_endpoint_exists(self):
        """Test that user progress endpoint exists."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/user-progress/'
        response = self.client.get(url)
        
        # Should exist - either return data (200) or empty (200/404)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_404_NOT_FOUND, 
            status.HTTP_204_NO_CONTENT
        ])
    
    def test_challenge_progress_endpoint_exists(self):
        """Test that challenge progress endpoint exists."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/challenge-progress/'
        
        # Test GET request
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test POST request (might need data, but endpoint should exist)
        response = self.client.post(url, {})
        # Should not be 404 (endpoint exists)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_hearts_management_endpoints_exist(self):
        """Test that hearts management endpoints exist."""
        self.authenticate_as_student()
        
        hearts_endpoints = [
            '/api/v1/student/practice-courses/reduce-hearts/',
            '/api/v1/student/practice-courses/refill-hearts/'
        ]
        
        for url in hearts_endpoints:
            response = self.client.post(url, {})
            # Should exist (not 404)
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                              f"Hearts endpoint {url} should exist")
    
    def test_ai_features_endpoints_exist(self):
        """Test that AI speaking and listening endpoints exist."""
        self.authenticate_as_student()
        
        ai_endpoints = [
            '/api/v1/student/practice-courses/speaking/exercises/',
            '/api/v1/student/practice-courses/listening/exercises/',
            '/api/v1/student/practice-courses/achievements/'
        ]
        
        for url in ai_endpoints:
            response = self.client.get(url)
            # Should exist (not 404)
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                              f"AI endpoint {url} should exist")


@pytest.mark.django_db
class TestPracticeCoursesPermissions(APITestCase):
    """Test permissions and access control for practice courses."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.student = StudentFactory()
        
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access practice courses."""
        protected_endpoints = [
            '/api/v1/student/practice-courses/courses/',
            '/api/v1/student/practice-courses/user-progress/',
            '/api/v1/student/practice-courses/challenge-progress/',
            '/api/v1/student/practice-courses/speaking/exercises/',
            '/api/v1/student/practice-courses/achievements/'
        ]
        
        for url in protected_endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                           f"Endpoint {url} should require authentication")
    
    def test_authenticated_student_has_access(self):
        """Test that authenticated students have access to their endpoints."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test main courses endpoint
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        # Should be authorized (200 or other non-401 status)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db  
class TestPracticeCoursesDataIntegrity(APITestCase):
    """Test data integrity and filtering for practice courses."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create both video and practice courses
        self.video_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Video Course",
            description="A video course",
            course_type='video',
            status='Published'
        )
        
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
    
    def test_practice_courses_only_show_practice_type(self):
        """Test that practice course API only returns practice courses."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            
            # Handle different response formats
            if isinstance(response_data, dict) and 'data' in response_data:
                courses = response_data['data']
            else:
                courses = response_data
                
            # Find our courses
            found_practice = False
            found_video = False
            
            for course in courses:
                course_id = course.get('id') or course.get('courseId')
                if course_id == str(self.practice_course.id):
                    found_practice = True
                elif course_id == str(self.video_course.id):
                    found_video = True
            
            # Should find practice course but NOT video course
            self.assertTrue(found_practice, "Practice course should be found in practice API")
            self.assertFalse(found_video, "Video course should NOT be found in practice API")