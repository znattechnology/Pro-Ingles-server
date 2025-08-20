"""
WebSocket routing for notifications app.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
    path('ws/notifications/admin/', consumers.NotificationAdminConsumer.as_asgi()),
]