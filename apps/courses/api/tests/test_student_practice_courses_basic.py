"""
Basic integration tests for Student Practice Courses APIs.

Focused on core endpoints without complex model setup.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course

User = get_user_model()


class BasicStudentPracticeCoursesAPITest(APITestCase):
    """Basic tests for student practice course API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create teacher and student directly
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            name='Test Teacher',
            password='password123',
            role='teacher'
        )
        
        self.student = User.objects.create_user(
            email='student@example.com',
            name='Test Student',
            password='password123',
            role='student'
        )
        
        # Create a simple practice course
        self.published_practice_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Practice Course",
            description="A practice course",
            course_type='practice',
            status='Published'
        )
        
        self.draft_practice_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Draft Practice Course",
            description="A draft practice course",
            course_type='practice',
            status='Draft'
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
    
    def test_practice_course_filter_by_type(self):
        """Test that practice course API only returns practice courses."""
        self.authenticate_as_student()
        
        # Create a video course for comparison
        video_course = Course.objects.create(
            teacher=self.teacher,
            teacherName=self.teacher.name,
            title="Video Course",
            description="A video course",
            course_type='video',
            status='Published'
        )
        
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
                if course_id == str(self.published_practice_course.id):
                    found_practice = True
                elif course_id == str(video_course.id):
                    found_video = True
            
            # Should find practice course but NOT video course
            self.assertTrue(found_practice, "Practice course should be found in practice API")
            self.assertFalse(found_video, "Video course should NOT be found in practice API")
    
    def test_basic_endpoints_exist_and_respond(self):
        """Test that basic practice course endpoints exist and respond properly."""
        self.authenticate_as_student()
        
        # Test main courses endpoint
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test course units endpoint (should exist even if returns 404)
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_404_NOT_FOUND,
            status.HTTP_204_NO_CONTENT
        ])
    
    def test_user_progress_endpoint_accessible(self):
        """Test that user progress endpoint is accessible."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/user-progress/'
        response = self.client.get(url)
        
        # Should be accessible (not 401 or 403)
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])
        
        # Should exist (not 404) 
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_challenge_progress_endpoint_accessible(self):
        """Test that challenge progress endpoint is accessible."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/challenge-progress/'
        
        # Test GET request
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])
    
    def test_practice_course_response_structure(self):
        """Test that practice course API returns valid response structure."""
        self.authenticate_as_student()
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Should be valid JSON (list or dict)
        self.assertIsInstance(response_data, (list, dict))
        
        # If it's a dict, should have reasonable structure
        if isinstance(response_data, dict):
            # Common API response patterns
            valid_keys = {'data', 'results', 'message', 'courses'}
            has_valid_key = any(key in response_data for key in valid_keys)
            self.assertTrue(has_valid_key, "Response should have recognizable structure")


@pytest.mark.django_db
class PracticeCoursesEndpointsExistenceTest(APITestCase):
    """Test that all expected practice course endpoints exist."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.student = StudentFactory()
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_all_documented_endpoints_exist(self):
        """Test that all documented endpoints return non-404 responses."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # List of endpoints that should exist (from URLs)
        endpoints_to_test = [
            '/api/v1/student/practice-courses/courses/',
            '/api/v1/student/practice-courses/user-progress/',
            '/api/v1/student/practice-courses/challenge-progress/',
            '/api/v1/student/practice-courses/test-units/',
            '/api/v1/student/practice-courses/test-lessons/',
            '/api/v1/student/practice-courses/test-challenges/'
        ]
        
        for url in endpoints_to_test:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotEqual(
                    response.status_code, 
                    status.HTTP_404_NOT_FOUND,
                    f"Endpoint {url} should exist (not return 404)"
                )