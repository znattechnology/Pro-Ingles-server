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

# Use FileSystem storage for tests (InMemoryStorage doesn't exist)
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Conditional PostgreSQL usage based on environment variables
import os
import dj_database_url

USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'False') == 'True'
DATABASE_URL = os.getenv('DATABASE_URL', None)

if USE_POSTGRESQL and DATABASE_URL:
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
if 'channels' in INSTALLED_APPS:
    INSTALLED_APPS.remove('channels')

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
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
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
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
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

# Allow real migrations during tests for proper FK relationships
# MIGRATION_MODULES = {}  # Commented out to enable real migrations

# JWT configuration for tests - ensure token blacklisting works properly
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Shorter for tests
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=30),  # Shorter for tests
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',
}

# Add rest_framework_simplejwt.token_blacklist to INSTALLED_APPS for tests
if 'rest_framework_simplejwt.token_blacklist' not in INSTALLED_APPS:
    INSTALLED_APPS = INSTALLED_APPS + ['rest_framework_simplejwt.token_blacklist']

# Force test database to be reset and all migrations run
# This ensures subscription plans are created  
import sys
if 'test' in sys.argv or 'pytest' in sys.modules:
    # Ensure all apps run their migrations in tests
    pass