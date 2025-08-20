"""
Django app configuration for chat.
"""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Configuration for the chat app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Real-time Chat'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.chat.signals  # noqa