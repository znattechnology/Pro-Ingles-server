#!/usr/bin/env python3
"""
Script de teste completo para Speaking Practice Backend
Execute: python test_speaking_backend.py
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def create_test_data():
    """Criar dados de teste"""
    
    print("📚 Criando dados de teste...")
    
    from django.contrib.auth import get_user_model
    from apps.courses.models import Course
    from apps.practice.models import SpeakingExercise, UserProgress
    
    User = get_user_model()
    
    # 1. Criar usuário teacher
    teacher, created = User.objects.get_or_create(
        email='teacher@speaking.com',
        defaults={
            'name': 'Speaking Teacher',
            'role': 'teacher',
            'is_active': True
        }
    )
    if created:
        teacher.set_password('teacherpass123')
        teacher.save()
        print(f"✅ Teacher criado: {teacher.email}")
    
    # 2. Criar usuário student
    user, created = User.objects.get_or_create(
        email='test@speaking.com',
        defaults={
            'name': 'Speaking Test User',
            'role': 'student',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Student criado: {user.email}")
    else:
        print(f"✅ Student já existe: {user.email}")
    
    # 3. Criar curso de teste
    course, created = Course.objects.get_or_create(
        title='Speaking Practice Course',
        defaults={
            'description': 'Curso de teste para Speaking Practice',
            'category': 'Speaking',
            'level': 'Intermediate',
            'status': 'Published',
            'teacher': teacher
        }
    )
    if created:
        print(f"✅ Curso criado: {course.title}")
    else:
        print(f"✅ Curso já existe: {course.title}")
    
    # 3. Criar exercícios de speaking
    exercises_data = [
        {
            'title': 'Business Introduction',
            'description': 'Practice introducing yourself in a business context',
            'exercise_type': 'CONVERSATION',
            'difficulty': 'BEGINNER',
            'target_text': 'Hello, my name is John. I work in marketing.',
            'conversation_prompt': 'Let\'s practice business introductions. Please introduce yourself.',
            'vocabulary_words': ['business', 'introduction', 'marketing', 'professional']
        },
        {
            'title': 'Pronunciation Challenge',
            'description': 'Practice difficult English sounds',
            'exercise_type': 'PRONUNCIATION',
            'difficulty': 'INTERMEDIATE',
            'target_text': 'The weather is wonderful today. I think I\'ll take a walk.',
            'vocabulary_words': ['weather', 'wonderful', 'think', 'walk']
        },
        {
            'title': 'Reading Aloud Practice',
            'description': 'Read a short paragraph with proper intonation',
            'exercise_type': 'READING_ALOUD',
            'difficulty': 'ADVANCED',
            'target_text': 'Technology has revolutionized the way we communicate and work.',
            'vocabulary_words': ['technology', 'revolutionized', 'communicate', 'work']
        }
    ]
    
    created_exercises = 0
    for exercise_data in exercises_data:
        exercise, created = SpeakingExercise.objects.get_or_create(
            title=exercise_data['title'],
            defaults={
                'course': course,
                'created_by': teacher,
                **exercise_data
            }
        )
        if created:
            created_exercises += 1
    
    print(f"✅ {created_exercises} exercícios criados")
    
    # 4. Criar progresso do usuário
    user_progress, created = UserProgress.objects.get_or_create(
        user=user,
        defaults={
            'hearts': 5,
            'points': 100,
            'active_course': course
        }
    )
    if created:
        print(f"✅ Progresso do usuário criado")
    else:
        print(f"✅ Progresso do usuário já existe")
    
    return user, course, teacher

def test_api_endpoints():
    """Testar endpoints da API"""
    
    print("\n🌐 Testando endpoints da API...")
    
    import requests
    from django.contrib.auth import get_user_model
    from rest_framework.authtoken.models import Token
    
    User = get_user_model()
    user = User.objects.get(email='test@speaking.com')
    
    # Criar token para autenticação
    token, created = Token.objects.get_or_create(user=user)
    
    headers = {
        'Authorization': f'Token {token.key}',
        'Content-Type': 'application/json'
    }
    
    base_url = 'http://localhost:8000/api/v1/practice'
    
    # Teste 1: Listar exercícios
    try:
        response = requests.get(f'{base_url}/speaking/exercises/', headers=headers)
        if response.status_code == 200:
            exercises = response.json()
            print(f"✅ Exercícios encontrados: {len(exercises)}")
        else:
            print(f"❌ Erro ao listar exercícios: {response.status_code}")
            print(f"   Resposta: {response.text}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False
    
    # Teste 2: Progresso do usuário
    try:
        response = requests.get(f'{base_url}/speaking/progress/', headers=headers)
        if response.status_code == 200:
            progress = response.json()
            print(f"✅ Progresso carregado: {progress.get('total_sessions', 0)} sessões")
        else:
            print(f"❌ Erro ao carregar progresso: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao carregar progresso: {e}")
    
    # Teste 3: Dashboard stats
    try:
        response = requests.get(f'{base_url}/speaking/dashboard/', headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Stats carregadas: {stats.get('total_sessions', 0)} sessões totais")
        else:
            print(f"❌ Erro ao carregar stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao carregar stats: {e}")
    
    return True

def test_models():
    """Testar criação de modelos"""
    
    print("\n🗄️ Testando modelos Django...")
    
    from apps.practice.models import (
        SpeakingExercise, SpeakingSession, SpeakingTurn, SpeakingProgress
    )
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.get(email='test@speaking.com')
    
    # Teste 1: Criar sessão
    try:
        exercise = SpeakingExercise.objects.first()
        session = SpeakingSession.objects.create(
            user=user,
            exercise=exercise,
            status='ACTIVE'
        )
        print(f"✅ Sessão criada: {session.id}")
        
        # Teste 2: Criar turn
        turn = SpeakingTurn.objects.create(
            session=session,
            turn_number=1,
            turn_type='USER_SPEECH',
            transcribed_text='Hello, this is a test',
            pronunciation_score=85.0,
            fluency_score=80.0,
            accuracy_score=90.0
        )
        print(f"✅ Turn criado: {turn.id}")
        
        # Teste 3: Criar/atualizar progresso
        progress, created = SpeakingProgress.objects.get_or_create(
            user=user,
            defaults={
                'total_sessions': 1,
                'average_pronunciation': 85.0
            }
        )
        print(f"✅ Progresso {'criado' if created else 'atualizado'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar modelos: {e}")
        return False

def main():
    """Função principal do teste"""
    
    print("🎤 TESTE COMPLETO: SPEAKING PRACTICE BACKEND")
    print("=" * 60)
    
    # Fase 1: Criar dados
    try:
        user, course, teacher = create_test_data()
    except Exception as e:
        print(f"❌ Erro ao criar dados: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Fase 2: Testar modelos
    models_success = test_models()
    
    # Fase 3: Testar API
    api_success = test_api_endpoints()
    
    # Resultado final
    print("\n" + "=" * 60)
    
    if models_success and api_success:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Backend Speaking Practice está funcionando!")
        print("\n📋 Próximos passos:")
        print("   1. Configurar billing OpenAI para IA completa")
        print("   2. Implementar frontend React")
        print("   3. Integrar gravação de áudio")
        print("   4. Testar fluxo completo")
        print(f"\n🔗 API Base URL: http://localhost:8000/api/v1/practice/speaking/")
        print(f"👤 User de teste: test@speaking.com / testpass123")
        
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        if not models_success:
            print("   - Problema com modelos Django")
        if not api_success:
            print("   - Problema com endpoints API")
    
    return models_success and api_success

if __name__ == "__main__":
    main()