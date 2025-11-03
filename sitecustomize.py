"""
Django setup for IDE support.
This file is automatically imported by Python to configure Django.
"""

import os
import sys

# Only run this if we're not in a Django management command
if not any(arg in sys.argv for arg in ['manage.py', 'runserver', 'migrate', 'shell', 'test']):
    try:
        # Configure Django settings
        if 'DJANGO_SETTINGS_MODULE' not in os.environ:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        
        # Setup Django if not already configured
        import django
        from django.conf import settings
        
        if not settings.configured:
            django.setup()
        
    except Exception:
        # Silently ignore any errors during IDE setup
        pass