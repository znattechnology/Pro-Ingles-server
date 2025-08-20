"""
Django app configuration for ratings and reviews.
"""

from django.apps import AppConfig


class RatingsConfig(AppConfig):
    """Configuration for the ratings app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ratings'
    verbose_name = 'Ratings & Reviews'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.ratings.signals  # noqa