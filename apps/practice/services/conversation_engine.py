"""
AI Conversation Engine
Handles real-time AI conversations for speaking practice
"""

import openai
import json
import asyncio
from typing import Dict, List, Optional
from django.conf import settings
from .speech_analyzer import SpeechAnalysisResult


class AIConversationEngine:
    """
    Engine principal para conversação com IA
    """
    
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.settings = settings.AI_SPEAKING_SETTINGS
        self.conversation_context = []
        self.user_profile = {}
        
    async def initialize_conversation(self, exercise_type: str, difficulty: str, topic: str) -> str:
        """Inicia uma nova conversação baseada no exercício"""
        
        system_prompt = f"""
        Você é um professor de inglês especializado em conversação, trabalhando com um aluno de nível {difficulty}.
        
        Contexto do exercício:
        - Tipo: {exercise_type}
        - Tópico: {topic}
        - Objetivo: Praticar conversação natural e avaliar pronúncia
        
        Instruções:
        1. Seja natural e encorajador
        2. Mantenha o nível de linguagem apropriado para {difficulty}
        3. Faça perguntas abertas que incentivem respostas elaboradas
        4. Se o aluno cometer erros, corrija gentilmente
        5. Adapte-se ao ritmo e interesse do aluno
        6. Mantenha o foco no tópico mas permita desvios naturais
        
        Comece a conversação com uma saudação apropriada e uma pergunta sobre o tópico.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Vamos começar uma conversação sobre {topic}"}
                ],
                max_tokens=self.settings['CONVERSATION']['MAX_TOKENS'],
                temperature=self.settings['CONVERSATION']['TEMPERATURE']
            )
            
            ai_message = response.choices[0].message.content
            self.conversation_context.append({"role": "assistant", "content": ai_message})
            
            return ai_message
            
        except Exception as e:
            print(f"Conversation initialization error: {e}")
            return f"Hello! I'm excited to talk with you about {topic}. How are you today?"
    
    async def continue_conversation(self, user_input: str, analysis_result: Optional[SpeechAnalysisResult] = None) -> str:
        """Continua a conversação baseada na entrada do usuário e análise"""
        
        # Construir contexto da análise para a IA
        analysis_context = ""
        if analysis_result:
            analysis_context = f"""
            Análise da fala do aluno:
            - Pontuação geral: {analysis_result.overall_score}%
            - Pronúncia: {analysis_result.pronunciation_score}%
            - Fluência: {analysis_result.fluency_score}%
            - Precisão: {analysis_result.accuracy_score}%
            - Texto falado: "{analysis_result.transcribed_text}"
            
            Principais erros detectados:
            {json.dumps(analysis_result.grammar_errors, indent=2)}
            """
        
        # Adicionar entrada do usuário ao contexto
        self.conversation_context.append({"role": "user", "content": user_input})
        
        # Preparar prompt para continuação
        continuation_prompt = f"""
        {analysis_context}
        
        Com base na análise acima:
        1. Responda naturalmente ao que o aluno disse
        2. Se houver erros significativos (< 70%), corrija gentilmente
        3. Se a pronúncia está baixa (< 60%), dê uma dica específica
        4. Mantenha a conversação fluindo naturalmente
        5. Faça uma nova pergunta para continuar o diálogo
        
        Seja encorajador e mantenha o tom positivo.
        """
        
        # Usar últimas mensagens para contexto (evitar limite de tokens)
        recent_messages = [
            {"role": "system", "content": continuation_prompt}
        ] + self.conversation_context[-self.settings['CONVERSATION']['MAX_CONTEXT_MESSAGES']:]
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=recent_messages,
                max_tokens=self.settings['CONVERSATION']['MAX_TOKENS'],
                temperature=self.settings['CONVERSATION']['TEMPERATURE']
            )
            
            ai_message = response.choices[0].message.content
            self.conversation_context.append({"role": "assistant", "content": ai_message})
            
            return ai_message
            
        except Exception as e:
            print(f"Conversation continuation error: {e}")
            return "That's interesting! Can you tell me more about that?"
    
    async def generate_topic_specific_question(self, topic: str, difficulty: str) -> str:
        """Gera uma pergunta específica sobre um tópico"""
        
        prompt = f"""
        Generate an engaging conversation starter question about {topic} 
        for a {difficulty} level English student.
        
        The question should:
        1. Be appropriate for the student's level
        2. Encourage detailed responses
        3. Be open-ended and interesting
        4. Relate to everyday life or practical situations
        
        Return only the question, nothing else.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Question generation error: {e}")
            return f"What do you think about {topic}?"
    
    async def generate_follow_up_exercises(self, conversation_history: List[Dict], 
                                         analysis_results: List[SpeechAnalysisResult]) -> List[str]:
        """Gera exercícios de follow-up baseados na conversa"""
        
        # Analisar padrões de erro comum
        common_errors = []
        weak_areas = []
        
        for result in analysis_results:
            if result.pronunciation_score < 70:
                weak_areas.append("pronunciation")
            if result.fluency_score < 70:
                weak_areas.append("fluency")
            if result.accuracy_score < 70:
                weak_areas.append("grammar")
            
            common_errors.extend(result.grammar_errors)
        
        exercises_prompt = f"""
        Based on the following conversation analysis:
        
        Weak areas: {', '.join(set(weak_areas))}
        Common errors: {json.dumps(common_errors[:3], indent=2)}
        
        Suggest 3 specific follow-up exercises that would help this student improve.
        Each exercise should be practical and focused on their specific challenges.
        
        Format as a JSON list of strings.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=[{"role": "user", "content": exercises_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            exercises = json.loads(response.choices[0].message.content)
            return exercises if isinstance(exercises, list) else []
            
        except Exception as e:
            print(f"Follow-up exercises error: {e}")
            return [
                "Practice pronunciation of challenging words",
                "Record yourself reading a short paragraph",
                "Have a 5-minute conversation about today's topic"
            ]
    
    def get_conversation_summary(self) -> Dict:
        """Retorna resumo da conversa atual"""
        
        return {
            "total_turns": len(self.conversation_context),
            "user_turns": len([msg for msg in self.conversation_context if msg["role"] == "user"]),
            "ai_turns": len([msg for msg in self.conversation_context if msg["role"] == "assistant"]),
            "conversation_length": sum(len(msg["content"].split()) for msg in self.conversation_context),
            "recent_context": self.conversation_context[-4:] if self.conversation_context else []
        }
    
    def reset_conversation(self):
        """Reinicia o contexto da conversa"""
        self.conversation_context = []
        self.user_profile = {}


class TTSEngine:
    """
    Text-to-Speech engine using OpenAI TTS
    """
    
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.settings = settings.AI_SPEAKING_SETTINGS['TTS']
    
    async def generate_speech(self, text: str, voice: Optional[str] = None) -> bytes:
        """Gera áudio TTS para o texto fornecido"""
        
        try:
            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                model=self.settings['MODEL'],
                voice=voice or self.settings['VOICE'],
                input=text,
                response_format=self.settings['RESPONSE_FORMAT']
            )
            
            return response.content
            
        except Exception as e:
            print(f"TTS generation error: {e}")
            return b""  # Return empty bytes on error
    
    async def generate_pronunciation_example(self, word: str, phonetic: str = "") -> bytes:
        """Gera exemplo de pronúncia para uma palavra específica"""
        
        # Create a sentence that emphasizes the word pronunciation
        example_text = f"Listen carefully: {word}. Now repeat: {word}."
        if phonetic:
            example_text = f"The word {word} is pronounced {phonetic}. Listen: {word}."
        
        return await self.generate_speech(example_text)
    
    def get_available_voices(self) -> List[str]:
        """Retorna lista de vozes disponíveis"""
        
        # OpenAI TTS voices
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]