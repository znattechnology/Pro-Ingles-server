"""
Django app configuration for e-commerce.
"""

from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    """Configuration for the e-commerce app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ecommerce'
    verbose_name = 'E-commerce'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        import apps.ecommerce.signals  # noqa