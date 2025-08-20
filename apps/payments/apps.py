"""
Django app configuration for payments.
"""

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Payments'

    def ready(self):
        """Import signals when app is ready."""
        import apps.payments.signals  # noqa