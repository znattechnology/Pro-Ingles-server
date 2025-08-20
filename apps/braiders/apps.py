from django.apps import AppConfig


class BraidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.braiders'
    verbose_name = 'Braiders'
    
    def ready(self):
        import apps.braiders.signals