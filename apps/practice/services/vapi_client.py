"""
Vapi API Client for Speech Practice Integration
"""

import requests
import json
from typing import Dict, Optional, List
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class VapiClient:
    """Client for Vapi API integration"""
    
    def __init__(self):
        self.private_key = getattr(settings, 'VAPI_PRIVATE_KEY', None)
        self.public_key = getattr(settings, 'VAPI_PUBLIC_KEY', None)
        self.base_url = getattr(settings, 'VAPI_BASE_URL', 'https://api.vapi.ai')
        
        if not self.private_key:
            raise ValueError("VAPI_PRIVATE_KEY must be set in settings")
    
    def _headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            'Authorization': f'Bearer {self.private_key}',
            'Content-Type': 'application/json'
        }
    
    def create_assistant(self, 
                        level: str = "B1", 
                        domain: str = "general",
                        name: str = "English Practice Assistant") -> Dict:
        """Create a Vapi assistant"""
        
        # System messages by level and domain
        system_messages = {
            'general': {
                'A1': "You are a friendly English tutor. Speak very slowly and clearly. Use simple words only. Ask one question at a time. Be very encouraging and patient.",
                'A2': "You are a patient English tutor. Speak slowly. Use basic vocabulary. Keep sentences short and simple. Encourage the student often.",
                'B1': "You are an English conversation partner. Speak at normal pace. Use everyday vocabulary. Ask follow-up questions. Be supportive and helpful.",
                'B2': "You are an engaging English tutor. Use varied vocabulary. Include some common idioms. Challenge the student appropriately.",
                'C1': "You are a sophisticated English conversation partner. Use advanced vocabulary. Discuss complex topics naturally.",
                'C2': "You are an expert English conversation partner. Use natural, complex language. Engage in intellectual discussions."
            },
            'petroleum': {
                'B1': "You are an English tutor for oil & gas workers. Use technical vocabulary: rig, offshore, drilling, safety equipment, pipeline. Focus on safety communication and workplace scenarios.",
                'B2': "You are an expert in petroleum English. Discuss drilling operations, safety procedures, equipment maintenance. Use industry terminology naturally and professionally.",
                'C1': "You are a senior petroleum professional. Discuss complex operations, environmental considerations, reservoir engineering, and advanced technical concepts."
            },
            'IT': {
                'B1': "You are an IT English tutor. Use basic technical terms: software, database, network, programming, debugging. Focus on workplace communication.",
                'B2': "You are a tech professional. Discuss programming languages, system architecture, DevOps practices, software development. Use technical vocabulary appropriately.",
                'C1': "You are a senior software architect. Engage in discussions about scalability, microservices, cloud architecture, AI/ML, and emerging technologies."
            },
            'business': {
                'B1': "You are a business English tutor. Focus on meetings, presentations, client communication, negotiations. Use professional business vocabulary.",
                'B2': "You are a business professional. Discuss strategies, market analysis, leadership, project management. Include business idioms and expressions.",
                'C1': "You are a senior executive. Engage in strategic discussions about innovation, global business trends, mergers, corporate governance."
            }
        }
        
        system_message = system_messages.get(domain, system_messages['general']).get(level, system_messages['general']['B1'])
        
        assistant_config = {
            "name": f"{name} - {level} {domain.title()}",
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "maxTokens": 120 if level in ['A1', 'A2'] else 150,
                "systemMessage": system_message
            },
            "voice": {
                "provider": "openai",
                "voiceId": "alloy",
                "speed": 0.8 if level in ['A1', 'A2'] else 0.9 if level in ['B1', 'B2'] else 1.0
            },
            "transcriber": {
                "provider": "openai", 
                "model": "whisper-1",
                "language": "en"
            },
            "firstMessage": f"Hello! I'm your English practice assistant. I'm here to help you practice {domain} English at {level} level. Let's start our conversation!",
            "endCallMessage": "Thank you for practicing English with me today! Keep up the great work!",
            "recordingEnabled": True,
            "endCallPhrases": ["goodbye", "end call", "stop practice", "that's all"],
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 600,
            "backgroundSound": "office"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/assistant",
                headers=self._headers(),
                json=assistant_config
            )
            response.raise_for_status()
            
            assistant = response.json()
            logger.info(f"✅ Created Vapi assistant: {assistant.get('id')} ({level} {domain})")
            return assistant
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error creating assistant: {str(e)}")
            raise
    
    def start_call(self, assistant_id: str, customer_number: str = "+1234567890") -> Dict:
        """Start a call with an assistant"""
        call_config = {
            "assistantId": assistant_id,
            "customer": {
                "numberE164": customer_number
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/call",
                headers=self._headers(),
                json=call_config
            )
            response.raise_for_status()
            
            call = response.json()
            logger.info(f"✅ Started call: {call.get('id')}")
            return call
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error starting call: {str(e)}")
            raise
    
    def list_assistants(self) -> List[Dict]:
        """List all assistants"""
        try:
            response = requests.get(
                f"{self.base_url}/assistant",
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error listing assistants: {str(e)}")
            raise
    
    def get_call_details(self, call_id: str) -> Dict:
        """Get call details"""
        try:
            response = requests.get(
                f"{self.base_url}/call/{call_id}",
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting call: {str(e)}")
            raise