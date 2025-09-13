#!/usr/bin/env python3
"""
Test script to check challenge data in Django database
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import PracticeChallenge, ChallengeOption, UserProgress, Course
from apps.users.models import User

def check_data():
    print("=== Django Challenge Data Check ===\n")
    
    # Check courses
    courses = Course.objects.all()
    print(f"📚 Courses: {courses.count()}")
    for course in courses[:3]:
        print(f"  - {course.title} (ID: {course.id})")
    
    # Check challenges
    challenges = PracticeChallenge.objects.all()
    print(f"\n🎯 Challenges: {challenges.count()}")
    for challenge in challenges[:3]:
        print(f"  - {challenge.question[:50]}... (ID: {challenge.id})")
        
        # Check options for this challenge
        options = ChallengeOption.objects.filter(challenge=challenge)
        print(f"    Options: {options.count()}")
        for option in options:
            correct = "✅" if option.is_correct else "❌"
            print(f"      {correct} {option.text} (ID: {option.id})")
    
    # Check users
    users = User.objects.all()
    print(f"\n👤 Users: {users.count()}")
    for user in users[:2]:
        print(f"  - {user.name} ({user.email})")
        
        # Check user progress
        try:
            progress = UserProgress.objects.get(user=user)
            print(f"    Hearts: {progress.hearts}, Points: {progress.points}")
        except UserProgress.DoesNotExist:
            print(f"    No progress data")
    
    print("\n=== Sample Challenge Test Data ===")
    if challenges.exists() and challenges.first().options.exists():
        sample_challenge = challenges.first()
        sample_option = sample_challenge.options.first()
        
        print(f"Sample Challenge ID: {sample_challenge.id}")
        print(f"Sample Option ID: {sample_option.id}")
        print(f"Option is correct: {sample_option.is_correct}")
        print(f"\nUse these IDs to test the challenge-progress endpoint:")
        print(f"Challenge: {sample_challenge.id}")
        print(f"Option: {sample_option.id}")
    else:
        print("No challenge data found!")

if __name__ == '__main__':
    check_data()