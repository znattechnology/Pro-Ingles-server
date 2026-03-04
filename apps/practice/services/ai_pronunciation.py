"""
AI Pronunciation Analysis Service
Provides intelligent pronunciation evaluation using OpenAI Whisper and GPT-4
"""

import openai
import json
import asyncio
import io
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from dataclasses import dataclass


@dataclass
class PronunciationResult:
    """Result of AI pronunciation analysis"""
    transcribed_text: str
    expected_text: str
    pronunciation_score: int  # 0-100: Overall pronunciation accuracy
    fluency_score: int       # 0-100: Speaking fluency and rhythm
    clarity_score: int       # 0-100: Articulation clarity
    overall_score: int       # 0-100: Combined score
    is_acceptable: bool      # Whether pronunciation is acceptable
    feedback: str           # Human-readable feedback
    problematic_words: List[str]  # Words that need improvement
    suggestions: List[str]   # Specific improvement suggestions
    partial_credit: int     # Points awarded (0-10)
    confidence_level: float # AI confidence in analysis (0-1)


class AIPronunciationAnalyzer:
    """
    Intelligent pronunciation analyzer using OpenAI Whisper + GPT-4
    """
    
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.whisper_model = "whisper-1"
        self.analysis_model = "gpt-4"
        
    async def analyze_pronunciation(self, 
                                  audio_file: io.BytesIO,
                                  expected_text: str,
                                  difficulty_level: str = "intermediate",
                                  language: str = "en") -> PronunciationResult:
        """
        Analyze pronunciation from audio file
        
        Args:
            audio_file: Audio file in BytesIO format
            expected_text: Text that should have been spoken
            difficulty_level: Student's level (beginner, intermediate, advanced)
            language: Target language for pronunciation (default: en)
        
        Returns:
            PronunciationResult with detailed analysis
        """
        
        try:
            # Step 1: Transcribe audio using Whisper
            transcribed_text = await self._transcribe_audio(audio_file)
            
            # Step 2: Analyze pronunciation using GPT-4
            analysis = await self._analyze_with_gpt4(
                transcribed_text, expected_text, difficulty_level
            )
            
            return analysis
            
        except Exception as e:
            print(f"Pronunciation analysis error: {e}")
            return self._create_fallback_result(expected_text)
    
    async def _transcribe_audio(self, audio_file: io.BytesIO) -> str:
        """Transcribe audio using OpenAI Whisper"""
        
        try:
            # Reset file pointer
            audio_file.seek(0)
            
            # Transcribe with Whisper
            response = await asyncio.to_thread(
                self.client.audio.transcriptions.create,
                model=self.whisper_model,
                file=audio_file,
                response_format="text"
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return ""
    
    async def _analyze_with_gpt4(self, 
                                transcribed: str, 
                                expected: str, 
                                level: str) -> PronunciationResult:
        """Analyze pronunciation accuracy using GPT-4"""
        
        prompt = self._build_analysis_prompt(transcribed, expected, level)
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return self._parse_analysis_response(result_json, transcribed, expected)
            
        except Exception as e:
            print(f"GPT-4 analysis error: {e}")
            return self._create_fallback_result(expected, transcribed)
    
    def _get_system_prompt(self) -> str:
        """System prompt for pronunciation analysis"""
        return """
        Você é um especialista em ensino de pronúncia de inglês com 20 anos de experiência.
        
        Sua tarefa é analisar a pronúncia de estudantes com critério pedagógico:
        
        1. SEJA ENCORAJADOR mas PRECISO
        2. IDENTIFIQUE erros específicos de pronúncia
        3. FORNEÇA feedback construtivo e acionável
        4. CONSIDERE o nível do estudante
        5. FOQUE em melhorias práticas
        
        Retorne SEMPRE um JSON válido com a estrutura exata solicitada.
        """
    
    def _build_analysis_prompt(self, transcribed: str, expected: str, level: str) -> str:
        """Build analysis prompt for GPT-4"""
        
        return f"""
        Analise esta pronúncia de inglês:
        
        TEXTO ESPERADO: "{expected}"
        TEXTO TRANSCRITO: "{transcribed}"
        NÍVEL DO ESTUDANTE: {level}
        
        Analise considerando:
        
        1. PRECISÃO DA PRONÚNCIA (0-100): Quão próximo está do esperado?
        2. FLUÊNCIA (0-100): Ritmo e flow natural da fala
        3. CLAREZA (0-100): Articulação clara das palavras
        4. PONTUAÇÃO GERAL (0-100): Média ponderada das três métricas
        
        Critérios de aceitação:
        - 90-100: Excelente (10 pontos)
        - 80-89: Muito bom (8 pontos)
        - 70-79: Bom (6 pontos)
        - 60-69: Aceitável (4 pontos)
        - 50-59: Precisa melhorar (2 pontos)
        - <50: Insatisfatório (0 pontos)
        
        RETORNE JSON EXATO:
        {{
            "pronunciation_score": <número 0-100>,
            "fluency_score": <número 0-100>,
            "clarity_score": <número 0-100>,
            "overall_score": <número 0-100>,
            "is_acceptable": <true se >= 60>,
            "feedback": "<feedback encorajador em português>",
            "problematic_words": ["<palavra1>", "<palavra2>"],
            "suggestions": ["<sugestão específica 1>", "<sugestão específica 2>"],
            "partial_credit": <pontos 0-10 baseado na faixa acima>,
            "confidence_level": <0.0-1.0 confiança na análise>
        }}
        """
    
    def _parse_analysis_response(self, response_data: Dict, 
                               transcribed: str, expected: str) -> PronunciationResult:
        """Parse GPT-4 response into PronunciationResult"""
        
        return PronunciationResult(
            transcribed_text=transcribed,
            expected_text=expected,
            pronunciation_score=int(response_data.get('pronunciation_score', 0)),
            fluency_score=int(response_data.get('fluency_score', 0)),
            clarity_score=int(response_data.get('clarity_score', 0)),
            overall_score=int(response_data.get('overall_score', 0)),
            is_acceptable=bool(response_data.get('is_acceptable', False)),
            feedback=str(response_data.get('feedback', '')),
            problematic_words=list(response_data.get('problematic_words', [])),
            suggestions=list(response_data.get('suggestions', [])),
            partial_credit=int(response_data.get('partial_credit', 0)),
            confidence_level=float(response_data.get('confidence_level', 0.5))
        )
    
    def _create_fallback_result(self, expected: str, transcribed: str = "") -> PronunciationResult:
        """Create fallback result when AI analysis fails"""
        
        # Basic similarity check as fallback
        if transcribed and expected:
            similarity = len(set(transcribed.lower().split()) & set(expected.lower().split()))
            similarity_ratio = similarity / max(len(expected.split()), 1)
            score = int(similarity_ratio * 100)
        else:
            score = 0
        
        return PronunciationResult(
            transcribed_text=transcribed,
            expected_text=expected,
            pronunciation_score=score,
            fluency_score=score,
            clarity_score=score,
            overall_score=score,
            is_acceptable=score >= 60,
            feedback="Sistema de análise temporariamente indisponível. Pontuação baseada em similaridade básica.",
            problematic_words=[],
            suggestions=["Tente falar mais devagar e articular claramente"],
            partial_credit=min(10, max(0, score // 10)),
            confidence_level=0.3
        )
    
    async def generate_pronunciation_exercise(self,
                                            topic: str = "daily conversation",
                                            difficulty_level: str = "intermediate",
                                            exercise_type: str = "word") -> Dict:
        """
        Generate pronunciation exercise with AI
        
        Args:
            topic: Exercise topic (e.g., "numbers", "food", "travel")
            difficulty_level: beginner, intermediate, advanced  
            exercise_type: word, phrase, sentence, paragraph
            
        Returns:
            Dict with text_to_speak, difficulty_notes, pronunciation_tips
        """
        
        prompt = f"""
        Crie um exercício de pronúncia de inglês:
        
        TÓPICO: {topic}
        NÍVEL: {difficulty_level}
        TIPO: {exercise_type}
        
        Gere:
        1. Texto apropriado para pronunciar
        2. Notas sobre dificuldades específicas
        3. Dicas de pronúncia
        4. Pontos focais para o estudante
        
        Retorne JSON:
        {{
            "text_to_speak": "<texto em inglês para pronunciar>",
            "difficulty_notes": ["<dificuldade 1>", "<dificuldade 2>"],
            "pronunciation_tips": ["<dica 1>", "<dica 2>"],
            "focus_points": ["<ponto focal 1>", "<ponto focal 2>"],
            "phonetic_guide": "<guia fonético se necessário>"
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.analysis_model,
                messages=[
                    {"role": "system", "content": "Você é um criador de exercícios de pronúncia. Crie conteúdo pedagógico de qualidade."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Exercise generation error: {e}")
            return {
                "text_to_speak": f"Practice pronunciation with {topic}",
                "difficulty_notes": ["Focus on clear articulation"],
                "pronunciation_tips": ["Speak slowly and clearly"],
                "focus_points": ["Consonant sounds", "Vowel sounds"],
                "phonetic_guide": ""
            }
    
    async def generate_reference_audio(self, text: str, voice: str = "alloy") -> bytes:
        """
        Generate reference audio using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice: TTS voice (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio bytes for reference pronunciation
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                model="tts-1",
                voice=voice,
                input=text,
                response_format="mp3"
            )
            
            return response.content

        except Exception as e:
            print(f"TTS generation error: {e}")
            return b""

    def generate_reference_audio_sync(self, text: str, voice: str = "alloy") -> bytes:
        """
        Synchronous version of generate_reference_audio for use in Django views.

        Args:
            text: Text to convert to speech
            voice: TTS voice (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            Audio bytes for reference pronunciation
        """

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                response_format="mp3"
            )

            return response.content

        except Exception as e:
            print(f"TTS generation error (sync): {e}")
            return b""


# Helper function for easy access
async def analyze_student_pronunciation(audio_file: io.BytesIO, 
                                      expected_text: str, 
                                      **kwargs) -> PronunciationResult:
    """Convenience function for analyzing pronunciation"""
    analyzer = AIPronunciationAnalyzer()
    return await analyzer.analyze_pronunciation(audio_file, expected_text, **kwargs)