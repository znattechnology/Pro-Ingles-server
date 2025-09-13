#!/usr/bin/env python3
"""
Create challenge examples for all 7 types
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import PracticeChallenge, ChallengeOption, PracticeLesson, PracticeUnit
from apps.courses.models import Course

def create_challenges():
    print("=== Creating 7 Types of Challenges ===\n")
    
    # Get or create a lesson to attach challenges to
    course = Course.objects.filter(status='Published').first()
    if not course:
        print("No published course found!")
        return
    
    lesson = PracticeLesson.objects.filter(unit__course=course).first()
    if not lesson:
        print("No lesson found in existing course. Creating one...")
        
        # Create a unit first
        unit = PracticeUnit.objects.filter(course=course).first()
        if not unit:
            unit = PracticeUnit.objects.create(
                course=course,
                title="Test Unit for Challenges",
                description="Unit created for testing all challenge types",
                order=1
            )
            print(f"Created unit: {unit.title}")
        
        # Create a lesson
        lesson = PracticeLesson.objects.create(
            unit=unit,
            title="All Challenge Types Demo",
            order=1
        )
        print(f"Created lesson: {lesson.title}")
    
    print(f"Adding challenges to: {lesson.title}")
    print(f"Course: {course.title}\n")
    
    # Clear existing challenges for this lesson to avoid duplicates
    PracticeChallenge.objects.filter(lesson=lesson).delete()
    
    # 1. Multiple Choice (SELECT)
    challenge1 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='SELECT',
        question='What is the capital of England?',
        order=1
    )
    
    ChallengeOption.objects.create(challenge=challenge1, text='London', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge1, text='Paris', is_correct=False, order=2)
    ChallengeOption.objects.create(challenge=challenge1, text='Berlin', is_correct=False, order=3)
    ChallengeOption.objects.create(challenge=challenge1, text='Madrid', is_correct=False, order=4)
    print("✅ Created SELECT (Multiple Choice) challenge")
    
    # 2. Fill in the Blank
    challenge2 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='FILL_BLANK',
        question='I _____ to school every day.',
        order=2
    )
    
    ChallengeOption.objects.create(challenge=challenge2, text='go', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge2, text='went', is_correct=False, order=2)
    ChallengeOption.objects.create(challenge=challenge2, text='going', is_correct=False, order=3)
    ChallengeOption.objects.create(challenge=challenge2, text='gone', is_correct=False, order=4)
    print("✅ Created FILL_BLANK challenge")
    
    # 3. Translation
    challenge3 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='TRANSLATION',
        question='Translate to English: "Olá, como está?"',
        order=3
    )
    
    ChallengeOption.objects.create(challenge=challenge3, text='Hello, how are you?', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge3, text='Hi, where are you?', is_correct=False, order=2)
    ChallengeOption.objects.create(challenge=challenge3, text='Hello, what are you?', is_correct=False, order=3)
    ChallengeOption.objects.create(challenge=challenge3, text='Hey, who are you?', is_correct=False, order=4)
    print("✅ Created TRANSLATION challenge")
    
    # 4. Listening Comprehension
    challenge4 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='LISTENING',
        question='Listen and select what you hear: "The cat is on the table"',
        order=4
    )
    
    ChallengeOption.objects.create(challenge=challenge4, text='The cat is on the table', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge4, text='The cat is under the table', is_correct=False, order=2)
    ChallengeOption.objects.create(challenge=challenge4, text='The dog is on the table', is_correct=False, order=3)
    ChallengeOption.objects.create(challenge=challenge4, text='The cat is in the table', is_correct=False, order=4)
    print("✅ Created LISTENING challenge")
    
    # 5. Speaking/Pronunciation
    challenge5 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='SPEAKING',
        question='Pronounce this sentence: "How are you today?"',
        order=5
    )
    
    # For speaking, we just need one "correct" option representing the expected pronunciation
    ChallengeOption.objects.create(challenge=challenge5, text='How are you today?', is_correct=True, order=1)
    print("✅ Created SPEAKING challenge")
    
    # 6. Match Pairs
    challenge6 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='MATCH_PAIRS',
        question='Match the English words with their Portuguese translations:',
        order=6
    )
    
    # For match pairs, we store the pairs as options
    ChallengeOption.objects.create(challenge=challenge6, text='Apple - Maçã', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge6, text='Book - Livro', is_correct=True, order=2)
    ChallengeOption.objects.create(challenge=challenge6, text='Water - Água', is_correct=True, order=3)
    ChallengeOption.objects.create(challenge=challenge6, text='House - Casa', is_correct=True, order=4)
    print("✅ Created MATCH_PAIRS challenge")
    
    # 7. Sentence Order
    challenge7 = PracticeChallenge.objects.create(
        lesson=lesson,
        type='SENTENCE_ORDER',
        question='Put the words in the correct order to form: "I love learning English"',
        order=7
    )
    
    # Store the words as individual options
    ChallengeOption.objects.create(challenge=challenge7, text='I', is_correct=True, order=1)
    ChallengeOption.objects.create(challenge=challenge7, text='love', is_correct=True, order=2)
    ChallengeOption.objects.create(challenge=challenge7, text='learning', is_correct=True, order=3)
    ChallengeOption.objects.create(challenge=challenge7, text='English', is_correct=True, order=4)
    print("✅ Created SENTENCE_ORDER challenge")
    
    print(f"\n🎉 Successfully created 7 different challenge types!")
    print(f"Lesson: {lesson.title}")
    print(f"Total challenges: {PracticeChallenge.objects.filter(lesson=lesson).count()}")
    
    # Print challenge IDs for testing
    print("\n📋 Challenge IDs for testing:")
    for challenge in PracticeChallenge.objects.filter(lesson=lesson).order_by('order'):
        print(f"{challenge.order}. {challenge.type}: {challenge.id}")
        print(f"   Question: {challenge.question[:50]}...")
        
        # Show first option ID
        first_option = challenge.options.first()
        if first_option:
            print(f"   First option ID: {first_option.id} ({'✅' if first_option.is_correct else '❌'} {first_option.text})")
        print()

if __name__ == '__main__':
    create_challenges()