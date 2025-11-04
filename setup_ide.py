#!/usr/bin/env python3
"""
Setup script to configure Django environment for IDE support.
Run this script if you're having Django import issues in your IDE.
"""

import os
import sys
import subprocess
import json

def setup_django_for_ide():
    """Setup Django environment for IDE support."""
    
    print("🔧 Configuring Django environment for IDE...")
    
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # Import and setup Django
        import django
        from django.conf import settings
        
        if not settings.configured:
            django.setup()
        
        print("✅ Django configured successfully!")
        print(f"   - Django version: {django.get_version()}")
        print(f"   - Settings module: {settings.SETTINGS_MODULE}")
        print(f"   - Apps ready: {django.apps.apps.ready}")
        
        # Test imports
        from django.db import connection
        from django.http import JsonResponse
        from django.utils.deprecation import MiddlewareMixin
        from django.core.cache import cache
        from django.db.models import Count, Avg
        
        print("✅ All Django imports successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configuring Django: {e}")
        return False

def check_vscode_config():
    """Check VS Code configuration."""
    
    vscode_settings = ".vscode/settings.json"
    if os.path.exists(vscode_settings):
        try:
            with open(vscode_settings, 'r') as f:
                config = json.load(f)
            
            interpreter = config.get('python.defaultInterpreterPath')
            if interpreter and 'venv' in interpreter:
                print("✅ VS Code Python interpreter configured correctly")
            else:
                print("⚠️  VS Code Python interpreter may need configuration")
                
        except Exception as e:
            print(f"⚠️  Error reading VS Code config: {e}")
    else:
        print("⚠️  VS Code settings not found")

def main():
    """Main setup function."""
    
    print("🚀 Django IDE Setup Script")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: This script must be run from the Django project root directory")
        sys.exit(1)
    
    # Setup Django
    if setup_django_for_ide():
        print("\n🎉 Django environment setup completed!")
        print("\nNext steps:")
        print("1. Restart your IDE (VS Code)")
        print("2. Select the correct Python interpreter: ./venv/bin/python")
        print("3. Reload the window if needed (Cmd+Shift+P → 'Developer: Reload Window')")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        sys.exit(1)
    
    # Check VS Code config
    print("\n" + "=" * 40)
    check_vscode_config()

if __name__ == "__main__":
    main()