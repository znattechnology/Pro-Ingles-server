"""
Management command to seed the practice database with sample data.

This command creates a complete practice course structure with:
- Units and Lessons
- Challenges with multiple choice and assist types
- Challenge options with correct answers
- Audio files for pronunciation
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.courses.models import Course
from apps.practice.models import (
    PracticeUnit, 
    PracticeLesson, 
    PracticeChallenge, 
    ChallengeOption, 
    UserProgress
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with practice laboratory data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing practice data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing practice data...')
            ChallengeOption.objects.all().delete()
            PracticeChallenge.objects.all().delete()
            PracticeLesson.objects.all().delete()
            PracticeUnit.objects.all().delete()
            UserProgress.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data.'))

        # Get or create a course - we need a teacher first
        try:
            # Try to get the first teacher user
            teacher = User.objects.filter(role='teacher').first()
            if not teacher:
                # If no teacher exists, create one
                teacher = User.objects.create_user(
                    email='teacher@example.com',
                    name='Practice Teacher',
                    role='teacher',
                    password='password123'
                )
                self.stdout.write('Created practice teacher user')

            # Create multiple specialized courses
            courses_data = [
                {
                    'title': 'Inglês Geral',
                    'description': 'Learn English from basics to advanced level',
                    'image': '/laboratory/challenges/english-1.jpg',
                    'category': 'General English',
                    'level': 'Beginner'
                },
                {
                    'title': 'Inglês para Negócios',
                    'description': 'Business English for professional communication',
                    'image': '/laboratory/challenges/english-2.jpg',
                    'category': 'Business English',
                    'level': 'Intermediate'
                },
                {
                    'title': 'Inglês para Tecnologia',
                    'description': 'Technical English for IT professionals',
                    'image': '/laboratory/challenges/english-1.jpg',
                    'category': 'Technical English',
                    'level': 'Intermediate'
                },
                {
                    'title': 'Inglês para o Setor Bancário',
                    'description': 'Financial English for banking professionals',
                    'image': '/laboratory/challenges/english-2.jpg',
                    'category': 'Financial English',
                    'level': 'Advanced'
                },
                {
                    'title': 'Inglês para o Setor Petrolífero',
                    'description': 'Oil and gas industry English',
                    'image': '/laboratory/challenges/english-1.jpg',
                    'category': 'Industry English',
                    'level': 'Advanced'
                }
            ]

            # Create all courses
            created_courses = []
            for course_data in courses_data:
                course, created = Course.objects.get_or_create(
                    title=course_data['title'],
                    defaults={
                        'teacher': teacher,
                        'teacherName': teacher.name,
                        'description': course_data['description'],
                        'image': course_data['image'],
                        'price': 0.00,
                        'category': course_data['category'],
                        'level': course_data['level'],
                        'status': 'Published'
                    }
                )
                created_courses.append(course)
                if created:
                    self.stdout.write(f'Created course: {course.title}')

            # Use the first course (Inglês Geral) for practice data
            course = created_courses[0]
        except Exception as e:
            self.stdout.write(f'Error creating course: {e}')
            return

        if created:
            self.stdout.write(f'Created course: {course.title}')
        else:
            self.stdout.write(f'Using existing course: {course.title}')

        # Create Units
        units_data = [
            {
                'title': 'Basic Vocabulary',
                'description': 'Learn essential English words and phrases',
                'order': 1,
                'lessons': [
                    {
                        'title': 'Greetings',
                        'order': 1,
                        'challenges': [
                            {
                                'type': 'SELECT',
                                'question': 'How do you say "Hello" in English?',
                                'order': 1,
                                'options': [
                                    {'text': 'Hello', 'is_correct': True, 'order': 1},
                                    {'text': 'Goodbye', 'is_correct': False, 'order': 2},
                                    {'text': 'Thank you', 'is_correct': False, 'order': 3},
                                    {'text': 'Please', 'is_correct': False, 'order': 4},
                                ]
                            },
                            {
                                'type': 'SELECT',
                                'question': 'What is the correct response to "How are you?"',
                                'order': 2,
                                'options': [
                                    {'text': 'I am fine, thank you', 'is_correct': True, 'order': 1},
                                    {'text': 'Hello', 'is_correct': False, 'order': 2},
                                    {'text': 'My name is John', 'is_correct': False, 'order': 3},
                                    {'text': 'Goodbye', 'is_correct': False, 'order': 4},
                                ]
                            },
                            {
                                'type': 'ASSIST',
                                'question': 'Select the correct translation of "Good morning"',
                                'order': 3,
                                'options': [
                                    {'text': 'Good morning', 'is_correct': True, 'order': 1},
                                    {'text': 'Good evening', 'is_correct': False, 'order': 2},
                                    {'text': 'Good night', 'is_correct': False, 'order': 3},
                                ]
                            }
                        ]
                    },
                    {
                        'title': 'Family Members',
                        'order': 2,
                        'challenges': [
                            {
                                'type': 'SELECT',
                                'question': 'Who is your father\'s father?',
                                'order': 1,
                                'options': [
                                    {'text': 'Grandfather', 'is_correct': True, 'order': 1},
                                    {'text': 'Uncle', 'is_correct': False, 'order': 2},
                                    {'text': 'Brother', 'is_correct': False, 'order': 3},
                                    {'text': 'Cousin', 'is_correct': False, 'order': 4},
                                ]
                            },
                            {
                                'type': 'SELECT',
                                'question': 'What do you call your parent\'s daughter?',
                                'order': 2,
                                'options': [
                                    {'text': 'Sister', 'is_correct': True, 'order': 1},
                                    {'text': 'Mother', 'is_correct': False, 'order': 2},
                                    {'text': 'Aunt', 'is_correct': False, 'order': 3},
                                    {'text': 'Friend', 'is_correct': False, 'order': 4},
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'title': 'Grammar Basics',
                'description': 'Learn fundamental English grammar rules',
                'order': 2,
                'lessons': [
                    {
                        'title': 'Verb "To Be"',
                        'order': 1,
                        'challenges': [
                            {
                                'type': 'SELECT',
                                'question': 'Complete: "I ___ a student"',
                                'order': 1,
                                'options': [
                                    {'text': 'am', 'is_correct': True, 'order': 1},
                                    {'text': 'is', 'is_correct': False, 'order': 2},
                                    {'text': 'are', 'is_correct': False, 'order': 3},
                                    {'text': 'be', 'is_correct': False, 'order': 4},
                                ]
                            },
                            {
                                'type': 'SELECT',
                                'question': 'Complete: "She ___ happy"',
                                'order': 2,
                                'options': [
                                    {'text': 'is', 'is_correct': True, 'order': 1},
                                    {'text': 'am', 'is_correct': False, 'order': 2},
                                    {'text': 'are', 'is_correct': False, 'order': 3},
                                    {'text': 'be', 'is_correct': False, 'order': 4},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        # Create the practice structure
        for unit_data in units_data:
            # Create unit
            unit = PracticeUnit.objects.create(
                course=course,
                title=unit_data['title'],
                description=unit_data['description'],
                order=unit_data['order']
            )
            self.stdout.write(f'Created unit: {unit.title}')

            # Create lessons
            for lesson_data in unit_data['lessons']:
                lesson = PracticeLesson.objects.create(
                    unit=unit,
                    title=lesson_data['title'],
                    order=lesson_data['order']
                )
                self.stdout.write(f'  Created lesson: {lesson.title}')

                # Create challenges
                for challenge_data in lesson_data['challenges']:
                    challenge = PracticeChallenge.objects.create(
                        lesson=lesson,
                        type=challenge_data['type'],
                        question=challenge_data['question'],
                        order=challenge_data['order']
                    )
                    self.stdout.write(f'    Created challenge: {challenge.question[:50]}...')

                    # Create challenge options
                    for option_data in challenge_data['options']:
                        audio_url = None
                        if option_data['text'].lower() in ['hello', 'good morning', 'i am fine, thank you']:
                            audio_url = '/laboratory/ing_woman.mp3'
                        elif option_data['text'].lower() in ['grandfather', 'sister']:
                            audio_url = '/laboratory/ing_man.mp3'

                        ChallengeOption.objects.create(
                            challenge=challenge,
                            text=option_data['text'],
                            is_correct=option_data['is_correct'],
                            audio_url=audio_url,
                            order=option_data['order']
                        )
                        self.stdout.write(f'      Created option: {option_data["text"]}')

        # Create sample user progress for all users
        users = User.objects.all()
        for user in users:
            user_progress, created = UserProgress.objects.get_or_create(
                user=user,
                defaults={
                    'active_course': course,
                    'hearts': 5,
                    'points': 0,
                    'user_image_src': '/mascot.jpg'
                }
            )
            if created:
                self.stdout.write(f'Created user progress for: {user.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded practice data!\n'
                f'Created:\n'
                f'- {PracticeUnit.objects.count()} units\n'
                f'- {PracticeLesson.objects.count()} lessons\n'
                f'- {PracticeChallenge.objects.count()} challenges\n'
                f'- {ChallengeOption.objects.count()} options\n'
                f'- {UserProgress.objects.count()} user progress records'
            )
        )