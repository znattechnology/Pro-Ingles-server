"""
Vapi Speech Practice API Views
REST endpoints for Vapi integration testing and standalone usage
"""

import json
import uuid
from functools import wraps
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.core.cache import cache
from asgiref.sync import async_to_sync
import logging

from .services.speech_orchestrator import SpeechOrchestrator, SessionConfig, ConversationTurn
from .services.vapi_client import VapiClient
from apps.subscriptions.models import UserSubscription, SubscriptionPlan

logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING DECORATOR FOR WEBHOOKS
# =============================================================================

def webhook_rate_limit(rate='200/minute'):
    """
    Simple rate limiting decorator for webhook endpoints.
    Uses Django's cache backend for IP-based throttling.

    Args:
        rate: Rate limit in format 'count/period' (e.g., '200/minute', '1000/hour')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Parse rate limit
            count, period = rate.split('/')
            max_requests = int(count)

            # Get period in seconds
            period_seconds = {
                'second': 1,
                'minute': 60,
                'hour': 3600,
                'day': 86400
            }.get(period, 60)

            # Get client IP
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip:
                ip = request.META.get('REMOTE_ADDR', 'unknown')

            # Create cache key
            cache_key = f'webhook_ratelimit:{ip}'

            # Get current request count
            current_count = cache.get(cache_key, 0)

            if current_count >= max_requests:
                logger.warning(f"Rate limit exceeded for IP {ip}: {current_count}/{max_requests}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': period_seconds
                }, status=429)

            # Increment counter
            cache.set(cache_key, current_count + 1, period_seconds)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def _authenticate_request(request):
    """
    Manually authenticate the request using JWT.
    This is needed because VapiSessionView is a Django View, not a DRF APIView.
    """
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    jwt_auth = JWTAuthentication()

    try:
        # The middleware already injected the token into HTTP_AUTHORIZATION
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header and auth_header.startswith('Bearer '):
            # Create a mock DRF request for JWT authentication
            from rest_framework.request import Request
            drf_request = Request(request)

            user_auth = jwt_auth.authenticate(drf_request)
            if user_auth:
                user, token = user_auth
                request.user = user
                logger.info(f"[JWT Auth] Successfully authenticated user: {user.id}")
                return True
    except (InvalidToken, TokenError) as e:
        logger.warning(f"[JWT Auth] Token error: {e}")
    except Exception as e:
        logger.error(f"[JWT Auth] Authentication error: {e}")

    return False


class VapiSessionView(View):
    """
    REST API for Vapi Speech Practice Sessions
    """

    def __init__(self):
        super().__init__()
        self.orchestrator = SpeechOrchestrator()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        # Manually authenticate the request
        _authenticate_request(request)
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
                return self._start_session(data, request)  # P0 FIX: Pass request for quota check
            elif action == 'process_transcript':
                return self._process_transcript(data, request)
            else:
                return JsonResponse({
                    'error': 'Invalid action. Use "start_session" or "process_transcript"'
                }, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in VapiSessionView: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    def _start_session(self, data: Dict[str, Any], request=None) -> JsonResponse:
        """Start a new Vapi session"""
        try:
            # P0 FIX: Verify quota BEFORE starting session
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user
                if hasattr(user, 'subscription'):
                    subscription = user.subscription
                    subscription.reset_daily_usage_if_needed()

                    # Check if user can use speaking (at least 1 minute)
                    if not subscription.can_use_speaking(1):
                        effective_limit = subscription.get_effective_speaking_limit()
                        is_trial = subscription.is_in_trial_period()

                        error_message = 'Limite diário de conversação atingido.'
                        if subscription.plan.plan_type == 'FREE' and not is_trial:
                            error_message = 'Seu período de teste expirou. Assine um plano para continuar praticando!'

                        return JsonResponse({
                            'success': False,
                            'error': error_message,
                            'error_code': 'QUOTA_EXCEEDED' if is_trial or subscription.plan.plan_type != 'FREE' else 'TRIAL_EXPIRED',
                            'can_start': False,
                            'quota': {
                                'daily_limit': effective_limit,
                                'daily_used': subscription.daily_speaking_minutes_used,
                                'daily_remaining': max(0, effective_limit - subscription.daily_speaking_minutes_used) if effective_limit else 0,
                            }
                        }, status=403)

                    logger.info(f"[VAPI] User {user.id} starting session. "
                               f"Quota: {subscription.daily_speaking_minutes_used}/{subscription.get_effective_speaking_limit()} min")

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

    def _process_transcript(self, data: Dict[str, Any], request=None) -> JsonResponse:
        """Process student transcript and generate response"""
        try:
            config_data = data.get('session_config', {})
            student_transcript = data.get('student_transcript', '')
            history_data = data.get('conversation_history', [])

            # If no direct transcript, extract from conversation history (batch analysis)
            if not student_transcript.strip() and history_data:
                # Extract all student messages from conversation history
                student_messages = [
                    item.get('text', '') for item in history_data
                    if item.get('who') == 'student' and item.get('text', '').strip()
                ]
                if student_messages:
                    # Use the last student message as the current transcript
                    student_transcript = student_messages[-1]

            if not student_transcript.strip():
                return JsonResponse({'error': 'Empty student transcript'}, status=400)

            session_id = config_data.get('session_id', str(uuid.uuid4()))
            student_level = config_data.get('student_level', 'B1')
            domain = config_data.get('domain', 'general')

            session_config = SessionConfig(
                session_id=session_id,
                student_name=config_data.get('student_name', 'Student'),
                student_level=student_level,
                domain=domain,
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

            # Calculate session metrics from conversation
            student_texts = [
                item.get('text', '') for item in history_data
                if item.get('who') == 'student'
            ]
            total_words = sum(len(text.split()) for text in student_texts)

            # Use real elapsed time from frontend if available, otherwise estimate
            elapsed_seconds = config_data.get('elapsed_seconds', 0)

            # P0 FIX: Validate elapsed_seconds to prevent abuse
            # Max 2 hours (7200 seconds) per session, minimum 1 minute if provided
            try:
                elapsed_seconds = int(elapsed_seconds) if elapsed_seconds else 0
                if elapsed_seconds < 0:
                    elapsed_seconds = 0
                elif elapsed_seconds > 7200:  # Max 2 hours
                    logger.warning(f"[SECURITY] elapsed_seconds={elapsed_seconds} exceeds max (7200). Capping.")
                    elapsed_seconds = 7200
            except (TypeError, ValueError):
                elapsed_seconds = 0

            if elapsed_seconds and elapsed_seconds >= 60:  # At least 1 minute
                duration_minutes = round(elapsed_seconds / 60, 1)
                # P0 FIX: Cap duration to subscription limit if authenticated
                if request and hasattr(request, 'user') and request.user.is_authenticated:
                    if hasattr(request.user, 'subscription'):
                        max_session = 60  # Default max 60 min
                        sub = request.user.subscription
                        effective_limit = sub.get_effective_speaking_limit()
                        if effective_limit and effective_limit > 0:
                            remaining = effective_limit - sub.daily_speaking_minutes_used
                            max_session = min(60, max(1, remaining))
                        if duration_minutes > max_session:
                            logger.warning(f"[SECURITY] duration_minutes={duration_minutes} exceeds remaining quota {max_session}. Capping.")
                            duration_minutes = max_session
                logger.info(f"Using real elapsed time: {elapsed_seconds}s = {duration_minutes} min")
            else:
                duration_minutes = max(1, len(history_data) // 2)  # Estimate based on turns
                logger.info(f"Using estimated time: {duration_minutes} min (based on {len(history_data)} turns)")

            words_per_minute = total_words / duration_minutes if duration_minutes > 0 else 0

            # Build session results for saving
            session_results = {
                'scores': {
                    'fluency': getattr(session_response, 'fluency_score', 75) or 75,
                    'pronunciation': getattr(session_response, 'pronunciation_score', 75) or 75,
                    'grammar': 75,  # Default if not available
                    'vocabulary': 80,  # Default if not available
                    'overall': (
                        (getattr(session_response, 'fluency_score', 75) or 75) +
                        (getattr(session_response, 'pronunciation_score', 75) or 75) +
                        75 + 80
                    ) // 4
                },
                'speaking_metrics': {
                    'total_words': total_words,
                    'words_per_minute': round(words_per_minute, 1),
                },
                'duration_minutes': duration_minutes,
                'elapsed_seconds': elapsed_seconds,  # Tempo real do frontend
                'corrections': [
                    {
                        'original_phrase': c.original_phrase,
                        'corrected_phrase': c.corrected_phrase,
                        'error_type': c.error_type,
                        'explanation_pt': c.explanation_pt
                    } for c in (getattr(session_response, 'corrections', None) or [])
                ],
                'conversation_history': history_data,
            }

            # Save session data if user is authenticated
            logger.info(f"Checking authentication - request exists: {request is not None}")
            if request:
                logger.info(f"Has user attr: {hasattr(request, 'user')}")
                if hasattr(request, 'user'):
                    logger.info(f"User authenticated: {request.user.is_authenticated}")
                    logger.info(f"User: {request.user}")

            if request and hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    logger.info(f"Saving session {session_id} for user {request.user.id}")
                    saved_session = save_vapi_session_data(
                        session_id=session_id,
                        user=request.user,
                        session_config={
                            'level': student_level,
                            'domain': domain,
                        },
                        session_results=session_results
                    )
                    if saved_session:
                        logger.info(f"Session {session_id} SAVED successfully for user {request.user.id}")
                    else:
                        logger.warning(f"Session {session_id} NOT saved - save_vapi_session_data returned None")
                except Exception as save_error:
                    logger.error(f"Error saving session data: {save_error}", exc_info=True)
                    # Continue even if save fails - don't break the response
            else:
                logger.warning(f"User not authenticated - session {session_id} will not be saved")

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


def _validate_webhook_request(request) -> tuple[bool, str]:
    """
    Validate incoming webhook request.
    """
    from django.conf import settings

    webhook_secret = getattr(settings, 'VAPI_WEBHOOK_SECRET', None)

    if webhook_secret:
        request_secret = request.headers.get('X-Vapi-Secret') or request.headers.get('X-Webhook-Secret')
        if request_secret != webhook_secret:
            logger.warning("SECURITY - Invalid webhook secret received")
            return False, "Invalid webhook secret"

    user_agent = request.headers.get('User-Agent', '')
    if 'vapi' not in user_agent.lower() and webhook_secret is None:
        logger.info("Webhook request without Vapi User-Agent")

    return True, ""


@csrf_exempt
@require_http_methods(["POST"])
@webhook_rate_limit(rate='200/minute')
def vapi_webhook(request):
    """
    Webhook endpoint for Vapi events.
    Rate limited to 200 requests per minute per IP.
    """
    is_valid, error_message = _validate_webhook_request(request)
    if not is_valid:
        return JsonResponse({'error': error_message}, status=403)

    try:
        data = json.loads(request.body)
        message_type = data.get('message', {}).get('type')

        logger.info(f"Received Vapi webhook: {message_type}")

        if message_type == 'transcript':
            return _handle_transcript_webhook(data)
        elif message_type == 'hang':
            return _handle_call_end_webhook(data)
        elif message_type == 'speech-update':
            return _handle_speech_update_webhook(data)
        elif message_type == 'function-call':
            return _handle_function_call_webhook(data)
        else:
            logger.info(f"Unhandled webhook type: {message_type}")
            return JsonResponse({'status': 'received'})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_transcript_webhook(data: Dict) -> JsonResponse:
    """Handle transcript updates from Vapi"""
    try:
        message = data.get('message', {})
        transcript = message.get('transcript', '')
        role = message.get('role', 'user')

        if role == 'user' and transcript.strip():
            logger.info(f"User transcript: {transcript}")
            return JsonResponse({
                'status': 'transcript_processed',
                'transcript': transcript
            })

        return JsonResponse({'status': 'received'})

    except Exception as e:
        logger.error(f"Transcript webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_call_end_webhook(data: Dict) -> JsonResponse:
    """Handle call end events"""
    try:
        call_info = data.get('call', {})
        call_id = call_info.get('id')

        logger.info(f"Call ended: {call_id}")

        return JsonResponse({
            'status': 'call_ended',
            'call_id': call_id
        })

    except Exception as e:
        logger.error(f"Call end webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_speech_update_webhook(data: Dict) -> JsonResponse:
    """Handle speech status updates"""
    try:
        message = data.get('message', {})
        status = message.get('status')

        logger.info(f"Speech update: {status}")

        return JsonResponse({'status': 'speech_update_received'})

    except Exception as e:
        logger.error(f"Speech update webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_function_call_webhook(data: Dict) -> JsonResponse:
    """Handle function calls from Vapi assistant"""
    try:
        message = data.get('message', {})
        function_call = message.get('functionCall', {})
        function_name = function_call.get('name')

        logger.info(f"Function call: {function_name}")

        return JsonResponse({
            'status': 'function_call_handled',
            'function': function_name
        })

    except Exception as e:
        logger.error(f"Function call webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def vapi_session_summary(request, session_id):
    """
    Get comprehensive summary for a Vapi session
    """
    try:
        real_session_data = _get_real_session_data(session_id)

        if real_session_data:
            logger.info(f"Serving REAL data for session {session_id}")
            return JsonResponse({
                'success': True,
                'session': real_session_data,
                'data_source': 'database'
            })

        logger.info(f"Serving MOCK data for session {session_id}")
        mock_data = _get_mock_session_data(session_id)

        return JsonResponse({
            'success': True,
            'session': mock_data,
            'data_source': 'mock'
        })

    except Exception as e:
        logger.error(f"Error generating session summary for {session_id}: {str(e)}")
        return JsonResponse({'error': f'Failed to generate session summary: {str(e)}'}, status=500)


def _get_real_session_data(session_id):
    """Retrieve real session data from database"""
    try:
        from .models import VapiSession

        session = VapiSession.objects.get(session_id=session_id)

        display_name = f"{session.user.first_name} {session.user.last_name}".strip()
        if not display_name:
            display_name = session.user.email or session.user.username

        real_data = {
            "session_id": session.session_id,
            "student_name": display_name,
            "level": session.level,
            "domain": session.domain,
            "duration_seconds": session.duration_minutes * 60,
            "date_time": session.created_at.isoformat(),
            "scores": {
                "fluency": session.fluency_score,
                "pronunciation": session.pronunciation_score,
                "grammar": session.grammar_score,
                "vocabulary": session.vocabulary_score,
                "overall": session.overall_score
            },
            "speaking_metrics": {
                "total_words": session.total_words,
                "words_per_minute": session.words_per_minute,
                "speaking_time_percentage": round((session.total_words / (session.words_per_minute * session.duration_minutes)) * 100) if session.words_per_minute > 0 else 45,
                "pause_analysis": f"Session completed in {session.duration_minutes} minutes with {session.total_words} words spoken"
            },
            "conversation_analysis": {
                "response_appropriateness": min(session.overall_score + 5, 100),
                "topic_maintenance": min(session.overall_score - 2, 100),
                "initiative_taking": min(session.overall_score - 8, 100),
                "cultural_awareness": min(session.overall_score + 1, 100)
            },
            "corrections": session.full_session_data.get('corrections', []),
            "key_phrases": session.full_session_data.get('key_phrases', []),
            "timeline": session.full_session_data.get('timeline', []),
            "suggested_drills": session.full_session_data.get('suggested_drills', []),
            "recommendations": session.full_session_data.get('recommendations', [
                f"Continue practicing with {session.level} level exercises",
                f"Focus on {session.domain} vocabulary",
                f"Great improvement of {session.improvement_from_last:.1f} points!" if session.improvement_from_last > 0 else "Keep practicing to improve your scores"
            ]),
            "next_level_ready": session.overall_score >= 85,
            "audio_refs": session.full_session_data.get('audio_refs', [])
        }

        return real_data

    except Exception:
        return None


def _get_mock_session_data(session_id):
    """Generate mock session data (fallback)"""
    return {
        "session_id": session_id,
        "student_name": "João Silva",
        "level": "B1",
        "domain": "general",
        "duration_seconds": 420,
        "date_time": "2025-01-25T10:30:00Z",
        "scores": {
            "fluency": 78,
            "pronunciation": 82,
            "grammar": 75,
            "vocabulary": 80,
            "overall": 79
        },
        "corrections": [
            {
                "original_phrase": "I have been study English",
                "corrected_phrase": "I have been studying English",
                "error_type": "Grammar",
                "short_explanation_pt": "Use o gerúndio (-ing) após 'have been'",
                "example_correct_use": "I have been studying for two hours",
                "timestamp": "02:15",
                "audio_ref": "correction_1_audio"
            }
        ],
        "key_phrases": [
            {
                "text": "I'm passionate about learning",
                "context": "Expressing enthusiasm for education",
                "difficulty": "medium",
                "audio_ref": "phrase_1_audio"
            }
        ],
        "suggested_drills": [
            {
                "title": "Present Perfect Continuous",
                "description": "Practice using 'have been + -ing' structures",
                "repetitions": 5,
                "example_text": "I have been working here for three years",
                "audio_ref": "drill_1_audio"
            }
        ],
        "timeline": [
            {
                "timestamp": "00:30",
                "type": "milestone",
                "description": "Conversation started",
                "content": "Hello! Nice to meet you."
            }
        ],
        "conversation_analysis": {
            "response_appropriateness": 85,
            "topic_maintenance": 78,
            "initiative_taking": 72,
            "cultural_awareness": 80
        },
        "speaking_metrics": {
            "total_words": 342,
            "words_per_minute": 49,
            "speaking_time_percentage": 45,
            "pause_analysis": "Natural pauses, good rhythm"
        },
        "recommendations": [
            "Continue practicing Present Perfect Continuous tense",
            "Focus on word order rules",
            "Excellent vocabulary usage"
        ],
        "next_level_ready": False,
        "audio_refs": ["session_intro_audio", "correction_1_audio"]
    }


@transaction.atomic
def save_vapi_session_data(session_id, user, session_config, session_results):
    """Save real session data to database. Uses atomic transaction for consistency."""
    try:
        from .models import VapiSession, DailyProgressSummary
        from django.utils import timezone

        # Usar duração real enviada pelo frontend, ou estimar
        duration_minutes = session_results.get('duration_minutes', 7)
        if session_results.get('elapsed_seconds'):
            duration_minutes = round(session_results.get('elapsed_seconds') / 60, 1)

        session, created = VapiSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': user,
                'level': session_config.get('level', 'B1'),
                'domain': session_config.get('domain', 'general'),
                'duration_minutes': duration_minutes,
                'fluency_score': session_results.get('scores', {}).get('fluency', 75),
                'pronunciation_score': session_results.get('scores', {}).get('pronunciation', 75),
                'grammar_score': session_results.get('scores', {}).get('grammar', 75),
                'vocabulary_score': session_results.get('scores', {}).get('vocabulary', 75),
                'overall_score': session_results.get('scores', {}).get('overall', 75),
                'total_words': session_results.get('speaking_metrics', {}).get('total_words', 300),
                'words_per_minute': session_results.get('speaking_metrics', {}).get('words_per_minute', 45),
                'corrections_count': len(session_results.get('corrections', [])),
                'full_session_data': session_results
            }
        )

        if not created:
            for field, value in {
                'duration_minutes': duration_minutes,
                'fluency_score': session_results.get('scores', {}).get('fluency', session.fluency_score),
                'pronunciation_score': session_results.get('scores', {}).get('pronunciation', session.pronunciation_score),
                'grammar_score': session_results.get('scores', {}).get('grammar', session.grammar_score),
                'vocabulary_score': session_results.get('scores', {}).get('vocabulary', session.vocabulary_score),
                'overall_score': session_results.get('scores', {}).get('overall', session.overall_score),
                'total_words': session_results.get('speaking_metrics', {}).get('total_words', session.total_words),
                'corrections_count': len(session_results.get('corrections', [])),
                'full_session_data': session_results
            }.items():
                setattr(session, field, value)
            session.save()

        # P0 FIX: Registrar uso na subscrição do usuário de forma ATÔMICA
        try:
            if hasattr(user, 'subscription'):
                from django.db.models import F

                subscription = user.subscription
                subscription.reset_daily_usage_if_needed()

                # P0 FIX: Usar update atômico com F() para evitar race conditions
                # Isso garante que atualizações concorrentes não sejam perdidas
                from apps.subscriptions.models import UserSubscription
                UserSubscription.objects.filter(pk=subscription.pk).update(
                    daily_speaking_minutes_used=F('daily_speaking_minutes_used') + int(duration_minutes)
                )

                # Refresh para obter valor atualizado
                subscription.refresh_from_db()
                effective_limit = subscription.get_effective_speaking_limit()
                remaining = (effective_limit or 999) - subscription.daily_speaking_minutes_used
                logger.info(f"[ATOMIC] Recorded {duration_minutes} min for user {user.id}. "
                           f"Used: {subscription.daily_speaking_minutes_used}, Remaining: {remaining}")
        except Exception as quota_error:
            logger.warning(f"Could not update subscription usage for user {user.id}: {quota_error}")

        today = timezone.now().date()
        DailyProgressSummary.update_for_user_date(user, today)

        logger.info(f"Saved real session data for {session_id} (duration: {duration_minutes} min)")
        return session

    except Exception as e:
        logger.error(f"Error saving session data for {session_id}: {str(e)}")
        return None


@csrf_exempt
@require_http_methods(["GET"])
def vapi_user_progress(request):
    """Get comprehensive user progress analytics"""
    try:
        from .models import VapiSession, DailyProgressSummary
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg, Sum, Count, Max

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'detail': 'Please log in to view your progress'
            }, status=401)

        user = request.user

        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        recent_sessions = VapiSession.objects.filter(
            user=user,
            date__gte=week_ago
        ).order_by('-created_at')[:10]

        weekly_stats = VapiSession.objects.filter(
            user=user,
            date__gte=week_ago
        ).aggregate(
            total_sessions=Count('session_id'),
            avg_score=Avg('overall_score'),
            total_minutes=Sum('duration_minutes'),
            total_words=Sum('total_words'),
            best_score=Max('overall_score')
        )

        monthly_stats = VapiSession.objects.filter(
            user=user,
            date__gte=month_ago
        ).aggregate(
            total_sessions=Count('session_id'),
            avg_score=Avg('overall_score'),
            total_minutes=Sum('duration_minutes'),
            best_score=Max('overall_score')
        )

        daily_stats_qs = VapiSession.objects.filter(
            user=user,
            date__gte=week_ago
        ).values('date').annotate(
            sessions=Count('session_id'),
            avg_score=Avg('overall_score'),
            total_minutes=Sum('duration_minutes')
        )

        daily_stats_dict = {item['date']: item for item in daily_stats_qs}

        daily_progress = []
        for i in range(7):
            check_date = today - timedelta(days=i)
            if check_date in daily_stats_dict:
                stats = daily_stats_dict[check_date]
                daily_progress.append({
                    'date': check_date.isoformat(),
                    'sessions': stats['sessions'],
                    'avg_score': round(stats['avg_score'] or 0, 1),
                    'total_minutes': stats['total_minutes'] or 0
                })
            else:
                daily_progress.append({
                    'date': check_date.isoformat(),
                    'sessions': 0,
                    'avg_score': 0,
                    'total_minutes': 0
                })

        session_dates = set(
            VapiSession.objects.filter(
                user=user,
                date__gte=today - timedelta(days=365)
            ).values_list('date', flat=True).distinct()
        )

        current_streak = 0
        check_date = today
        while check_date in session_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        progress_data = {
            'user': {
                'username': user.username,
                'current_streak': current_streak
            },
            'today': {
                'sessions': VapiSession.objects.filter(user=user, date=today).count(),
                'avg_score': round(VapiSession.objects.filter(user=user, date=today).aggregate(avg=Avg('overall_score'))['avg'] or 0, 1)
            },
            'weekly': {
                'total_sessions': weekly_stats['total_sessions'] or 0,
                'avg_score': round(weekly_stats['avg_score'] or 0, 1),
                'total_minutes': weekly_stats['total_minutes'] or 0,
                'total_words': weekly_stats['total_words'] or 0,
                'best_score': weekly_stats['best_score'] or 0
            },
            'monthly': {
                'total_sessions': monthly_stats['total_sessions'] or 0,
                'avg_score': round(monthly_stats['avg_score'] or 0, 1),
                'total_minutes': monthly_stats['total_minutes'] or 0,
                'best_score': monthly_stats['best_score'] or 0
            },
            'daily_chart': list(reversed(daily_progress)),
            'recent_sessions': [
                {
                    'session_id': s.session_id,
                    'date': s.date.isoformat(),
                    'overall_score': s.overall_score,
                    'duration_minutes': s.duration_minutes,
                    'improvement': s.improvement_from_last
                }
                for s in recent_sessions
            ]
        }

        return JsonResponse({
            'success': True,
            'progress': progress_data
        })

    except Exception as e:
        logger.error(f"Error fetching user progress: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def vapi_complete_session(request):
    """Mark a session as completed and save progress data"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        session_config = data.get('session_config', {})
        session_results = data.get('session_results', {})

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'detail': 'Please log in to save your session progress'
            }, status=401)

        user = request.user

        saved_session = save_vapi_session_data(session_id, user, session_config, session_results)

        if saved_session:
            return JsonResponse({
                'success': True,
                'message': 'Session completed and saved',
                'session_id': session_id,
                'overall_score': saved_session.overall_score,
                'improvement': saved_session.improvement_from_last,
                'streak': saved_session.streak_days
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Session completed (data not saved)',
                'session_id': session_id
            })

    except Exception as e:
        logger.error(f"Error completing session: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def vapi_dashboard_analytics(request):
    """Comprehensive speaking progress dashboard"""
    try:
        from .models import VapiSession, DailyProgressSummary
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg, Sum, Count, Max, Min
        from collections import defaultdict

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'detail': 'Please log in to view your dashboard'
            }, status=401)

        user = request.user

        now = timezone.now()
        today = now.date()
        thirty_days_ago = today - timedelta(days=30)

        all_sessions = VapiSession.objects.filter(user=user).order_by('-created_at')
        recent_sessions = all_sessions.filter(date__gte=thirty_days_ago)

        total_stats = all_sessions.aggregate(
            total_sessions=Count('session_id'),
            total_minutes=Sum('duration_minutes'),
            total_words=Sum('total_words'),
            avg_score=Avg('overall_score'),
            best_score=Max('overall_score'),
            first_session=Min('created_at')
        )

        recent_stats = recent_sessions.aggregate(
            sessions_count=Count('session_id'),
            avg_score=Avg('overall_score'),
            avg_fluency=Avg('fluency_score'),
            avg_pronunciation=Avg('pronunciation_score'),
            avg_grammar=Avg('grammar_score'),
            avg_vocabulary=Avg('vocabulary_score'),
            total_minutes=Sum('duration_minutes'),
            total_corrections=Sum('corrections_count')
        )

        session_dates = set(
            all_sessions.filter(
                date__gte=today - timedelta(days=365)
            ).values_list('date', flat=True).distinct()
        )

        current_streak = 0
        check_date = today
        while check_date in session_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        if current_streak == 0 and (today - timedelta(days=1)) in session_dates:
            check_date = today - timedelta(days=1)
            while check_date in session_dates:
                current_streak += 1
                check_date -= timedelta(days=1)

        longest_streak = 0
        if session_dates:
            sorted_dates = sorted(session_dates, reverse=True)
            temp_streak = 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
                    temp_streak += 1
                else:
                    longest_streak = max(longest_streak, temp_streak)
                    temp_streak = 1
            longest_streak = max(longest_streak, temp_streak)

        current_level = 'A1'
        level_progression = []
        if all_sessions.exists():
            sessions_by_level = defaultdict(int)
            for session in all_sessions:
                sessions_by_level[session.level] += 1

            current_level = all_sessions.first().level
            level_progression = [{'level': k, 'sessions': v} for k, v in sessions_by_level.items()]

        dashboard_data = {
            'user_info': {
                'name': f"{user.first_name} {user.last_name}".strip() or user.email,
                'email': user.email,
                'current_level': current_level,
                'member_since': total_stats['first_session'].date().isoformat() if total_stats['first_session'] else today.isoformat()
            },
            'overall_stats': {
                'total_sessions': total_stats['total_sessions'] or 0,
                'total_hours': round((total_stats['total_minutes'] or 0) / 60, 1),
                'total_words_spoken': total_stats['total_words'] or 0,
                'overall_average_score': round(total_stats['avg_score'] or 0, 1),
                'personal_best_score': total_stats['best_score'] or 0,
                'current_streak_days': current_streak,
                'longest_streak_days': longest_streak
            },
            'recent_performance': {
                'last_30_days_sessions': recent_stats['sessions_count'] or 0,
                'recent_average_score': round(recent_stats['avg_score'] or 0, 1),
                'recent_fluency': round(recent_stats['avg_fluency'] or 0, 1),
                'recent_pronunciation': round(recent_stats['avg_pronunciation'] or 0, 1),
                'recent_grammar': round(recent_stats['avg_grammar'] or 0, 1),
                'recent_vocabulary': round(recent_stats['avg_vocabulary'] or 0, 1),
                'recent_practice_hours': round((recent_stats['total_minutes'] or 0) / 60, 1),
                'recent_corrections_total': recent_stats['total_corrections'] or 0
            },
            'level_progression': level_progression
        }

        return JsonResponse({
            'success': True,
            'dashboard': dashboard_data
        })

    except Exception as e:
        logger.error(f"Error generating dashboard analytics: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def vapi_assistant_manager(request):
    """Create and manage Vapi assistants"""
    if request.method == 'GET':
        try:
            from django.conf import settings
            english_assistant_id = getattr(settings, 'VAPI_ENGLISH_ASSISTANT_ID', None)

            if english_assistant_id:
                assistants = [{
                    'id': english_assistant_id,
                    'name': 'English Practice Assistant',
                    'type': 'english_practice',
                    'description': 'Specialized assistant for English conversation practice'
                }]
            else:
                vapi_client = VapiClient()
                assistants = vapi_client.list_assistants()

            return JsonResponse({
                'success': True,
                'assistants': assistants
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'POST':
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


# =============================================================================
# CONVERSATION QUOTA MANAGEMENT ENDPOINTS (Using existing Subscription system)
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def vapi_check_quota(request):
    """
    Verifica se o usuário pode iniciar uma sessão de conversação.
    Usa o sistema de subscrição existente (apps/subscriptions).
    """
    try:
        _authenticate_request(request)

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'can_start': False,
                'error': 'Autenticação necessária',
                'error_code': 'AUTH_REQUIRED'
            }, status=401)

        user = request.user

        # Usar sistema de subscrição existente
        if not hasattr(user, 'subscription'):
            # Criar subscrição gratuita se não existir
            free_plan = SubscriptionPlan.objects.filter(plan_type='FREE').first()
            if free_plan:
                from django.utils import timezone
                UserSubscription.objects.create(
                    user=user,
                    plan=free_plan,
                    expires_at=timezone.now() + timezone.timedelta(days=365*10)
                )
            return JsonResponse({
                'success': True,
                'can_start': True,
                'message': 'OK',
                'quota': _get_default_quota_response()
            })

        subscription = user.subscription
        subscription.reset_daily_usage_if_needed()

        plan = subscription.plan
        can_start = subscription.can_use_speaking(1)

        # Verificar trial
        is_trial = subscription.is_in_trial_period()
        trial_days_remaining = subscription.get_trial_remaining_days() if is_trial else 0

        # Obter limite efetivo (considera trial)
        effective_limit = subscription.get_effective_speaking_limit()
        daily_used = subscription.daily_speaking_minutes_used

        # Se limite é None (ilimitado), usar valor alto para display
        if effective_limit is None:
            daily_limit = 999
            daily_remaining = 999
        else:
            daily_limit = effective_limit
            daily_remaining = max(0, daily_limit - daily_used)

        # Mensagens contextuais
        if can_start:
            if is_trial:
                message = f'Trial ativo ({trial_days_remaining} dias restantes)'
            else:
                message = 'OK'
        else:
            if plan.plan_type == 'FREE' and not is_trial:
                message = 'Seu período de teste expirou. Assine um plano para continuar praticando!'
            else:
                message = f'Limite diário de {daily_limit} minutos atingido'

        response_data = {
            'success': True,
            'can_start': can_start,
            'message': message,
            'quota': {
                'plan_name': plan.name,
                'plan_type': plan.plan_type,
                # Limites efetivos (considerando trial)
                'daily_limit': daily_limit,
                'max_session_minutes': min(daily_remaining, 30) if daily_remaining < 999 else 30,
                # Uso atual
                'daily_minutes_used': daily_used,
                'daily_minutes_remaining': daily_remaining,
                # Recursos do plano
                'ai_tutor': plan.ai_tutor,
                'advanced_analytics': plan.advanced_analytics,
            },
            'trial': {
                'is_active': is_trial,
                'days_remaining': trial_days_remaining,
                'total_days': plan.trial_days,
                'speaking_minutes_per_day': plan.trial_speaking_minutes,
            }
        }

        if not can_start:
            if plan.plan_type == 'FREE' and not is_trial:
                response_data['error_code'] = 'TRIAL_EXPIRED'
            else:
                response_data['error_code'] = 'QUOTA_EXCEEDED'

        return JsonResponse(response_data)

    except Exception as e:
        # P0 FIX: Fail-CLOSED for security - don't allow access on errors
        logger.error(f"[SECURITY] Error checking quota: {str(e)} - blocking access")
        return JsonResponse({
            'success': False,
            'can_start': False,  # P0 FIX: Fail-CLOSED, not fail-open
            'error': 'Erro ao verificar quota. Tente novamente.',
            'error_code': 'QUOTA_CHECK_ERROR'
        }, status=500)


def _get_default_quota_response():
    """Retorna resposta padrão de quota para usuários sem subscrição (trial ativo)"""
    return {
        'plan_name': 'Gratuito (Trial)',
        'plan_type': 'FREE',
        'daily_limit': 10,  # Minutos de trial
        'max_session_minutes': 10,
        'daily_minutes_used': 0,
        'daily_minutes_remaining': 10,
        'ai_tutor': False,
        'advanced_analytics': False,
    }


@csrf_exempt
@require_http_methods(["GET"])
def vapi_quota_status(request):
    """
    Retorna o status detalhado da quota do usuário.
    Usa o sistema de subscrição existente (apps/subscriptions).
    """
    try:
        _authenticate_request(request)

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)

        user = request.user

        if not hasattr(user, 'subscription'):
            return JsonResponse({
                'success': True,
                'user': {'email': user.email, 'name': user.name or user.email},
                'plan': {'name': 'Gratuito', 'type': 'FREE'},
                'usage': {'daily': {'minutes_used': 0, 'minutes_limit': 15, 'percent_used': 0}},
                'status': {'can_start_session': True}
            })

        subscription = user.subscription
        subscription.reset_daily_usage_if_needed()
        plan = subscription.plan

        daily_limit = plan.daily_speaking_minutes or 999
        daily_used = subscription.daily_speaking_minutes_used
        daily_remaining = max(0, daily_limit - daily_used)
        daily_percent = (daily_used / daily_limit * 100) if daily_limit > 0 else 0

        return JsonResponse({
            'success': True,
            'user': {
                'email': user.email,
                'name': user.name or user.email
            },
            'plan': {
                'name': plan.name,
                'type': plan.plan_type,
                'description': plan.description,
                'price_monthly': float(plan.monthly_price),
                'features': {
                    'ai_tutor': plan.ai_tutor,
                    'advanced_analytics': plan.advanced_analytics,
                    'certificates': plan.certificates,
                    'offline_downloads': plan.offline_downloads,
                }
            },
            'usage': {
                'daily': {
                    'minutes_used': daily_used,
                    'minutes_limit': daily_limit,
                    'minutes_remaining': daily_remaining,
                    'percent_used': round(min(daily_percent, 100), 1),
                },
            },
            'limits': {
                'max_session_minutes': 30,
            },
            'status': {
                'can_start_session': subscription.can_use_speaking(1),
                'subscription_active': subscription.is_active(),
                'days_until_expiry': subscription.days_until_expiry(),
            }
        })

    except Exception as e:
        logger.error(f"Error getting quota status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def vapi_available_plans(request):
    """
    Lista todos os planos de subscrição disponíveis.
    Usa o sistema de subscrição existente (apps/subscriptions).
    """
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price')

        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': str(plan.id),
                'name': plan.name,
                'type': plan.plan_type,
                'description': plan.description,
                'price_monthly': float(plan.monthly_price),
                'price_yearly': float(plan.yearly_price) if plan.yearly_price else None,
                'limits': {
                    'daily_speaking_minutes': plan.daily_speaking_minutes,
                    'daily_listening_minutes': plan.daily_listening_minutes,
                    'daily_lessons_limit': plan.daily_lessons_limit,
                    'daily_ai_analyses_limit': plan.daily_ai_analyses_limit,
                },
                'features': {
                    'ai_tutor': plan.ai_tutor,
                    'certificates': plan.certificates,
                    'offline_downloads': plan.offline_downloads,
                    'advanced_analytics': plan.advanced_analytics,
                    'priority_support': plan.priority_support,
                    'native_teacher_sessions': plan.native_teacher_sessions,
                },
            })

        return JsonResponse({
            'success': True,
            'plans': plans_data
        })

    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
