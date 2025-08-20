"""
Django app configuration for analytics.
"""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'
    verbose_name = 'Analytics & Reporting'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.analytics.signals
        except ImportError:
            pass