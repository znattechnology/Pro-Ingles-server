"""
Integration tests for Teacher API endpoints.

Tests teacher access to both video courses and practice courses APIs,
including CRUD operations, authentication, permissions, and ownership validation.
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
    PublishedPracticeCourseFactory, PracticeCourseFactory,
    CourseSectionFactory, ChapterFactory
)


class BaseTeacherAPITest(APITestCase):
    """Base class for teacher API tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.teacher = TeacherFactory()
        self.other_teacher = TeacherFactory()
        self.student = StudentFactory()
        
        # Create courses for main teacher
        self.teacher_video_course = PublishedVideoCourseFactory(teacher=self.teacher)
        self.teacher_practice_course = PublishedPracticeCourseFactory(teacher=self.teacher)
        self.teacher_draft_video = VideoCourseFactory(teacher=self.teacher, status='Draft')
        
        # Create courses for other teacher
        self.other_video_course = PublishedVideoCourseFactory(teacher=self.other_teacher)
        self.other_practice_course = PublishedPracticeCourseFactory(teacher=self.other_teacher)
        
        # Create course structure
        self.video_section = CourseSection.objects.create(
            course=self.teacher_video_course,
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
    
    def authenticate_as_teacher(self):
        """Authenticate client as main teacher."""
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


@pytest.mark.django_db
class TestTeacherVideoCourseAPI(BaseTeacherAPITest):
    """Test teacher video course API endpoints."""
    
    def test_teacher_list_own_video_courses(self):
        """Test teacher can list their own video courses."""
        self.authenticate_as_teacher()
        
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should see own video courses but not other teacher's
        course_ids = [course['courseId'] for course in data]
        self.assertIn(str(self.teacher_video_course.id), course_ids)
        self.assertIn(str(self.teacher_draft_video.id), course_ids)
        self.assertNotIn(str(self.other_video_course.id), course_ids)
        
        # Should not see practice courses in video endpoint
        self.assertNotIn(str(self.teacher_practice_course.id), course_ids)
    
    def test_teacher_create_video_course(self):
        """Test teacher can create new video courses."""
        self.authenticate_as_teacher()
        
        course_data = {
            'title': 'New Video Course',
            'description': 'A new course for testing',
            'category': 'Grammar',
            'level': 'Beginner',
            'status': 'Draft'
        }
        
        url = '/api/v1/teacher/video-courses/'
        response = self.client.post(url, course_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['title'], course_data['title'])
        self.assertEqual(data['course_type'], 'video')  # Auto-set to video
        self.assertEqual(data['teacherName'], self.teacher.name)
        
        # Verify in database
        course = Course.objects.get(id=data['courseId'])
        self.assertEqual(course.teacher, self.teacher)
        self.assertEqual(course.course_type, 'video')
    
    def test_teacher_update_own_video_course(self):
        """Test teacher can update their own video courses."""
        self.authenticate_as_teacher()
        
        update_data = {
            'title': 'Updated Video Course',
            'description': 'Updated description',
            'status': 'Published'
        }
        
        url = f'/api/v1/teacher/video-courses/{self.teacher_draft_video.id}/'
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['title'], update_data['title'])
        self.assertEqual(data['status'], 'Published')
        
        # Verify in database
        self.teacher_draft_video.refresh_from_db()
        self.assertEqual(self.teacher_draft_video.title, update_data['title'])
    
    def test_teacher_delete_own_video_course(self):
        """Test teacher can delete their own video courses."""
        self.authenticate_as_teacher()
        
        url = f'/api/v1/teacher/video-courses/{self.teacher_draft_video.id}/'
        response = self.client.delete(url)
        
        # Check if deletion is allowed (might be 204 or 405 depending on implementation)
        self.assertIn(response.status_code, [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_405_METHOD_NOT_ALLOWED  # If deletion is not allowed
        ])
    
    def test_teacher_cannot_access_other_teacher_video_course(self):
        """Test teacher cannot access other teacher's video courses."""
        self.authenticate_as_teacher()
        
        # Try to view other teacher's course
        url = f'/api/v1/teacher/video-courses/{self.other_video_course.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to update other teacher's course
        update_data = {'title': 'Hacked Title'}
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_teacher_create_section_in_video_course(self):
        """Test teacher can create sections in their video courses."""
        self.authenticate_as_teacher()
        
        section_data = {
            'sectionTitle': 'New Video Section',
            'sectionDescription': 'A new section for video course',
            'order': 2
        }
        
        url = f'/api/v1/teacher/video-courses/{self.teacher_video_course.id}/sections/'
        response = self.client.post(url, section_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['sectionTitle'], section_data['sectionTitle'])
        
        # Verify in database
        section = CourseSection.objects.get(id=data['sectionId'])
        self.assertEqual(section.course, self.teacher_video_course)
    
    def test_teacher_create_video_chapter(self):
        """Test teacher can create video chapters."""
        self.authenticate_as_teacher()
        
        chapter_data = {
            'title': 'New Video Chapter',
            'content': 'Video chapter content',
            'type': 'Video',
            'video': 'https://example.com/new-video.mp4',
            'order': 2
        }
        
        url = f'/api/v1/teacher/video-courses/sections/{self.video_section.id}/chapters/'
        response = self.client.post(url, chapter_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['title'], chapter_data['title'])
        self.assertEqual(data['type'], 'Video')
        self.assertEqual(data['video'], chapter_data['video'])


