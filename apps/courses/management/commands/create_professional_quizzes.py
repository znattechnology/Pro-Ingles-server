"""
Django management command to create professional quiz questions for all Quiz chapters.
"""
import json
import random
from django.core.management.base import BaseCommand
from apps.courses.models import Chapter


class Command(BaseCommand):
    help = 'Create professional quiz questions for all Quiz chapters'

    def handle(self, *args, **options):
        self.stdout.write('🧠 Criando quizzes profissionais para capítulos Quiz...')

        # Buscar todos os capítulos do tipo Quiz
        quiz_chapters = Chapter.objects.filter(type='Quiz', quiz_enabled=True)
        
        if not quiz_chapters.exists():
            self.stdout.write('⚠️ Nenhum capítulo Quiz encontrado')
            return

        # Pool de perguntas profissionais por categoria
        english_questions = {
            'grammar': [
                {
                    'id': 'gram_001',
                    'category': 'Present Simple',
                    'text': 'Choose the correct form of the verb to complete the sentence:\n\n"She _____ to work every morning at 8 AM."',
                    'options': [
                        {'id': 'opt1', 'text': 'go', 'is_correct': False},
                        {'id': 'opt2', 'text': 'goes', 'is_correct': True},
                        {'id': 'opt3', 'text': 'going', 'is_correct': False},
                        {'id': 'opt4', 'text': 'gone', 'is_correct': False}
                    ],
                    'explanation': 'In third person singular (she/he/it), we add -s or -es to the verb in present simple.'
                },
                {
                    'id': 'gram_002',
                    'category': 'Articles',
                    'text': 'Select the correct article:\n\n"___ apple a day keeps the doctor away."',
                    'options': [
                        {'id': 'opt1', 'text': 'A', 'is_correct': False},
                        {'id': 'opt2', 'text': 'An', 'is_correct': True},
                        {'id': 'opt3', 'text': 'The', 'is_correct': False},
                        {'id': 'opt4', 'text': 'No article needed', 'is_correct': False}
                    ],
                    'explanation': 'We use "an" before words that begin with a vowel sound. "Apple" starts with a vowel sound.'
                },
                {
                    'id': 'gram_003',
                    'category': 'Past Simple',
                    'text': 'Complete the sentence with the correct past tense form:\n\n"Yesterday, I _____ to the cinema with my friends."',
                    'options': [
                        {'id': 'opt1', 'text': 'go', 'is_correct': False},
                        {'id': 'opt2', 'text': 'goes', 'is_correct': False},
                        {'id': 'opt3', 'text': 'went', 'is_correct': True},
                        {'id': 'opt4', 'text': 'going', 'is_correct': False}
                    ],
                    'explanation': '"Went" is the irregular past tense form of the verb "go".'
                },
                {
                    'id': 'gram_004',
                    'category': 'Prepositions',
                    'text': 'Choose the correct preposition:\n\n"The meeting is scheduled _____ Monday morning."',
                    'options': [
                        {'id': 'opt1', 'text': 'in', 'is_correct': False},
                        {'id': 'opt2', 'text': 'on', 'is_correct': True},
                        {'id': 'opt3', 'text': 'at', 'is_correct': False},
                        {'id': 'opt4', 'text': 'by', 'is_correct': False}
                    ],
                    'explanation': 'We use "on" with days of the week and specific dates.'
                },
                {
                    'id': 'gram_005',
                    'category': 'Present Continuous',
                    'text': 'What is the correct present continuous form?\n\n"Look! It _____ outside."',
                    'options': [
                        {'id': 'opt1', 'text': 'rain', 'is_correct': False},
                        {'id': 'opt2', 'text': 'rains', 'is_correct': False},
                        {'id': 'opt3', 'text': 'is raining', 'is_correct': True},
                        {'id': 'opt4', 'text': 'was raining', 'is_correct': False}
                    ],
                    'explanation': 'Present continuous is formed with "be" + verb-ing. We use it for actions happening now.'
                }
            ],
            'vocabulary': [
                {
                    'id': 'vocab_001',
                    'category': 'Daily Routines',
                    'text': 'What do you call the first meal of the day?',
                    'options': [
                        {'id': 'opt1', 'text': 'Dinner', 'is_correct': False},
                        {'id': 'opt2', 'text': 'Lunch', 'is_correct': False},
                        {'id': 'opt3', 'text': 'Breakfast', 'is_correct': True},
                        {'id': 'opt4', 'text': 'Snack', 'is_correct': False}
                    ],
                    'explanation': 'Breakfast is the first meal of the day, usually eaten in the morning.'
                },
                {
                    'id': 'vocab_002',
                    'category': 'Family',
                    'text': 'What do you call your father\'s sister?',
                    'options': [
                        {'id': 'opt1', 'text': 'Aunt', 'is_correct': True},
                        {'id': 'opt2', 'text': 'Uncle', 'is_correct': False},
                        {'id': 'opt3', 'text': 'Cousin', 'is_correct': False},
                        {'id': 'opt4', 'text': 'Sister-in-law', 'is_correct': False}
                    ],
                    'explanation': 'Your father\'s sister is your aunt. Your father\'s brother would be your uncle.'
                },
                {
                    'id': 'vocab_003',
                    'category': 'Colors',
                    'text': 'Which color do you get when you mix blue and yellow?',
                    'options': [
                        {'id': 'opt1', 'text': 'Purple', 'is_correct': False},
                        {'id': 'opt2', 'text': 'Green', 'is_correct': True},
                        {'id': 'opt3', 'text': 'Orange', 'is_correct': False},
                        {'id': 'opt4', 'text': 'Red', 'is_correct': False}
                    ],
                    'explanation': 'Blue + Yellow = Green. This is a basic color mixing principle.'
                }
            ],
            'reading': [
                {
                    'id': 'read_001',
                    'category': 'Reading Comprehension',
                    'text': 'Read the sentence and choose the best meaning:\n\n"She has a green thumb."\n\nWhat does this expression mean?',
                    'options': [
                        {'id': 'opt1', 'text': 'She has an injured thumb', 'is_correct': False},
                        {'id': 'opt2', 'text': 'She is good at gardening', 'is_correct': True},
                        {'id': 'opt3', 'text': 'She painted her thumb green', 'is_correct': False},
                        {'id': 'opt4', 'text': 'She is jealous', 'is_correct': False}
                    ],
                    'explanation': 'Having a "green thumb" is an idiom meaning someone is skilled at growing plants.'
                }
            ]
        }

        # Contar quantos quizzes foram criados
        updated_count = 0

        for chapter in quiz_chapters:
            # Criar quiz data baseado no título/conteúdo do capítulo
            quiz_title = f"English Quiz: {chapter.title}"
            
            # Selecionar perguntas baseadas no conteúdo
            selected_questions = []
            
            # Adicionar 2-3 perguntas de gramática
            selected_questions.extend(random.sample(english_questions['grammar'], min(3, len(english_questions['grammar']))))
            
            # Adicionar 1-2 perguntas de vocabulário
            selected_questions.extend(random.sample(english_questions['vocabulary'], min(2, len(english_questions['vocabulary']))))
            
            # Adicionar 1 pergunta de leitura
            if english_questions['reading']:
                selected_questions.extend(random.sample(english_questions['reading'], 1))

            # Embaralhar as perguntas
            random.shuffle(selected_questions)
            
            # Limitar a 5 perguntas por quiz
            selected_questions = selected_questions[:5]

            # Criar estrutura do quiz
            quiz_data = {
                'title': quiz_title,
                'description': f'Test your English knowledge with this comprehensive quiz covering grammar, vocabulary, and reading comprehension.',
                'total_questions': len(selected_questions),
                'time_limit': 300,  # 5 minutos
                'passing_score': 60,  # 60% para passar
                'questions': selected_questions
            }

            # Atualizar o capítulo
            chapter.quiz_data = quiz_data
            chapter.save()
            
            updated_count += 1
            self.stdout.write(f'  ✅ Quiz criado para: {chapter.title} ({len(selected_questions)} perguntas)')

        self.stdout.write(
            self.style.SUCCESS(f'🎉 {updated_count} quizzes profissionais criados com sucesso!')
        )