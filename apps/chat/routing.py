"""
WebSocket URL routing for chat app.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<uuid:conversation_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]