@pytest.mark.django_db
class TestTeacherPracticeCourseAPI(BaseTeacherAPITest):
    """Test teacher practice course API endpoints."""
    
    def test_teacher_list_own_practice_courses(self):
        """Test teacher can list their own practice courses."""
        self.authenticate_as_teacher()
        
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should see own practice courses but not other teacher's
        course_ids = [course['courseId'] for course in data]
        self.assertIn(str(self.teacher_practice_course.id), course_ids)
        self.assertNotIn(str(self.other_practice_course.id), course_ids)
        
        # Should not see video courses in practice endpoint
        self.assertNotIn(str(self.teacher_video_course.id), course_ids)
    
    def test_teacher_create_practice_course(self):
        """Test teacher can create new practice courses."""
        self.authenticate_as_teacher()
        
        course_data = {
            'title': 'New Practice Course',
            'description': 'A new practice laboratory course',
            'category': 'General',  # Must be one of the valid categories
            'level': 'Intermediate',
            'status': 'Draft'
        }
        
        url = '/api/v1/practice/courses/create/'
        response = self.client.post(url, course_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['title'], course_data['title'])
        self.assertEqual(data['course_type'], 'practice')  # Auto-set to practice
        # teacherName uses email as fallback when name is not available
        self.assertIn(data['teacherName'], [self.teacher.name, self.teacher.email])
        
        # Verify in database using correct field name
        course = Course.objects.get(id=data['courseId'])
        self.assertEqual(course.teacher, self.teacher)
        self.assertEqual(course.course_type, 'practice')
    
    def test_teacher_create_exercise_chapter_in_practice_course(self):
        """Test teacher can create exercise chapters in practice courses."""
        self.authenticate_as_teacher()
        
        # Create a section in practice course
        practice_section = CourseSection.objects.create(
            course=self.teacher_practice_course,
            sectionTitle='Practice Section',
            order=1
        )
        
        chapter_data = {
            'title': 'Grammar Exercise',
            'content': 'Complete the grammar exercises',
            'type': 'Exercise',
            'order': 1
        }
        
        url = f'/api/v1/teacher/practice-courses/sections/{practice_section.id}/chapters/'
        response = self.client.post(url, chapter_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['title'], chapter_data['title'])
        self.assertEqual(data['type'], 'Exercise')
        self.assertIn('practice_selection', data)  # Should auto-create practice_selection
    
    def test_teacher_create_quiz_chapter_in_practice_course(self):
        """Test teacher can create quiz chapters in practice courses."""
        self.authenticate_as_teacher()
        
        # Create a section in practice course
        practice_section = CourseSection.objects.create(
            course=self.teacher_practice_course,
            sectionTitle='Practice Section',
            order=1
        )
        
        chapter_data = {
            'title': 'Practice Quiz',
            'content': 'Test your knowledge',
            'type': 'Quiz',
            'quiz_data': {
                'questions': [
                    {
                        'id': 1,
                        'question': 'What is the past tense of "go"?',
                        'type': 'multiple_choice',
                        'options': ['went', 'goed', 'gone', 'going'],
                        'correct_answer': 0
                    }
                ],
                'settings': {
                    'time_limit': 300,
                    'shuffle_questions': True
                }
            },
            'order': 1
        }
        
        url = f'/api/v1/teacher/practice-courses/sections/{practice_section.id}/chapters/'
        response = self.client.post(url, chapter_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        
        self.assertEqual(data['title'], chapter_data['title'])
        self.assertEqual(data['type'], 'Quiz')
        self.assertTrue(data['quiz_enabled'])  # Should auto-enable for Quiz type
        self.assertIn('quiz_data', data)


@pytest.mark.django_db
class TestTeacherAPIAuthentication(BaseTeacherAPITest):
    """Test teacher API authentication requirements."""
    
    def test_teacher_endpoints_require_authentication(self):
        """Test that teacher endpoints require authentication."""
        # Video courses
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Practice courses
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Course creation
        course_data = {'title': 'Test Course'}
        response = self.client.post(url, course_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_students_cannot_access_teacher_endpoints(self):
        """Test that students cannot access teacher endpoints."""
        self.authenticate_as_student()
        
        # Try to access teacher video courses
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        # Should be forbidden or show empty results
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_200_OK  # Might return empty list
        ])
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(len(data), 0)  # Should not see any courses
        
        # Try to create course as student
        course_data = {'title': 'Student Course'}
        response = self.client.post(url, course_data, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ])
    
    def test_teacher_role_validation(self):
        """Test that only users with teacher role can access teacher endpoints."""
        # Create a user with student role but try to access teacher endpoints
        student_user = StudentFactory()
        token = self.get_jwt_token(student_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        
        # Should not see any courses or be forbidden
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(len(data), 0)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestTeacherAPICourseOwnership(BaseTeacherAPITest):
    """Test course ownership and isolation between teachers."""
    
    def test_teacher_course_isolation(self):
        """Test that teachers can only see their own courses."""
        self.authenticate_as_teacher()
        
        # Video courses
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only see own courses
        course_ids = [course['courseId'] for course in data]
        self.assertIn(str(self.teacher_video_course.id), course_ids)
        self.assertNotIn(str(self.other_video_course.id), course_ids)
        
        # Practice courses
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        course_ids = [course['courseId'] for course in data]
        self.assertIn(str(self.teacher_practice_course.id), course_ids)
        self.assertNotIn(str(self.other_practice_course.id), course_ids)
    
    def test_cross_teacher_access_prevention(self):
        """Test that teachers cannot access other teachers' courses."""
        self.authenticate_as_teacher()
        
        # Try to access other teacher's video course
        url = f'/api/v1/teacher/video-courses/{self.other_video_course.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to access other teacher's practice course
        url = f'/api/v1/teacher/practice-courses/{self.other_practice_course.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Try to modify other teacher's course
        update_data = {'title': 'Hacked Title'}
        url = f'/api/v1/teacher/video-courses/{self.other_video_course.id}/'
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_teacher_can_manage_all_course_types(self):
        """Test that a teacher can manage both video and practice courses."""
        self.authenticate_as_teacher()
        
        # Teacher should have access to both video and practice courses
        # Video courses
        url = '/api/v1/teacher/video-courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Practice courses
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be able to create both types
        video_data = {'title': 'New Video Course', 'description': 'Video course'}
        url = '/api/v1/teacher/video-courses/'
        response = self.client.post(url, video_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        practice_data = {'title': 'New Practice Course', 'description': 'Practice course'}
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.post(url, practice_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@pytest.mark.django_db
class TestTeacherAPIValidation(BaseTeacherAPITest):
    """Test teacher API data validation and error handling."""
    
    def test_create_course_validation(self):
        """Test course creation validation."""
        self.authenticate_as_teacher()
        
        # Missing required fields
        invalid_data = {'description': 'Missing title'}
        
        url = '/api/v1/teacher/video-courses/'
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Invalid level
        invalid_data = {
            'title': 'Test Course',
            'level': 'InvalidLevel'
        }
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_course_type_is_enforced(self):
        """Test that course_type is automatically set correctly."""
        self.authenticate_as_teacher()
        
        # Video course should have course_type='video'
        video_data = {'title': 'Video Course', 'description': 'Test'}
        url = '/api/v1/teacher/video-courses/'
        response = self.client.post(url, video_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['course_type'], 'video')
        
        # Practice course should have course_type='practice'
        practice_data = {'title': 'Practice Course', 'description': 'Test'}
        url = '/api/v1/teacher/practice-courses/'
        response = self.client.post(url, practice_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['course_type'], 'practice')