"""
AI Speech Analysis Service
Provides comprehensive speech analysis using OpenAI APIs
"""

import openai
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import io
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile


class FeedbackType(Enum):
    PRONUNCIATION = "pronunciation"
    FLUENCY = "fluency" 
    ACCURACY = "accuracy"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    CONFIDENCE = "confidence"


@dataclass
class SpeechAnalysisResult:
    """Resultado da análise de fala"""
    overall_score: float
    pronunciation_score: float
    fluency_score: float
    accuracy_score: float
    confidence_score: float
    
    transcribed_text: str
    target_text: str
    
    word_analysis: List[Dict]
    phoneme_analysis: List[Dict]
    grammar_errors: List[Dict]
    
    feedback_text: str
    improvement_suggestions: List[str]
    next_exercises: List[str]


class SpeechAnalyzer:
    """
    Analisador principal de fala usando OpenAI Whisper e análise customizada
    """
    
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.settings = settings.AI_SPEAKING_SETTINGS
    
    async def analyze_speech(self, audio_file, target_text: str = "") -> SpeechAnalysisResult:
        """Análise completa de um arquivo de áudio"""
        
        # 1. Transcrição com Whisper
        transcription = await self._transcribe_audio(audio_file)
        
        # 2. Análise de pronúncia
        pronunciation_analysis = await self._analyze_pronunciation(transcription, target_text)
        
        # 3. Análise de fluência
        fluency_analysis = await self._analyze_fluency(transcription)
        
        # 4. Análise de precisão/gramática
        accuracy_analysis = await self._analyze_accuracy(transcription, target_text)
        
        # 5. Análise de confiança
        confidence_analysis = await self._analyze_confidence()
        
        # 6. Geração de feedback
        feedback = await self._generate_feedback(
            transcription, target_text, pronunciation_analysis, 
            fluency_analysis, accuracy_analysis
        )
        
        # 7. Cálculo de pontuação geral
        overall_score = self._calculate_overall_score(
            pronunciation_analysis['score'],
            fluency_analysis['score'],
            accuracy_analysis['score'],
            confidence_analysis['score']
        )
        
        return SpeechAnalysisResult(
            overall_score=overall_score,
            pronunciation_score=pronunciation_analysis['score'],
            fluency_score=fluency_analysis['score'],
            accuracy_score=accuracy_analysis['score'],
            confidence_score=confidence_analysis['score'],
            transcribed_text=transcription,
            target_text=target_text,
            word_analysis=pronunciation_analysis['word_analysis'],
            phoneme_analysis=pronunciation_analysis['phoneme_analysis'],
            grammar_errors=accuracy_analysis['grammar_errors'],
            feedback_text=feedback['text'],
            improvement_suggestions=feedback['suggestions'],
            next_exercises=feedback['next_exercises']
        )
    
    async def _transcribe_audio(self, audio_file) -> str:
        """Transcreve áudio usando OpenAI Whisper"""
        
        try:
            # Convert Django uploaded file to format expected by OpenAI
            if hasattr(audio_file, 'read'):
                audio_data = audio_file.read()
                audio_file.seek(0)  # Reset file pointer
            else:
                audio_data = audio_file
            
            # Create a file-like object for OpenAI
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = "speech.wav"  # OpenAI requires a filename
            
            response = await asyncio.to_thread(
                self.client.audio.transcriptions.create,
                model=self.settings['MODELS']['WHISPER'],
                file=audio_buffer,
                response_format="json",
                language="en"
            )
            
            return response.text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return "Erro na transcrição do áudio"
    
    async def _analyze_pronunciation(self, transcription: str, target_text: str) -> Dict:
        """Análise detalhada de pronúncia"""
        
        word_analysis = []
        phoneme_analysis = []
        
        if target_text:
            # Comparação palavra por palavra
            target_words = target_text.lower().split()
            spoken_words = transcription.lower().split()
            
            for i, target_word in enumerate(target_words):
                spoken_word = spoken_words[i] if i < len(spoken_words) else ""
                
                # Cálculo de similaridade
                similarity = self._calculate_word_similarity(target_word, spoken_word)
                
                word_analysis.append({
                    "word": target_word,
                    "spoken": spoken_word,
                    "accuracy": similarity,
                    "phonetic_errors": self._detect_phonetic_errors(target_word, spoken_word)
                })
        
        # Pontuação geral de pronúncia
        pronunciation_score = np.mean([w["accuracy"] for w in word_analysis]) if word_analysis else 85.0
        
        return {
            "score": min(100.0, max(0.0, pronunciation_score)),
            "word_analysis": word_analysis,
            "phoneme_analysis": phoneme_analysis
        }
    
    async def _analyze_fluency(self, transcription: str) -> Dict:
        """Análise de fluência baseada em pausas e ritmo"""
        
        words = transcription.split()
        word_count = len(words)
        
        # Estimativa de fluência baseada em critérios simples
        fluency_factors = {
            "word_count": min(100, word_count * 10),  # Mais palavras = maior fluência
            "sentence_structure": 85 if len(words) > 5 else 60,  # Frases completas
            "hesitation_markers": 90 if not any(marker in transcription.lower() 
                                              for marker in ["um", "uh", "er"]) else 70
        }
        
        fluency_score = np.mean(list(fluency_factors.values()))
        
        return {
            "score": fluency_score,
            "analysis": fluency_factors,
            "words_per_minute": word_count * 2,  # Estimativa
            "pause_analysis": []
        }
    
    async def _analyze_accuracy(self, transcription: str, target_text: str) -> Dict:
        """Análise de precisão gramatical e semântica"""
        
        grammar_prompt = f"""
        Analise a seguinte fala em inglês para erros gramaticais e de vocabulário:
        
        Texto falado: "{transcription}"
        Texto alvo (se houver): "{target_text}"
        
        Retorne uma análise em formato JSON com:
        1. Pontuação geral (0-100)
        2. Lista de erros gramaticais encontrados
        3. Sugestões de correção
        4. Nível de adequação vocabular
        
        Seja específico mas construtivo.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=[{"role": "user", "content": grammar_prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            # Parse da resposta (assumindo JSON válido)
            analysis = json.loads(response.choices[0].message.content)
            
        except:
            # Fallback para análise simples
            analysis = {
                "score": 85.0,
                "grammar_errors": [],
                "suggestions": ["Continue praticando!"],
                "vocabulary_level": "appropriate"
            }
        
        return {
            "score": analysis.get("score", 85.0),
            "grammar_errors": analysis.get("grammar_errors", []),
            "suggestions": analysis.get("suggestions", [])
        }
    
    async def _analyze_confidence(self) -> Dict:
        """Análise de confiança baseada em características de áudio"""
        
        # Análise simplificada - em produção usar análise de audio real
        # Características como volume, clareza, hesitação, etc.
        
        confidence_score = 80.0  # Base score
        
        return {
            "score": confidence_score,
            "volume_analysis": "adequate",
            "clarity_rating": "good",
            "hesitation_count": 2
        }
    
    async def _generate_feedback(self, transcription: str, target_text: str, 
                                pronunciation: Dict, fluency: Dict, accuracy: Dict) -> Dict:
        """Gera feedback personalizado usando GPT-4"""
        
        feedback_prompt = f"""
        Como professor de inglês experiente, gere feedback construtivo para um aluno baseado na seguinte análise:
        
        Texto falado: "{transcription}"
        Texto alvo: "{target_text}"
        
        Pontuações:
        - Pronúncia: {pronunciation['score']}%
        - Fluência: {fluency['score']}%
        - Precisão: {accuracy['score']}%
        
        Erros detectados:
        {json.dumps(accuracy['grammar_errors'], indent=2)}
        
        Gere:
        1. Feedback encorajador (2-3 frases)
        2. 3 sugestões específicas de melhoria
        3. 2 exercícios recomendados para próximas práticas
        
        Tom: Positivo, específico e actionable.
        Formato: JSON com campos 'text', 'suggestions', 'next_exercises'
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.settings['MODELS']['CHAT'],
                messages=[{"role": "user", "content": feedback_prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            feedback = json.loads(response.choices[0].message.content)
            
        except:
            # Fallback feedback
            feedback = {
                "text": "Ótimo trabalho! Continue praticando para melhorar ainda mais.",
                "suggestions": [
                    "Foque na pronúncia de palavras específicas",
                    "Tente falar mais devagar para maior clareza",
                    "Pratique frases mais longas"
                ],
                "next_exercises": [
                    "Exercício de pronúncia focado",
                    "Prática de conversação livre"
                ]
            }
        
        return feedback
    
    def _calculate_overall_score(self, pronunciation: float, fluency: float, 
                                accuracy: float, confidence: float) -> float:
        """Calcula pontuação geral ponderada"""
        
        weights = self.settings['SCORING_WEIGHTS']
        
        overall = (
            pronunciation * weights['PRONUNCIATION'] +
            fluency * weights['FLUENCY'] +
            accuracy * weights['ACCURACY'] +
            confidence * weights['CONFIDENCE']
        )
        
        return round(overall, 1)
    
    def _calculate_word_similarity(self, target: str, spoken: str) -> float:
        """Calcula similaridade entre duas palavras"""
        
        if target == spoken:
            return 100.0
        
        if len(target) == 0:
            return 0.0
        
        # Algoritmo simples de similaridade
        common_chars = sum(1 for a, b in zip(target, spoken) if a == b)
        similarity = (common_chars / len(target)) * 100
        
        return max(0.0, similarity)
    
    def _detect_phonetic_errors(self, target: str, spoken: str) -> List[str]:
        """Detecta erros fonéticos comuns"""
        
        # Análise simplificada - em produção usar IPA e análise fonética real
        errors = []
        
        common_substitutions = {
            'th': ['f', 'd', 't'],
            'v': ['w', 'b'],
            'w': ['v', 'u'],
            'r': ['l', 'w']
        }
        
        for phoneme, substitutions in common_substitutions.items():
            if phoneme in target and any(sub in spoken for sub in substitutions):
                errors.append(f"Possível substituição de '{phoneme}' sound")
        
        return errors


class QuickAnalyzer:
    """
    Analyzer for real-time feedback during recording
    """
    
    def __init__(self):
        pass
    
    async def quick_analysis(self, audio_chunk: bytes) -> Dict:
        """Análise rápida de chunk de áudio"""
        
        # Análise simplificada para demo
        # Em produção, usar bibliotecas de processamento de áudio real
        
        return {
            "confidence": np.random.uniform(70, 90),
            "volume": np.random.uniform(40, 80),
            "clarity": np.random.uniform(60, 85)
        }