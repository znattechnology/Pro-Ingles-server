#!/usr/bin/env python3
"""
Fix user hearts for testing
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import UserProgress
from apps.users.models import User

def fix_hearts():
    print("=== Fixing User Hearts ===\n")
    
    # Get all users with progress
    user_progresses = UserProgress.objects.all()
    
    for progress in user_progresses:
        old_hearts = progress.hearts
        progress.hearts = 5  # Reset to max hearts
        progress.save()
        
        print(f"User: {progress.user.name}")
        print(f"  Hearts: {old_hearts} -> {progress.hearts}")
        print(f"  Points: {progress.points}")
        print()

if __name__ == '__main__':
    fix_hearts()
    print("✅ All users now have 5 hearts!")