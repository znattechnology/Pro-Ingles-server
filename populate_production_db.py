#!/usr/bin/env python
"""
Script para popular o banco de dados de produção com usuários e cursos de exemplo.
Execute: python populate_production_db.py
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Erro ao configurar Django: {e}")
    sys.exit(1)

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.courses.models import Course, CourseSection, Chapter
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from decimal import Decimal

User = get_user_model()

def create_users():
    """Criar usuários de exemplo para teste."""
    
    print("🔧 Criando usuários de exemplo...")
    
    users_data = [
        {
            'email': 'admin@proenglish.com',
            'password': 'Admin123!',
            'first_name': 'Admin',
            'last_name': 'Sistema',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'phone': '+351910000001',
        },
        {
            'email': 'professor@proenglish.com',
            'password': 'Professor123!',
            'first_name': 'João',
            'last_name': 'Professor',
            'role': 'teacher',
            'is_staff': True,
            'is_superuser': False,
            'phone': '+351910000002',
        },
        {
            'email': 'estudante@proenglish.com',
            'password': 'Estudante123!',
            'first_name': 'Maria',
            'last_name': 'Estudante',
            'role': 'student',
            'is_staff': False,
            'is_superuser': False,
            'phone': '+351910000003',
        }
    ]
    
    created_users = {}
    
    for user_data in users_data:
        email = user_data['email']
        
        # Verificar se usuário já existe
        if User.objects.filter(email=email).exists():
            print(f"✅ Usuário {email} já existe")
            created_users[user_data['role']] = User.objects.get(email=email)
            continue
        
        try:
            # Criar usuário
            full_name = f"{user_data['first_name']} {user_data['last_name']}"
            user = User.objects.create_user(
                email=email,
                name=full_name,
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                role=user_data['role'],
                is_staff=user_data['is_staff'],
                is_superuser=user_data['is_superuser'],
                is_active=True,
                email_verified=True
            )
            
            created_users[user_data['role']] = user
            print(f"✅ Usuário criado: {email} ({user_data['role']})")
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário {email}: {e}")
    
    return created_users

def create_subscription_plans():
    """Criar planos de assinatura se não existirem."""
    
    print("📋 Verificando planos de assinatura...")
    
    plans_data = [
        {
            'name': 'Plano Gratuito',
            'description': 'Acesso básico ao conteúdo',
            'price': Decimal('0.00'),
            'billing_cycle': 'monthly',
            'features': ['Acesso a cursos básicos', 'Suporte por email'],
            'max_courses': 3,
            'max_downloads': 10,
            'is_active': True,
        },
        {
            'name': 'Tuwi Premium',
            'description': 'Acesso completo com funcionalidades avançadas',
            'price': Decimal('29.90'),
            'billing_cycle': 'monthly',
            'features': ['Acesso ilimitado', 'Suporte prioritário', 'Downloads ilimitados'],
            'max_courses': 999,
            'max_downloads': 999,
            'is_active': True,
        },
        {
            'name': 'Tuwi Premium Plus',
            'description': 'Plano completo com mentoria personalizada',
            'price': Decimal('49.90'),
            'billing_cycle': 'monthly',
            'features': ['Tudo do Premium', 'Mentoria 1-on-1', 'Certificados'],
            'max_courses': 999,
            'max_downloads': 999,
            'is_active': True,
        }
    ]
    
    for plan_data in plans_data:
        plan, created = SubscriptionPlan.objects.get_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )
        
        if created:
            print(f"✅ Plano criado: {plan.name}")
        else:
            print(f"✅ Plano já existe: {plan.name}")

def create_sample_courses(teacher_user):
    """Criar cursos de exemplo."""
    
    print("📚 Criando cursos de exemplo...")
    
    # Cursos de Vídeo
    video_courses_data = [
        {
            'title': 'English Grammar Fundamentals',
            'description': 'Master the basics of English grammar with comprehensive video lessons.',
            'course_type': 'video',
            'status': 'Published',
            'category': 'Grammar',
            'level': 'Beginner',
            'sections': [
                {
                    'title': 'Introduction to Grammar',
                    'description': 'Basic grammar concepts',
                    'chapters': [
                        {
                            'title': 'What is Grammar?',
                            'description': 'Understanding the fundamentals',
                            'type': 'Video',
                            'video': 'https://example.com/video1.mp4'
                        },
                        {
                            'title': 'Parts of Speech',
                            'description': 'Nouns, verbs, adjectives and more',
                            'type': 'Video',
                            'video': 'https://example.com/video2.mp4'
                        }
                    ]
                },
                {
                    'title': 'Sentence Structure',
                    'description': 'Building proper sentences',
                    'chapters': [
                        {
                            'title': 'Simple Sentences',
                            'description': 'Subject + Verb + Object',
                            'type': 'Video',
                            'video': 'https://example.com/video3.mp4'
                        }
                    ]
                }
            ]
        },
        {
            'title': 'Business English Conversations',
            'description': 'Professional English for workplace communication.',
            'course_type': 'video',
            'status': 'Published',
            'category': 'Business',
            'level': 'Intermediate',
            'sections': [
                {
                    'title': 'Meeting English',
                    'description': 'Language for business meetings',
                    'chapters': [
                        {
                            'title': 'Starting a Meeting',
                            'description': 'Opening phrases and introductions',
                            'type': 'Video',
                            'video': 'https://example.com/business1.mp4'
                        }
                    ]
                }
            ]
        }
    ]
    
    # Cursos Práticos
    practice_courses_data = [
        {
            'title': 'Daily English Practice',
            'description': 'Interactive exercises for everyday English skills.',
            'course_type': 'practice',
            'status': 'Published',
            'category': 'General',
            'level': 'Beginner',
            'sections': [
                {
                    'title': 'Basic Conversations',
                    'description': 'Practice everyday dialogues',
                    'chapters': [
                        {
                            'title': 'Greeting People',
                            'description': 'How to say hello and introduce yourself',
                            'type': 'Exercise',
                            'practice_selection': {
                                'type': 'multiple_choice',
                                'question': 'How do you greet someone in the morning?',
                                'options': ['Good morning', 'Good evening', 'Good night', 'Goodbye'],
                                'correct_answer': 'Good morning'
                            }
                        },
                        {
                            'title': 'Asking for Directions',
                            'description': 'Practice asking and giving directions',
                            'type': 'Exercise',
                            'practice_selection': {
                                'type': 'fill_in_blank',
                                'question': 'Excuse me, _____ you tell me how to get to the train station?',
                                'correct_answer': 'can'
                            }
                        }
                    ]
                }
            ]
        },
        {
            'title': 'English Pronunciation Practice',
            'description': 'Improve your English pronunciation with guided exercises.',
            'course_type': 'practice',
            'status': 'Published',
            'category': 'Pronunciation',
            'level': 'All Levels',
            'sections': [
                {
                    'title': 'Vowel Sounds',
                    'description': 'Master English vowel pronunciation',
                    'chapters': [
                        {
                            'title': 'Short Vowels',
                            'description': 'Practice /æ/, /ɛ/, /ɪ/, /ɒ/, /ʌ/',
                            'type': 'Exercise',
                            'practice_selection': {
                                'type': 'speaking',
                                'question': 'Repeat after the audio: "cat, bat, hat"',
                                'audio_url': 'https://example.com/vowels1.mp3'
                            }
                        }
                    ]
                }
            ]
        }
    ]
    
    created_courses = []
    
    # Criar cursos de vídeo
    for course_data in video_courses_data:
        course, created = Course.objects.get_or_create(
            title=course_data['title'],
            defaults={
                'description': course_data['description'],
                'course_type': course_data['course_type'],
                'status': course_data['status'],
                'category': course_data['category'],
                'level': course_data['level'],
                'teacher': teacher_user,
                'created_at': timezone.now(),
                'updated_at': timezone.now(),
            }
        )
        
        if created:
            print(f"✅ Curso criado: {course.title}")
            
            # Criar seções e capítulos
            for section_data in course_data['sections']:
                section = CourseSection.objects.create(
                    course=course,
                    sectionTitle=section_data['title'],
                    order=1
                )
                
                for chapter_data in section_data['chapters']:
                    Chapter.objects.create(
                        section=section,
                        title=chapter_data['title'],
                        content=chapter_data['description'],
                        type=chapter_data['type'],
                        video=chapter_data.get('video', ''),
                        order=1
                    )
        else:
            print(f"✅ Curso já existe: {course.title}")
        
        created_courses.append(course)
    
    # Criar cursos práticos
    for course_data in practice_courses_data:
        course, created = Course.objects.get_or_create(
            title=course_data['title'],
            defaults={
                'description': course_data['description'],
                'course_type': course_data['course_type'],
                'status': course_data['status'],
                'category': course_data['category'],
                'level': course_data['level'],
                'teacher': teacher_user,
                'created_at': timezone.now(),
                'updated_at': timezone.now(),
            }
        )
        
        if created:
            print(f"✅ Curso prático criado: {course.title}")
            
            # Criar seções e capítulos
            for section_data in course_data['sections']:
                section = CourseSection.objects.create(
                    course=course,
                    sectionTitle=section_data['title'],
                    order=1
                )
                
                for chapter_data in section_data['chapters']:
                    Chapter.objects.create(
                        section=section,
                        title=chapter_data['title'],
                        content=chapter_data['description'],
                        type=chapter_data['type'],
                        practice_selection=chapter_data.get('practice_selection', {}),
                        order=1
                    )
        else:
            print(f"✅ Curso prático já existe: {course.title}")
        
        created_courses.append(course)
    
    return created_courses

def assign_subscriptions(users):
    """Atribuir assinaturas aos usuários."""
    
    print("💳 Configurando assinaturas...")
    
    # Obter planos
    free_plan = SubscriptionPlan.objects.filter(name='Plano Gratuito').first()
    premium_plan = SubscriptionPlan.objects.filter(name='Tuwi Premium').first()
    
    if not free_plan or not premium_plan:
        print("❌ Planos de assinatura não encontrados")
        return
    
    # Assinatura para estudante (gratuito)
    if 'student' in users:
        student_user = users['student']
        subscription, created = UserSubscription.objects.get_or_create(
            user=student_user,
            defaults={
                'plan': free_plan,
                'status': 'active',
                'start_date': timezone.now(),
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + timezone.timedelta(days=30),
            }
        )
        
        if created:
            print(f"✅ Assinatura gratuita criada para {student_user.email}")
        else:
            print(f"✅ Assinatura já existe para {student_user.email}")
    
    # Assinatura para professor (premium)
    if 'teacher' in users:
        teacher_user = users['teacher']
        subscription, created = UserSubscription.objects.get_or_create(
            user=teacher_user,
            defaults={
                'plan': premium_plan,
                'status': 'active',
                'start_date': timezone.now(),
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + timezone.timedelta(days=30),
            }
        )
        
        if created:
            print(f"✅ Assinatura premium criada para {teacher_user.email}")
        else:
            print(f"✅ Assinatura já existe para {teacher_user.email}")

def main():
    """Função principal."""
    
    print("🚀 Iniciando população do banco de dados de produção...\n")
    
    try:
        with transaction.atomic():
            # 1. Criar usuários
            users = create_users()
            print()
            
            # 2. Criar planos de assinatura
            create_subscription_plans()
            print()
            
            # 3. Criar cursos de exemplo
            if 'teacher' in users:
                courses = create_sample_courses(users['teacher'])
                print()
            
            # 4. Atribuir assinaturas
            assign_subscriptions(users)
            print()
            
            print("🎉 População do banco de dados concluída com sucesso!")
            print("\n" + "="*60)
            print("📋 USUÁRIOS CRIADOS:")
            print("="*60)
            print("🔧 ADMIN")
            print("  Email: admin@proenglish.com")
            print("  Senha: Admin123!")
            print("  Dashboard: /admin/dashboard")
            print("  Acesso: Gestão completa do sistema")
            print()
            print("👨‍🏫 PROFESSOR")
            print("  Email: professor@proenglish.com")
            print("  Senha: Professor123!")
            print("  Dashboard: /teacher/courses")
            print("  Acesso: Gestão de cursos e estudantes")
            print()
            print("🎓 ESTUDANTE")
            print("  Email: estudante@proenglish.com")
            print("  Senha: Estudante123!")
            print("  Dashboard: /user/courses")
            print("  Acesso: Visualização de cursos e progresso")
            print("="*60)
            print("🌐 URLs:")
            print("  Frontend: https://pro-ingles-client-nine.vercel.app")
            print("  Backend: http://pro-english-alb-343566329.eu-west-1.elb.amazonaws.com")
            print("  Admin: http://pro-english-alb-343566329.eu-west-1.elb.amazonaws.com/admin/")
            print("="*60)
            
    except Exception as e:
        print(f"❌ Erro durante a população: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()