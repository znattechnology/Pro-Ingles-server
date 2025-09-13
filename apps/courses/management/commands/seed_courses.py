"""
Management command to seed course data.

This command creates sample courses, sections, and chapters
based on the Node.js seed data structure.
"""

import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.courses.models import (
    Course, CourseSection, Chapter, CourseEnrollment, UserCourseProgress
)


class Command(BaseCommand):
    help = 'Seed course data with sample courses, sections, and chapters'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing course data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing course data...')
            Course.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        # Create teacher if doesn't exist
        teacher, created = User.objects.get_or_create(
            email='teacher@proenglish.com',
            defaults={
                'name': 'Professor ProEnglish',
                'role': 'teacher',
                'email_verified': True
            }
        )
        if created:
            self.stdout.write(f'Created teacher: {teacher.name}')

        # Create sample student for enrollments
        student, created = User.objects.get_or_create(
            email='student@proenglish.com',
            defaults={
                'name': 'Estudante ProEnglish',
                'role': 'student',
                'email_verified': True
            }
        )
        if created:
            self.stdout.write(f'Created student: {student.name}')

        # Course data based on Node.js seed
        courses_data = [
            {
                'title': 'Introduction to Programming',
                'description': 'Learn the basics of programming with this comprehensive course.',
                'category': 'Computer Science',
                'image': 'https://images.pexels.com/photos/5905888/pexels-photo-5905888.jpeg',
                'price': 99.99,
                'level': 'Beginner',
                'status': 'Published',
                'template': 'technology',
                'sections': [
                    {
                        'title': 'Getting Started',
                        'description': 'Introduction to programming concepts',
                        'order': 1,
                        'chapters': [
                            {
                                'title': 'What is Programming?',
                                'content': 'Programming is the process of creating a set of instructions that tell a computer how to perform a task.',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'Setting up your Environment',
                                'content': 'Learn how to set up your development environment.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4',
                                'order': 2
                            },
                            {
                                'title': 'Your First Program',
                                'content': 'Write your first "Hello World" program.',
                                'type': 'Quiz',
                                'order': 3
                            }
                        ]
                    },
                    {
                        'title': 'Programming Fundamentals',
                        'description': 'Core programming concepts',
                        'order': 2,
                        'chapters': [
                            {
                                'title': 'Variables and Data Types',
                                'content': 'Understanding variables and different data types in programming.',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'Control Structures',
                                'content': 'Learn about if statements, loops, and other control structures.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4',
                                'order': 2
                            },
                            {
                                'title': 'Functions and Methods',
                                'content': 'Understanding how to create and use functions.',
                                'type': 'Text',
                                'order': 3
                            }
                        ]
                    },
                    {
                        'title': 'Advanced Concepts',
                        'description': 'Advanced programming topics',
                        'order': 3,
                        'chapters': [
                            {
                                'title': 'Object-Oriented Programming',
                                'content': 'Introduction to OOP concepts like classes, objects, inheritance.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_3mb.mp4',
                                'order': 1
                            },
                            {
                                'title': 'Error Handling',
                                'content': 'Learn how to handle errors and exceptions in your code.',
                                'type': 'Text',
                                'order': 2
                            },
                            {
                                'title': 'Final Project',
                                'content': 'Build a complete application using everything you have learned.',
                                'type': 'Quiz',
                                'order': 3
                            }
                        ]
                    }
                ]
            },
            {
                'title': 'Advanced Machine Learning',
                'description': 'Dive deep into machine learning algorithms and techniques.',
                'category': 'Artificial Intelligence',
                'image': 'https://images.pexels.com/photos/6303596/pexels-photo-6303596.jpeg',
                'price': 149.99,
                'level': 'Advanced',
                'status': 'Published',
                'template': 'technology',
                'sections': [
                    {
                        'title': 'Machine Learning Foundations',
                        'description': 'Core ML concepts and mathematics',
                        'order': 1,
                        'chapters': [
                            {
                                'title': 'Introduction to Machine Learning',
                                'content': 'What is machine learning and how does it work?',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'Types of Neural Networks',
                                'content': 'Explore different neural network architectures.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_4mb.mp4',
                                'order': 2
                            },
                            {
                                'title': 'Mathematics for ML',
                                'content': 'Essential mathematical concepts for machine learning.',
                                'type': 'Quiz',
                                'order': 3
                            }
                        ]
                    },
                    {
                        'title': 'Deep Learning',
                        'description': 'Advanced neural networks',
                        'order': 2,
                        'chapters': [
                            {
                                'title': 'Convolutional Neural Networks',
                                'content': 'Learn about CNNs for image processing.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_5mb.mp4',
                                'order': 1
                            },
                            {
                                'title': 'Recurrent Neural Networks',
                                'content': 'Understanding RNNs for sequential data.',
                                'type': 'Text',
                                'order': 2
                            },
                            {
                                'title': 'Transfer Learning',
                                'content': 'Using pre-trained models for your tasks.',
                                'type': 'Quiz',
                                'order': 3
                            }
                        ]
                    },
                    {
                        'title': 'Practical Applications',
                        'description': 'Real-world ML applications',
                        'order': 3,
                        'chapters': [
                            {
                                'title': 'Computer Vision Projects',
                                'content': 'Build image classification and object detection systems.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_6mb.mp4',
                                'order': 1
                            },
                            {
                                'title': 'Natural Language Processing',
                                'content': 'Working with text data and language models.',
                                'type': 'Text',
                                'order': 2
                            },
                            {
                                'title': 'Deployment and Production',
                                'content': 'Deploy your ML models to production.',
                                'type': 'Quiz',
                                'order': 3
                            }
                        ]
                    }
                ]
            },
            {
                'title': 'Web Development Fundamentals',
                'description': 'Learn the basics of HTML, CSS, and JavaScript to build modern websites.',
                'category': 'Web Development',
                'image': 'https://images.pexels.com/photos/6001397/pexels-photo-6001397.jpeg',
                'price': 79.99,
                'level': 'Beginner',
                'status': 'Published',
                'template': 'technology',
                'sections': [
                    {
                        'title': 'HTML Fundamentals',
                        'description': 'Learn the structure of web pages',
                        'order': 1,
                        'chapters': [
                            {
                                'title': 'Introduction to HTML',
                                'content': 'What is HTML and how to create basic web pages.',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'HTML Elements and Tags',
                                'content': 'Learn about different HTML elements and how to use them.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_7mb.mp4',
                                'order': 2
                            }
                        ]
                    },
                    {
                        'title': 'CSS Styling',
                        'description': 'Make your websites look beautiful',
                        'order': 2,
                        'chapters': [
                            {
                                'title': 'CSS Layout Techniques',
                                'content': 'Learn about Flexbox, Grid, and other layout methods.',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'Responsive Design',
                                'content': 'Create websites that work on all devices.',
                                'type': 'Video',
                                'video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_8mb.mp4',
                                'order': 2
                            }
                        ]
                    },
                    {
                        'title': 'JavaScript Interactivity',
                        'description': 'Add dynamic behavior to your websites',
                        'order': 3,
                        'chapters': [
                            {
                                'title': 'JavaScript Basics',
                                'content': 'Variables, functions, and basic programming concepts in JavaScript.',
                                'type': 'Text',
                                'order': 1
                            },
                            {
                                'title': 'DOM Manipulation',
                                'content': 'How to change web page content with JavaScript.',
                                'type': 'Quiz',
                                'order': 2
                            }
                        ]
                    }
                ]
            }
        ]

        self.stdout.write('Creating courses...')
        created_count = 0

        for course_data in courses_data:
            # Check if course already exists by title
            if Course.objects.filter(title=course_data['title']).exists():
                self.stdout.write(f'Course {course_data["title"]} already exists, skipping...')
                continue

            # Create course
            course = Course.objects.create(
                teacher=teacher,
                teacherName=teacher.name,
                title=course_data['title'],
                description=course_data['description'],
                category=course_data['category'],
                image=course_data['image'],
                price=course_data['price'],
                level=course_data['level'],
                status=course_data['status'],
                template=course_data['template']
            )

            # Create sections and chapters
            for section_data in course_data['sections']:
                section = CourseSection.objects.create(
                    course=course,
                    sectionTitle=section_data['title'],
                    sectionDescription=section_data['description'],
                    order=section_data['order']
                )

                for chapter_data in section_data['chapters']:
                    chapter = Chapter.objects.create(
                        section=section,
                        title=chapter_data['title'],
                        content=chapter_data['content'],
                        type=chapter_data['type'],
                        video=chapter_data.get('video', ''),
                        order=chapter_data['order']
                    )

            # Create enrollment for the sample student
            enrollment, created = CourseEnrollment.objects.get_or_create(
                user=student,
                course=course
            )

            # Create progress for the student
            if created:
                progress = UserCourseProgress.objects.create(
                    user=student,
                    course=course,
                    enrollmentDate=timezone.now(),
                    overallProgress=45.0 if course.title == 'Introduction to Programming' else 
                                  (20.0 if course.title == 'Advanced Machine Learning' else 60.0)
                )

            created_count += 1
            self.stdout.write(f'Created course: {course.title}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} courses with sections and chapters')
        )