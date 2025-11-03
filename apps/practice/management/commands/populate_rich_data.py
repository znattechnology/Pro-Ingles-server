"""
Script completo para popular o sistema com dados ricos:
- Unidades e lições avançadas
- Sistema de conquistas completo  
- Rankings e ligas
- Progressos de usuários
- Exercícios de speaking e listening
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

from apps.courses.models import Course
from apps.practice.models import (
    PracticeUnit, PracticeLesson, PracticeChallenge, ChallengeOption,
    UserProgress, Achievement, AchievementCategory, UserAchievement,
    UserLeague, LeaguePromotion, Competition, CompetitionParticipant,
    LeaderboardSnapshot, UserStreak, ChallengeProgress,
    SpeakingExercise, ListeningExercise
)
from django.db import models

User = get_user_model()


class Command(BaseCommand):
    help = 'Popular o sistema com dados ricos para demonstração completa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpar dados existentes antes de popular',
        )
        parser.add_argument(
            '--units-only',
            action='store_true',
            help='Criar apenas unidades e lições',
        )
        parser.add_argument(
            '--achievements-only', 
            action='store_true',
            help='Criar apenas conquistas',
        )
        parser.add_argument(
            '--rankings-only',
            action='store_true',
            help='Criar apenas rankings e ligas',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_data()

        if options['units_only']:
            self.create_rich_practice_content()
        elif options['achievements_only']:
            self.create_achievements_system()
        elif options['rankings_only']:
            self.create_rankings_and_leagues()
        else:
            # Criar tudo
            self.create_rich_practice_content()
            self.create_achievements_system() 
            self.create_rankings_and_leagues()
            self.create_speaking_listening_exercises()
            self.simulate_user_activity()

        self.show_summary()

    def clear_existing_data(self):
        """Limpar dados existentes"""
        self.stdout.write('🧹 Limpando dados existentes...')
        
        # Ordem específica para evitar violações de foreign key
        UserAchievement.objects.all().delete()
        Achievement.objects.all().delete()
        AchievementCategory.objects.all().delete()
        
        CompetitionParticipant.objects.all().delete()
        Competition.objects.all().delete()
        LeaderboardSnapshot.objects.all().delete()
        LeaguePromotion.objects.all().delete()
        UserLeague.objects.all().delete()
        UserStreak.objects.all().delete()
        
        ChallengeProgress.objects.all().delete()
        ChallengeOption.objects.all().delete()
        PracticeChallenge.objects.all().delete()
        PracticeLesson.objects.all().delete()
        PracticeUnit.objects.all().delete()
        
        SpeakingExercise.objects.all().delete()
        ListeningExercise.objects.all().delete()
        
        # Manter UserProgress mas resetar
        UserProgress.objects.update(
            hearts=5, points=0, total_speaking_sessions=0,
            total_listening_sessions=0, average_pronunciation_score=0.0
        )
        
        self.stdout.write('✅ Dados limpos com sucesso')

    def create_rich_practice_content(self):
        """Criar conteúdo de prática rico"""
        self.stdout.write('\n📚 Criando conteúdo de prática rico...')

        # Obter cursos existentes
        courses = Course.objects.filter(course_type='practice')[:5]
        
        if not courses:
            self.stdout.write('⚠️ Nenhum curso de prática encontrado')
            return

        units_data = {
            'English Pronunciation Practice': [
                {
                    'title': 'Vowel Sounds Mastery',
                    'description': 'Master English vowel sounds with interactive exercises',
                    'lessons': [
                        {
                            'title': 'Short Vowel Sounds',
                            'challenges': [
                                {
                                    'type': 'PRONUNCIATION',
                                    'question': 'Pronounce the word "cat" correctly',
                                    'target_pronunciation': 'cat',
                                    'options': [
                                        {'text': '/kæt/', 'is_correct': True},
                                        {'text': '/keɪt/', 'is_correct': False},
                                        {'text': '/kʌt/', 'is_correct': False}
                                    ]
                                },
                                {
                                    'type': 'LISTENING',
                                    'question': 'Which word do you hear?',
                                    'audio_content_url': '/audio/cat_pronunciation.mp3',
                                    'options': [
                                        {'text': 'cat', 'is_correct': True},
                                        {'text': 'cut', 'is_correct': False},
                                        {'text': 'cot', 'is_correct': False}
                                    ]
                                }
                            ]
                        },
                        {
                            'title': 'Long Vowel Sounds', 
                            'challenges': [
                                {
                                    'type': 'PRONUNCIATION',
                                    'question': 'Pronounce "make" with the correct long A sound',
                                    'target_pronunciation': 'make',
                                    'options': [
                                        {'text': '/meɪk/', 'is_correct': True},
                                        {'text': '/mæk/', 'is_correct': False},
                                        {'text': '/mʌk/', 'is_correct': False}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'title': 'Consonant Combinations',
                    'description': 'Practice difficult consonant sounds and combinations',
                    'lessons': [
                        {
                            'title': 'TH Sounds',
                            'challenges': [
                                {
                                    'type': 'PRONUNCIATION',
                                    'question': 'Practice the "th" sound in "think"',
                                    'target_pronunciation': 'think',
                                    'options': [
                                        {'text': '/θɪŋk/', 'is_correct': True},
                                        {'text': '/sɪŋk/', 'is_correct': False},
                                        {'text': '/fɪŋk/', 'is_correct': False}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            'Daily English Practice': [
                {
                    'title': 'Everyday Conversations',
                    'description': 'Essential phrases for daily English communication',
                    'lessons': [
                        {
                            'title': 'Greeting People',
                            'challenges': [
                                {
                                    'type': 'CONVERSATION',
                                    'question': 'How would you greet someone you meet for the first time?',
                                    'conversation_context': {
                                        'scenario': 'Meeting someone new at work',
                                        'your_role': 'New employee',
                                        'ai_role': 'Colleague'
                                    },
                                    'options': [
                                        {'text': 'Nice to meet you', 'is_correct': True},
                                        {'text': 'See you later', 'is_correct': False},
                                        {'text': 'Good night', 'is_correct': False}
                                    ]
                                },
                                {
                                    'type': 'SELECT',
                                    'question': 'What is the most appropriate response to "How are you?"',
                                    'options': [
                                        {'text': 'I\'m fine, thank you. How about you?', 'is_correct': True},
                                        {'text': 'My name is John', 'is_correct': False},
                                        {'text': 'I live in Luanda', 'is_correct': False},
                                        {'text': 'Goodbye', 'is_correct': False}
                                    ]
                                }
                            ]
                        },
                        {
                            'title': 'Asking for Directions',
                            'challenges': [
                                {
                                    'type': 'CONVERSATION',
                                    'question': 'Ask politely how to get to the bank',
                                    'conversation_context': {
                                        'scenario': 'Lost in the city center',
                                        'your_role': 'Tourist',
                                        'ai_role': 'Local person'
                                    },
                                    'options': [
                                        {'text': 'Excuse me, could you tell me how to get to the bank?', 'is_correct': True},
                                        {'text': 'Where bank?', 'is_correct': False},
                                        {'text': 'Bank location now!', 'is_correct': False}
                                    ]
                                }
                            ]
                        },
                        {
                            'title': 'Shopping and Buying',
                            'challenges': [
                                {
                                    'type': 'SELECT',
                                    'question': 'How do you politely ask the price of something?',
                                    'options': [
                                        {'text': 'How much does this cost?', 'is_correct': True},
                                        {'text': 'Money this?', 'is_correct': False},
                                        {'text': 'Price tell me!', 'is_correct': False},
                                        {'text': 'Cost what?', 'is_correct': False}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    'title': 'Time and Scheduling',
                    'description': 'Learn to talk about time, dates, and appointments',
                    'lessons': [
                        {
                            'title': 'Telling Time',
                            'challenges': [
                                {
                                    'type': 'SELECT',
                                    'question': 'How do you say 3:30 in English?',
                                    'options': [
                                        {'text': 'Half past three', 'is_correct': True},
                                        {'text': 'Three and thirty', 'is_correct': False},
                                        {'text': 'Three thirty o\'clock', 'is_correct': False},
                                        {'text': 'Thirty after three', 'is_correct': False}
                                    ]
                                },
                                {
                                    'type': 'LISTENING',
                                    'question': 'What time do you hear?',
                                    'audio_content_url': '/audio/time_quarter_to_five.mp3',
                                    'audio_transcript': 'It\'s quarter to five',
                                    'options': [
                                        {'text': '4:45', 'is_correct': True},
                                        {'text': '5:15', 'is_correct': False},
                                        {'text': '4:15', 'is_correct': False},
                                        {'text': '5:45', 'is_correct': False}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        for course in courses:
            if course.title in units_data:
                self.create_units_for_course(course, units_data[course.title])

    def create_units_for_course(self, course, units_data):
        """Criar unidades para um curso específico"""
        self.stdout.write(f'  📖 Curso: {course.title}')
        
        for unit_order, unit_data in enumerate(units_data, 1):
            # Criar unidade
            unit = PracticeUnit.objects.create(
                course=course,
                title=unit_data['title'],
                description=unit_data['description'],
                order=unit_order
            )
            self.stdout.write(f'    ✅ Unidade: {unit.title}')
            
            # Criar lições
            for lesson_order, lesson_data in enumerate(unit_data['lessons'], 1):
                lesson = PracticeLesson.objects.create(
                    unit=unit,
                    title=lesson_data['title'],
                    order=lesson_order
                )
                self.stdout.write(f'      📚 Lição: {lesson.title}')
                
                # Criar desafios
                for challenge_order, challenge_data in enumerate(lesson_data['challenges'], 1):
                    challenge = PracticeChallenge.objects.create(
                        lesson=lesson,
                        type=challenge_data['type'],
                        question=challenge_data['question'],
                        order=challenge_order,
                        target_pronunciation=challenge_data.get('target_pronunciation', ''),
                        conversation_context=challenge_data.get('conversation_context', {}),
                        audio_content_url=challenge_data.get('audio_content_url', ''),
                        audio_transcript=challenge_data.get('audio_transcript', '')
                    )
                    
                    # Criar opções
                    for option_order, option_data in enumerate(challenge_data['options']):
                        ChallengeOption.objects.create(
                            challenge=challenge,
                            text=option_data['text'],
                            is_correct=option_data['is_correct'],
                            order=option_order
                        )
                    
                    self.stdout.write(f'        🎮 Desafio: {challenge_data["type"]}')

    def create_achievements_system(self):
        """Criar sistema de conquistas completo"""
        self.stdout.write('\n🏆 Criando sistema de conquistas...')
        
        # Criar categorias de conquistas
        categories_data = [
            {
                'name': 'learning',
                'display_name': 'Aprendizado',
                'description': 'Conquistas relacionadas ao progresso nos estudos',
                'icon_class': 'fa-graduation-cap',
                'color': 'text-blue-500',
                'order': 1
            },
            {
                'name': 'streak',
                'display_name': 'Sequência',
                'description': 'Conquistas por praticar consecutivamente',
                'icon_class': 'fa-fire',
                'color': 'text-orange-500',
                'order': 2
            },
            {
                'name': 'social',
                'display_name': 'Social',
                'description': 'Conquistas por interação e competição',
                'icon_class': 'fa-users',
                'color': 'text-green-500',
                'order': 3
            },
            {
                'name': 'milestone',
                'display_name': 'Marcos',
                'description': 'Conquistas por atingir objetivos importantes',
                'icon_class': 'fa-trophy',
                'color': 'text-yellow-500',
                'order': 4
            },
            {
                'name': 'special',
                'display_name': 'Especiais',
                'description': 'Conquistas raras e eventos especiais',
                'icon_class': 'fa-star',
                'color': 'text-purple-500',
                'order': 5
            }
        ]
        
        for cat_data in categories_data:
            AchievementCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            
        # Criar conquistas
        achievements_data = [
            # Conquistas de Aprendizado
            {
                'title': 'Primeiro Passo',
                'description': 'Complete seu primeiro desafio no laboratório',
                'icon': '🎯',
                'category': 'learning',
                'rarity': 'common',
                'points': 10,
                'requirement_type': 'challenges_completed',
                'requirement_target': 1,
                'requirement_unit': 'desafios',
                'order': 1
            },
            {
                'title': 'Estudante Dedicado',
                'description': 'Complete 25 desafios',
                'icon': '📚',
                'category': 'learning',
                'rarity': 'common',
                'points': 50,
                'requirement_type': 'challenges_completed',
                'requirement_target': 25,
                'requirement_unit': 'desafios',
                'order': 2
            },
            {
                'title': 'Mestre dos Desafios',
                'description': 'Complete 100 desafios',
                'icon': '🎓',
                'category': 'learning',
                'rarity': 'rare',
                'points': 200,
                'requirement_type': 'challenges_completed',
                'requirement_target': 100,
                'requirement_unit': 'desafios',
                'order': 3
            },
            {
                'title': 'Primeira Lição',
                'description': 'Complete sua primeira lição completa',
                'icon': '📖',
                'category': 'learning',
                'rarity': 'common',
                'points': 25,
                'requirement_type': 'lessons_completed',
                'requirement_target': 1,
                'requirement_unit': 'lições',
                'order': 4
            },
            {
                'title': 'Estudioso',
                'description': 'Complete 10 lições',
                'icon': '🤓',
                'category': 'learning',
                'rarity': 'rare',
                'points': 150,
                'requirement_type': 'lessons_completed',
                'requirement_target': 10,
                'requirement_unit': 'lições',
                'order': 5
            },
            
            # Conquistas de Sequência
            {
                'title': 'Começou a Sequência',
                'description': 'Pratique por 3 dias consecutivos',
                'icon': '🔥',
                'category': 'streak',
                'rarity': 'common',
                'points': 30,
                'requirement_type': 'streak_days',
                'requirement_target': 3,
                'requirement_unit': 'dias',
                'order': 10
            },
            {
                'title': 'Uma Semana Forte',
                'description': 'Pratique por 7 dias consecutivos',
                'icon': '🌟',
                'category': 'streak',
                'rarity': 'rare',
                'points': 100,
                'requirement_type': 'streak_days',
                'requirement_target': 7,
                'requirement_unit': 'dias',
                'order': 11
            },
            {
                'title': 'Incansável',
                'description': 'Pratique por 30 dias consecutivos',
                'icon': '💪',
                'category': 'streak',
                'rarity': 'epic',
                'points': 500,
                'requirement_type': 'streak_days',
                'requirement_target': 30,
                'requirement_unit': 'dias',
                'order': 12
            },
            
            # Conquistas de Pontos
            {
                'title': 'Primeiros Pontos',
                'description': 'Ganhe seus primeiros 100 pontos',
                'icon': '💎',
                'category': 'milestone',
                'rarity': 'common',
                'points': 20,
                'requirement_type': 'points_earned',
                'requirement_target': 100,
                'requirement_unit': 'pontos',
                'order': 20
            },
            {
                'title': 'Colecionador',
                'description': 'Acumule 1000 pontos',
                'icon': '💰',
                'category': 'milestone',
                'rarity': 'rare',
                'points': 100,
                'requirement_type': 'points_earned',
                'requirement_target': 1000,
                'requirement_unit': 'pontos',
                'order': 21
            },
            {
                'title': 'Rico em Conhecimento',
                'description': 'Acumule 5000 pontos',
                'icon': '👑',
                'category': 'milestone',
                'rarity': 'epic',
                'points': 300,
                'requirement_type': 'points_earned',
                'requirement_target': 5000,
                'requirement_unit': 'pontos',
                'order': 22
            },
            
            # Conquistas Especiais
            {
                'title': 'Beta Tester',
                'description': 'Um dos primeiros usuários do ProEnglish',
                'icon': '🚀',
                'category': 'special',
                'rarity': 'legendary',
                'points': 1000,
                'requirement_type': 'special_beta',
                'requirement_target': 1,
                'requirement_unit': 'registro',
                'is_secret': True,
                'order': 30
            },
            {
                'title': 'Madrugador',
                'description': 'Complete uma lição antes das 6h da manhã',
                'icon': '🌅',
                'category': 'special',
                'rarity': 'rare',
                'points': 75,
                'requirement_type': 'early_bird',
                'requirement_target': 1,
                'requirement_unit': 'sessão',
                'order': 31
            }
        ]
        
        for achievement_data in achievements_data:
            Achievement.objects.get_or_create(
                title=achievement_data['title'],
                defaults=achievement_data
            )
            
        self.stdout.write(f'✅ Criadas {len(achievements_data)} conquistas em {len(categories_data)} categorias')

    def create_rankings_and_leagues(self):
        """Criar sistema de rankings e ligas"""
        self.stdout.write('\n🥇 Criando sistema de rankings...')
        
        # Criar ligas para todos os usuários
        users = User.objects.all()
        
        for user in users:
            # Criar ou atualizar UserProgress
            user_progress, created = UserProgress.objects.get_or_create(
                user=user,
                defaults={
                    'hearts': 5,
                    'points': random.randint(0, 3000),
                    'user_image_src': '/mascot.jpg'
                }
            )
            
            if not created and user_progress.points == 0:
                # Adicionar pontos aleatórios para simulação
                user_progress.points = random.randint(50, 2500)
                user_progress.save()
            
            # Criar UserLeague
            league_name = UserLeague.get_league_for_points(user_progress.points)
            user_league, created = UserLeague.objects.get_or_create(
                user=user,
                defaults={
                    'current_league': league_name,
                    'points_when_promoted': user_progress.points
                }
            )
            
            if created:
                self.stdout.write(f'  🏆 {user.name}: {league_name.title()} League ({user_progress.points} pts)')
            
            # Criar UserStreak
            streak, created = UserStreak.objects.get_or_create(
                user=user,
                defaults={
                    'current_streak': random.randint(0, 15),
                    'longest_streak': random.randint(0, 30),
                    'last_practice_date': timezone.now().date()
                }
            )
        
        # Criar competição ativa
        competition = Competition.objects.create(
            title='Desafio de Outubro 2024',
            description='Competição mensal para praticar inglês e ganhar prêmios incríveis!',
            type='monthly',
            status='active',
            start_date=timezone.now() - timedelta(days=15),
            end_date=timezone.now() + timedelta(days=15),
            min_points_to_participate=50,
            first_place_prize='Badge Dourado + 1000 pontos',
            second_place_prize='Badge Prata + 500 pontos',
            third_place_prize='Badge Bronze + 300 pontos'
        )
        
        # Adicionar participantes
        eligible_users = User.objects.filter(practice_progress__points__gte=50)
        for user in eligible_users[:8]:
            CompetitionParticipant.objects.create(
                competition=competition,
                user=user,
                points_earned=random.randint(10, 500),
                challenges_completed=random.randint(5, 50),
                lessons_completed=random.randint(1, 10),
                streak_days=random.randint(1, 15),
                current_rank=None  # Will be calculated
            )
        
        # Calcular rankings
        participants = CompetitionParticipant.objects.filter(
            competition=competition
        ).order_by('-points_earned', '-challenges_completed')
        
        for rank, participant in enumerate(participants, 1):
            participant.current_rank = rank
            participant.best_rank = rank
            participant.save()
        
        self.stdout.write(f'✅ Competição criada com {participants.count()} participantes')
        
        # Criar snapshots de leaderboard
        self.create_leaderboard_snapshots()

    def create_leaderboard_snapshots(self):
        """Criar snapshots históricos do leaderboard"""
        users_with_progress = User.objects.filter(
            practice_progress__isnull=False
        ).order_by('-practice_progress__points')
        
        # Criar snapshot de hoje
        for rank, user in enumerate(users_with_progress[:10], 1):
            LeaderboardSnapshot.objects.create(
                user=user,
                rank=rank,
                points=user.practice_progress.points,
                league=user.league.current_league,
                rank_change=random.randint(-3, 3),
                points_change=random.randint(0, 50),
                snapshot_type='daily'
            )
        
        self.stdout.write('📊 Snapshots de leaderboard criados')

    def create_speaking_listening_exercises(self):
        """Criar exercícios de speaking e listening"""
        self.stdout.write('\n🎙️ Criando exercícios de speaking e listening...')
        
        courses = Course.objects.filter(course_type='practice')[:3]
        users = User.objects.filter(role='teacher')
        
        if not users:
            return
            
        teacher = users.first()
        
        for course in courses:
            # Exercícios de Speaking
            SpeakingExercise.objects.get_or_create(
                title=f'Pronúncia Avançada - {course.title}',
                defaults={
                    'course': course,
                    'description': f'Exercício de pronúncia focado no conteúdo de {course.title}',
                    'exercise_type': 'PRONUNCIATION',
                    'difficulty': 'INTERMEDIATE',
                    'is_course_specific': True,
                    'lesson_context': course.category,
                    'target_text': 'The quick brown fox jumps over the lazy dog',
                    'conversation_prompt': f'Practice pronunciation related to {course.category}',
                    'vocabulary_words': ['pronunciation', 'accuracy', 'fluency'],
                    'created_by': teacher
                }
            )
            
            # Exercícios de Listening
            ListeningExercise.objects.get_or_create(
                title=f'Compreensão Auditiva - {course.title}',
                defaults={
                    'course': course,
                    'description': f'Exercício de listening baseado em {course.title}',
                    'exercise_type': 'AUDIO_COMPREHENSION',
                    'difficulty': 'BEGINNER',
                    'accent_type': 'AMERICAN',
                    'is_course_specific': True,
                    'lesson_context': course.category,
                    'audio_url': '/audio/sample_conversation.mp3',
                    'audio_duration': timedelta(minutes=2),
                    'transcript': 'Sample conversation for listening practice',
                    'questions': [
                        'What is the main topic of the conversation?',
                        'How many people are speaking?'
                    ],
                    'correct_answers': [
                        'English learning',
                        'Two people'
                    ],
                    'key_vocabulary': ['conversation', 'practice', 'learning'],
                    'created_by': teacher
                }
            )
        
        self.stdout.write('✅ Exercícios de speaking e listening criados')

    def simulate_user_activity(self):
        """Simular atividade de usuários"""
        self.stdout.write('\n👥 Simulando atividade de usuários...')
        
        challenges = PracticeChallenge.objects.all()
        achievements = Achievement.objects.all()
        users = User.objects.filter(role='student')
        
        for user in users:
            # Simular progresso em alguns desafios
            completed_challenges = random.sample(
                list(challenges), 
                min(random.randint(1, 10), len(challenges))
            )
            
            for challenge in completed_challenges:
                ChallengeProgress.objects.get_or_create(
                    user=user,
                    challenge=challenge,
                    defaults={'completed': True}
                )
            
            # Simular algumas conquistas desbloqueadas
            available_achievements = random.sample(
                list(achievements), 
                min(random.randint(1, 3), len(achievements))
            )
            
            for achievement in available_achievements:
                if achievement.requirement_type == 'challenges_completed':
                    progress = min(
                        len(completed_challenges),
                        achievement.requirement_target
                    )
                elif achievement.requirement_type == 'points_earned':
                    progress = user.practice_progress.points if hasattr(user, 'practice_progress') else 0
                else:
                    progress = random.randint(0, achievement.requirement_target)
                
                user_achievement, created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={
                        'current_progress': progress,
                        'is_unlocked': progress >= achievement.requirement_target
                    }
                )
                
                if user_achievement.is_unlocked and created:
                    self.stdout.write(f'  🏆 {user.name} desbloqueou: {achievement.title}')
        
        self.stdout.write('✅ Atividade de usuários simulada')

    def show_summary(self):
        """Mostrar resumo dos dados criados"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('📊 RESUMO DOS DADOS CRIADOS')
        self.stdout.write('='*50)
        
        # Contar dados de prática
        units_count = PracticeUnit.objects.count()
        lessons_count = PracticeLesson.objects.count()
        challenges_count = PracticeChallenge.objects.count()
        options_count = ChallengeOption.objects.count()
        
        self.stdout.write(f'📚 Conteúdo de Prática:')
        self.stdout.write(f'   - {units_count} unidades')
        self.stdout.write(f'   - {lessons_count} lições')
        self.stdout.write(f'   - {challenges_count} desafios')
        self.stdout.write(f'   - {options_count} opções de resposta')
        
        # Contar conquistas
        categories_count = AchievementCategory.objects.count()
        achievements_count = Achievement.objects.count()
        user_achievements_count = UserAchievement.objects.count()
        unlocked_count = UserAchievement.objects.filter(is_unlocked=True).count()
        
        self.stdout.write(f'\n🏆 Sistema de Conquistas:')
        self.stdout.write(f'   - {categories_count} categorias')
        self.stdout.write(f'   - {achievements_count} conquistas disponíveis')
        self.stdout.write(f'   - {user_achievements_count} conquistas de usuários')
        self.stdout.write(f'   - {unlocked_count} conquistas desbloqueadas')
        
        # Contar rankings
        leagues_count = UserLeague.objects.count()
        competitions_count = Competition.objects.count()
        participants_count = CompetitionParticipant.objects.count()
        snapshots_count = LeaderboardSnapshot.objects.count()
        
        self.stdout.write(f'\n🥇 Sistema de Rankings:')
        self.stdout.write(f'   - {leagues_count} usuários em ligas')
        self.stdout.write(f'   - {competitions_count} competições')
        self.stdout.write(f'   - {participants_count} participantes em competições')
        self.stdout.write(f'   - {snapshots_count} snapshots de leaderboard')
        
        # Contar speaking/listening
        speaking_count = SpeakingExercise.objects.count()
        listening_count = ListeningExercise.objects.count()
        
        self.stdout.write(f'\n🎙️ Exercícios Especiais:')
        self.stdout.write(f'   - {speaking_count} exercícios de speaking')
        self.stdout.write(f'   - {listening_count} exercícios de listening')
        
        # Contar usuários ativos
        users_with_progress = UserProgress.objects.count()
        total_points = UserProgress.objects.aggregate(
            total=models.Sum('points')
        )['total'] or 0
        
        self.stdout.write(f'\n👥 Atividade de Usuários:')
        self.stdout.write(f'   - {users_with_progress} usuários com progresso')
        self.stdout.write(f'   - {total_points} pontos totais no sistema')
        
        self.stdout.write('\n✅ Sistema populated with rich data!')
        self.stdout.write('🚀 Ready for comprehensive testing!')