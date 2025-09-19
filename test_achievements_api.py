#!/usr/bin/env python
"""
Test achievements API responses
"""
import os
import sys
import django
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import Achievement, UserAchievement
from apps.users.models import User
from apps.practice.serializers import AchievementSerializer, UserAchievementSerializer

def test_achievements_data():
    """Test what data is being returned by achievements APIs"""
    
    print("🔍 Testing Achievements API Data...")
    print("=" * 60)
    
    # Test 1: Check Achievement objects (Teacher API)
    print("\n1. TEACHER API DATA (Achievement objects):")
    print("-" * 40)
    
    achievements = Achievement.objects.filter(is_active=True).order_by('category', 'order')
    print(f"📊 Total active achievements: {achievements.count()}")
    
    serializer = AchievementSerializer(achievements, many=True)
    teacher_data = serializer.data
    
    for i, achievement in enumerate(teacher_data[:3]):  # Show first 3
        print(f"\n  Achievement {i+1}:")
        print(f"    ID: {achievement['id']}")
        print(f"    Title: {achievement['title']}")
        print(f"    Category: {achievement['category']}")
        print(f"    Is Active: {achievement.get('is_active', 'Missing!')}")
        print(f"    Unlocked Count: {achievement.get('unlocked_count', 'Missing!')}")
    
    print(f"\n  ... and {len(teacher_data) - 3} more achievements")
    
    # Test 2: Check if we have users
    print("\n\n2. USER DATA:")
    print("-" * 40)
    
    users = User.objects.all()
    print(f"📊 Total users: {users.count()}")
    
    if users.exists():
        test_user = users.first()
        print(f"🧪 Testing with user: {test_user.name} (ID: {test_user.id})")
        
        # Test 3: Check UserAchievement objects (Student API)
        print("\n\n3. STUDENT API DATA (UserAchievement objects):")
        print("-" * 40)
        
        # Simulate what the student API does
        all_achievements = Achievement.objects.filter(is_active=True)
        print(f"📋 Creating UserAchievement records for {all_achievements.count()} achievements...")
        
        created_count = 0
        for achievement in all_achievements:
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
        
        print(f"✅ Created {created_count} new UserAchievement records")
        
        # Get user achievements
        user_achievements = UserAchievement.objects.filter(
            user=test_user,
            achievement__is_active=True
        ).select_related('achievement').order_by(
            'achievement__category', 'achievement__order'
        )
        
        print(f"📊 Total user achievements: {user_achievements.count()}")
        
        # Serialize the data
        user_serializer = UserAchievementSerializer(user_achievements, many=True)
        student_data = user_serializer.data
        
        for i, user_achievement in enumerate(student_data[:3]):  # Show first 3
            achievement = user_achievement['achievement']
            print(f"\n  UserAchievement {i+1}:")
            print(f"    Achievement Title: {achievement['title']}")
            print(f"    Category: {achievement['category']}")
            print(f"    Is Unlocked: {user_achievement['is_unlocked']}")
            print(f"    Current Progress: {user_achievement['current_progress']}")
            print(f"    Achievement Data: {json.dumps(achievement, indent=6)[:200]}...")
        
        print(f"\n  ... and {len(student_data) - 3} more user achievements")
        
        # Test 4: Check what frontend will receive
        print("\n\n4. FRONTEND TRANSFORMATION:")
        print("-" * 40)
        
        # Simulate frontend transformation (from achievementsApi.ts)
        frontend_data = []
        for user_achievement in student_data:
            if user_achievement.get('achievement'):  # Filter out items without achievement
                transformed = {
                    'id': user_achievement['achievement']['id'],
                    'title': user_achievement['achievement']['title'],
                    'description': user_achievement['achievement']['description'],
                    'icon': user_achievement['achievement']['icon'],
                    'category': user_achievement['achievement']['category'],
                    'rarity': user_achievement['achievement']['rarity'],
                    'points': user_achievement['achievement']['points'],
                    'isUnlocked': user_achievement['is_unlocked'],
                    'unlockedAt': user_achievement.get('unlocked_at_formatted'),
                }
                
                if not user_achievement['is_unlocked']:
                    transformed['progress'] = {
                        'current': user_achievement['current_progress'],
                        'target': user_achievement['achievement']['requirement_target'],
                        'unit': user_achievement['achievement']['requirement_unit']
                    }
                
                frontend_data.append(transformed)
        
        print(f"📊 Frontend will receive {len(frontend_data)} achievements")
        
        for i, achievement in enumerate(frontend_data[:3]):  # Show first 3
            print(f"\n  Frontend Achievement {i+1}:")
            print(f"    ID: {achievement['id']}")
            print(f"    Title: {achievement['title']}")
            print(f"    Category: {achievement['category']}")
            print(f"    Is Unlocked: {achievement['isUnlocked']}")
            if 'progress' in achievement:
                progress = achievement['progress']
                print(f"    Progress: {progress['current']}/{progress['target']} {progress['unit']}")
        
        print(f"\n  ... and {len(frontend_data) - 3} more for the frontend")
        
    else:
        print("❌ No users found! Create a user first.")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == '__main__':
    test_achievements_data()