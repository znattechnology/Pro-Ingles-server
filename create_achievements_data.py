#!/usr/bin/env python
"""
Create test data for achievements system
"""
import os
import sys
import django
from datetime import datetime, date, timedelta
import random

# Setup Django
if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from django.contrib.auth import get_user_model
    from apps.practice.models import (
        Achievement, AchievementCategory, UserAchievement,
        AchievementNotification, UserProgress
    )
    
    User = get_user_model()
    
    print("Creating achievement categories and achievements...")
    
    # Create achievement categories
    categories_data = [
        {
            'name': 'learning',
            'display_name': 'Aprendizagem',
            'description': 'Conquistas relacionadas ao aprendizado e conclusão de lições',
            'icon_class': 'BookOpen',
            'color': 'text-blue-400',
            'order': 1
        },
        {
            'name': 'streak',
            'display_name': 'Sequência',
            'description': 'Conquistas de prática diária e consistência',
            'icon_class': 'Flame',
            'color': 'text-orange-400',
            'order': 2
        },
        {
            'name': 'milestone',
            'display_name': 'Marcos',
            'description': 'Grandes marcos de progresso e aprendizado',
            'icon_class': 'Target',
            'color': 'text-green-400',
            'order': 3
        },
        {
            'name': 'social',
            'display_name': 'Social',
            'description': 'Conquistas relacionadas a rankings e competições',
            'icon_class': 'Users',
            'color': 'text-purple-400',
            'order': 4
        },
        {
            'name': 'special',
            'display_name': 'Especiais',
            'description': 'Conquistas especiais e eventos únicos',
            'icon_class': 'Crown',
            'color': 'text-yellow-400',
            'order': 5
        }
    ]
    
    for cat_data in categories_data:
        category, created = AchievementCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        if created:
            print(f"Created category: {category.display_name}")
    
    # Create achievements based on the mock data from the frontend
    achievements_data = [
        # Learning achievements
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
            'order': 1
        },
        {
            'title': 'Perfeccionista',
            'description': 'Obtenha 100% de acerto em 5 lições consecutivas',
            'icon': '⭐',
            'category': 'learning',
            'rarity': 'epic',
            'points': 100,
            'requirement_type': 'perfect_lessons',
            'requirement_target': 5,
            'requirement_unit': 'lições',
            'order': 2
        },
        {
            'title': 'Mestre das Palavras',
            'description': 'Aprenda 500 palavras novas',
            'icon': '📚',
            'category': 'learning',
            'rarity': 'epic',
            'points': 150,
            'requirement_type': 'words_learned',
            'requirement_target': 500,
            'requirement_unit': 'palavras',
            'order': 3
        },
        {
            'title': 'Estudioso Dedicado',
            'description': 'Complete 10 lições em um dia',
            'icon': '📖',
            'category': 'learning',
            'rarity': 'rare',
            'points': 75,
            'requirement_type': 'daily_lessons',
            'requirement_target': 10,
            'requirement_unit': 'lições',
            'order': 4
        },
        
        # Streak achievements
        {
            'title': 'Sequência de Ferro',
            'description': 'Mantenha uma sequência de 7 dias',
            'icon': '🔥',
            'category': 'streak',
            'rarity': 'rare',
            'points': 50,
            'requirement_type': 'streak_days',
            'requirement_target': 7,
            'requirement_unit': 'dias',
            'order': 1
        },
        {
            'title': 'Lenda Dourada',
            'description': 'Mantenha uma sequência de 30 dias',
            'icon': '👑',
            'category': 'streak',
            'rarity': 'legendary',
            'points': 300,
            'requirement_type': 'streak_days',
            'requirement_target': 30,
            'requirement_unit': 'dias',
            'order': 2
        },
        {
            'title': 'Consistência Total',
            'description': 'Mantenha uma sequência de 100 dias',
            'icon': '💎',
            'category': 'streak',
            'rarity': 'legendary',
            'points': 1000,
            'requirement_type': 'streak_days',
            'requirement_target': 100,
            'requirement_unit': 'dias',
            'order': 3
        },
        
        # Milestone achievements
        {
            'title': 'Maratona de Aprendizado',
            'description': 'Complete 50 lições no total',
            'icon': '🏃',
            'category': 'milestone',
            'rarity': 'rare',
            'points': 75,
            'requirement_type': 'lessons_completed',
            'requirement_target': 50,
            'requirement_unit': 'lições',
            'order': 1
        },
        {
            'title': 'Campeão dos Desafios',
            'description': 'Complete 1000 desafios',
            'icon': '🏆',
            'category': 'milestone',
            'rarity': 'epic',
            'points': 200,
            'requirement_type': 'challenges_completed',
            'requirement_target': 1000,
            'requirement_unit': 'desafios',
            'order': 2
        },
        {
            'title': 'Mestre de Pontos',
            'description': 'Acumule 10.000 pontos',
            'icon': '⚡',
            'category': 'milestone',
            'rarity': 'legendary',
            'points': 500,
            'requirement_type': 'points_earned',
            'requirement_target': 10000,
            'requirement_unit': 'pontos',
            'order': 3
        },
        
        # Social achievements
        {
            'title': 'Competidor',
            'description': 'Entre no top 10 do ranking semanal',
            'icon': '🥇',
            'category': 'social',
            'rarity': 'rare',
            'points': 80,
            'requirement_type': 'ranking_position',
            'requirement_target': 10,
            'requirement_unit': 'posição',
            'order': 1
        },
        {
            'title': 'Líder das Ligas',
            'description': 'Alcance a Liga Diamante',
            'icon': '💠',
            'category': 'social',
            'rarity': 'epic',
            'points': 250,
            'requirement_type': 'league_reached',
            'requirement_target': 4,  # Diamond league
            'requirement_unit': 'liga',
            'order': 2
        },
        
        # Special achievements
        {
            'title': 'Noturno Dedicado',
            'description': 'Complete lições após 22h por 5 dias',
            'icon': '🌙',
            'category': 'special',
            'rarity': 'epic',
            'points': 120,
            'requirement_type': 'night_lessons',
            'requirement_target': 5,
            'requirement_unit': 'dias',
            'order': 1
        },
        {
            'title': 'Madrugador',
            'description': 'Complete lições antes das 6h por 5 dias',
            'icon': '🌅',
            'category': 'special',
            'rarity': 'epic',
            'points': 120,
            'requirement_type': 'morning_lessons',
            'requirement_target': 5,
            'requirement_unit': 'dias',
            'order': 2
        },
        {
            'title': 'Speedrunner',
            'description': 'Complete uma lição em menos de 2 minutos',
            'icon': '⚡',
            'category': 'special',
            'rarity': 'rare',
            'points': 60,
            'requirement_type': 'fast_lesson',
            'requirement_target': 1,
            'requirement_unit': 'lição',
            'order': 3
        },
    ]
    
    created_achievements = []
    
    for ach_data in achievements_data:
        achievement, created = Achievement.objects.get_or_create(
            title=ach_data['title'],
            defaults=ach_data
        )
        if created:
            print(f"Created achievement: {achievement.title} ({achievement.rarity})")
            created_achievements.append(achievement)
        else:
            created_achievements.append(achievement)
    
    # Create some user achievements for existing users
    users = User.objects.all()[:5]  # Get first 5 users
    
    for user in users:
        print(f"\nCreating achievements for user: {user.name if hasattr(user, 'name') else user.email}")
        
        # Unlock some achievements for variety
        achievements_to_unlock = random.sample(created_achievements, random.randint(1, 4))
        
        for achievement in achievements_to_unlock:
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={
                    'is_unlocked': True,
                    'current_progress': achievement.requirement_target,
                    'unlocked_at': datetime.now() - timedelta(days=random.randint(0, 30))
                }
            )
            
            if created and user_achievement.is_unlocked:
                print(f"  ✅ Unlocked: {achievement.title}")
                
                # Create notification
                notification, notif_created = AchievementNotification.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={
                        'is_read': random.choice([True, False]),
                        'is_celebrated': True
                    }
                )
        
        # Set progress for some locked achievements
        locked_achievements = Achievement.objects.exclude(
            user_achievements__user=user,
            user_achievements__is_unlocked=True
        )[:3]
        
        for achievement in locked_achievements:
            max_progress = max(1, achievement.requirement_target - 1)
            progress = random.randint(1, max_progress) if max_progress > 1 else 1
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={
                    'current_progress': progress,
                    'is_unlocked': False
                }
            )
            
            if created:
                print(f"  📈 Progress: {achievement.title} ({progress}/{achievement.requirement_target})")
    
    print(f"\nAchievements system created successfully!")
    print(f"- Created {len(created_achievements)} achievements")
    print(f"- Created achievement progress for {len(users)} users")
    print(f"- Total categories: {AchievementCategory.objects.count()}")
    print(f"- Total user achievements: {UserAchievement.objects.count()}")
    print(f"- Total notifications: {AchievementNotification.objects.count()}")