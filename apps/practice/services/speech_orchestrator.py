"""
Speech Practice Orchestrator for Vapi Integration
Manages speech practice sessions with real-time TTS/STT streaming
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import openai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class SessionConfig:
    """Configuration for a speech practice session"""
    session_id: str
    student_name: str
    student_level: str  # A1, A2, B1, B2, C1, C2
    domain: str  # general, petroleum, IT, business
    objective: str
    speaking_speed_target: float = 1.0
    correction_mode: str = "gentle"  # gentle, direct
    vapi_stream_url: Optional[str] = None
    language: str = "en-US"

@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    who: str  # agent or student
    text: str
    timestamp: str
    audio_ref: Optional[str] = None

@dataclass
class Correction:
    """Represents a speech correction"""
    original_phrase: str
    corrected_phrase: str
    error_type: str  # pronunciation, grammar, vocab, fluency
    explanation_pt: str
    example_correct_use: str

@dataclass
class SpeechSessionResponse:
    """Complete response for a speech practice session"""
    session_id: str
    agent_text: str
    agent_ssml: str
    expected_transcript: List[str]
    simulated_student_utterance: Optional[str] = None
    student_transcript: Optional[str] = None
    corrections: List[Correction] = None
    fluency_score: Optional[int] = None
    pronunciation_score: Optional[int] = None
    session_feedback_pt: Optional[str] = None
    session_feedback_en: Optional[str] = None
    suggested_drill: Optional[str] = None
    next_agent_prompt: Optional[str] = None
    metadata: Optional[Dict] = None

class SpeechOrchestrator:
    """
    Speech Practice Orchestrator for Vapi Integration
    
    Controls dialogue, generates agent speech in SSML format,
    produces expected transcriptions, identifies and corrects student errors,
    and delivers pedagogical summary at session end.
    """
    
    # Domain-specific vocabulary
    DOMAIN_VOCABULARIES = {
        'petroleum': {
            'A1-A2': ['oil', 'gas', 'drill', 'rig', 'pipe', 'safety'],
            'B1-B2': ['exploration', 'extraction', 'refinery', 'offshore', 'pipeline', 'pressure', 'equipment'],
            'C1-C2': ['hydrocarbon', 'seismic survey', 'reservoir', 'wellhead', 'subsea', 'petrochemical', 'upstream']
        },
        'IT': {
            'A1-A2': ['computer', 'software', 'data', 'code', 'bug', 'system'],
            'B1-B2': ['database', 'server', 'network', 'programming', 'debugging', 'interface', 'deployment'],
            'C1-C2': ['architecture', 'scalability', 'microservices', 'containerization', 'orchestration', 'DevOps']
        },
        'business': {
            'A1-A2': ['meeting', 'client', 'project', 'team', 'budget', 'deadline'],
            'B1-B2': ['negotiation', 'contract', 'stakeholder', 'revenue', 'strategy', 'proposal'],
            'C1-C2': ['leverage', 'synergy', 'optimization', 'diversification', 'monetization', 'scalability']
        }
    }
    
    def __init__(self):
        """Initialize the speech orchestrator"""
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def orchestrate_session(self, 
                                session_config: SessionConfig,
                                conversation_history: List[ConversationTurn],
                                student_audio_ref: Optional[str] = None,
                                student_transcript: Optional[str] = None) -> SpeechSessionResponse:
        """
        Main orchestration method - handles a complete session turn
        
        Args:
            session_config: Session configuration
            conversation_history: Previous conversation turns
            student_audio_ref: Audio file reference (if not streaming)
            student_transcript: Student's transcribed speech
            
        Returns:
            Complete session response with agent speech, corrections, and feedback
        """
        try:
            logger.info(f"🎭 Orchestrating session {session_config.session_id}")
            
            # Generate agent response
            agent_text, agent_ssml = await self._generate_agent_response(
                session_config, conversation_history
            )
            
            # Generate expected transcript
            expected_transcript = await self._generate_expected_transcript(
                session_config, agent_text, conversation_history
            )
            
            response = SpeechSessionResponse(
                session_id=session_config.session_id,
                agent_text=agent_text,
                agent_ssml=agent_ssml,
                expected_transcript=expected_transcript,
                metadata={
                    'level': session_config.student_level,
                    'domain': session_config.domain,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # If student transcript provided, analyze and correct
            if student_transcript:
                response.student_transcript = student_transcript
                
                # Generate corrections
                response.corrections = await self._generate_corrections(
                    session_config, student_transcript, expected_transcript
                )
                
                # Calculate scores
                response.fluency_score, response.pronunciation_score = await self._calculate_scores(
                    session_config, student_transcript, response.corrections
                )
                
                # Generate drill suggestion
                response.suggested_drill = await self._generate_drill(
                    session_config, response.corrections
                )
                
                # Generate session feedback if session is ending
                if len(conversation_history) >= 5:  # Minimum turns for feedback
                    response.session_feedback_pt, response.session_feedback_en = await self._generate_session_feedback(
                        session_config, conversation_history, response.corrections
                    )
            else:
                # Generate simulated student utterance for testing
                response.simulated_student_utterance = await self._simulate_student_utterance(
                    session_config, expected_transcript
                )
            
            # Generate next agent prompt
            response.next_agent_prompt = await self._generate_next_agent_prompt(
                session_config, conversation_history, response.corrections
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error orchestrating session: {str(e)}")
            raise
    
    async def _generate_agent_response(self, 
                                     config: SessionConfig, 
                                     history: List[ConversationTurn]) -> tuple[str, str]:
        """Generate agent's next response in text and SSML format"""
        
        # Get appropriate template
        template = self._get_session_template(config)
        
        # Build conversation context
        context = self._build_conversation_context(history)
        
        # Get domain vocabulary
        vocab_level = self._get_vocab_level_key(config.student_level)
        domain_vocab = self.DOMAIN_VOCABULARIES.get(config.domain, {}).get(vocab_level, [])
        
        prompt = f"""
{template}

STUDENT LEVEL: {config.student_level}
DOMAIN: {config.domain}
OBJECTIVE: {config.objective}
CORRECTION MODE: {config.correction_mode}

DOMAIN VOCABULARY TO INCLUDE: {', '.join(domain_vocab[:3])}

CONVERSATION CONTEXT:
{context}

Generate the agent's next response. Keep it appropriate for {config.student_level} level.
Speak naturally but adjust complexity to the level.

For {config.student_level}:
- A1-A2: Use simple sentences, basic vocabulary, speak slowly
- B1-B2: Use varied vocabulary, moderate complexity
- C1-C2: Use advanced vocabulary, natural complexity

Response should be 1-3 sentences maximum.
"""
        
        response = await self._call_openai(prompt, max_tokens=150, temperature=0.7)
        agent_text = response.strip()
        
        # Convert to SSML
        agent_ssml = self._convert_to_ssml(agent_text, config)
        
        return agent_text, agent_ssml
    
    def _convert_to_ssml(self, text: str, config: SessionConfig) -> str:
        """Convert text to SSML format with appropriate pauses and emphasis"""
        
        # Adjust speaking rate based on level
        rate_map = {
            'A1': 'slow', 'A2': 'slow',
            'B1': 'medium', 'B2': 'medium',
            'C1': 'medium', 'C2': 'medium'
        }
        rate = rate_map.get(config.student_level, 'medium')
        
        # Add pauses after sentences and questions
        ssml_text = text.replace('.', '.<break time="200ms"/>')
        ssml_text = ssml_text.replace('?', '?<break time="300ms"/>')
        ssml_text = ssml_text.replace('!', '!<break time="200ms"/>')
        
        # Wrap in SSML speak tags
        ssml = f'<speak rate="{rate}">{ssml_text}</speak>'
        
        return ssml
    
    async def _generate_expected_transcript(self, 
                                          config: SessionConfig,
                                          agent_text: str,
                                          history: List[ConversationTurn]) -> List[str]:
        """Generate expected student responses"""
        
        prompt = f"""
The agent just said: "{agent_text}"

Generate 2-3 possible appropriate responses a {config.student_level} level student might give.
Domain: {config.domain}

For {config.student_level}:
- A1-A2: Simple responses, basic vocabulary
- B1-B2: More varied responses, some complexity
- C1-C2: Natural, varied responses with good vocabulary

Return as a JSON list of strings.
"""
        
        response = await self._call_openai(prompt, max_tokens=100, temperature=0.8)
        
        try:
            expected = json.loads(response)
            return expected if isinstance(expected, list) else [response]
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return [response.strip()]
    
    async def _generate_corrections(self, 
                                  config: SessionConfig,
                                  student_transcript: str,
                                  expected_transcript: List[str]) -> List[Correction]:
        """Generate corrections for student's speech"""
        
        prompt = f"""
STUDENT LEVEL: {config.student_level}
STUDENT SAID: "{student_transcript}"
EXPECTED RESPONSES: {expected_transcript}
CORRECTION MODE: {config.correction_mode}

Analyze the student's speech and identify errors. For each error, provide:
1. The exact phrase with the error
2. The corrected version
3. Error type: pronunciation, grammar, vocab, or fluency
4. Brief explanation in Portuguese
5. Example of correct usage

Be {config.correction_mode} in your approach.

Return as JSON array of objects with fields:
- original_phrase
- corrected_phrase  
- error_type
- explanation_pt
- example_correct_use

If no significant errors, return empty array.
"""
        
        response = await self._call_openai(prompt, max_tokens=300, temperature=0.3)
        
        try:
            corrections_data = json.loads(response)
            corrections = []
            
            for item in corrections_data:
                correction = Correction(
                    original_phrase=item.get('original_phrase', ''),
                    corrected_phrase=item.get('corrected_phrase', ''),
                    error_type=item.get('error_type', 'grammar'),
                    explanation_pt=item.get('explanation_pt', ''),
                    example_correct_use=item.get('example_correct_use', '')
                )
                corrections.append(correction)
            
            return corrections
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parsing corrections: {e}")
            return []
    
    async def _calculate_scores(self, 
                              config: SessionConfig,
                              student_transcript: str,
                              corrections: List[Correction]) -> tuple[int, int]:
        """Calculate fluency and pronunciation scores"""
        
        # Base scores
        base_fluency = 75
        base_pronunciation = 75
        
        # Adjust based on transcript length and complexity
        word_count = len(student_transcript.split())
        
        if word_count < 3:
            base_fluency -= 20
        elif word_count > 10:
            base_fluency += 10
        
        # Reduce scores based on corrections
        for correction in corrections:
            if correction.error_type == 'fluency':
                base_fluency -= 10
            elif correction.error_type == 'pronunciation':
                base_pronunciation -= 15
            elif correction.error_type == 'grammar':
                base_fluency -= 5
                base_pronunciation -= 5
        
        # Ensure scores are in valid range
        fluency_score = max(0, min(100, base_fluency))
        pronunciation_score = max(0, min(100, base_pronunciation))
        
        return fluency_score, pronunciation_score
    
    async def _generate_drill(self, 
                            config: SessionConfig,
                            corrections: List[Correction]) -> str:
        """Generate a practice drill based on corrections"""
        
        if not corrections:
            return f"Continue practicing {config.domain} vocabulary and speaking naturally."
        
        main_error = corrections[0]
        
        drills = {
            'pronunciation': f"Practice saying: '{main_error.corrected_phrase}' slowly 3 times.",
            'grammar': f"Repeat this structure: '{main_error.corrected_phrase}'",
            'vocab': f"Use this word in a sentence: '{main_error.corrected_phrase.split()[0]}'",
            'fluency': f"Practice speaking this smoothly: '{main_error.corrected_phrase}'"
        }
        
        return drills.get(main_error.error_type, "Keep practicing speaking clearly and naturally.")
    
    async def _generate_session_feedback(self, 
                                       config: SessionConfig,
                                       history: List[ConversationTurn],
                                       corrections: List[Correction]) -> tuple[str, str]:
        """Generate comprehensive session feedback"""
        
        prompt = f"""
STUDENT LEVEL: {config.student_level}
DOMAIN: {config.domain}
TOTAL TURNS: {len(history)}
TOTAL CORRECTIONS: {len(corrections)}

Generate session feedback in both Portuguese and English:

1. Overall performance summary
2. 3 specific improvement actions
3. 3 key phrases to practice

Be encouraging but specific about areas for improvement.

Return as JSON with fields: feedback_pt, feedback_en
"""
        
        response = await self._call_openai(prompt, max_tokens=400, temperature=0.5)
        
        try:
            feedback_data = json.loads(response)
            return feedback_data.get('feedback_pt', ''), feedback_data.get('feedback_en', '')
        except json.JSONDecodeError:
            return "Boa sessão de prática!", "Good practice session!"
    
    async def _simulate_student_utterance(self, 
                                        config: SessionConfig,
                                        expected_transcript: List[str]) -> str:
        """Generate a simulated student response for testing"""
        
        if not expected_transcript:
            return "I understand."
        
        # Add some typical student errors based on level
        base_response = expected_transcript[0]
        
        if config.student_level in ['A1', 'A2']:
            # Simulate common beginner errors
            return base_response.replace("I'd", "I").replace(" a ", " ").lower()
        
        return base_response
    
    async def _generate_next_agent_prompt(self, 
                                        config: SessionConfig,
                                        history: List[ConversationTurn],
                                        corrections: Optional[List[Correction]]) -> str:
        """Generate instruction for next agent turn"""
        
        if not corrections:
            return f"Continue naturally. Maintain {config.student_level} level complexity."
        
        error_types = [c.error_type for c in corrections]
        
        if 'pronunciation' in error_types:
            return "Speak more clearly and slowly. Consider repeating key words."
        elif 'grammar' in error_types:
            return "Model correct grammar naturally in your response."
        elif 'fluency' in error_types:
            return "Give student more time to respond. Ask simpler questions."
        else:
            return "Continue encouraging the student. Maintain current pace."
    
    def _get_session_template(self, config: SessionConfig) -> str:
        """Get appropriate session template based on domain and level"""
        
        templates = {
            ('general', 'A1'): "Roleplay: simple conversation at a cafe. Speak slowly, ask one question at a time.",
            ('general', 'A2'): "Roleplay: small talk with a neighbor. Use basic vocabulary, be encouraging.",
            ('petroleum', 'B1'): "Scenario: Safety briefing before entering offshore platform. Use technical vocabulary appropriately.",
            ('petroleum', 'B2'): "Scenario: Discussing drilling operations with team member. Include technical terms naturally.",
            ('IT', 'B1'): "Scenario: Explaining a simple software problem to a colleague.",
            ('IT', 'B2'): "Scenario: Technical discussion about system architecture.",
            ('business', 'B1'): "Scenario: Team meeting discussion about project timeline.",
            ('business', 'B2'): "Scenario: Client presentation about service proposal."
        }
        
        key = (config.domain, config.student_level)
        return templates.get(key, "Have a natural conversation appropriate for the student's level.")
    
    def _build_conversation_context(self, history: List[ConversationTurn]) -> str:
        """Build conversation context from history"""
        
        if not history:
            return "Starting new conversation."
        
        context_lines = []
        for turn in history[-4:]:  # Last 4 turns
            speaker = "Agent" if turn.who == "agent" else "Student"
            context_lines.append(f"{speaker}: {turn.text}")
        
        return "\n".join(context_lines)
    
    def _get_vocab_level_key(self, level: str) -> str:
        """Convert level to vocabulary key"""
        if level in ['A1', 'A2']:
            return 'A1-A2'
        elif level in ['B1', 'B2']:
            return 'B1-B2'
        else:
            return 'C1-C2'
    
    async def _call_openai(self, prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Make OpenAI API call"""
        try:
            import asyncio
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def to_json(self, response: SpeechSessionResponse) -> str:
        """Convert response to JSON format for API"""
        
        # Convert corrections to dict format
        corrections_dict = []
        if response.corrections:
            corrections_dict = [asdict(correction) for correction in response.corrections]
        
        result = {
            "session_id": response.session_id,
            "agent_text": response.agent_text,
            "agent_ssml": response.agent_ssml,
            "expected_transcript": response.expected_transcript,
            "corrections": corrections_dict,
            "fluency_score": response.fluency_score,
            "pronunciation_score": response.pronunciation_score,
            "session_feedback_pt": response.session_feedback_pt,
            "session_feedback_en": response.session_feedback_en,
            "suggested_drill": response.suggested_drill,
            "next_agent_prompt": response.next_agent_prompt,
            "metadata": response.metadata
        }
        
        # Add optional fields
        if response.simulated_student_utterance:
            result["simulated_student_utterance"] = response.simulated_student_utterance
        if response.student_transcript:
            result["student_transcript"] = response.student_transcript
        
        return json.dumps(result, ensure_ascii=False, indent=2)