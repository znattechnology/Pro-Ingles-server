"""
WebSocket URL routing for practice app.
Handles real-time conversation and speaking practice.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/conversation/(?P<session_id>\w+)/$', consumers.ConversationConsumer.as_asgi()),
]