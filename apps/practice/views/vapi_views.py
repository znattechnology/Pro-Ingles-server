"""
Vapi Speech Practice API Views
REST endpoints for Vapi integration testing and standalone usage
"""

import json
import uuid
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from asgiref.sync import async_to_sync
import logging

from ..services.speech_orchestrator import SpeechOrchestrator, SessionConfig, ConversationTurn
from ..services.vapi_client import VapiClient

logger = logging.getLogger(__name__)

class VapiSessionView(View):
    """
    REST API for Vapi Speech Practice Sessions
    """
    
    def __init__(self):
        super().__init__()
        self.orchestrator = SpeechOrchestrator()
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        """
        Start a new Vapi session or process student transcript
        
        Expected JSON body:
        {
            "action": "start_session" | "process_transcript",
            "session_config": {
                "session_id": "uuid",
                "student_name": "string",
                "student_level": "A1|A2|B1|B2|C1|C2",
                "domain": "general|petroleum|IT|business",
                "objective": "string",
                "correction_mode": "gentle|direct",
                "language": "en-US"
            },
            "conversation_history": [...], // For process_transcript
            "student_transcript": "string" // For process_transcript
        }
        """
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'start_session':
                return self._start_session(data)
            elif action == 'process_transcript':
                return self._process_transcript(data)
            else:
                return JsonResponse({
                    'error': 'Invalid action. Use "start_session" or "process_transcript"'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in VapiSessionView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def _start_session(self, data: Dict[str, Any]) -> JsonResponse:
        """Start a new Vapi session"""
        try:
            config_data = data.get('session_config', {})
            
            session_config = SessionConfig(
                session_id=config_data.get('session_id', str(uuid.uuid4())),
                student_name=config_data.get('student_name', 'Student'),
                student_level=config_data.get('student_level', 'B1'),
                domain=config_data.get('domain', 'general'),
                objective=config_data.get('objective', 'Practice speaking naturally'),
                correction_mode=config_data.get('correction_mode', 'gentle'),
                language=config_data.get('language', 'en-US')
            )
            
            # Generate initial session
            session_response = async_to_sync(self.orchestrator.orchestrate_session)(
                session_config=session_config,
                conversation_history=[]
            )
            
            # Convert to JSON format
            response_json = json.loads(self.orchestrator.to_json(session_response))
            
            return JsonResponse({
                'success': True,
                'session': response_json
            })
            
        except Exception as e:
            logger.error(f"Error starting Vapi session: {str(e)}")
            return JsonResponse({'error': f'Failed to start session: {str(e)}'}, status=500)
    
    def _process_transcript(self, data: Dict[str, Any]) -> JsonResponse:
        """Process student transcript and generate response"""
        try:
            config_data = data.get('session_config', {})
            student_transcript = data.get('student_transcript', '')
            history_data = data.get('conversation_history', [])
            
            if not student_transcript.strip():
                return JsonResponse({'error': 'Empty student transcript'}, status=400)
            
            session_config = SessionConfig(
                session_id=config_data.get('session_id', str(uuid.uuid4())),
                student_name=config_data.get('student_name', 'Student'),
                student_level=config_data.get('student_level', 'B1'),
                domain=config_data.get('domain', 'general'),
                objective=config_data.get('objective', 'Continue conversation'),
                correction_mode=config_data.get('correction_mode', 'gentle'),
                language=config_data.get('language', 'en-US')
            )
            
            # Convert history to ConversationTurn objects
            conversation_history = []
            for item in history_data:
                turn = ConversationTurn(
                    who=item.get('who', 'student'),
                    text=item.get('text', ''),
                    timestamp=item.get('timestamp', ''),
                    audio_ref=item.get('audio_ref')
                )
                conversation_history.append(turn)
            
            # Process with orchestrator
            session_response = async_to_sync(self.orchestrator.orchestrate_session)(
                session_config=session_config,
                conversation_history=conversation_history,
                student_transcript=student_transcript
            )
            
            # Convert to JSON format
            response_json = json.loads(self.orchestrator.to_json(session_response))
            
            return JsonResponse({
                'success': True,
                'session': response_json
            })
            
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            return JsonResponse({'error': f'Failed to process transcript: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def vapi_templates(request):
    """
    Get available session templates for different domains and levels
    """
    templates = {
        'domains': ['general', 'petroleum', 'IT', 'business'],
        'levels': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
        'correction_modes': ['gentle', 'direct'],
        'sample_objectives': {
            'general': [
                'Practice everyday conversation',
                'Improve pronunciation and fluency',
                'Build confidence in speaking'
            ],
            'petroleum': [
                'Learn technical oil & gas vocabulary',
                'Practice safety communication',
                'Offshore operations discussion'
            ],
            'IT': [
                'Technical interview preparation',
                'Software development discussions',
                'IT project communication'
            ],
            'business': [
                'Business meeting participation',
                'Client presentation skills',
                'Negotiation practice'
            ]
        },
        'sample_config': {
            'session_id': 'uuid-here',
            'student_name': 'João Silva',
            'student_level': 'B1',
            'domain': 'petroleum',
            'objective': 'Learn technical oil & gas vocabulary',
            'correction_mode': 'gentle',
            'language': 'en-US'
        }
    }
    
    return JsonResponse(templates)


@csrf_exempt  
@require_http_methods(["POST"])
def vapi_simulate(request):
    """
    Simulate a complete Vapi conversation for testing
    """
    try:
        data = json.loads(request.body)
        turns = data.get('turns', 3)
        student_level = data.get('student_level', 'B1')
        domain = data.get('domain', 'general')
        
        orchestrator = SpeechOrchestrator()
        
        session_config = SessionConfig(
            session_id=str(uuid.uuid4()),
            student_name='Test Student',
            student_level=student_level,
            domain=domain,
            objective='Simulation test',
            correction_mode='gentle'
        )
        
        conversation_log = []
        conversation_history = []
        
        # Start session
        session_response = async_to_sync(orchestrator.orchestrate_session)(
            session_config=session_config,
            conversation_history=[]
        )
        
        conversation_log.append({
            'turn': 0,
            'type': 'agent_start',
            'agent_text': session_response.agent_text,
            'agent_ssml': session_response.agent_ssml,
            'expected_transcript': session_response.expected_transcript
        })
        
        # Simulate conversation turns
        for turn in range(1, turns + 1):
            # Use simulated student response
            if session_response.expected_transcript:
                student_response = session_response.expected_transcript[0]
            else:
                student_response = "I understand."
            
            # Add simulated student turn
            student_turn = ConversationTurn(
                who='student',
                text=student_response,
                timestamp=f'turn-{turn}'
            )
            conversation_history.append(student_turn)
            
            # Generate agent response
            session_response = async_to_sync(orchestrator.orchestrate_session)(
                session_config=session_config,
                conversation_history=conversation_history,
                student_transcript=student_response
            )
            
            # Add agent turn
            agent_turn = ConversationTurn(
                who='agent',
                text=session_response.agent_text,
                timestamp=f'turn-{turn}-agent'
            )
            conversation_history.append(agent_turn)
            
            conversation_log.append({
                'turn': turn,
                'student_said': student_response,
                'agent_text': session_response.agent_text,
                'agent_ssml': session_response.agent_ssml,
                'corrections': [
                    {
                        'original_phrase': c.original_phrase,
                        'corrected_phrase': c.corrected_phrase,
                        'error_type': c.error_type,
                        'explanation_pt': c.explanation_pt
                    } for c in (session_response.corrections or [])
                ],
                'scores': {
                    'fluency': session_response.fluency_score,
                    'pronunciation': session_response.pronunciation_score
                }
            })
        
        return JsonResponse({
            'success': True,
            'simulation': {
                'session_id': session_config.session_id,
                'config': {
                    'student_level': student_level,
                    'domain': domain,
                    'total_turns': turns
                },
                'conversation_log': conversation_log
            }
        })
        
    except Exception as e:
        logger.error(f"Error in simulation: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def vapi_webhook(request):
    """
    Webhook endpoint for Vapi events
    Receives real-time updates from Vapi during calls
    """
    try:
        data = json.loads(request.body)
        message_type = data.get('message', {}).get('type')
        
        logger.info(f"📞 Received Vapi webhook: {message_type}")
        
        if message_type == 'transcript':
            # Handle real-time transcript
            return _handle_transcript_webhook(data)
        
        elif message_type == 'hang':
            # Handle call end
            return _handle_call_end_webhook(data)
            
        elif message_type == 'speech-update':
            # Handle speech status updates
            return _handle_speech_update_webhook(data)
            
        elif message_type == 'function-call':
            # Handle function calls from assistant
            return _handle_function_call_webhook(data)
        
        else:
            logger.info(f"Unhandled webhook type: {message_type}")
            return JsonResponse({'status': 'received'})
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_transcript_webhook(data: Dict) -> JsonResponse:
    """Handle transcript updates from Vapi"""
    try:
        message = data.get('message', {})
        transcript = message.get('transcript', '')
        role = message.get('role', 'user')  # user or assistant
        
        if role == 'user' and transcript.strip():
            logger.info(f"📝 User transcript: {transcript}")
            
            # Here you could trigger our speech orchestrator
            # to analyze and provide corrections in real-time
            
            # For now, just log and acknowledge
            return JsonResponse({
                'status': 'transcript_processed',
                'transcript': transcript
            })
        
        return JsonResponse({'status': 'received'})
        
    except Exception as e:
        logger.error(f"❌ Transcript webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_call_end_webhook(data: Dict) -> JsonResponse:
    """Handle call end events"""
    try:
        call_info = data.get('call', {})
        call_id = call_info.get('id')
        
        logger.info(f"📞 Call ended: {call_id}")
        
        # Here you could generate final session report
        # using our speech orchestrator's feedback system
        
        return JsonResponse({
            'status': 'call_ended',
            'call_id': call_id
        })
        
    except Exception as e:
        logger.error(f"❌ Call end webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_speech_update_webhook(data: Dict) -> JsonResponse:
    """Handle speech status updates"""
    try:
        message = data.get('message', {})
        status = message.get('status')  # started, stopped
        
        logger.info(f"🗣️ Speech update: {status}")
        
        return JsonResponse({'status': 'speech_update_received'})
        
    except Exception as e:
        logger.error(f"❌ Speech update webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_function_call_webhook(data: Dict) -> JsonResponse:
    """Handle function calls from Vapi assistant"""
    try:
        message = data.get('message', {})
        function_call = message.get('functionCall', {})
        function_name = function_call.get('name')
        
        logger.info(f"🔧 Function call: {function_name}")
        
        # You can implement custom functions here
        # that the Vapi assistant can call during conversation
        
        return JsonResponse({
            'status': 'function_call_handled',
            'function': function_name
        })
        
    except Exception as e:
        logger.error(f"❌ Function call webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def vapi_assistant_manager(request):
    """
    Create and manage Vapi assistants
    """
    if request.method == 'GET':
        # Return English practice assistant specifically
        try:
            from django.conf import settings
            english_assistant_id = getattr(settings, 'VAPI_ENGLISH_ASSISTANT_ID', None)
            
            if english_assistant_id:
                # Return our specific English practice assistant
                assistants = [{
                    'id': english_assistant_id,
                    'name': 'English Practice Assistant',
                    'type': 'english_practice',
                    'description': 'Specialized assistant for English conversation practice'
                }]
            else:
                # Fallback to listing all assistants from Vapi
                vapi_client = VapiClient()
                assistants = vapi_client.list_assistants()
            
            return JsonResponse({
                'success': True,
                'assistants': assistants
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        # Create new assistant
        try:
            data = json.loads(request.body)
            level = data.get('level', 'B1')
            domain = data.get('domain', 'general')
            name = data.get('name', 'English Practice Assistant')
            
            vapi_client = VapiClient()
            assistant = vapi_client.create_assistant(
                level=level,
                domain=domain,
                name=name
            )
            
            return JsonResponse({
                'success': True,
                'assistant': assistant
            })
            
        except Exception as e:
            logger.error(f"Error creating assistant: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)