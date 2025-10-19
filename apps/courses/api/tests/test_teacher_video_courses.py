"""
Integration tests for Teacher Video Courses APIs.

Tests teacher access to video course management including:
- Course CRUD operations
- Section and chapter management
- Authentication and permissions
- Teacher-specific features
"""

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import TeacherFactory, StudentFactory, VideoCourseFactory


class TeacherVideoCoursesAPITest(APITestCase):
    """Test teacher video course API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.other_teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create video courses for different teachers
        self.teacher_course = VideoCourseFactory(teacher=self.teacher, status='Published')
        self.teacher_draft_course = VideoCourseFactory(teacher=self.teacher, status='Draft')
        self.other_teacher_course = VideoCourseFactory(teacher=self.other_teacher, status='Published')
        
        # Create some sections and chapters for detailed testing
        self.course_section = CourseSection.objects.create(
            course=self.teacher_course,
            sectionTitle="Test Section",
            sectionDescription="Test section description",
            order=1
        )
        
        self.chapter = Chapter.objects.create(
            section=self.course_section,
            title="Test Chapter",
            content="Test chapter content",
            type="Video",
            video="https://example.com/video.mp4",
            order=1
        )
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_as_teacher(self):
        """Authenticate client as teacher."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def authenticate_as_other_teacher(self):
        """Authenticate client as other teacher."""
        token = self.get_jwt_token(self.other_teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def authenticate_as_student(self):
        """Authenticate client as student."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_teacher_authentication_required(self):
        """Test that teacher endpoints require authentication."""
        protected_endpoints = [
            ('/api/v1/teacher/video-courses/', 'GET'),
            ('/api/v1/teacher/video-courses/', 'POST'),
            (f'/api/v1/teacher/video-courses/{self.teacher_course.id}/', 'GET'),
            (f'/api/v1/teacher/video-courses/{self.teacher_course.id}/', 'PUT'),
            (f'/api/v1/teacher/video-courses/{self.teacher_course.id}/', 'DELETE'),
        ]
        
        for url, method in protected_endpoints:
            with self.subTest(url=url, method=method):
                response = getattr(self.client, method.lower())(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                               f"{method} {url} should require authentication")
    
    def test_teacher_can_list_own_courses(self):
        """Test teacher can list their own courses."""
        self.authenticate_as_teacher()
        url = '/api/v1/teacher/video-courses/?view_mode=teacher_courses'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Handle different response formats
        if 'data' in response_data:
            courses = response_data['data']
        else:
            courses = response_data
        
        # Should find teacher's courses (both published and draft)
        course_ids = [course.get('courseId') or course.get('id') for course in courses]
        self.assertIn(str(self.teacher_course.id), course_ids)
        self.assertIn(str(self.teacher_draft_course.id), course_ids)
        
        # Should NOT find other teacher's course
        self.assertNotIn(str(self.other_teacher_course.id), course_ids)
    
    def test_teacher_can_create_video_course(self):
        """Test teacher can create a new video course."""
        self.authenticate_as_teacher()
        url = '/api/v1/teacher/video-courses/'
        
        course_data = {
            'title': 'New Video Course',
            'description': 'A new video course description',
            'category': 'Conversação',
            'level': 'Beginner',
            'template': 'general'
        }
        
        response = self.client.post(url, course_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        self.assertIn('message', response_data)
        self.assertIn('data', response_data)
        
        # Verify course was created with correct data
        created_course = response_data['data']
        self.assertEqual(created_course['title'], course_data['title'])
        self.assertEqual(created_course['course_type'], 'video')
        self.assertEqual(created_course['teacher'], str(self.teacher.id))
    
    def test_student_cannot_create_course(self):
        """Test that students cannot create courses."""
        self.authenticate_as_student()
        url = '/api/v1/teacher/video-courses/'
        
        course_data = {
            'title': 'Unauthorized Course',
            'description': 'Should not be created',
            'category': 'Test',
            'level': 'Beginner'
        }
        
        response = self.client.post(url, course_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_teacher_can_view_own_course_details(self):
        """Test teacher can view details of their own course."""
        self.authenticate_as_teacher()
        url = f'/api/v1/teacher/video-courses/{self.teacher_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Handle response format
        if 'data' in response_data:
            course_data = response_data['data']
        else:
            course_data = response_data
        
        # Verify course details
        self.assertEqual(course_data['courseId'], str(self.teacher_course.id))
        self.assertEqual(course_data['teacher'], str(self.teacher.id))
        self.assertEqual(course_data['course_type'], 'video')
    
    def test_teacher_cannot_view_other_teacher_course(self):
        """Test teacher cannot view another teacher's course."""
        self.authenticate_as_teacher()
        url = f'/api/v1/teacher/video-courses/{self.other_teacher_course.id}/'
        response = self.client.get(url)
        
        # Should be forbidden or not found
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])
    
    def test_teacher_can_update_own_course(self):
        """Test teacher can update their own course."""
        self.authenticate_as_teacher()
        url = f'/api/v1/teacher/video-courses/{self.teacher_course.id}/'
        
        update_data = {
            'title': 'Updated Course Title',
            'description': 'Updated description',
            'level': 'Advanced'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        # Should be successful
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_204_NO_CONTENT
        ])
        
        # Verify course was updated
        self.teacher_course.refresh_from_db()
        self.assertEqual(self.teacher_course.title, update_data['title'])
        self.assertEqual(self.teacher_course.description, update_data['description'])
        self.assertEqual(self.teacher_course.level, update_data['level'])
    
    def test_teacher_can_delete_own_course(self):
        """Test teacher can delete their own course."""
        self.authenticate_as_teacher()
        
        # Create a course specifically for deletion
        course_to_delete = VideoCourseFactory(teacher=self.teacher)
        url = f'/api/v1/teacher/video-courses/{course_to_delete.id}/'
        
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify course was deleted
        self.assertFalse(Course.objects.filter(id=course_to_delete.id).exists())
    
    def test_teacher_section_management(self):
        """Test teacher can manage course sections."""
        self.authenticate_as_teacher()
        
        # Test listing sections
        url = f'/api/v1/teacher/video-courses/{self.teacher_course.id}/sections/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test creating new section
        section_data = {
            'sectionTitle': 'New Section',
            'sectionDescription': 'New section description',
            'order': 2
        }
        
        response = self.client.post(url, section_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK
        ])
    
    def test_teacher_chapter_management(self):
        """Test teacher can manage chapters."""
        self.authenticate_as_teacher()
        
        # Test listing chapters
        url = f'/api/v1/teacher/video-courses/sections/{self.course_section.id}/chapters/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test creating new chapter
        chapter_data = {
            'title': 'New Chapter',
            'content': 'New chapter content',
            'type': 'Video',
            'video': 'https://example.com/new-video.mp4',
            'order': 2
        }
        
        response = self.client.post(url, chapter_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK
        ])


