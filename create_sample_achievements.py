#!/usr/bin/env python
"""
Create sample achievements for testing
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.practice.models import Achievement

def create_sample_achievements():
    """Create sample achievements for testing"""
    
    achievements_data = [
        {
            'title': 'Primeiro Passo',
            'description': 'Complete sua primeira lição',
            'icon': '🎯',
            'category': 'learning',
            'rarity': 'common',
            'points': 10,
            'requirement_type': 'lessons_completed',
            'requirement_target': 1,
            'requirement_unit': 'lições',
            'is_active': True,
            'is_secret': False,
            'order': 1
        },
        {
            'title': 'Sequência Iniciante',
            'description': 'Mantenha uma sequência de 3 dias consecutivos',
            'icon': '🔥',
            'category': 'streak',
            'rarity': 'common',
            'points': 15,
            'requirement_type': 'streak_days',
            'requirement_target': 3,
            'requirement_unit': 'dias',
            'is_active': True,
            'is_secret': False,
            'order': 2
        },
        {
            'title': 'Mestre dos Pontos',
            'description': 'Acumule 1000 pontos de experiência',
            'icon': '⭐',
            'category': 'milestone',
            'rarity': 'rare',
            'points': 50,
            'requirement_type': 'points_earned',
            'requirement_target': 1000,
            'requirement_unit': 'pontos',
            'is_active': True,
            'is_secret': False,
            'order': 3
        },
        {
            'title': 'Lenda do Aprendizado',
            'description': 'Complete 100 lições com perfeição',
            'icon': '👑',
            'category': 'special',
            'rarity': 'legendary',
            'points': 200,
            'requirement_type': 'perfect_lessons',
            'requirement_target': 100,
            'requirement_unit': 'lições',
            'is_active': True,
            'is_secret': True,
            'order': 4
        }
    ]
    
    created_count = 0
    
    for data in achievements_data:
        achievement, created = Achievement.objects.get_or_create(
            title=data['title'],
            defaults=data
        )
        
        if created:
            print(f"✅ Created achievement: {achievement.title}")
            created_count += 1
        else:
            print(f"⚠️  Achievement already exists: {achievement.title}")
    
    print(f"\n🎉 Created {created_count} new achievements!")
    print(f"📊 Total achievements in database: {Achievement.objects.count()}")

if __name__ == '__main__':
    create_sample_achievements()