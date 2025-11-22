"""
WebSocket consumers for real-time conversation practice.
Handles streaming audio and AI conversation processing.
"""

import json
import asyncio
import uuid
import base64
import time
from typing import Dict, List, Optional
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from .services.conversation_ai import ConversationAIService
from .services.speech_orchestrator import SpeechOrchestrator, SessionConfig, ConversationTurn

User = get_user_model()


class ConversationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time AI conversation practice.
    
    Handles:
    - User audio streaming (speech-to-text)
    - AI response generation
    - Text-to-speech streaming
    - Conversation state management
    - Session timing and controls
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.user = None
        self.conversation_service = None
        self.speech_orchestrator = None
        self.conversation_state = {
            'active': False,
            'messages': [],
            'start_time': None,
            'max_duration': 600,  # 10 minutes default
            'level': 'intermediate',
            'topic': 'general',
            'user_profile': {},
            'domain': 'general',
            'correction_mode': 'gentle',
            'speaking_speed_target': 1.0
        }
        self.audio_buffer = b''
        self.processing_audio = False
        self.streaming_buffer = b''
        self.last_stream_time = None
        self.vapi_enabled = False
    
    async def connect(self):
        """Accept WebSocket connection and initialize session."""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.user = self.scope.get('user')
        
        # Check authentication - temporarily disabled for testing
        # if isinstance(self.user, AnonymousUser):
        #     await self.close(code=4001)
        #     return
        
        # Join session group
        self.session_group_name = f'conversation_{self.session_id}'
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        
        # Initialize conversation service
        self.conversation_service = ConversationAIService()
        self.speech_orchestrator = SpeechOrchestrator()
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'message': 'Connected to real-time conversation'
        }))
    
    async def disconnect(self, close_code):
        """Clean up when WebSocket disconnects."""
        # Leave session group
        if hasattr(self, 'session_group_name'):
            await self.channel_layer.group_discard(
                self.session_group_name,
                self.channel_name
            )
        
        # Stop any active conversation
        if self.conversation_state['active']:
            await self._end_conversation()
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages."""
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'start_conversation':
                    await self._handle_start_conversation(data)
                elif message_type == 'end_conversation':
                    await self._handle_end_conversation()
                elif message_type == 'audio_chunk':
                    await self._handle_audio_chunk(data)
                elif message_type == 'audio_stream_chunk':
                    await self._handle_streaming_audio_chunk(data)
                elif message_type == 'text_message':
                    await self._handle_text_message(data)
                elif message_type == 'pause_conversation':
                    await self._handle_pause_conversation()
                elif message_type == 'resume_conversation':
                    await self._handle_resume_conversation()
                elif message_type == 'start_vapi_session':
                    await self._handle_start_vapi_session(data)
                elif message_type == 'vapi_transcript':
                    await self._handle_vapi_transcript(data)
                elif message_type == 'vapi_audio_complete':
                    await self._handle_vapi_audio_complete(data)
                else:
                    await self._send_error(f'Unknown message type: {message_type}')
            
            elif bytes_data:
                # Handle binary audio data
                await self._handle_binary_audio(bytes_data)
                
        except json.JSONDecodeError:
            await self._send_error('Invalid JSON format')
        except Exception as e:
            await self._send_error(f'Error processing message: {str(e)}')
    
    async def _handle_start_conversation(self, data):
        """Start a new AI conversation session."""
        print(f"🎬 Starting conversation - Current state active: {self.conversation_state['active']}")
        
        # Reset conversation state if needed
        if self.conversation_state['active']:
            print("⚠️ Conversation already active, resetting...")
            self.conversation_state['active'] = False
            self.conversation_state['messages'] = []
        
        # Extract conversation parameters
        self.conversation_state.update({
            'active': True,
            'level': data.get('level', 'intermediate'),
            'topic': data.get('topic', 'general'),
            'max_duration': data.get('max_duration', 600),
            'user_profile': data.get('user_profile', {}),
            'messages': [],
            'start_time': asyncio.get_event_loop().time()
        })
        
        try:
            print("🤖 Generating AI opening message...")
            # Generate AI opening message
            ai_response = await self._get_ai_response(
                user_message="",
                is_opening=True
            )
            print(f"✅ AI response generated: {ai_response.get('text', '')[:50]}...")
            
            # Send conversation started confirmation
            await self.send(text_data=json.dumps({
                'type': 'conversation_started',
                'ai_message': ai_response['text'],
                'audio_url': ai_response.get('audio_url'),
                'session_config': {
                    'level': self.conversation_state['level'],
                    'topic': self.conversation_state['topic'],
                    'max_duration': self.conversation_state['max_duration']
                }
            }))
            
            # Start conversation timer
            asyncio.create_task(self._conversation_timer())
            
        except Exception as e:
            await self._send_error(f'Failed to start conversation: {str(e)}')
    
    async def _handle_end_conversation(self):
        """End the current conversation and provide summary."""
        if not self.conversation_state['active']:
            await self._send_error('No active conversation to end')
            return
        
        await self._end_conversation()
    
    async def _handle_audio_chunk(self, data):
        """Process incoming audio chunks for speech-to-text."""
        if not self.conversation_state['active']:
            await self._send_error('No active conversation')
            return
        
        if self.processing_audio:
            return  # Skip if already processing
        
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(data.get('audio', ''))
            self.audio_buffer += audio_data
            
            # Check if we have enough audio for processing (e.g., 2 seconds)
            if data.get('is_final', False) and self.audio_buffer:
                self.processing_audio = True
                
                # Send processing status
                await self.send(text_data=json.dumps({
                    'type': 'processing_audio',
                    'message': 'Processing your speech...'
                }))
                
                # Convert speech to text
                transcription = await self._process_speech_to_text(self.audio_buffer)
                
                if transcription and transcription.strip():
                    # Get AI response
                    ai_response = await self._get_ai_response(transcription)
                    
                    # Send response
                    await self.send(text_data=json.dumps({
                        'type': 'conversation_message',
                        'user_message': transcription,
                        'ai_message': ai_response['text'],
                        'audio_url': ai_response.get('audio_url'),
                        'timestamp': asyncio.get_event_loop().time()
                    }))
                
                # Reset buffer
                self.audio_buffer = b''
                self.processing_audio = False
                
        except Exception as e:
            self.processing_audio = False
            await self._send_error(f'Error processing audio: {str(e)}')
    
    async def _handle_streaming_audio_chunk(self, data):
        """Handle real-time streaming audio chunks."""
        if not self.conversation_state['active']:
            return
        
        try:
            import time
            current_time = time.time()
            
            # Decode base64 audio data
            audio_data = base64.b64decode(data.get('audio', ''))
            self.streaming_buffer += audio_data
            
            # Send partial transcription every 2 seconds or when buffer gets large
            if (self.last_stream_time is None or 
                current_time - self.last_stream_time > 2.0 or 
                len(self.streaming_buffer) > 32000):
                
                if len(self.streaming_buffer) > 1000:  # Minimum audio for transcription
                    await self._process_streaming_transcription()
                    self.last_stream_time = current_time
                    
        except Exception as e:
            print(f"❌ Error processing streaming audio: {str(e)}")
    
    async def _process_streaming_transcription(self):
        """Process accumulated streaming buffer for partial transcription."""
        try:
            if len(self.streaming_buffer) == 0:
                return
                
            # Use conversation service for speech-to-text
            transcription = await self.conversation_service.transcribe_audio(self.streaming_buffer)
            
            if transcription and transcription.strip():
                # Send partial transcription to frontend
                await self.send(text_data=json.dumps({
                    'type': 'streaming_transcription',
                    'partial_text': transcription,
                    'is_final': False
                }))
                
                print(f"📝 Streaming transcription: {transcription[:50]}...")
            
            # Clear buffer after processing
            self.streaming_buffer = b''
            
        except Exception as e:
            print(f"❌ Error in streaming transcription: {str(e)}")
    
    async def _handle_binary_audio(self, audio_data):
        """Handle binary audio streaming."""
        if not self.conversation_state['active']:
            return
        
        # Add to buffer for processing
        self.audio_buffer += audio_data
        
        # Process when buffer reaches certain size or on silence detection
        if len(self.audio_buffer) > 32000:  # ~2 seconds at 16kHz
            await self._process_audio_buffer()
    
    async def _handle_text_message(self, data):
        """Handle text-based conversation messages."""
        if not self.conversation_state['active']:
            await self._send_error('No active conversation')
            return
        
        message = data.get('message', '').strip()
        if not message:
            await self._send_error('Empty message')
            return
        
        try:
            # Get AI response to text
            ai_response = await self._get_ai_response(user_message=message)
            
            # Send response
            await self.send(text_data=json.dumps({
                'type': 'conversation_message',
                'user_message': message,
                'ai_message': ai_response['text'],
                'audio_url': ai_response.get('audio_url'),
                'timestamp': asyncio.get_event_loop().time()
            }))
            
        except Exception as e:
            await self._send_error(f'Error processing message: {str(e)}')
    
    async def _handle_pause_conversation(self):
        """Pause the active conversation."""
        if self.conversation_state['active']:
            self.conversation_state['paused'] = True
            await self.send(text_data=json.dumps({
                'type': 'conversation_paused',
                'message': 'Conversation paused'
            }))
    
    async def _handle_resume_conversation(self):
        """Resume a paused conversation."""
        if self.conversation_state.get('paused'):
            self.conversation_state['paused'] = False
            await self.send(text_data=json.dumps({
                'type': 'conversation_resumed',
                'message': 'Conversation resumed'
            }))
    
    async def _get_ai_response(self, user_message: str, is_opening: bool = False) -> Dict:
        """Get AI response for user message."""
        try:
            print(f"🤖 Getting AI response - Opening: {is_opening}, Level: {self.conversation_state.get('level')}")
            
            if is_opening:
                # Generate opening message
                print(f"📝 Calling start_conversation with level: {self.conversation_state['level']}")
                response = await self.conversation_service.start_conversation(
                    level=self.conversation_state['level'],
                    topic=self.conversation_state['topic'],
                    user_profile=self.conversation_state.get('user_profile')
                )
                print(f"✅ start_conversation response: {type(response)}")
            else:
                # Continue conversation
                # Add user message to history
                self.conversation_state['messages'].append({
                    'role': 'user',
                    'content': user_message,
                    'timestamp': asyncio.get_event_loop().time()
                })
                
                response = await self.conversation_service.continue_conversation(
                    conversation_id=self.session_id,
                    user_message=user_message,
                    conversation_history=self.conversation_state['messages'],
                    level=self.conversation_state['level'],
                    topic=self.conversation_state['topic']
                )
            
            # Add AI response to history
            self.conversation_state['messages'].append({
                'role': 'assistant',
                'content': response.message,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return {
                'text': response.message,
                'audio_url': response.audio_url,
                'conversation_id': response.conversation_id
            }
            
        except Exception as e:
            print(f"❌ Error in _get_ai_response: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f'AI service error: {str(e)}')
    
    async def _process_speech_to_text(self, audio_data: bytes) -> str:
        """Convert audio to text using OpenAI Whisper."""
        try:
            # Use conversation service for speech-to-text
            transcription = await self.conversation_service.transcribe_audio(audio_data)
            return transcription
        except Exception as e:
            raise Exception(f'Speech-to-text error: {str(e)}')
    
    async def _process_audio_buffer(self):
        """Process accumulated audio buffer."""
        if self.processing_audio or not self.audio_buffer:
            return
        
        self.processing_audio = True
        
        try:
            # Send processing status
            await self.send(text_data=json.dumps({
                'type': 'processing_audio',
                'message': 'Processing speech...'
            }))
            
            # Process speech-to-text
            transcription = await self._process_speech_to_text(self.audio_buffer)
            
            if transcription and transcription.strip():
                # Get AI response
                ai_response = await self._get_ai_response(transcription)
                
                # Send response
                await self.send(text_data=json.dumps({
                    'type': 'conversation_message',
                    'user_message': transcription,
                    'ai_message': ai_response['text'],
                    'audio_url': ai_response.get('audio_url'),
                    'timestamp': asyncio.get_event_loop().time()
                }))
            
        except Exception as e:
            await self._send_error(f'Error processing audio buffer: {str(e)}')
        finally:
            self.audio_buffer = b''
            self.processing_audio = False
    
    async def _conversation_timer(self):
        """Monitor conversation duration and auto-end if needed."""
        while self.conversation_state['active']:
            elapsed = asyncio.get_event_loop().time() - self.conversation_state['start_time']
            remaining = self.conversation_state['max_duration'] - elapsed
            
            if remaining <= 0:
                # Time's up - end conversation
                await self._end_conversation(reason='time_limit')
                break
            
            # Send time updates every 30 seconds
            if int(remaining) % 30 == 0:
                await self.send(text_data=json.dumps({
                    'type': 'time_update',
                    'remaining_seconds': int(remaining)
                }))
            
            await asyncio.sleep(1)
    
    async def _end_conversation(self, reason: str = 'manual'):
        """End the conversation and generate summary."""
        if not self.conversation_state['active']:
            return
        
        self.conversation_state['active'] = False
        
        try:
            # Generate conversation summary and evaluation
            summary = await self._generate_conversation_summary()
            
            # Send conversation ended event
            await self.send(text_data=json.dumps({
                'type': 'conversation_ended',
                'reason': reason,
                'summary': summary,
                'total_duration': asyncio.get_event_loop().time() - self.conversation_state['start_time'],
                'message_count': len([msg for msg in self.conversation_state['messages'] if msg['role'] == 'user'])
            }))
            
        except Exception as e:
            await self._send_error(f'Error generating summary: {str(e)}')
    
    async def _generate_conversation_summary(self) -> Dict:
        """Generate comprehensive conversation summary and evaluation."""
        try:
            # Extract conversation messages
            conversation_text = []
            user_messages = []
            
            for msg in self.conversation_state['messages']:
                if msg['role'] == 'user':
                    user_messages.append(msg['content'])
                conversation_text.append(f"{msg['role']}: {msg['content']}")
            
            # Generate evaluation using AI service
            evaluation = await self.conversation_service.evaluate_conversation(
                conversation_history=self.conversation_state['messages'],
                level=self.conversation_state['level'],
                user_profile=self.conversation_state.get('user_profile', {})
            )
            
            return {
                'conversation_transcript': "\n".join(conversation_text),
                'evaluation': evaluation,
                'stats': {
                    'total_messages': len(user_messages),
                    'duration_minutes': (asyncio.get_event_loop().time() - self.conversation_state['start_time']) / 60,
                    'level': self.conversation_state['level'],
                    'topic': self.conversation_state['topic']
                }
            }
            
        except Exception as e:
            return {
                'error': f'Failed to generate summary: {str(e)}',
                'conversation_transcript': "Error generating transcript",
                'evaluation': {},
                'stats': {}
            }
    
    async def _send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    @database_sync_to_async
    def _get_user_profile(self):
        """Get user profile from database."""
        if self.user.is_authenticated:
            return {
                'id': self.user.id,
                'name': self.user.get_full_name() or self.user.username,
                'level': getattr(self.user, 'english_level', 'intermediate')
            }
        return {}
    
    async def _handle_start_vapi_session(self, data):
        """Start a new Vapi-powered speech practice session."""
        print(f"🎬 Starting Vapi session - Current state active: {self.conversation_state['active']}")
        
        # Reset conversation state if needed
        if self.conversation_state['active']:
            print("⚠️ Conversation already active, resetting...")
            self.conversation_state['active'] = False
            self.conversation_state['messages'] = []
        
        # Extract Vapi session parameters
        self.conversation_state.update({
            'active': True,
            'level': data.get('level', 'B1'),
            'topic': data.get('topic', 'general'),
            'domain': data.get('domain', 'general'),
            'max_duration': data.get('max_duration', 600),
            'user_profile': data.get('user_profile', {}),
            'correction_mode': data.get('correction_mode', 'gentle'),
            'speaking_speed_target': data.get('speaking_speed_target', 1.0),
            'messages': [],
            'start_time': asyncio.get_event_loop().time()
        })
        
        # Enable Vapi mode
        self.vapi_enabled = True
        
        try:
            print("🎭 Generating initial Vapi session...")
            
            # Create session config
            session_config = SessionConfig(
                session_id=self.session_id,
                student_name=data.get('student_name', 'Student'),
                student_level=self.conversation_state['level'],
                domain=self.conversation_state['domain'],
                objective=data.get('objective', 'Practice speaking naturally'),
                speaking_speed_target=self.conversation_state['speaking_speed_target'],
                correction_mode=self.conversation_state['correction_mode'],
                vapi_stream_url=data.get('vapi_stream_url'),
                language=data.get('language', 'en-US')
            )
            
            # Generate initial agent response
            session_response = await self.speech_orchestrator.orchestrate_session(
                session_config=session_config,
                conversation_history=[]
            )
            
            print(f"✅ Vapi session started: {session_response.agent_text[:50]}...")
            
            # Send session started confirmation with SSML
            await self.send(text_data=json.dumps({
                'type': 'vapi_session_started',
                'session_id': self.session_id,
                'agent_text': session_response.agent_text,
                'agent_ssml': session_response.agent_ssml,
                'expected_transcript': session_response.expected_transcript,
                'session_config': {
                    'level': self.conversation_state['level'],
                    'topic': self.conversation_state['topic'],
                    'domain': self.conversation_state['domain'],
                    'correction_mode': self.conversation_state['correction_mode'],
                    'max_duration': self.conversation_state['max_duration']
                },
                'metadata': session_response.metadata
            }))
            
            # Start conversation timer
            asyncio.create_task(self._conversation_timer())
            
        except Exception as e:
            await self._send_error(f'Failed to start Vapi session: {str(e)}')
    
    async def _handle_vapi_transcript(self, data):
        """Handle student transcript from Vapi STT."""
        if not self.conversation_state['active'] or not self.vapi_enabled:
            await self._send_error('No active Vapi session')
            return
        
        student_transcript = data.get('transcript', '').strip()
        if not student_transcript:
            await self._send_error('Empty transcript')
            return
        
        try:
            print(f"📝 Processing Vapi transcript: {student_transcript}")
            
            # Create session config
            session_config = SessionConfig(
                session_id=self.session_id,
                student_name=data.get('student_name', 'Student'),
                student_level=self.conversation_state['level'],
                domain=self.conversation_state['domain'],
                objective="Continue conversation practice",
                correction_mode=self.conversation_state['correction_mode'],
                language='en-US'
            )
            
            # Build conversation history from messages
            conversation_history = []
            for msg in self.conversation_state['messages']:
                turn = ConversationTurn(
                    who='agent' if msg['role'] == 'assistant' else 'student',
                    text=msg['content'],
                    timestamp=str(msg.get('timestamp', asyncio.get_event_loop().time()))
                )
                conversation_history.append(turn)
            
            # Process with speech orchestrator
            session_response = await self.speech_orchestrator.orchestrate_session(
                session_config=session_config,
                conversation_history=conversation_history,
                student_transcript=student_transcript
            )
            
            # Add student message to history
            self.conversation_state['messages'].append({
                'role': 'user',
                'content': student_transcript,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Add AI response to history
            self.conversation_state['messages'].append({
                'role': 'assistant',
                'content': session_response.agent_text,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Send comprehensive response
            await self.send(text_data=json.dumps({
                'type': 'vapi_response',
                'student_transcript': student_transcript,
                'agent_text': session_response.agent_text,
                'agent_ssml': session_response.agent_ssml,
                'expected_transcript': session_response.expected_transcript,
                'corrections': [
                    {
                        'original_phrase': c.original_phrase,
                        'corrected_phrase': c.corrected_phrase,
                        'error_type': c.error_type,
                        'explanation_pt': c.explanation_pt,
                        'example_correct_use': c.example_correct_use
                    } for c in (session_response.corrections or [])
                ],
                'fluency_score': session_response.fluency_score,
                'pronunciation_score': session_response.pronunciation_score,
                'suggested_drill': session_response.suggested_drill,
                'next_agent_prompt': session_response.next_agent_prompt,
                'timestamp': asyncio.get_event_loop().time()
            }))
            
        except Exception as e:
            await self._send_error(f'Error processing Vapi transcript: {str(e)}')
    
    async def _handle_vapi_audio_complete(self, data):
        """Handle completion of audio processing from Vapi."""
        if not self.conversation_state['active'] or not self.vapi_enabled:
            return
        
        try:
            # Send session feedback if this was the final turn
            session_length = len(self.conversation_state['messages'])
            
            if session_length >= 10:  # Minimum for comprehensive feedback
                # Create session config
                session_config = SessionConfig(
                    session_id=self.session_id,
                    student_name=data.get('student_name', 'Student'),
                    student_level=self.conversation_state['level'],
                    domain=self.conversation_state['domain'],
                    objective="Session completion",
                    correction_mode=self.conversation_state['correction_mode']
                )
                
                # Generate session feedback
                conversation_history = []
                for msg in self.conversation_state['messages']:
                    turn = ConversationTurn(
                        who='agent' if msg['role'] == 'assistant' else 'student',
                        text=msg['content'],
                        timestamp=str(msg.get('timestamp', asyncio.get_event_loop().time()))
                    )
                    conversation_history.append(turn)
                
                session_response = await self.speech_orchestrator.orchestrate_session(
                    session_config=session_config,
                    conversation_history=conversation_history
                )
                
                if session_response.session_feedback_pt:
                    await self.send(text_data=json.dumps({
                        'type': 'vapi_session_feedback',
                        'feedback_pt': session_response.session_feedback_pt,
                        'feedback_en': session_response.session_feedback_en,
                        'total_turns': session_length,
                        'session_duration': asyncio.get_event_loop().time() - self.conversation_state['start_time']
                    }))
            
        except Exception as e:
            print(f"❌ Error in Vapi audio complete handler: {str(e)}")