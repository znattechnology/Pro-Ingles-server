#!/usr/bin/env python3
"""
Test script to verify achievements integration is working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.practice.models import UserProgress, UserAchievement, Achievement


def test_achievements_integration():
    print("🧪 Testing Achievements Integration...")
    
    # Get a test user
    try:
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"👤 Testing with user: {user.name or user.email}")
        
        # Get or create user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=user,
            defaults={'hearts': 5, 'points': 0}
        )
        
        if created:
            print("✅ Created new UserProgress")
        else:
            print(f"📊 Current points: {user_progress.points}")
        
        # Test: Add points (should trigger achievements)
        print("\n🔥 Testing points-based achievements...")
        initial_points = user_progress.points
        user_progress.add_points(100)  # This should trigger achievement checks
        
        print(f"➕ Added 100 points: {initial_points} → {user_progress.points}")
        
        # Check if any achievements were unlocked
        user_achievements = UserAchievement.objects.filter(
            user=user, 
            is_unlocked=True
        ).count()
        
        total_achievements = Achievement.objects.filter(is_active=True).count()
        
        print(f"🏆 User has {user_achievements}/{total_achievements} achievements unlocked")
        
        # Test specific achievements for points
        points_achievements = Achievement.objects.filter(
            requirement_type='points_earned',
            is_active=True
        )
        
        print("\n📈 Points-based achievements:")
        for achievement in points_achievements:
            user_achievement = UserAchievement.objects.filter(
                user=user,
                achievement=achievement
            ).first()
            
            if user_achievement:
                status = "🏆 UNLOCKED" if user_achievement.is_unlocked else f"📊 {user_achievement.current_progress}/{achievement.requirement_target}"
                print(f"  • {achievement.title}: {status}")
            else:
                print(f"  • {achievement.title}: ❓ No progress record")
        
        print("\n✅ Integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_achievements_integration()