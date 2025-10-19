"""
Integration tests focused only on Video Course APIs.

This test file focuses exclusively on video course functionality 
to avoid practice app dependencies while testing core functionality.
"""

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.courses.models import Course, CourseSection, Chapter
from tests.factories import (
    TeacherFactory, StudentFactory, 
    PublishedVideoCourseFactory, VideoCourseFactory,
    CourseSectionFactory, ChapterFactory
)


class VideoCoursesAPITest(APITestCase):
    """Test video course API endpoints only."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create video courses only
        self.published_video_course = PublishedVideoCourseFactory(teacher=self.teacher)
        self.draft_video_course = VideoCourseFactory(teacher=self.teacher, status='Draft')
        
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
    
    def get_jwt_token(self, user):
        """Get JWT token for user authentication."""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_as_student(self):
        """Authenticate client as student."""
        token = self.get_jwt_token(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_student_list_published_video_courses(self):
        """Test student can list published video courses."""
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
    
    def test_student_video_course_detail(self):
        """Test student can view published video course details."""
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # API returns {message: ..., data: {...}}
        self.assertIn('data', response_data)
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
        
        # Check if it's wrapped in {data: ...} format
        if 'data' in response_data:
            data = response_data['data']
        else:
            data = response_data
        
        # Find our specific section in the data
        video_section_found = False
        for section in data:
            if section['sectionId'] == str(self.video_section.id):
                self.assertEqual(section['sectionTitle'], 'Video Section')
                video_section_found = True
                break
        
        self.assertTrue(video_section_found, "Video section not found in response")
    
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
    
    def test_video_api_only_shows_video_courses(self):
        """Test video course API only returns video courses."""
        url = '/api/v1/student/video-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        if 'data' in response_data:
            courses = response_data['data']
            # All returned courses should be video type
            for course in courses:
                if 'course_type' in course:
                    self.assertEqual(course['course_type'], 'video')
    
    def test_video_course_response_structure(self):
        """Test video course API response has correct structure."""
        url = f'/api/v1/student/video-courses/{self.published_video_course.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # API returns {message: ..., data: {...}}
        self.assertIn('message', response_data)
        self.assertIn('data', response_data)
        
        data = response_data['data']
        
        # Check required fields
        required_fields = ['courseId', 'title', 'description', 'teacher', 'status', 'course_type']
        for field in required_fields:
            self.assertIn(field, data, f"Field '{field}' not found in response data")
        
        # Check course type is video
        self.assertEqual(data['course_type'], 'video')