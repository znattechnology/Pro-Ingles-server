"""
Django settings for ProEnglish Platform.

Clean backend focused on authentication system for English learning platform.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CORE SETTINGS
# =============================================================================

SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-only-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# =============================================================================
# DATABASE
# =============================================================================

# Use SQLite for development, PostgreSQL for production
USE_POSTGRESQL = config('USE_POSTGRESQL', default=False, cast=bool)

if USE_POSTGRESQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='proenglish_dev'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': {
                'charset': 'utf8',
            },
            'TEST': {
                'NAME': 'test_proenglish_dev',
            },
        }
    }
else:
    # SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =============================================================================
# AUTHENTICATION & SECURITY
# =============================================================================

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

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
        'rest_framework.parsers.FileUploadParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =============================================================================
# JWT SETTINGS
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# =============================================================================
# CORS SETTINGS
# =============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Europe/Lisbon'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# AWS S3 Settings (for production)
USE_S3 = config('USE_S3', default=False, cast=bool)

# AWS S3 configuration will be added later
# if USE_S3:
#     AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
#     AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
#     AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
#     AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='eu-west-1')
#     AWS_DEFAULT_ACL = None
#     AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
#     AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
#     
#     # Static files settings
#     STATICFILES_STORAGE = 'storages.backends.s3boto3.StaticS3Boto3Storage'
#     DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.MediaS3Boto3Storage'

# =============================================================================
# EMAIL SETTINGS
# =============================================================================

EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)

# SMTP Settings
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)

if EMAIL_BACKEND == 'anymail.backends.mailgun.EmailBackend':
    ANYMAIL = {
        'MAILGUN_API_KEY': config('MAILGUN_API_KEY'),
        'MAILGUN_SENDER_DOMAIN': config('MAILGUN_SENDER_DOMAIN'),
    }

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@proenglish.com')
CONTACT_EMAIL = config('CONTACT_EMAIL', default='contact@proenglish.com')

# Frontend URL for email links
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# =============================================================================
# GOOGLE OAUTH SETTINGS
# =============================================================================

# Google OAuth2 configuration
GOOGLE_OAUTH2_CLIENT_ID = config('GOOGLE_OAUTH2_CLIENT_ID', default='')
GOOGLE_OAUTH2_CLIENT_SECRET = config('GOOGLE_OAUTH2_CLIENT_SECRET', default='')
GOOGLE_OAUTH2_REDIRECT_URI = config('GOOGLE_OAUTH2_REDIRECT_URI', default='http://localhost:3000/auth/google/callback')

# OAuth2 settings
OAUTH2_SETTINGS = {
    'GOOGLE': {
        'CLIENT_ID': GOOGLE_OAUTH2_CLIENT_ID,
        'CLIENT_SECRET': GOOGLE_OAUTH2_CLIENT_SECRET,
        'REDIRECT_URI': GOOGLE_OAUTH2_REDIRECT_URI,
        'SCOPE': [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ],
        'AUTH_URI': 'https://accounts.google.com/o/oauth2/auth',
        'TOKEN_URI': 'https://oauth2.googleapis.com/token',
        'USER_INFO_URI': 'https://www.googleapis.com/oauth2/v2/userinfo',
    }
}

# =============================================================================
# LOGGING & STRUCTURED LOGGING
# =============================================================================

import structlog

# Structlog configuration
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.WriteLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    cache_logger_on_first_use=True,
)

# Django structlog configuration
STRUCTLOG_SETTINGS = {
    "CONTEXT_CLASS": dict,
    "LOGGER_FACTORY": structlog.WriteLoggerFactory(),
    "WRAPPER_CLASS": structlog.make_filtering_bound_logger(20),
    "CACHE_LOGGER_ON_FIRST_USE": True,
    "LOG_LEVEL": "INFO",
    "PROCESSORS": [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
}

# Standard Django logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'json' if not DEBUG else 'verbose',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'formatter': 'json' if not DEBUG else 'verbose',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'performance': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'performance.log',
            'formatter': 'json' if not DEBUG else 'verbose',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 3,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.core.monitoring': {
            'handlers': ['performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'structlog': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# API DOCUMENTATION
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Tuwi Beauty Platform API',
    'DESCRIPTION': '''
    Comprehensive API for the Tuwi Beauty Platform - a modern marketplace connecting clients with professional braiders.
    
    ## Features
    - 🔐 User Authentication & Authorization (JWT)
    - 👥 User & Braider Management
    - 📅 Booking & Appointment System
    - 🛒 E-commerce & Product Management
    - ⭐ Reviews & Ratings
    - 💬 Real-time Chat System
    - 🔔 Push Notifications
    - 💳 Payment Processing (Stripe)
    - 📊 Analytics & Reporting
    - 🤖 Machine Learning & AI Features
    - 🔗 External Integrations
    
    ## Rate Limiting
    API endpoints are rate-limited to ensure fair usage:
    - Authentication endpoints: 20 requests per 15 minutes
    - ML endpoints: 50 requests per hour
    - General API: 1000 requests per hour
    
    ## Response Format
    All API responses follow a consistent format with appropriate HTTP status codes.
    Error responses include detailed error messages and validation errors where applicable.
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'CONTACT': {
        'name': 'Tuwi Development Team',
        'email': 'dev@tuwi.pt',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'User authentication and authorization endpoints'
        },
        {
            'name': 'Users',
            'description': 'User profile and account management'
        },
        {
            'name': 'Braiders',
            'description': 'Braider profiles, services, and availability'
        },
        {
            'name': 'Bookings',
            'description': 'Appointment booking and management'
        },
        {
            'name': 'E-commerce',
            'description': 'Products, categories, and cart management'
        },
        {
            'name': 'Reviews',
            'description': 'Rating and review system'
        },
        {
            'name': 'Chat',
            'description': 'Real-time messaging between users and braiders'
        },
        {
            'name': 'Notifications',
            'description': 'Push notifications and alerts'
        },
        {
            'name': 'Payments',
            'description': 'Payment processing and transaction management'
        },
        {
            'name': 'Analytics',
            'description': 'Business intelligence and reporting'
        },
        {
            'name': 'Machine Learning',
            'description': 'AI-powered recommendations and predictions'
        },
        {
            'name': 'Integrations',
            'description': 'External service integrations'
        },
    ],
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Development server'
        },
        {
            'url': 'https://api.tuwi.pt',
            'description': 'Production server'
        },
    ],
    'EXTERNAL_DOCS': {
        'description': 'Full Documentation',
        'url': 'https://docs.tuwi.pt'
    },
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SORT_OPERATIONS': True,
    'ENUM_NAME_OVERRIDES': {
        'ValidationErrorEnum': 'django.core.exceptions.ValidationError',
    },
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums'
    ],
    'SECURITY': [
        {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    ],
}

# =============================================================================
# ADMIN INTERFACE
# =============================================================================

X_FRAME_OPTIONS = 'SAMEORIGIN'
SILENCED_SYSTEM_CHECKS = ['security.W019']

# =============================================================================
# DEFAULT FIELD SETTINGS
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CACHE SETTINGS
# =============================================================================

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_CACHE_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'tuwi',
        'TIMEOUT': 1800,  # 30 minutes default
    }
}

# Cache configuration
CACHE_TTL = config('CACHE_TTL', default=1800, cast=int)  # 30 minutes

# Session cache (use Redis)
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'  # Redis não disponível
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Usar database temporariamente
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours

# =============================================================================
# CELERY SETTINGS
# =============================================================================

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')

# Celery Task Configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Celery Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Task routing
CELERY_TASK_ROUTES = {
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.chat.tasks.*': {'queue': 'chat'},
    'apps.payments.tasks.*': {'queue': 'payments'},
    'apps.ml.tasks.*': {'queue': 'ml'},
    'apps.analytics.tasks.*': {'queue': 'analytics'},
    'apps.core.tasks.*': {'queue': 'core'},
}

# Celery Beat (Scheduler)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task time limits
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',
    'retry_on_timeout': True,
}

# Task annotations for specific rate limits
CELERY_TASK_ANNOTATIONS = {
    '*': {
        'rate_limit': '100/m',
    },
    'apps.ml.tasks.train_model': {
        'rate_limit': '10/m',
        'time_limit': 2 * 60 * 60,  # 2 hours
    },
    'apps.core.tasks.backup_database': {
        'rate_limit': '1/h',
    },
}

# =============================================================================
# STRIPE SETTINGS
# =============================================================================

STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

if DEBUG:
    # Allow all hosts in development
    ALLOWED_HOSTS = ['*']
    
    # Disable CORS in development
    CORS_ALLOW_ALL_ORIGINS = True

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
