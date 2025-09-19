#!/usr/bin/env python3
"""
Check current achievements status
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.practice.models import UserAchievement, Achievement


def check_achievements():
    print("🏆 Current Achievements Status\n")
    
    # Show all achievements
    achievements = Achievement.objects.filter(is_active=True).order_by('category', 'order')
    print(f"📊 Total achievements available: {achievements.count()}\n")
    
    # Show users and their achievements
    users = User.objects.all()
    
    for user in users:
        user_achievements = UserAchievement.objects.filter(user=user, is_unlocked=True)
        user_progress = UserAchievement.objects.filter(user=user, is_unlocked=False, current_progress__gt=0)
        
        print(f"👤 {user.name or user.email}")
        print(f"   🏆 Unlocked: {user_achievements.count()}")
        print(f"   📈 In Progress: {user_progress.count()}")
        
        if user_achievements.exists():
            print("   Unlocked achievements:")
            for ua in user_achievements:
                print(f"     • {ua.achievement.title} ({ua.achievement.points} pts)")
        
        if user_progress.exists():
            print("   In progress:")
            for ua in user_progress[:3]:  # Show first 3
                print(f"     • {ua.achievement.title}: {ua.current_progress}/{ua.achievement.requirement_target}")
        
        print()


if __name__ == "__main__":
    check_achievements()