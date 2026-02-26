"""
Chatbot API Views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
import uuid
import logging

from .services import chatbot_service

logger = logging.getLogger(__name__)


class ChatbotThrottle(AnonRateThrottle):
    """Rate limiting para o chatbot - 30 mensagens por minuto"""
    rate = '30/minute'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ChatbotThrottle])
def chat(request):
    """
    Endpoint principal do chatbot

    POST /api/chatbot/chat/

    Body:
    {
        "message": "Qual o preço do plano Professional?",
        "session_id": "optional-session-id",
        "history": [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"}
        ]
    }

    Response:
    {
        "response": "O plano Professional custa 14.950 AOA/mês...",
        "session_id": "uuid",
        "cached": false
    }
    """
    try:
        message = request.data.get('message', '').strip()

        if not message:
            return Response({
                'error': 'Mensagem é obrigatória'
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(message) > 1000:
            return Response({
                'error': 'Mensagem muito longa (máximo 1000 caracteres)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Obter ou gerar session_id
        session_id = request.data.get('session_id') or str(uuid.uuid4())

        # Obter histórico da conversa
        history = request.data.get('history', [])

        # Validar histórico
        if not isinstance(history, list):
            history = []

        # Limitar histórico a 20 mensagens
        history = history[-20:] if len(history) > 20 else history

        # Processar mensagem
        result = chatbot_service.chat_sync(
            message=message,
            conversation_history=history,
            session_id=session_id
        )

        return Response({
            'response': result.get('response', ''),
            'session_id': session_id,
            'cached': result.get('cached', False)
        })

    except Exception as e:
        logger.error(f"❌ Chatbot API error: {str(e)}")
        return Response({
            'error': 'Erro interno do servidor',
            'response': 'Desculpe, ocorreu um erro. Por favor, tente novamente.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """
    Health check do chatbot

    GET /api/chatbot/health/
    """
    return Response({
        'status': 'healthy',
        'service': 'chatbot'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_actions(request):
    """
    Retorna ações rápidas disponíveis

    GET /api/chatbot/quick-actions/
    """
    actions = [
        {
            'id': 'pricing',
            'label': 'Preços',
            'message': 'Quais são os preços dos planos?',
            'icon': 'zap'
        },
        {
            'id': 'courses',
            'label': 'Cursos',
            'message': 'Que cursos especializados vocês oferecem?',
            'icon': 'book'
        },
        {
            'id': 'demo',
            'label': 'Demonstração',
            'message': 'Como posso experimentar a plataforma?',
            'icon': 'play'
        },
        {
            'id': 'support',
            'label': 'Suporte',
            'message': 'Como posso contactar o suporte?',
            'icon': 'headphones'
        }
    ]

    return Response({
        'actions': actions
    })
