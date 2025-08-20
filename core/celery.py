"""
Celery configuration for Tuwi Beauty Platform.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('tuwi')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # Task routing
    task_routes={
        'apps.notifications.tasks.*': {'queue': 'notifications'},
        'apps.chat.tasks.*': {'queue': 'chat'},
        'apps.payments.tasks.*': {'queue': 'payments'},
        'apps.ml.tasks.*': {'queue': 'ml'},
        'apps.analytics.tasks.*': {'queue': 'analytics'},
        'apps.core.tasks.*': {'queue': 'core'},
    },
    
    # Beat schedule
    beat_schedule={
        'cleanup-expired-tokens': {
            'task': 'apps.core.tasks.cleanup_expired_tokens',
            'schedule': 3600.0,  # Every hour
        },
        'update-analytics': {
            'task': 'apps.analytics.tasks.update_daily_analytics',
            'schedule': 86400.0,  # Every 24 hours
        },
        'process-ml-predictions': {
            'task': 'apps.ml.tasks.process_batch_predictions',
            'schedule': 1800.0,  # Every 30 minutes
        },
        'cleanup-old-logs': {
            'task': 'apps.core.tasks.cleanup_old_logs',
            'schedule': 604800.0,  # Every week
        },
        'backup-database': {
            'task': 'apps.core.tasks.backup_database',
            'schedule': 86400.0,  # Daily backup
        },
        'warm-up-cache': {
            'task': 'apps.core.tasks.warm_up_cache',
            'schedule': 3600.0,  # Every hour
        },
        'process-scheduled-notifications': {
            'task': 'apps.notifications.tasks.process_scheduled_notifications',
            'schedule': 60.0,  # Every minute
        },
        'cleanup-old-notifications': {
            'task': 'apps.notifications.tasks.cleanup_old_notifications',
            'schedule': 3600.0,  # Every hour
        },
        'generate-scheduled-reports': {
            'task': 'apps.analytics.tasks.generate_scheduled_reports',
            'schedule': 3600.0,  # Every hour
        },
        'check-metric-alerts': {
            'task': 'apps.analytics.tasks.check_metric_alerts',
            'schedule': 300.0,  # Every 5 minutes
        },
    },
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
    },
    
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Error handling
    task_annotations={
        '*': {
            'rate_limit': '100/m',
            'time_limit': 30 * 60,  # 30 minutes
            'soft_time_limit': 25 * 60,  # 25 minutes
        },
        'apps.ml.tasks.train_model': {
            'rate_limit': '10/m',
            'time_limit': 2 * 60 * 60,  # 2 hours
            'soft_time_limit': 110 * 60,  # 110 minutes
        },
        'apps.core.tasks.backup_database': {
            'rate_limit': '1/h',
            'time_limit': 30 * 60,  # 30 minutes
        },
    },
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')