#!/usr/bin/env python3
"""
Update MATCH_PAIRS challenge with more diverse vocabulary
"""

import os
import sys
import django

# Setup Django
sys.path.append('/Users/vadao/Documents/Projectos_Next/Sistema_Ingles/Tuwi-Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import PracticeChallenge, ChallengeOption

def update_match_pairs():
    print("=== Updating MATCH_PAIRS Challenge ===\n")
    
    # Find MATCH_PAIRS challenge
    match_challenge = PracticeChallenge.objects.filter(type='MATCH_PAIRS').first()
    if not match_challenge:
        print("❌ MATCH_PAIRS challenge not found")
        return
    
    # Clear existing options
    match_challenge.options.all().delete()
    
    # Create more diverse and challenging pairs
    pairs = [
        ('Butterfly', 'Borboleta'),
        ('Rainbow', 'Arco-íris'), 
        ('Freedom', 'Liberdade'),
        ('Friendship', 'Amizade'),
        ('Adventure', 'Aventura'),
        ('Knowledge', 'Conhecimento')
    ]
    
    print(f"Creating {len(pairs)} challenging word pairs:")
    for i, (english, portuguese) in enumerate(pairs, 1):
        option = ChallengeOption.objects.create(
            challenge=match_challenge,
            text=f'{english} - {portuguese}',
            is_correct=True,
            order=i
        )
        print(f"  {i}. {english} → {portuguese} (ID: {option.id})")
    
    print(f"\n✅ Successfully updated MATCH_PAIRS challenge!")
    print(f"Challenge ID: {match_challenge.id}")
    print("Words are now shuffled and much more challenging!")

if __name__ == '__main__':
    update_match_pairs()