"""
Test-specific settings that override main settings for testing environment.
"""

from .settings import *

# Use in-memory cache for tests instead of Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use database session backend for tests
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Disable Celery task execution in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use simple password hasher for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use dummy storage for tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Force PostgreSQL database for CI/CD tests
import os
DATABASE_URL = os.getenv('DATABASE_URL', None)

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Use SQLite for local testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# Disable channels for tests to avoid Redis dependency
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'channels']

# Use in-memory channel layers for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Simplified REST Framework config for tests
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Test-specific security settings
DEBUG = False
SECRET_KEY = 'test-secret-key-for-ci-cd-pipeline-with-sufficient-length-and-complexity-123456789'
SECURE_HSTS_SECONDS = 0  # Disabled for tests
SECURE_SSL_REDIRECT = False  # Disabled for tests  
SESSION_COOKIE_SECURE = False  # Disabled for tests
CSRF_COOKIE_SECURE = False  # Disabled for tests

# Remove static directory that doesn't exist in CI
STATICFILES_DIRS = []

# Disable rate limiting for tests
RATELIMIT_ENABLE = False

# Ensure migrations are run in test database
MIGRATION_MODULES = {}

# Force test database to be reset and all migrations run
# This ensures subscription plans are created  
import sys
if 'test' in sys.argv or 'pytest' in sys.modules:
    # Ensure all apps run their migrations in tests
    pass