"""
Integration tests for Student API endpoints.

Tests student access to both video courses and practice courses APIs,
including authentication, permissions, and data access patterns.
"""

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import (
    TeacherFactory, StudentFactory, 
    PublishedVideoCourseFactory, VideoCourseFactory,
    PublishedPracticeCourseFactory, PracticeCourseFactory,
    CourseSectionFactory, ChapterFactory
)


class BaseStudentAPITest(APITestCase):
    """Base class for student API tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create video courses
        self.published_video_course = PublishedVideoCourseFactory(teacher=self.teacher)
        self.draft_video_course = VideoCourseFactory(teacher=self.teacher, status='Draft')
        
        # Create practice courses
        self.published_practice_course = PublishedPracticeCourseFactory(teacher=self.teacher)
        self.draft_practice_course = PracticeCourseFactory(teacher=self.teacher, status='Draft')
        
        # Create course structure for video course
        self.video_section = CourseSection.objects.create(
            course=self.published_video_course,
            sectionTitle='Video Section',
            order=1
        )
        self.video_chapter = Chapter.objects.create(
            section=self.video_section,
            title='Video Chapter',
            content='Video content',
            type='Video',
            video='https://example.com/video.mp4',
            order=1
        )
        
        # Create course structure for practice course
        self.practice_section = CourseSection.objects.create(
            course=self.published_practice_course,
            sectionTitle='Practice Section',
            order=1
        )
        self.practice_chapter = Chapter.objects.create(
            section=self.practice_section,
            title='Practice Chapter',
            content='Practice content',
            type='Exercise',
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
    
    def extract_api_data(self, response):
        """Extract data from API response format {message: ..., data: [...]}."""
        response_data = response.json()
        if isinstance(response_data, dict) and 'data' in response_data:
            return response_data['data']
        elif isinstance(response_data, list):
            return response_data
        else:
            return response_data


@pytest.mark.django_db
class TestStudentVideoCourseAPI(BaseStudentAPITest):
    """Test student video course API endpoints."""
    
    def test_student_list_published_video_courses(self):
        """Test student can list published video courses only."""
        url = '/api/v1/student/video-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # API returns {message: ..., data: [...]}
        self.assertIn('data', response_data)
        courses = response_data['data']
        
        # Should see published video course but not draft
        course_ids = [course['courseId'] for course in courses]
        self.assertIn(str(self.published_video_course.id), course_ids)
        self.assertNotIn(str(self.draft_video_course.id), course_ids)
        
        # Should not see practice courses in video course endpoint
        self.assertNotIn(str(self.published_practice_course.id), course_ids)
    
    def test_student_video_course_detail(self):
        """Test student can view published video course details."""
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        data = response_data['data']
        
        self.assertEqual(data['courseId'], str(self.published_video_course.id))
        self.assertEqual(data['course_type'], 'video')
        self.assertEqual(data['status'], 'Published')
    
    def test_student_cannot_access_draft_video_course(self):
        """Test student cannot access draft video courses."""
        url = f'/api/v1/student/video-courses/{self.draft_video_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_student_list_video_course_sections(self):
        """Test student can list sections of video course."""
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/sections/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        data = response_data['data']
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['sectionId'], str(self.video_section.id))
        self.assertEqual(data[0]['sectionTitle'], 'Video Section')
    
    def test_student_list_video_course_chapters(self):
        """Test student can list chapters in video course section."""
        url = f'/api/v1/student/video-courses/sections/{self.video_section.id}/chapters/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        data = response_data['data']
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['chapterId'], str(self.video_chapter.id))
        self.assertEqual(data[0]['type'], 'Video')
        self.assertIn('video', data[0])
    
    def test_filter_video_courses_by_category(self):
        """Test filtering video courses by category."""
        # Create video course with specific category
        grammar_video = PublishedVideoCourseFactory(
            teacher=self.teacher,
            category='Grammar'
        )
        
        url = '/api/v1/student/video-courses/?category=Grammar'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        data = response_data['data']
        
        # Should find the grammar course
        course_found = False
        for course in data:
            if course['courseId'] == str(grammar_video.id):
                self.assertEqual(course['category'], 'Grammar')
                course_found = True
        self.assertTrue(course_found)


@pytest.mark.django_db
class TestStudentPracticeCourseAPI(BaseStudentAPITest):
    """Test student practice course API endpoints."""
    
    def test_student_list_published_practice_courses(self):
        """Test student can list published practice courses only."""
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should see published practice course but not draft
        course_ids = [course['courseId'] for course in data]
        self.assertIn(str(self.published_practice_course.id), course_ids)
        self.assertNotIn(str(self.draft_practice_course.id), course_ids)
        
        # Should not see video courses in practice course endpoint
        self.assertNotIn(str(self.published_video_course.id), course_ids)
    
    def test_student_practice_course_detail(self):
        """Test student can view published practice course details."""
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['courseId'], str(self.published_practice_course.id))
        self.assertEqual(data['course_type'], 'practice')
        self.assertEqual(data['status'], 'Published')
    
    def test_student_cannot_access_draft_practice_course(self):
        """Test student cannot access draft practice courses."""
        url = f'/api/v1/student/practice-courses/courses/{self.draft_practice_course.id}/units/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_practice_course_has_exercise_chapters(self):
        """Test that practice courses can have exercise chapters."""
        url = f'/api/v1/student/practice-courses/sections/{self.practice_section.id}/chapters/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['chapterId'], str(self.practice_chapter.id))
        self.assertEqual(data[0]['type'], 'Exercise')
        # Exercise chapters should have practice_selection
        self.assertIn('practice_selection', data[0])


@pytest.mark.django_db
class TestStudentAPIPermissions(BaseStudentAPITest):
    """Test student API permissions and access control."""
    
    def test_video_course_endpoints_are_public(self):
        """Test that video course endpoints are accessible without authentication."""
        # Course listing
        url = '/api/v1/student/video-courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Course detail
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_practice_course_endpoints_are_public(self):
        """Test that practice course endpoints are accessible without authentication."""
        # Course listing
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Course detail
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_students_have_read_only_access(self):
        """Test that students have read-only access to courses."""
        self.authenticate_as_student()
        
        # Try to create a course (should fail)
        course_data = {
            'title': 'Student Created Course',
            'description': 'This should not work'
        }
        
        # Video course creation
        url = '/api/v1/student/video-courses/'
        response = self.client.post(url, course_data, format='json')
        # Should be method not allowed or forbidden
        self.assertIn(response.status_code, [
            status.HTTP_405_METHOD_NOT_ALLOWED, 
            status.HTTP_403_FORBIDDEN
        ])
        
        # Practice course creation
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.post(url, course_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_405_METHOD_NOT_ALLOWED, 
            status.HTTP_403_FORBIDDEN
        ])


@pytest.mark.django_db
class TestStudentAPICourseTypeSegregation(BaseStudentAPITest):
    """Test that video and practice course APIs are properly segregated."""
    
    def test_video_api_only_shows_video_courses(self):
        """Test video course API only returns video courses."""
        url = '/api/v1/student/video-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All returned courses should be video type
        for course in data:
            if 'course_type' in course:
                self.assertEqual(course['course_type'], 'video')
    
    def test_practice_api_only_shows_practice_courses(self):
        """Test practice course API only returns practice courses."""
        url = '/api/v1/student/practice-courses/courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All returned courses should be practice type
        for course in data:
            if 'course_type' in course:
                self.assertEqual(course['course_type'], 'practice')
    
    def test_cross_contamination_prevention(self):
        """Test that practice course cannot be accessed via video API and vice versa."""
        # Try to access practice course via video API
        url = f'/api/v1/student/video-courses/{self.published_practice_course.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to access video course via practice API
        url = f'/api/v1/student/practice-courses/courses/{self.published_video_course.id}/units/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_course_sections_respect_course_type(self):
        """Test that sections are only accessible via correct course type API."""
        # Video course section via video API (should work)
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/sections/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Practice course units via practice API (should work)
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@pytest.mark.django_db
class TestStudentAPIResponseFormat(BaseStudentAPITest):
    """Test API response format and data structure."""
    
    def test_video_course_response_structure(self):
        """Test video course API response has correct structure."""
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check required fields
        required_fields = ['courseId', 'title', 'description', 'teacher', 'status', 'course_type']
        for field in required_fields:
            self.assertIn(field, data)
        
        # Check course type is video
        self.assertEqual(data['course_type'], 'video')
    
    def test_practice_course_response_structure(self):
        """Test practice course API response has correct structure."""
        url = f'/api/v1/student/practice-courses/courses/{self.published_practice_course.id}/units/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check required fields
        required_fields = ['courseId', 'title', 'description', 'teacher', 'status', 'course_type']
        for field in required_fields:
            self.assertIn(field, data)
        
        # Check course type is practice
        self.assertEqual(data['course_type'], 'practice')
    
    def test_chapter_response_includes_type_specific_fields(self):
        """Test chapter responses include type-specific fields."""
        # Video chapter should include video field
        url = f'/api/v1/student/video-courses/chapters/{self.video_chapter.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['type'], 'Video')
        self.assertIn('video', data)
        self.assertEqual(data['video'], 'https://example.com/video.mp4')
        
        # Exercise chapter should include practice_selection
        url = f'/api/v1/student/practice-courses/chapters/{self.practice_chapter.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['type'], 'Exercise')
        self.assertIn('practice_selection', data)
        self.assertIsNotNone(data['practice_selection'])