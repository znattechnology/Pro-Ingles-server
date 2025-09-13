"""
Create simple quiz records using direct SQL to bypass FK constraints.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from apps.courses.models import Chapter
import uuid
from datetime import datetime


class Command(BaseCommand):
    help = 'Create simple quiz records for testing (bypasses FK constraints)'

    def handle(self, *args, **options):
        self.stdout.write('🧠 Criando quizzes via SQL...')

        # Get chapters with quiz enabled
        chapters = Chapter.objects.filter(quiz_enabled=True)

        if not chapters:
            self.stdout.write('⚠️ Nenhum capítulo com quiz_enabled=True encontrado')
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
        
        with connection.cursor() as cursor:
            # Check if table exists and get columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'courses_chapterquiz'
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            if not columns:
                self.stdout.write('❌ Tabela courses_chapterquiz não encontrada')
                return
            
            self.stdout.write(f'📋 Colunas disponíveis: {columns}')
            
            for i, chapter in enumerate(chapters[:5]):  # Limit to 5 for testing
                quiz_data = sample_quizzes[i % len(sample_quizzes)].copy()
                quiz_id = str(uuid.uuid4())
                practice_lesson_id = f'lesson-{chapter.id}-{uuid.uuid4().hex[:8]}'
                
                # Check if quiz already exists for this chapter
                cursor.execute("""
                    SELECT COUNT(*) FROM courses_chapterquiz WHERE chapter_id = %s
                """, [str(chapter.id)])
                
                if cursor.fetchone()[0] > 0:
                    self.stdout.write(f'⏭️ Quiz já existe para: {chapter.title}')
                    continue
                
                try:
                    # Insert quiz record with minimal required fields
                    cursor.execute("""
                        INSERT INTO courses_chapterquiz (
                            id, chapter_id, title, description, practice_lesson_id,
                            points_reward, hearts_cost, passing_score, max_attempts,
                            time_limit, is_active, created_by_id, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        quiz_id,
                        str(chapter.id), 
                        f"{quiz_data['title']} - {chapter.title}",
                        quiz_data['description'],
                        practice_lesson_id,
                        quiz_data['points_reward'],
                        quiz_data['hearts_cost'], 
                        quiz_data['passing_score'],
                        quiz_data['max_attempts'],
                        quiz_data['time_limit'],
                        True,  # is_active
                        str(chapter.section.course.teacher.id),
                        datetime.now(),
                        datetime.now()
                    ])
                    
                    created_count += 1
                    self.stdout.write(f'  ✅ Quiz criado via SQL: {chapter.title}')
                    
                except Exception as e:
                    self.stdout.write(f'  ❌ Erro ao criar quiz para {chapter.title}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'🎉 Criados {created_count} quizzes via SQL!'
            )
        )