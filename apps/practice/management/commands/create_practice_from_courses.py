"""
Create Practice Lab content automatically from existing Course chapters.
This creates the bridge between Course System and Practice Lab.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.courses.models import Course, Chapter
from apps.practice.models import (
    PracticeUnit, PracticeLesson, PracticeChallenge, 
    ChallengeOption, UserProgress
)
from apps.users.models import User
import uuid


class Command(BaseCommand):
    help = 'Create Practice Lab content from existing Course chapters'

    def handle(self, *args, **options):
        self.stdout.write('🔗 Criando integração Course → Practice Lab...')

        courses = Course.objects.filter(status='Published').prefetch_related(
            'sections__chapters'
        )
        
        if not courses:
            self.stdout.write('⚠️ Nenhum curso publicado encontrado')
            return

        created_units = 0
        created_lessons = 0  
        created_challenges = 0
        linked_chapters = 0

        for course in courses:
            self.stdout.write(f'\n📚 Processando curso: {course.title}')
            
            # Create Practice Unit for each Course
            practice_unit, unit_created = PracticeUnit.objects.get_or_create(
                course=course,
                defaults={
                    'title': f'Prática: {course.title}',
                    'description': f'Exercícios práticos para o curso "{course.title}". '
                                 f'Complete desafios baseados no conteúdo das aulas para '
                                 f'fixar seu aprendizado.',
                    'order': 1
                }
            )
            
            if unit_created:
                created_units += 1
                self.stdout.write(f'  ✅ Unit criada: {practice_unit.title}')

            lesson_order = 1
            
            # Process each section and chapter
            for section in course.sections.all()[:5]:  # Limit to first 5 sections
                chapters = section.chapters.all()[:3]  # Limit to first 3 chapters per section
                
                for chapter in chapters:
                    if chapter.practice_lesson:
                        self.stdout.write(f'  ⏭️ Chapter já tem practice lesson: {chapter.title}')
                        continue
                    
                    # Create Practice Lesson for Chapter
                    practice_lesson = PracticeLesson.objects.create(
                        unit=practice_unit,
                        title=chapter.title,
                        order=lesson_order
                    )
                    
                    # Link Chapter to Practice Lesson
                    chapter.practice_lesson = practice_lesson
                    chapter.save()
                    
                    created_lessons += 1
                    linked_chapters += 1
                    lesson_order += 1
                    
                    self.stdout.write(f'    📖 Lesson criada: {practice_lesson.title}')
                    
                    # Generate Challenges based on Chapter content
                    challenges_created = self._create_challenges_for_chapter(
                        chapter, practice_lesson
                    )
                    created_challenges += challenges_created
                    
                    self.stdout.write(f'      🎮 {challenges_created} challenges criados')

        # Create sample UserProgress for existing users
        self._create_sample_user_progress(courses)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Integração concluída com sucesso!\n'
                f'   📦 Units criadas: {created_units}\n'
                f'   📚 Lessons criadas: {created_lessons}\n'  
                f'   🎮 Challenges criados: {created_challenges}\n'
                f'   🔗 Chapters conectados: {linked_chapters}'
            )
        )

    def _create_challenges_for_chapter(self, chapter, practice_lesson):
        """Create practice challenges based on chapter content and type"""
        challenges_created = 0
        
        # Different challenge types based on chapter type and content
        challenge_templates = self._get_challenge_templates_for_chapter(chapter)
        
        for i, template in enumerate(challenge_templates):
            challenge = PracticeChallenge.objects.create(
                lesson=practice_lesson,
                type=template['type'],
                question=template['question'],
                order=i + 1
            )
            
            # Create options for the challenge
            for j, option_data in enumerate(template['options']):
                ChallengeOption.objects.create(
                    challenge=challenge,
                    text=option_data['text'],
                    is_correct=option_data['is_correct'],
                    order=j
                )
            
            challenges_created += 1
        
        return challenges_created

    def _get_challenge_templates_for_chapter(self, chapter):
        """Generate appropriate challenges based on chapter type and content"""
        templates = []
        
        # Base challenges for any chapter
        templates.extend([
            {
                'type': 'SELECT',
                'question': f'Qual é o tema principal do capítulo "{chapter.title}"?',
                'options': [
                    {'text': chapter.title, 'is_correct': True},
                    {'text': 'Conceitos Avançados', 'is_correct': False},
                    {'text': 'Introdução Geral', 'is_correct': False},
                    {'text': 'Revisão Final', 'is_correct': False}
                ]
            }
        ])
        
        # Video-specific challenges
        if chapter.type == 'Video' and chapter.video:
            templates.extend([
                {
                    'type': 'SELECT', 
                    'question': 'Este capítulo contém qual tipo de conteúdo principal?',
                    'options': [
                        {'text': 'Vídeo explicativo', 'is_correct': True},
                        {'text': 'Apenas texto', 'is_correct': False},
                        {'text': 'Quiz interativo', 'is_correct': False},
                        {'text': 'Exercício prático', 'is_correct': False}
                    ]
                },
                {
                    'type': 'FILL_BLANK',
                    'question': f'Complete: "No vídeo sobre {chapter.title}, aprendemos sobre ____"',
                    'options': [
                        {'text': 'conceitos fundamentais', 'is_correct': True},
                        {'text': 'apenas teoria', 'is_correct': False},
                        {'text': 'exercícios avançados', 'is_correct': False}
                    ]
                }
            ])
        
        # Quiz-specific challenges  
        if chapter.quiz_enabled:
            templates.extend([
                {
                    'type': 'SELECT',
                    'question': 'Este capítulo inclui qual funcionalidade especial?',
                    'options': [
                        {'text': 'Quiz interativo gamificado', 'is_correct': True},
                        {'text': 'Apenas leitura', 'is_correct': False},
                        {'text': 'Vídeo básico', 'is_correct': False},
                        {'text': 'Lista de recursos', 'is_correct': False}
                    ]
                }
            ])

        # Text-based challenges
        if chapter.type == 'Text':
            content_preview = chapter.content[:100] + "..." if len(chapter.content) > 100 else chapter.content
            templates.extend([
                {
                    'type': 'TRANSLATION',
                    'question': f'Traduza o conceito principal: "{chapter.title}"',
                    'options': [
                        {'text': f'{chapter.title} (conceito-chave)', 'is_correct': True},
                        {'text': 'Tradução incorreta 1', 'is_correct': False},
                        {'text': 'Tradução incorreta 2', 'is_correct': False}
                    ]
                }
            ])

        # Content-based challenges
        if chapter.content:
            # Extract key concepts from content (simplified approach)
            content_words = chapter.content.lower().split()
            key_terms = [word for word in content_words if len(word) > 6][:3]
            
            if key_terms:
                templates.append({
                    'type': 'MATCH_PAIRS',
                    'question': f'Relacione os conceitos do capítulo "{chapter.title}"',
                    'options': [
                        {'text': f'{key_terms[0]} - conceito principal', 'is_correct': True},
                        {'text': f'{key_terms[1] if len(key_terms) > 1 else "termo"} - conceito secundário', 'is_correct': False},
                        {'text': 'Conceito não relacionado', 'is_correct': False}
                    ]
                })

        # Ensure we have at least 3 challenges per chapter
        while len(templates) < 3:
            templates.append({
                'type': 'SELECT',
                'question': f'Sobre o capítulo "{chapter.title}", qual afirmação está correta?',
                'options': [
                    {'text': 'É um conteúdo importante para o aprendizado', 'is_correct': True},
                    {'text': 'Não tem relevância no curso', 'is_correct': False},
                    {'text': 'É apenas conteúdo opcional', 'is_correct': False},
                    {'text': 'Deve ser ignorado pelos estudantes', 'is_correct': False}
                ]
            })

        return templates[:5]  # Limit to 5 challenges per lesson

    def _create_sample_user_progress(self, courses):
        """Create sample UserProgress for existing users"""
        users = User.objects.all()[:10]  # Limit to first 10 users
        
        for user in users:
            if hasattr(user, 'practice_progress'):
                continue  # User already has progress
                
            # Select a random active course or first published course
            active_course = courses.first() if courses else None
            
            if active_course:
                UserProgress.objects.create(
                    user=user,
                    active_course=active_course,
                    hearts=5,
                    points=0,
                    user_image_src="/mascot.jpg"
                )
                self.stdout.write(f'    👤 UserProgress criado para: {user.name}')