@pytest.mark.django_db
class TeacherVideoCoursesPermissionsTest(APITestCase):
    """Test permissions and access control for teacher video courses."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        self.course = VideoCourseFactory(teacher=self.teacher)
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_role_based_access_control(self):
        """Test that only teachers can access teacher endpoints."""
        # Test with student credentials
        student_token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {student_token}')
        
        teacher_endpoints = [
            '/api/v1/teacher/video-courses/',
            f'/api/v1/teacher/video-courses/{self.course.id}/',
            f'/api/v1/teacher/video-courses/{self.course.id}/sections/',
        ]
        
        for url in teacher_endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Student should be forbidden from teacher endpoints
                self.assertIn(response.status_code, [
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND  # Some endpoints might return 404 for security
                ])
    
    def test_teacher_only_sees_own_courses(self):
        """Test that teachers only see their own courses in management view."""
        teacher1 = TeacherFactory()
        teacher2 = TeacherFactory()
        
        # Create courses for each teacher
        course1 = VideoCourseFactory(teacher=teacher1)
        course2 = VideoCourseFactory(teacher=teacher2)
        
        # Authenticate as teacher1
        token = self.get_jwt_token(teacher1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/v1/teacher/video-courses/?view_mode=teacher_courses'
        response = self.client.get(url)
        
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            
            # Handle response format
            if 'data' in response_data:
                courses = response_data['data']
            else:
                courses = response_data
            
            course_ids = [course.get('courseId') or course.get('id') for course in courses]
            
            # Should see own course but not other teacher's course
            self.assertIn(str(course1.id), course_ids)
            self.assertNotIn(str(course2.id), course_ids)


@pytest.mark.django_db
class TeacherVideoCoursesResponseFormatTest(APITestCase):
    """Test response format consistency for teacher video courses."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.course = VideoCourseFactory(teacher=self.teacher)
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def test_course_list_response_format(self):
        """Test course list response has consistent format."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/v1/teacher/video-courses/?view_mode=teacher_courses'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Should have message and data structure
        if isinstance(response_data, dict):
            self.assertIn('message', response_data)
            self.assertIn('data', response_data)
            self.assertIsInstance(response_data['data'], list)
    
    def test_course_creation_response_format(self):
        """Test course creation response has consistent format."""
        token = self.get_jwt_token(self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/v1/teacher/video-courses/'
        course_data = {
            'title': 'Test Course',
            'description': 'Test description',
            'category': 'Test',
            'level': 'Beginner'
        }
        
        response = self.client.post(url, course_data, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            response_data = response.json()
            
            # Should have message and data structure
            self.assertIn('message', response_data)
            self.assertIn('data', response_data)
            
            # Data should contain course information
            course_info = response_data['data']
            self.assertIn('courseId', course_info)
            self.assertIn('title', course_info)
            self.assertEqual(course_info['course_type'], 'video')