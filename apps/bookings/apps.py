"""
Django app configuration for bookings.
"""

from django.apps import AppConfig


class BookingsConfig(AppConfig):
    """Configuration for the bookings app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bookings'
    verbose_name = 'Booking Management'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.bookings.signals  # noqa