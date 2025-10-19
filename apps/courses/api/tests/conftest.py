"""
Configuration for API tests.

This ensures Django is properly configured before running tests.
"""

import os
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.test_settings')
    django.setup()