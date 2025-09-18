"""
AI Translation Validation Service
Provides intelligent translation evaluation using OpenAI GPT-4
"""

import openai
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from dataclasses import dataclass


@dataclass
class TranslationResult:
    """Result of AI translation validation"""
    semantic_score: int  # 0-100: How well meaning is preserved
    fluency_score: int   # 0-100: How natural the translation sounds
    fidelity_score: int  # 0-100: How faithful to original text
    overall_score: int   # 0-100: Combined score
    is_acceptable: bool  # Whether translation should be accepted
    feedback: str        # Human-readable feedback
    suggestions: List[str]  # Alternative translations
    explanation: str     # Why this score was given
    partial_credit: int  # Points awarded (0-10)


class AITranslationValidator:
    """
    Intelligent translation validator using OpenAI GPT-4
    """
    
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"
        
    async def validate_translation(self, 
                                 source_text: str, 
                                 user_translation: str,
                                 source_language: str = "en",
                                 target_language: str = "pt",
                                 difficulty_level: str = "intermediate") -> TranslationResult:
        """
        Validate user's translation using AI analysis
        
        Args:
            source_text: Original text to translate
            user_translation: User's translation attempt
            source_language: Source language code (default: en)
            target_language: Target language code (default: pt)
            difficulty_level: Student's level (beginner, intermediate, advanced)
        
        Returns:
            TranslationResult with scores and feedback
        """
        
        prompt = self._build_validation_prompt(
            source_text, user_translation, source_language, 
            target_language, difficulty_level
        )
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                response_format={"type": "json_object"}
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return self._parse_ai_response(result_json)
            
        except Exception as e:
            print(f"AI Translation validation error: {e}")
            # Fallback to basic validation
            return self._fallback_validation(source_text, user_translation)
    
    def _get_system_prompt(self) -> str:
        """System prompt for the AI translation evaluator"""
        return """
        Você é um professor especialista em tradução inglês-português com 20 anos de experiência.
        
        Sua tarefa é avaliar traduções de estudantes com critério pedagógico:
        
        1. SEJA JUSTO mas ENCORAJADOR
        2. ACEITE traduções semanticamente corretas, mesmo que não sejam perfeitas
        3. CONSIDERE o nível do estudante
        4. FORNEÇA feedback construtivo
        5. SUGIRA melhorias específicas
        
        Retorne SEMPRE um JSON válido com a estrutura exata solicitada.
        """
    
    def _build_validation_prompt(self, source_text: str, user_translation: str, 
                               source_lang: str, target_lang: str, level: str) -> str:
        """Build the validation prompt for AI"""
        
        return f"""
        Avalie esta tradução de {source_lang} para {target_lang}:
        
        TEXTO ORIGINAL: "{source_text}"
        TRADUÇÃO DO ESTUDANTE: "{user_translation}"
        NÍVEL DO ESTUDANTE: {level}
        
        Analise considerando:
        
        1. CORREÇÃO SEMÂNTICA (0-100): O significado foi preservado?
        2. FLUÊNCIA (0-100): Soa natural em português?
        3. FIDELIDADE (0-100): Quão próximo do original?
        4. PONTUAÇÃO GERAL (0-100): Média ponderada
        
        Critérios de aceitação:
        - 90-100: Excelente (10 pontos)
        - 75-89: Muito bom (8 pontos)
        - 60-74: Bom com pequenos erros (6 pontos)
        - 45-59: Aceitável mas precisa melhorar (4 pontos)
        - 30-44: Parcialmente correto (2 pontos)
        - <30: Incorreto (0 pontos)
        
        RETORNE JSON EXATO:
        {{
            "semantic_score": <número 0-100>,
            "fluency_score": <número 0-100>,
            "fidelity_score": <número 0-100>,
            "overall_score": <número 0-100>,
            "is_acceptable": <true se >= 45>,
            "feedback": "<feedback encorajador em português>",
            "suggestions": ["<alternativa 1>", "<alternativa 2>", "<alternativa 3>"],
            "explanation": "<explicação pedagógica do por que desta pontuação>",
            "partial_credit": <pontos 0-10 baseado na faixa acima>
        }}
        """
    
    def _parse_ai_response(self, response_data: Dict) -> TranslationResult:
        """Parse AI response into TranslationResult"""
        
        return TranslationResult(
            semantic_score=int(response_data.get('semantic_score', 0)),
            fluency_score=int(response_data.get('fluency_score', 0)),
            fidelity_score=int(response_data.get('fidelity_score', 0)),
            overall_score=int(response_data.get('overall_score', 0)),
            is_acceptable=bool(response_data.get('is_acceptable', False)),
            feedback=str(response_data.get('feedback', '')),
            suggestions=list(response_data.get('suggestions', [])),
            explanation=str(response_data.get('explanation', '')),
            partial_credit=int(response_data.get('partial_credit', 0))
        )
    
    def _fallback_validation(self, source_text: str, user_translation: str) -> TranslationResult:
        """Fallback validation when AI fails"""
        
        # Simple word-based similarity as fallback
        source_words = set(source_text.lower().split())
        user_words = set(user_translation.lower().split())
        
        # Basic similarity score
        if user_translation.strip():
            similarity = len(source_words & user_words) / max(len(source_words), len(user_words))
            score = int(similarity * 100)
        else:
            score = 0
        
        return TranslationResult(
            semantic_score=score,
            fluency_score=score,
            fidelity_score=score,
            overall_score=score,
            is_acceptable=score >= 45,
            feedback="Sistema temporariamente indisponível. Tradução avaliada com critério básico.",
            suggestions=["Tente reformular sua tradução"],
            explanation="Avaliação automática básica aplicada.",
            partial_credit=min(10, max(0, score // 10))
        )
    
    async def generate_translation_suggestions(self, 
                                             source_text: str,
                                             difficulty_level: str = "intermediate",
                                             count: int = 3) -> List[str]:
        """
        Generate multiple correct translation alternatives for teachers
        
        Args:
            source_text: Text to translate
            difficulty_level: Target difficulty level
            count: Number of alternatives to generate
            
        Returns:
            List of alternative translations
        """
        
        prompt = f"""
        Gere {count} traduções diferentes mas igualmente corretas para:
        
        TEXTO: "{source_text}"
        NÍVEL: {difficulty_level}
        
        Critérios:
        1. Todas devem estar semanticamente corretas
        2. Variar o nível de formalidade
        3. Usar vocabulário apropriado para o nível
        4. Incluir traduções mais literais e mais naturais
        
        Retorne JSON:
        {{
            "translations": ["<tradução 1>", "<tradução 2>", "<tradução 3>"]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em tradução. Gere alternativas precisas."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('translations', [])
            
        except Exception as e:
            print(f"Translation suggestions error: {e}")
            return [f"Tradução de: {source_text}"]
    
    async def generate_translation_exercise(self,
                                          topic: str,
                                          difficulty_level: str = "intermediate",
                                          exercise_type: str = "sentence") -> Dict:
        """
        Generate a complete translation exercise with source text and expected answers
        
        Args:
            topic: Exercise topic (e.g., "daily routines", "food", "travel")
            difficulty_level: beginner, intermediate, advanced
            exercise_type: sentence, paragraph, dialogue
            
        Returns:
            Dict with source_text, expected_translations, hints, context
        """
        
        prompt = f"""
        Crie um exercício de tradução inglês-português:
        
        TÓPICO: {topic}
        NÍVEL: {difficulty_level}
        TIPO: {exercise_type}
        
        Gere:
        1. Um texto em inglês apropriado para o nível
        2. 2-3 traduções corretas diferentes
        3. 2 dicas úteis
        4. Contexto/situação onde seria usado
        
        Retorne JSON:
        {{
            "source_text": "<texto em inglês>",
            "expected_translations": ["<tradução 1>", "<tradução 2>"],
            "hints": ["<dica 1>", "<dica 2>"],
            "context": "<onde/quando usar>",
            "vocabulary_focus": ["<palavra-chave 1>", "<palavra-chave 2>"]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um criador de exercícios de inglês. Crie conteúdo pedagógico de qualidade."},
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
                "source_text": f"Create an exercise about {topic}",
                "expected_translations": [f"Criar um exercício sobre {topic}"],
                "hints": ["Considere o contexto", "Use vocabulário apropriado"],
                "context": "Exercício educacional",
                "vocabulary_focus": ["exercise", "topic"]
            }


# Helper function for easy access
async def validate_student_translation(source_text: str, user_translation: str, **kwargs) -> TranslationResult:
    """Convenience function for validating translations"""
    validator = AITranslationValidator()
    return await validator.validate_translation(source_text, user_translation, **kwargs)