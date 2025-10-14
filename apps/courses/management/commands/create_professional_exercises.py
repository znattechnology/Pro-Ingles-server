"""
Django management command to create professional exercise data for all Exercise chapters.
"""
import json
import random
from django.core.management.base import BaseCommand
from apps.courses.models import Chapter


class Command(BaseCommand):
    help = 'Create professional exercise data for all Exercise chapters'

    def handle(self, *args, **options):
        self.stdout.write('💪 Criando exercícios profissionais para capítulos Exercise...')

        # Buscar todos os capítulos do tipo Exercise
        exercise_chapters = Chapter.objects.filter(type='Exercise')
        
        if not exercise_chapters.exists():
            self.stdout.write('⚠️ Nenhum capítulo Exercise encontrado')
            return

        # Pool de exercícios práticos profissionais
        practice_exercises = {
            'speaking': [
                {
                    'id': 'speak_001',
                    'title': 'Daily Conversation Practice',
                    'description': 'Practice common daily conversation scenarios',
                    'type': 'conversation',
                    'difficulty': 'beginner',
                    'estimated_time': 5,
                    'activities': [
                        {
                            'type': 'role_play',
                            'scenario': 'Ordering food at a restaurant',
                            'prompts': [
                                'Greet the waiter',
                                'Ask about the menu',
                                'Order your meal',
                                'Ask for the bill'
                            ]
                        },
                        {
                            'type': 'pronunciation',
                            'words': ['restaurant', 'delicious', 'appetizer', 'dessert'],
                            'focus': 'R and L sounds'
                        }
                    ]
                },
                {
                    'id': 'speak_002',
                    'title': 'Business English Conversations',
                    'description': 'Professional communication scenarios',
                    'type': 'conversation',
                    'difficulty': 'intermediate',
                    'estimated_time': 8,
                    'activities': [
                        {
                            'type': 'presentation',
                            'topic': 'Introducing yourself in a meeting',
                            'key_phrases': [
                                'Good morning, everyone',
                                'I\'d like to introduce myself',
                                'I\'m responsible for...',
                                'Thank you for your time'
                            ]
                        }
                    ]
                }
            ],
            'listening': [
                {
                    'id': 'listen_001',
                    'title': 'Accent Recognition Challenge',
                    'description': 'Train your ear to different English accents',
                    'type': 'listening',
                    'difficulty': 'intermediate',
                    'estimated_time': 10,
                    'activities': [
                        {
                            'type': 'accent_identification',
                            'accents': ['American', 'British', 'Australian', 'Canadian'],
                            'exercises': [
                                {
                                    'audio_description': 'Listen to the weather forecast',
                                    'question': 'Which accent is the speaker using?',
                                    'options': ['American', 'British', 'Australian', 'Canadian']
                                }
                            ]
                        }
                    ]
                },
                {
                    'id': 'listen_002',
                    'title': 'News Comprehension',
                    'description': 'Understand news broadcasts and current events',
                    'type': 'listening',
                    'difficulty': 'advanced',
                    'estimated_time': 15,
                    'activities': [
                        {
                            'type': 'news_analysis',
                            'topics': ['Technology', 'Environment', 'Health', 'Economy'],
                            'skills': ['Main idea identification', 'Detail recognition', 'Inference']
                        }
                    ]
                }
            ],
            'grammar': [
                {
                    'id': 'gram_ex_001',
                    'title': 'Verb Tenses in Context',
                    'description': 'Master English verb tenses through practical exercises',
                    'type': 'grammar',
                    'difficulty': 'intermediate',
                    'estimated_time': 12,
                    'activities': [
                        {
                            'type': 'sentence_transformation',
                            'focus': 'Present Perfect vs Past Simple',
                            'exercises': [
                                {
                                    'instruction': 'Transform the sentence using Present Perfect',
                                    'base_sentence': 'I lived in London for 5 years.',
                                    'target': 'I have lived in London for 5 years.'
                                }
                            ]
                        },
                        {
                            'type': 'gap_fill',
                            'text': 'Yesterday I _____ (go) to the store. I _____ (buy) some groceries.',
                            'answers': ['went', 'bought']
                        }
                    ]
                }
            ],
            'vocabulary': [
                {
                    'id': 'vocab_ex_001',
                    'title': 'Professional Vocabulary Builder',
                    'description': 'Expand your business and academic vocabulary',
                    'type': 'vocabulary',
                    'difficulty': 'advanced',
                    'estimated_time': 8,
                    'activities': [
                        {
                            'type': 'word_matching',
                            'theme': 'Business terminology',
                            'words': [
                                {'word': 'leverage', 'definition': 'to use something to maximum advantage'},
                                {'word': 'synergy', 'definition': 'combined effort greater than individual parts'},
                                {'word': 'stakeholder', 'definition': 'person with interest in a business'}
                            ]
                        },
                        {
                            'type': 'contextual_usage',
                            'sentences': [
                                'The company plans to _____ its new technology.',
                                'The _____ between departments improved efficiency.'
                            ]
                        }
                    ]
                }
            ]
        }

        # Contar quantos exercícios foram criados
        updated_count = 0

        for chapter in exercise_chapters:
            # Selecionar tipo de exercício baseado no conteúdo do capítulo
            content_lower = (chapter.content + chapter.title).lower()
            
            if any(word in content_lower for word in ['speak', 'conversation', 'talk', 'pronunciation']):
                exercise_type = 'speaking'
            elif any(word in content_lower for word in ['listen', 'hear', 'audio', 'sound']):
                exercise_type = 'listening'
            elif any(word in content_lower for word in ['grammar', 'verb', 'tense', 'sentence']):
                exercise_type = 'grammar'
            elif any(word in content_lower for word in ['vocabulary', 'words', 'meaning']):
                exercise_type = 'vocabulary'
            else:
                # Default to a mix of activities
                exercise_type = random.choice(['speaking', 'listening', 'grammar', 'vocabulary'])

            # Selecionar exercícios do tipo escolhido
            available_exercises = practice_exercises.get(exercise_type, practice_exercises['grammar'])
            selected_exercise = random.choice(available_exercises)

            # Criar practice_selection structure
            practice_selection = {
                'course_id': 'english_practice_lab',
                'course_name': 'English Practice Laboratory',
                'lesson_ids': [selected_exercise['id']],
                'lesson_details': [selected_exercise],
                'settings': {
                    'shuffle': True,
                    'time_limit': selected_exercise.get('estimated_time', 10) * 60,  # Convert to seconds
                    'auto_advance': False,
                    'show_hints': True,
                    'difficulty': selected_exercise.get('difficulty', 'intermediate')
                },
                'integration_type': 'embedded',  # Can be 'embedded' or 'external'
                'completion_criteria': {
                    'min_score': 70,
                    'required_activities': len(selected_exercise.get('activities', [])),
                    'time_bonus': True
                }
            }

            # Atualizar o capítulo
            chapter.practice_selection = practice_selection
            chapter.save()
            
            updated_count += 1
            exercise_title = selected_exercise['title']
            exercise_type_display = exercise_type.title()
            self.stdout.write(f'  ✅ Exercício criado para: {chapter.title} ({exercise_type_display}: {exercise_title})')

        self.stdout.write(
            self.style.SUCCESS(f'🎉 {updated_count} exercícios profissionais criados com sucesso!')
        )