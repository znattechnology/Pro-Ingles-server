"""
Management command to populate chapter data for testing Phase 2 functionality.
"""
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.courses.models import Chapter, ChapterResource, ChapterQuiz
import uuid


class Command(BaseCommand):
    help = 'Populate existing chapters with transcripts, resources, and quizzes for testing'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Populando dados de teste para capítulos...')

        # Sample transcripts for video chapters
        sample_transcripts = {
            'basic_english': """[00:00] Olá, bem-vindos ao nosso curso de inglês básico!
[00:10] Hoje vamos aprender sobre cumprimentos básicos em inglês.
[00:20] A primeira palavra que vocês precisam saber é "Hello" - que significa "Olá".
[00:35] Outra forma comum de cumprimentar é "Hi" - mais informal.
[00:50] Para perguntar como alguém está, usamos "How are you?" - "Como você está?"
[01:10] Uma resposta comum é "I'm fine, thank you" - "Estou bem, obrigado(a)".
[01:25] Lembrem-se de sempre responder com educação!""",
            
            'grammar_intro': """[00:00] Bem-vindos à aula de gramática básica!
[00:12] Hoje vamos falar sobre a estrutura básica das frases em inglês.
[00:25] A ordem mais comum é: Sujeito + Verbo + Objeto.
[00:40] Por exemplo: "I eat apples" - "Eu como maçãs".
[00:55] O sujeito é "I" (eu), o verbo é "eat" (como), o objeto é "apples" (maçãs).
[01:15] Vamos praticar com mais exemplos durante a aula!""",
            
            'vocabulary': """[00:00] Vamos expandir nosso vocabulário hoje!
[00:10] Primeiro, vamos aprender palavras sobre família.
[00:20] "Mother" significa mãe, "Father" significa pai.
[00:35] "Sister" é irmã, "Brother" é irmão.
[00:50] "Grandmother" é avó, "Grandfather" é avô.
[01:05] Tentem usar essas palavras em frases simples!"""
        }

        # Sample resources data
        sample_resources = [
            {
                'title': 'Lista de Vocabulário Básico',
                'description': 'Palavras essenciais para iniciantes com tradução',
                'resource_type': 'PDF',
                'external_url': 'https://example.com/vocabulary-basic.pdf',
                'is_featured': True
            },
            {
                'title': 'Exercícios de Gramática',
                'description': 'Exercícios práticos sobre estrutura de frases',
                'resource_type': 'WORKSHEET',
                'external_url': 'https://example.com/grammar-exercises.pdf',
                'is_featured': False
            },
            {
                'title': 'Áudio - Pronunciação Correta',
                'description': 'Exemplos de pronúncia nativa',
                'resource_type': 'AUDIO',
                'external_url': 'https://example.com/pronunciation.mp3',
                'is_featured': False
            },
            {
                'title': 'Cambridge Dictionary Online',
                'description': 'Dicionário completo para consultas',
                'resource_type': 'LINK',
                'external_url': 'https://dictionary.cambridge.org',
                'is_featured': True
            },
            {
                'title': 'Código HTML - Exemplo',
                'description': 'Exemplo de código para estudantes de programação',
                'resource_type': 'CODE',
                'external_url': 'https://github.com/example/html-basics',
                'is_featured': False
            },
            {
                'title': 'Infográfico - Tempos Verbais',
                'description': 'Guia visual dos principais tempos verbais',
                'resource_type': 'IMAGE',
                'external_url': 'https://example.com/verb-tenses-infographic.jpg',
                'is_featured': True
            }
        ]

        # Sample quizzes data
        sample_quizzes = [
            {
                'title': 'Quiz: Cumprimentos Básicos',
                'description': 'Teste seu conhecimento sobre cumprimentos em inglês',
                'practice_lesson': 'greetings-101',
                'points_reward': 20,
                'hearts_cost': 1,
                'passing_score': 80,
                'max_attempts': 3,
                'time_limit': 300  # 5 minutes
            },
            {
                'title': 'Quiz: Estrutura de Frases',
                'description': 'Avalie sua compreensão sobre ordem das palavras',
                'practice_lesson': 'sentence-structure-101',
                'points_reward': 25,
                'hearts_cost': 2,
                'passing_score': 75,
                'max_attempts': 2,
                'time_limit': 600  # 10 minutes
            },
            {
                'title': 'Quiz: Vocabulário Familiar',
                'description': 'Teste sobre palavras da família em inglês',
                'practice_lesson': 'family-vocabulary-101',
                'points_reward': 15,
                'hearts_cost': 1,
                'passing_score': 85,
                'max_attempts': 4,
                'time_limit': 240  # 4 minutes
            }
        ]

        # Get existing chapters
        chapters = Chapter.objects.all()[:15]  # Limit to first 15 chapters
        
        if not chapters:
            self.stdout.write(self.style.ERROR('❌ Nenhum capítulo encontrado no banco de dados'))
            return

        self.stdout.write(f'📚 Encontrados {len(chapters)} capítulos para popular')

        updated_count = 0
        
        for i, chapter in enumerate(chapters):
            # Add transcript to some chapters
            if i % 3 == 0 and not chapter.transcript:  # Every 3rd chapter gets a transcript
                transcript_key = list(sample_transcripts.keys())[i % len(sample_transcripts)]
                chapter.transcript = sample_transcripts[transcript_key]
                updated_count += 1

            # Add resources to chapters
            if i % 2 == 0:  # Every 2nd chapter gets resources
                # Create 2-4 resources per chapter
                num_resources = min(4, len(sample_resources) - (i % len(sample_resources)))
                
                for j in range(num_resources):
                    resource_data = sample_resources[(i + j) % len(sample_resources)].copy()
                    resource_data['title'] = f"{resource_data['title']} - Cap {i+1}"
                    
                    resource, created = ChapterResource.objects.get_or_create(
                        chapter=chapter,
                        title=resource_data['title'],
                        defaults={
                            'description': resource_data['description'],
                            'resource_type': resource_data['resource_type'],
                            'external_url': resource_data['external_url'],
                            'is_featured': resource_data['is_featured'],
                            'order': j,
                            'created_by': chapter.section.course.teacher
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  ➕ Recurso criado: {resource.title}')

            # TODO: Add quiz to some chapters (requires PracticeLesson instances)
            # For now, we'll skip quiz creation and focus on transcripts and resources
            if i % 4 == 0 and not chapter.quiz_enabled:
                # Just enable quiz flag for testing the interface
                chapter.quiz_enabled = True
                updated_count += 1
                self.stdout.write(f'  🧠 Quiz habilitado para: {chapter.title}')

            # Save chapter with new data
            chapter.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Dados de teste populados com sucesso!\n'
                f'   📝 Capítulos atualizados: {updated_count}\n'
                f'   📁 Recursos criados: {ChapterResource.objects.count()}\n'
                f'   🧠 Quizzes criados: {ChapterQuiz.objects.count()}'
            )
        )

        # Show some examples
        self.stdout.write('\n📊 Exemplos de capítulos populados:')
        for chapter in chapters[:5]:
            resources_count = ChapterResource.objects.filter(chapter=chapter).count()
            has_quiz = chapter.quiz_enabled
            has_transcript = bool(chapter.transcript)
            
            status_icons = []
            if has_transcript:
                status_icons.append('📝')
            if resources_count > 0:
                status_icons.append(f'📁({resources_count})')
            if has_quiz:
                status_icons.append('🧠')
                
            status = ' '.join(status_icons) if status_icons else '📖'
            
            self.stdout.write(f'   {status} {chapter.title}')

        self.stdout.write('\n🎉 Pronto para testar as novas funcionalidades da Fase 2!')