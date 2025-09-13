"""
Simple command to create sample quizzes for testing.
"""
from django.core.management.base import BaseCommand
from apps.courses.models import Chapter, ChapterQuiz
import uuid


class Command(BaseCommand):
    help = 'Create sample quizzes for chapters that have quiz_enabled=True'

    def handle(self, *args, **options):
        self.stdout.write('🧠 Criando quizzes de exemplo...')

        # Get chapters with quiz enabled but no existing quiz
        chapters_with_quiz_enabled = Chapter.objects.filter(
            quiz_enabled=True,
            quiz__isnull=True  # No existing quiz
        )

        if not chapters_with_quiz_enabled:
            self.stdout.write('⚠️ Nenhum capítulo com quiz_enabled=True sem quiz encontrado')
            return

        sample_quizzes = [
            {
                'title': 'Quiz: Conceitos Básicos',
                'description': 'Teste seus conhecimentos sobre conceitos fundamentais',
                'points_reward': 20,
                'hearts_cost': 1,
                'passing_score': 80,
                'max_attempts': 3,
                'time_limit': 300
            },
            {
                'title': 'Quiz: Aplicação Prática',
                'description': 'Avalie sua capacidade de aplicar os conceitos aprendidos',
                'points_reward': 25,
                'hearts_cost': 2,
                'passing_score': 75,
                'max_attempts': 2,
                'time_limit': 600
            },
            {
                'title': 'Quiz: Revisão Completa',
                'description': 'Quiz abrangente sobre todo o conteúdo do capítulo',
                'points_reward': 30,
                'hearts_cost': 1,
                'passing_score': 85,
                'max_attempts': 4,
                'time_limit': 450
            }
        ]

        created_count = 0
        
        for i, chapter in enumerate(chapters_with_quiz_enabled):
            quiz_data = sample_quizzes[i % len(sample_quizzes)].copy()
            
            # Customize based on chapter
            quiz_data['title'] = f"{quiz_data['title']} - {chapter.title}"
            
            # Create a simple practice lesson ID (string for now)
            practice_lesson_id = f'lesson-{chapter.id}-{uuid.uuid4().hex[:8]}'

            try:
                # Try to create quiz with minimal data first
                quiz = ChapterQuiz(
                    chapter=chapter,
                    title=quiz_data['title'],
                    description=quiz_data['description'],
                    practice_lesson_id=practice_lesson_id,  # Use string ID for now
                    points_reward=quiz_data['points_reward'],
                    hearts_cost=quiz_data['hearts_cost'],
                    passing_score=quiz_data['passing_score'],
                    max_attempts=quiz_data['max_attempts'],
                    time_limit=quiz_data['time_limit'],
                    is_active=True,
                    created_by=chapter.section.course.teacher
                )
                quiz.save()
                
                created_count += 1
                self.stdout.write(f'  ✅ Quiz criado: {quiz.title}')
                
            except Exception as e:
                self.stdout.write(f'  ❌ Erro ao criar quiz para {chapter.title}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'🎉 Criados {created_count} quizzes de exemplo!'
            )
        )