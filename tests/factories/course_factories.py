"""
Factory classes for Course-related models.
"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal

from apps.courses.models import Course, CourseSection, Chapter, CourseEnrollment
from .user_factories import TeacherFactory, StudentFactory


class CourseFactory(DjangoModelFactory):
    """Factory for creating Course instances."""
    
    class Meta:
        model = Course
        django_get_or_create = ('title', 'teacher')
    
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph', nb_sentences=3)
    category = factory.Iterator([
        'Inglês Geral', 'Inglês para Negócios', 'Inglês para Tecnologia',
        'Inglês Médico', 'Inglês Jurídico', 'Conversação', 'Gramática'
    ])
    level = factory.Iterator(['Beginner', 'Intermediate', 'Advanced'])
    status = factory.Iterator(['Draft', 'Published', 'Archived'])
    template = factory.Iterator(['general', 'business', 'technology', 'medical', 'legal'])
    course_type = factory.Iterator(['video', 'practice'])
    
    teacher = factory.SubFactory(TeacherFactory)
    
    @factory.lazy_attribute
    def teacherName(self):
        return self.teacher.name
    
    @factory.post_generation
    def sections(self, create, extracted, **kwargs):
        """Create sections after course creation."""
        if not create:
            return
        
        if extracted:
            for section_data in extracted:
                CourseSectionFactory(course=self, **section_data)
        else:
            # Create 2-3 default sections
            for i in range(2):
                CourseSectionFactory(course=self, order=i+1)


class CourseSectionFactory(DjangoModelFactory):
    """Factory for creating CourseSection instances."""
    
    class Meta:
        model = CourseSection
        django_get_or_create = ('course', 'order')
    
    course = factory.SubFactory(CourseFactory)
    sectionTitle = factory.Faker('sentence', nb_words=3)
    sectionDescription = factory.Faker('paragraph', nb_sentences=2)
    order = factory.Sequence(lambda n: n + 1)
    
    @factory.post_generation
    def chapters(self, create, extracted, **kwargs):
        """Create chapters after section creation."""
        if not create:
            return
        
        if extracted:
            for chapter_data in extracted:
                ChapterFactory(section=self, **chapter_data)
        else:
            # Create 3-5 default chapters
            for i in range(3):
                ChapterFactory(section=self, order=i+1)


class ChapterFactory(DjangoModelFactory):
    """Factory for creating Chapter instances."""
    
    class Meta:
        model = Chapter
        django_get_or_create = ('section', 'order')
    
    section = factory.SubFactory(CourseSectionFactory)
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('paragraph', nb_sentences=5)
    type = factory.Iterator(['Text', 'Quiz', 'Video'])
    video = factory.Faker('url')
    order = factory.Sequence(lambda n: n + 1)
    quiz_enabled = factory.Iterator([True, False])
    
    practice_lesson = None  # Simplified for now


class CourseEnrollmentFactory(DjangoModelFactory):
    """Factory for creating CourseEnrollment instances."""
    
    class Meta:
        model = CourseEnrollment
        django_get_or_create = ('user', 'course')
    
    user = factory.SubFactory(StudentFactory)
    course = factory.SubFactory(CourseFactory)
    enrollment_date = factory.Faker('date_time_this_year')


# Specialized Course Factories for different categories

class BusinessCourseFactory(CourseFactory):
    """Factory for Business English courses."""
    
    category = 'Inglês para Negócios'
    template = 'business'
    level = factory.Iterator(['Intermediate', 'Advanced'])


class TechnologyCourseFactory(CourseFactory):
    """Factory for Technology English courses."""
    
    category = 'Inglês para Tecnologia'
    template = 'technology'
    level = factory.Iterator(['Intermediate', 'Advanced'])


class MedicalCourseFactory(CourseFactory):
    """Factory for Medical English courses."""
    
    category = 'Inglês Médico'
    template = 'medical'
    level = 'Advanced'  # Medical courses are always advanced


class BeginnerCourseFactory(CourseFactory):
    """Factory for Beginner level courses."""
    
    level = 'Beginner'
    category = factory.Iterator(['Inglês Geral', 'Conversação', 'Gramática'])
    template = 'general'


class VideoCourseFactory(CourseFactory):
    """Factory for video courses specifically."""
    
    course_type = 'video'


class PracticeCourseFactory(CourseFactory):
    """Factory for practice laboratory courses."""
    
    course_type = 'practice'


class PublishedVideoCourseFactory(CourseFactory):
    """Factory for published video courses with full content."""
    
    status = 'Published'
    course_type = 'video'


class PublishedPracticeCourseFactory(CourseFactory):
    """Factory for published practice courses."""
    
    status = 'Published'
    course_type = 'practice'


class PublishedCourseFactory(CourseFactory):
    """Factory for published courses with full content."""
    
    status = 'Published'
    
    @factory.post_generation
    def create_full_content(self, create, extracted, **kwargs):
        """Create full course content."""
        if not create:
            return
        
        # Create 3 sections with 4 chapters each
        for section_order in range(1, 4):
            section = CourseSectionFactory(
                course=self,
                order=section_order,
                sectionTitle=f'Section {section_order}'
            )
            
            for chapter_order in range(1, 5):
                ChapterFactory(
                    section=section,
                    order=chapter_order,
                    title=f'Chapter {section_order}.{chapter_order}'
                )