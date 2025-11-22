"""
AI Conversation Service
Gerencia conversações em tempo real com IA para prática de inglês
"""

import asyncio
import openai
import uuid
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationLevel:
    """Configurações de nível de conversação"""
    name: str
    difficulty: str
    description: str
    topics: List[str]
    target_turns: int
    conversation_style: str
    vocabulary_complexity: str

@dataclass
class ConversationContext:
    """Contexto atual da conversação"""
    level: ConversationLevel
    topic: str
    turns: List[Dict[str, str]]
    user_language_level: str
    conversation_goals: List[str]

@dataclass
class AIResponse:
    """Resposta da IA"""
    message: str
    audio_url: Optional[str]
    conversation_id: str
    conversation_metadata: Optional[Dict[str, any]] = None
    
    # Backward compatibility
    @property
    def text(self):
        return self.message

class ConversationAIService:
    """
    Serviço de IA Conversacional
    
    Gerencia conversas naturais adaptadas ao nível do usuário
    """
    
    # Configurações de níveis
    LEVELS = {
        'BEGINNER': ConversationLevel(
            name='Beginner',
            difficulty='BEGINNER',
            description='Basic conversations with simple vocabulary',
            topics=['introductions', 'daily_routine', 'family', 'food', 'weather'],
            target_turns=6,
            conversation_style='slow_clear_simple',
            vocabulary_complexity='basic_1000_words'
        ),
        'INTERMEDIATE': ConversationLevel(
            name='Intermediate',
            difficulty='INTERMEDIATE',
            description='More complex topics with varied vocabulary',
            topics=['travel', 'work', 'hobbies', 'current_events', 'opinions'],
            target_turns=10,
            conversation_style='natural_moderate',
            vocabulary_complexity='intermediate_3000_words'
        ),
        'ADVANCED': ConversationLevel(
            name='Advanced',
            difficulty='ADVANCED',
            description='Nuanced discussions with advanced vocabulary',
            topics=['philosophy', 'business', 'culture', 'technology', 'literature'],
            target_turns=15,
            conversation_style='natural_complex',
            vocabulary_complexity='advanced_unlimited'
        )
    }
    
    def __init__(self):
        """Inicializar serviço com OpenAI"""
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def start_conversation(self, level: str, topic: str, user_profile: Optional[Dict] = None) -> AIResponse:
        """
        Iniciar nova conversação
        
        Args:
            level: Nível de dificuldade
            topic: Tópico da conversa
            user_profile: Perfil do usuário (opcional)
            
        Returns:
            Primeira mensagem da IA
        """
        try:
            # Convert level to uppercase to match LEVELS keys
            level_upper = level.upper()
            if level_upper not in self.LEVELS:
                raise ValueError(f"Nível inválido: {level}. Níveis disponíveis: {list(self.LEVELS.keys())}")
                
            conversation_level = self.LEVELS[level_upper]
            
            # Criar contexto inicial
            context = ConversationContext(
                level=conversation_level,
                topic=topic,
                turns=[],
                user_language_level=level.lower(),
                conversation_goals=['practice_speaking', 'improve_fluency', 'build_confidence']
            )
            
            # Gerar primeira mensagem
            initial_prompt = self._create_conversation_starter_prompt(context, user_profile)
            
            response = await self._generate_ai_response(initial_prompt, context)
            
            logger.info(f"🤖 Conversa iniciada - Nível: {level}, Tópico: {topic}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar conversa: {str(e)}")
            raise
    
    async def continue_conversation_legacy(self, 
                                         context: ConversationContext, 
                                         user_input: str,
                                         user_analysis: Optional[Dict] = None) -> AIResponse:
        """
        Continuar conversação existente
        
        Args:
            context: Contexto atual da conversa
            user_input: Input do usuário (transcrito)
            user_analysis: Análise da fala do usuário
            
        Returns:
            Resposta da IA
        """
        try:
            # Adicionar input do usuário ao histórico
            context.turns.append({
                'speaker': 'user',
                'content': user_input,
                'analysis': user_analysis
            })
            
            # Gerar prompt para continuação
            continuation_prompt = self._create_conversation_continuation_prompt(context, user_analysis)
            
            response = await self._generate_ai_response(continuation_prompt, context)
            
            # Adicionar resposta da IA ao contexto
            context.turns.append({
                'speaker': 'ai',
                'content': response.message,
                'metadata': response.conversation_metadata
            })
            
            logger.info(f"🤖 Conversa continuada - Turn {len(context.turns)}/{context.level.target_turns}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro ao continuar conversa: {str(e)}")
            raise
    
    async def _generate_ai_response(self, prompt: str, context: ConversationContext) -> AIResponse:
        """Gerar resposta usando OpenAI"""
        try:
            # Configurar parâmetros baseados no nível
            temperature = {
                'BEGINNER': 0.3,      # Mais determinística
                'INTERMEDIATE': 0.5,  # Balanceada  
                'ADVANCED': 0.7       # Mais criativa
            }.get(context.level.difficulty, 0.5)
            
            max_tokens = {
                'BEGINNER': 50,
                'INTERMEDIATE': 80,
                'ADVANCED': 120
            }.get(context.level.difficulty, 80)
            
            # Gerar resposta
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            ai_text = response.choices[0].message.content.strip()
            
            # Gerar áudio se necessário (TTS)
            audio_url = await self._generate_speech_audio(ai_text, context.level)
            
            # Metadata da conversa
            metadata = {
                'turn_number': len(context.turns) + 1,
                'target_turns': context.level.target_turns,
                'topic': context.topic,
                'level': context.level.difficulty,
                'tokens_used': response.usage.total_tokens if response.usage else 0
            }
            
            return AIResponse(
                message=ai_text,
                audio_url=audio_url,
                conversation_id=str(uuid.uuid4()),
                conversation_metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resposta AI: {str(e)}")
            raise
    
    async def _generate_speech_audio(self, text: str, level: ConversationLevel) -> Optional[str]:
        """
        Gerar áudio TTS para a resposta da IA
        
        Args:
            text: Texto para converter
            level: Nível de conversação (para ajustar velocidade)
            
        Returns:
            URL do arquivo de áudio gerado
        """
        try:
            # Configurar velocidade baseada no nível
            speed = {
                'BEGINNER': 0.8,      # Mais devagar
                'INTERMEDIATE': 1.0,  # Normal
                'ADVANCED': 1.1       # Ligeiramente mais rápido
            }.get(level.difficulty, 1.0)
            
            # Gerar áudio usando OpenAI TTS
            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                model="tts-1",
                voice="alloy",  # Voz feminina clara
                input=text,
                speed=speed,
                response_format="mp3"  # Formato MP3 explícito
            )
            
            # Salvar arquivo (em produção usar S3/CloudStorage)
            import os
            import uuid
            from django.conf import settings
            
            # Criar diretório se não existir
            audio_dir = os.path.join(settings.MEDIA_ROOT, 'ai_speech')
            os.makedirs(audio_dir, exist_ok=True)
            
            # Nome único do arquivo
            filename = f"ai_speech_{uuid.uuid4().hex}.mp3"
            file_path = os.path.join(audio_dir, filename)
            
            # Salvar áudio
            with open(file_path, 'wb') as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            
            # Retornar URL relativa
            audio_url = f"/media/ai_speech/{filename}"
            
            logger.info(f"🎵 Áudio TTS gerado: {audio_url}")
            
            return audio_url
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar áudio TTS: {str(e)}")
            return None
    
    def _create_conversation_starter_prompt(self, context: ConversationContext, user_profile: Optional[Dict]) -> str:
        """Criar prompt para iniciar conversa"""
        
        level_instructions = {
            'BEGINNER': """
You are a friendly English tutor for BEGINNER students. 
- Use simple, basic vocabulary (1000 most common words)
- Speak slowly and clearly
- Use short, simple sentences (5-10 words)
- Ask one question at a time
- Be encouraging and patient
- Avoid complex grammar structures
""",
            'INTERMEDIATE': """
You are an engaging English tutor for INTERMEDIATE students.
- Use varied vocabulary (up to 3000 words)
- Speak at normal pace with clear pronunciation
- Use medium-length sentences (10-15 words)
- Include some idiomatic expressions
- Ask follow-up questions to encourage elaboration
- Provide gentle corrections when needed
""",
            'ADVANCED': """
You are a sophisticated English conversation partner for ADVANCED students.
- Use complex vocabulary and expressions
- Speak naturally with varied intonation
- Use complex sentence structures
- Include idioms, metaphors, and cultural references
- Challenge the student with thought-provoking questions
- Engage in nuanced discussions
"""
        }
        
        topic_starters = {
            'introductions': "Start by introducing yourself and asking the student about themselves",
            'daily_routine': "Ask about their typical day and daily activities", 
            'family': "Ask about their family members and family traditions",
            'food': "Discuss favorite foods and cooking experiences",
            'weather': "Talk about today's weather and seasonal preferences",
            'travel': "Discuss travel experiences and dream destinations",
            'work': "Talk about careers, jobs, and work-life balance",
            'hobbies': "Explore interests, hobbies, and free time activities",
            'current_events': "Discuss recent news or interesting developments",
            'opinions': "Ask for opinions on various topics and preferences",
            'philosophy': "Engage in deep discussions about life and meaning",
            'business': "Discuss business trends, entrepreneurship, and economics",
            'culture': "Explore cultural differences and traditions",
            'technology': "Talk about technological advances and their impact",
            'literature': "Discuss books, authors, and storytelling"
        }
        
        user_context = ""
        if user_profile:
            user_context = f"User background: {user_profile.get('background', 'Not specified')}"
        
        prompt = f"""
{level_instructions.get(context.level.difficulty, level_instructions['INTERMEDIATE'])}

CONVERSATION SETUP:
- Topic: {context.topic}
- Level: {context.level.difficulty}
- Target turns: {context.level.target_turns}
- Conversation style: {context.level.conversation_style}

TOPIC GUIDANCE: {topic_starters.get(context.topic, f"Have a natural conversation about {context.topic}")}

{user_context}

Your goal is to create an engaging, natural conversation that helps the student practice speaking English at their level. Start the conversation now with a warm, appropriate greeting and introduction to the topic.

Remember: You are speaking, so write in a conversational, natural tone as if you're talking to them face-to-face.
"""
        
        return prompt
    
    def _create_conversation_continuation_prompt(self, context: ConversationContext, user_analysis: Optional[Dict]) -> str:
        """Criar prompt para continuar conversa"""
        
        # Histórico da conversa
        conversation_history = ""
        for turn in context.turns[-4:]:  # Últimas 4 interações
            speaker = "You" if turn['speaker'] == 'ai' else "Student"
            conversation_history += f"{speaker}: {turn['content']}\n"
        
        # Análise do usuário
        analysis_context = ""
        if user_analysis:
            scores = {
                'pronunciation': user_analysis.get('pronunciation_score', 0),
                'fluency': user_analysis.get('fluency_score', 0),
                'grammar': user_analysis.get('grammar_accuracy', 0)
            }
            
            analysis_context = f"""
STUDENT PERFORMANCE IN LAST TURN:
- Pronunciation: {scores['pronunciation']}%
- Fluency: {scores['fluency']}%  
- Grammar: {scores['grammar']}%

Adjust your response accordingly:
- If pronunciation < 70%: Speak more clearly, maybe repeat key words
- If fluency < 70%: Give more time, ask simpler questions
- If grammar < 70%: Model correct grammar naturally in your response
"""

        level_continuation_style = {
            'BEGINNER': "Continue with simple, encouraging responses. Praise their effort.",
            'INTERMEDIATE': "Continue naturally, maybe introduce a new perspective or related topic.",
            'ADVANCED': "Deepen the discussion with more complex ideas or challenging questions."
        }
        
        prompt = f"""
You are continuing a natural English conversation with a {context.level.difficulty} level student.

CONVERSATION CONTEXT:
- Topic: {context.topic}
- Turn {len(context.turns)}/{context.level.target_turns}
- Level style: {context.level.conversation_style}

RECENT CONVERSATION:
{conversation_history}

{analysis_context}

CONTINUATION STYLE: {level_continuation_style.get(context.level.difficulty, '')}

Continue the conversation naturally. Respond to what the student just said and keep the flow going. Be engaging, supportive, and help them practice speaking English effectively at their level.
"""
        
        return prompt
    
    async def analyze_conversation_completion(self, context: ConversationContext) -> Dict[str, any]:
        """
        Analisar conversa completa e gerar feedback
        
        Args:
            context: Contexto completo da conversa
            
        Returns:
            Análise detalhada da performance
        """
        try:
            user_turns = [turn for turn in context.turns if turn['speaker'] == 'user']
            
            if not user_turns:
                return {
                    'overall_score': 0,
                    'analysis': 'No user input to analyze',
                    'recommendations': ['Try participating more in the conversation']
                }
            
            # Calcular scores médios
            total_turns = len(user_turns)
            avg_scores = {
                'pronunciation': 0,
                'fluency': 0,
                'vocabulary': 0,
                'grammar': 0
            }
            
            for turn in user_turns:
                if turn.get('analysis'):
                    analysis = turn['analysis']
                    avg_scores['pronunciation'] += analysis.get('pronunciation_score', 0)
                    avg_scores['fluency'] += analysis.get('fluency_score', 0)
                    avg_scores['vocabulary'] += analysis.get('vocabulary_usage', 0)
                    avg_scores['grammar'] += analysis.get('grammar_accuracy', 0)
            
            # Calcular médias
            for score_type in avg_scores:
                avg_scores[score_type] = round(avg_scores[score_type] / total_turns, 1)
            
            overall_score = round(sum(avg_scores.values()) / len(avg_scores), 1)
            
            # Gerar análise detalhada usando IA
            analysis_prompt = f"""
Analyze this English conversation practice session:

STUDENT LEVEL: {context.level.difficulty}
TOPIC: {context.topic}
TOTAL TURNS: {total_turns}/{context.level.target_turns}

AVERAGE SCORES:
- Pronunciation: {avg_scores['pronunciation']}%
- Fluency: {avg_scores['fluency']}%
- Vocabulary: {avg_scores['vocabulary']}%
- Grammar: {avg_scores['grammar']}%

CONVERSATION CONTENT:
{self._format_conversation_for_analysis(context.turns)}

Provide a comprehensive analysis including:
1. Strengths (what they did well)
2. Areas for improvement
3. Specific recommendations
4. Whether they're ready for the next level
5. Conversation flow assessment

Be encouraging but honest. Focus on practical, actionable feedback.
"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            ai_analysis = response.choices[0].message.content.strip()
            
            # Determinar se está pronto para próximo nível
            next_level_ready = (
                overall_score >= 80 and 
                avg_scores['pronunciation'] >= 75 and
                avg_scores['fluency'] >= 75
            )
            
            return {
                'overall_score': overall_score,
                'pronunciation_avg': avg_scores['pronunciation'],
                'fluency_avg': avg_scores['fluency'],
                'vocabulary_diversity': avg_scores['vocabulary'],
                'grammar_accuracy': avg_scores['grammar'],
                'conversation_flow': min(100, (total_turns / context.level.target_turns) * 100),
                'total_turns': total_turns,
                'target_turns': context.level.target_turns,
                'ai_analysis': ai_analysis,
                'next_level_ready': next_level_ready,
                'level_completed': context.level.difficulty,
                'topic_completed': context.topic
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar conversa: {str(e)}")
            return {
                'overall_score': 0,
                'analysis': f'Error analyzing conversation: {str(e)}',
                'recommendations': ['Please try again']
            }
    
    def _format_conversation_for_analysis(self, turns: List[Dict]) -> str:
        """Formatar conversa para análise"""
        formatted = ""
        for i, turn in enumerate(turns):
            speaker = "Student" if turn['speaker'] == 'user' else "AI"
            formatted += f"{i+1}. {speaker}: {turn['content']}\n"
        return formatted
    
    def get_available_topics(self, level: str) -> List[str]:
        """Obter tópicos disponíveis para um nível"""
        if level in self.LEVELS:
            return self.LEVELS[level].topics
        return []
    
    def get_level_info(self, level: str) -> Optional[Dict]:
        """Obter informações de um nível"""
        if level in self.LEVELS:
            level_obj = self.LEVELS[level]
            return {
                'name': level_obj.name,
                'difficulty': level_obj.difficulty,
                'description': level_obj.description,
                'topics': level_obj.topics,
                'target_turns': level_obj.target_turns,
                'conversation_style': level_obj.conversation_style
            }
        return None
    
    async def continue_conversation(self, 
                                  conversation_id: str,
                                  user_message: str,
                                  conversation_history: List[Dict],
                                  level: str,
                                  topic: str) -> AIResponse:
        """
        Continue conversation - WebSocket compatible version
        
        Args:
            conversation_id: ID of the conversation session
            user_message: User's message
            conversation_history: List of previous messages
            level: Conversation level
            topic: Conversation topic
            
        Returns:
            AI response
        """
        try:
            if level.upper() not in self.LEVELS:
                raise ValueError(f"Invalid level: {level}")
                
            conversation_level = self.LEVELS[level.upper()]
            
            # Create context from history
            context = ConversationContext(
                level=conversation_level,
                topic=topic,
                turns=conversation_history,
                user_language_level=level.lower(),
                conversation_goals=['practice_speaking', 'improve_fluency']
            )
            
            # Continue conversation using existing method
            return await self.continue_conversation_with_context(context, user_message)
            
        except Exception as e:
            logger.error(f"❌ Error continuing conversation: {str(e)}")
            raise

    async def continue_conversation_with_context(self, 
                                               context: ConversationContext, 
                                               user_input: str,
                                               user_analysis: Optional[Dict] = None) -> AIResponse:
        """
        Continue conversation with full context (renamed from original method)
        """
        try:
            # Add user input to history
            context.turns.append({
                'speaker': 'user',
                'content': user_input,
                'analysis': user_analysis
            })
            
            # Generate continuation prompt
            continuation_prompt = self._create_conversation_continuation_prompt(context, user_analysis)
            
            response = await self._generate_ai_response(continuation_prompt, context)
            
            # Add AI response to context
            context.turns.append({
                'speaker': 'ai',
                'content': response.message,
                'metadata': response.conversation_metadata
            })
            
            logger.info(f"🤖 Conversation continued - Turn {len(context.turns)}/{context.level.target_turns}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error continuing conversation: {str(e)}")
            raise
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio to text using OpenAI Whisper
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"  # OpenAI requires a filename
            
            # Transcribe using Whisper
            response = await asyncio.to_thread(
                self.client.audio.transcriptions.create,
                model="whisper-1",
                file=audio_file,
                language="en"  # Force English transcription
            )
            
            transcription = response.text.strip()
            logger.info(f"🎤 Audio transcribed: {transcription[:50]}...")
            
            return transcription
            
        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {str(e)}")
            return ""
    
    async def evaluate_conversation(self, 
                                  conversation_history: List[Dict],
                                  level: str,
                                  user_profile: Optional[Dict] = None) -> Dict:
        """
        Evaluate a completed conversation
        
        Args:
            conversation_history: List of conversation messages
            level: Conversation level
            user_profile: Optional user profile information
            
        Returns:
            Evaluation results
        """
        try:
            # Convert to legacy format for analysis
            if level.upper() not in self.LEVELS:
                level = 'INTERMEDIATE'
                
            conversation_level = self.LEVELS[level.upper()]
            
            # Create context for analysis
            context = ConversationContext(
                level=conversation_level,
                topic="general",
                turns=conversation_history,
                user_language_level=level.lower(),
                conversation_goals=['practice_speaking']
            )
            
            # Use existing analysis method
            analysis = await self.analyze_conversation_completion(context)
            
            # Format for WebSocket response
            return {
                'overall_score': analysis.get('overall_score', 75),
                'pronunciation': analysis.get('pronunciation_avg', 75),
                'fluency': analysis.get('fluency_avg', 75),
                'vocabulary': analysis.get('vocabulary_diversity', 75),
                'grammar': analysis.get('grammar_accuracy', 75),
                'conversation_flow': analysis.get('conversation_flow', 75),
                'detailed_feedback': analysis.get('ai_analysis', 'Good conversation practice!'),
                'recommendations': [
                    'Continue practicing regularly',
                    'Focus on speaking with confidence',
                    'Try more challenging topics'
                ],
                'next_level_ready': analysis.get('next_level_ready', False),
                'total_turns': analysis.get('total_turns', 0),
                'strengths': [
                    'Active participation',
                    'Good conversation flow'
                ],
                'areas_for_improvement': [
                    'Continue building vocabulary',
                    'Practice pronunciation'
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Error evaluating conversation: {str(e)}")
            return {
                'overall_score': 75,
                'pronunciation': 75,
                'fluency': 75,
                'vocabulary': 75,
                'grammar': 75,
                'conversation_flow': 75,
                'detailed_feedback': 'Unable to generate detailed evaluation at this time.',
                'recommendations': ['Keep practicing!'],
                'next_level_ready': False,
                'total_turns': len([msg for msg in conversation_history if msg.get('role') == 'user']),
                'strengths': ['Participation'],
                'areas_for_improvement': ['Continue practicing']
            }