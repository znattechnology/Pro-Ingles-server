#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.courses.models import Course, CourseSection, Chapter
from apps.users.models import User
import uuid

def create_demo_courses():
    # Get the first teacher user
    try:
        teacher = User.objects.filter(role='teacher').first()
        if not teacher:
            print("❌ Nenhum professor encontrado. Criando um...")
            teacher = User.objects.create(
                name="Prof. Demo",
                email="teacher@demo.com",
                role='teacher'
            )
    except Exception as e:
        print(f"Erro ao buscar professor: {e}")
        return

    courses_data = [
        {
            'title': 'English for Business Communication',
            'description': 'Master professional English communication skills for the modern workplace. Learn business vocabulary, email writing, presentations, and meeting etiquette.',
            'category': 'Business English',
            'level': 'Intermediate',
            'template': 'business',
            'price': 7999,  # €79.99
            'sections': [
                {
                    'title': 'Professional Email Writing',
                    'description': 'Learn to write clear, professional emails',
                    'chapters': [
                        'Email Structure and Format',
                        'Professional Tone and Language',
                        'Common Business Email Types'
                    ]
                },
                {
                    'title': 'Presentation Skills',
                    'description': 'Deliver confident business presentations',
                    'chapters': [
                        'Introduction and Opening Techniques',
                        'Structuring Your Presentation',
                        'Handling Questions and Closing'
                    ]
                }
            ]
        },
        {
            'title': 'Medical English for Healthcare Professionals',
            'description': 'Essential English for doctors, nurses, and healthcare workers. Covers medical terminology, patient communication, and clinical documentation.',
            'category': 'Medical English',
            'level': 'Advanced', 
            'template': 'medical',
            'price': 9999,  # €99.99
            'sections': [
                {
                    'title': 'Medical Terminology',
                    'description': 'Essential medical vocabulary and terminology',
                    'chapters': [
                        'Anatomy and Body Systems',
                        'Symptoms and Conditions',
                        'Treatment and Procedures'
                    ]
                },
                {
                    'title': 'Patient Communication',
                    'description': 'Effective communication with patients',
                    'chapters': [
                        'Taking Patient History',
                        'Explaining Diagnoses',
                        'Treatment Instructions'
                    ]
                }
            ]
        },
        {
            'title': 'English for Tech Professionals',
            'description': 'Technical English for software developers, IT professionals, and engineers. Focus on technical documentation, code reviews, and team collaboration.',
            'category': 'Technology',
            'level': 'Intermediate',
            'template': 'technology',
            'price': 6999,  # €69.99
            'sections': [
                {
                    'title': 'Technical Documentation',
                    'description': 'Writing clear technical documents',
                    'chapters': [
                        'API Documentation Best Practices',
                        'User Manuals and Guides',
                        'Code Comments and README Files'
                    ]
                },
                {
                    'title': 'Team Communication',
                    'description': 'Collaborating effectively in tech teams',
                    'chapters': [
                        'Code Review Communication',
                        'Sprint Planning and Stand-ups',
                        'Technical Problem Solving'
                    ]
                }
            ]
        },
        {
            'title': 'Legal English Fundamentals',
            'description': 'English for legal professionals, paralegals, and law students. Covers legal terminology, contract language, and court procedures.',
            'category': 'Legal English',
            'level': 'Advanced',
            'template': 'legal',
            'price': 11999,  # €119.99
            'sections': [
                {
                    'title': 'Contract Language',
                    'description': 'Understanding and drafting contracts',
                    'chapters': [
                        'Contract Structure and Clauses',
                        'Terms and Conditions',
                        'Legal Obligations and Rights'
                    ]
                },
                {
                    'title': 'Court Procedures',
                    'description': 'English for courtroom and legal proceedings',
                    'chapters': [
                        'Legal Proceedings Vocabulary',
                        'Evidence and Testimony',
                        'Legal Arguments and Motions'
                    ]
                }
            ]
        },
        {
            'title': 'English Conversation Mastery',
            'description': 'Improve your conversational English skills with real-world scenarios, idioms, and cultural context. Perfect for everyday communication.',
            'category': 'General English',
            'level': 'Beginner',
            'template': 'general',
            'price': 4999,  # €49.99
            'sections': [
                {
                    'title': 'Daily Conversations',
                    'description': 'Common everyday conversation topics',
                    'chapters': [
                        'Introducing Yourself',
                        'Talking About Hobbies',
                        'Making Plans and Appointments'
                    ]
                },
                {
                    'title': 'Cultural Context',
                    'description': 'Understanding cultural nuances in English',
                    'chapters': [
                        'Idioms and Expressions',
                        'Small Talk and Social Situations',
                        'Cultural Differences and Etiquette'
                    ]
                }
            ]
        }
    ]

    created_courses = 0
    
    for course_data in courses_data:
        try:
            # Check if course already exists
            if Course.objects.filter(title=course_data['title']).exists():
                print(f"⏭️ Curso já existe: {course_data['title']}")
                continue
                
            course = Course.objects.create(
                id=uuid.uuid4(),
                teacher=teacher,
                title=course_data['title'],
                description=course_data['description'],
                category=course_data['category'],
                level=course_data['level'],
                template=course_data['template'],
                price=course_data['price'],
                status='Published',
                image='/laboratory/challenges/english-business.jpg'  # Default image
            )
            
            created_courses += 1
            print(f"✅ Curso criado: {course.title}")
            
            # Create sections and chapters
            for section_index, section_data in enumerate(course_data['sections']):
                section = CourseSection.objects.create(
                    id=uuid.uuid4(),
                    course=course,
                    sectionTitle=section_data['title'],
                    sectionDescription=section_data['description'],
                    order=section_index + 1
                )
                
                print(f"  📁 Seção: {section.sectionTitle}")
                
                for chapter_index, chapter_title in enumerate(section_data['chapters']):
                    chapter = Chapter.objects.create(
                        id=uuid.uuid4(),
                        section=section,
                        title=chapter_title,
                        content=f"Este capítulo cobre {chapter_title.lower()}. Você aprenderá conceitos fundamentais, técnicas práticas e aplicações do mundo real.\n\nPontos principais:\n- Conceitos teóricos\n- Exemplos práticos\n- Exercícios aplicados\n- Estudos de caso\n\nAo final deste capítulo, você será capaz de aplicar esses conceitos em situações reais.",
                        type='Text',
                        order=chapter_index + 1
                    )
                    
                    print(f"    📖 Capítulo: {chapter.title}")
        
        except Exception as e:
            print(f"❌ Erro ao criar curso {course_data['title']}: {e}")
    
    print(f"\n🎉 {created_courses} cursos criados com sucesso!")
    return created_courses

if __name__ == "__main__":
    create_demo_courses()