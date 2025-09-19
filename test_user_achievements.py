#!/usr/bin/env python
"""
Test user achievements access with token
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.practice.models import Achievement, UserAchievement
from rest_framework_simplejwt.tokens import RefreshToken

def test_user_achievements():
    """Test user achievements with authentication"""
    
    print("🔍 Testing User Achievements with Authentication...")
    print("=" * 60)
    
    # Get a test user
    users = User.objects.all()
    if not users.exists():
        print("❌ No users found! Creating test user...")
        test_user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='testpass123'
        )
        print(f"✅ Created test user: {test_user.name}")
    else:
        test_user = users.first()
        print(f"🧪 Using test user: {test_user.name} (ID: {test_user.id})")
    
    # Generate token for test user
    refresh = RefreshToken.for_user(test_user)
    access_token = str(refresh.access_token)
    
    print(f"🔑 Generated access token: {access_token[:50]}...")
    
    # Check achievements
    achievements = Achievement.objects.filter(is_active=True)
    print(f"📊 Total active achievements: {achievements.count()}")
    
    # Check user achievements
    user_achievements = UserAchievement.objects.filter(
        user=test_user,
        achievement__is_active=True
    )
    print(f"📋 User achievements already created: {user_achievements.count()}")
    
    # Create missing user achievements
    created_count = 0
    for achievement in achievements:
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=test_user,
            achievement=achievement,
            defaults={
                'current_progress': 0,
                'is_unlocked': False
            }
        )
        if created:
            created_count += 1
    
    print(f"✅ Created {created_count} new user achievements")
    
    # Final count
    final_count = UserAchievement.objects.filter(
        user=test_user,
        achievement__is_active=True
    ).count()
    print(f"📊 Final user achievements count: {final_count}")
    
    # Unlock a few achievements for testing
    print("\n🎯 Unlocking some achievements for testing...")
    user_achievements_to_unlock = UserAchievement.objects.filter(
        user=test_user,
        achievement__is_active=True,
        is_unlocked=False
    )[:3]  # Unlock first 3
    
    unlocked_count = 0
    for ua in user_achievements_to_unlock:
        ua.is_unlocked = True
        ua.unlocked_at = datetime.now()
        ua.current_progress = ua.achievement.requirement_target
        ua.save()
        unlocked_count += 1
        print(f"  ✅ Unlocked: {ua.achievement.title}")
    
    print(f"🎉 Unlocked {unlocked_count} achievements for testing")
    
    # Stats
    total_unlocked = UserAchievement.objects.filter(
        user=test_user,
        is_unlocked=True
    ).count()
    
    total_points = sum(
        ua.achievement.points for ua in UserAchievement.objects.filter(
            user=test_user,
            is_unlocked=True
        )
    )
    
    print(f"\n📈 User Stats:")
    print(f"  Total Unlocked: {total_unlocked}")
    print(f"  Total Points: {total_points}")
    
    print(f"\n🌐 Test this in your browser:")
    print(f"  1. Open browser console")
    print(f"  2. Set token: localStorage.setItem('access_token', '{access_token}')")
    print(f"  3. Navigate to: http://localhost:3000/user/laboratory/achievements")
    print(f"  4. You should see {final_count} achievements with {total_unlocked} unlocked")
    
    print("\n" + "=" * 60)
    print("✅ Test setup completed!")

if __name__ == '__main__':
    test_user_achievements()