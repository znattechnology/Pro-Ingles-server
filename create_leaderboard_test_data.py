#!/usr/bin/env python
"""
Create test data for leaderboard system
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
        UserProgress, UserLeague, UserStreak, 
        Competition, CompetitionParticipant
    )
    
    User = get_user_model()
    
    print("Creating test users and leaderboard data...")
    
    # Create test users with progress
    test_users = [
        {'name': 'Alexandre_Pro', 'email': 'alexandre@test.com', 'points': 2850, 'streak': 45, 'hearts': 5},
        {'name': 'Maria_Study', 'email': 'maria@test.com', 'points': 2720, 'streak': 32, 'hearts': 4},
        {'name': 'João_English', 'email': 'joao@test.com', 'points': 2680, 'streak': 28, 'hearts': 5},
        {'name': 'Ana_Learning', 'email': 'ana@test.com', 'points': 2450, 'streak': 21, 'hearts': 3},
        {'name': 'Pedro_Fast', 'email': 'pedro@test.com', 'points': 2380, 'streak': 19, 'hearts': 5},
        {'name': 'Carla_Smart', 'email': 'carla@test.com', 'points': 2200, 'streak': 15, 'hearts': 4},
        {'name': 'Bruno_Focus', 'email': 'bruno@test.com', 'points': 2100, 'streak': 12, 'hearts': 5},
        {'name': 'Sofia_Quick', 'email': 'sofia@test.com', 'points': 1950, 'streak': 8, 'hearts': 3},
        {'name': 'Diego_Pro', 'email': 'diego@test.com', 'points': 1890, 'streak': 7, 'hearts': 5},
        {'name': 'Lucia_Star', 'email': 'lucia@test.com', 'points': 1750, 'streak': 5, 'hearts': 4},
        {'name': 'Rafael_Go', 'email': 'rafael@test.com', 'points': 1650, 'streak': 3, 'hearts': 5},
        {'name': 'Isabella_Win', 'email': 'isabella@test.com', 'points': 1500, 'streak': 2, 'hearts': 3},
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Create or get user
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                'name': user_data['name'],
                'first_name': user_data['name'].split('_')[0],
                'last_name': user_data['name'].split('_')[1] if '_' in user_data['name'] else '',
            }
        )
        
        if created:
            print(f"Created user: {user.name}")
        
        # Create or update user progress
        user_progress, created = UserProgress.objects.get_or_create(
            user=user,
            defaults={
                'points': user_data['points'],
                'hearts': user_data['hearts'],
            }
        )
        
        if not created:
            user_progress.points = user_data['points']
            user_progress.hearts = user_data['hearts']
            user_progress.save()
        
        # Create or update user league
        league = UserLeague.get_league_for_points(user_data['points'])
        user_league, created = UserLeague.objects.get_or_create(
            user=user,
            defaults={
                'current_league': league,
                'points_when_promoted': user_data['points'],
            }
        )
        
        if not created:
            user_league.current_league = league
            user_league.points_when_promoted = user_data['points']
            user_league.save()
        
        # Create or update user streak
        user_streak, created = UserStreak.objects.get_or_create(
            user=user,
            defaults={
                'current_streak': user_data['streak'],
                'longest_streak': user_data['streak'],
                'last_practice_date': date.today() - timedelta(days=random.randint(0, 2)),
            }
        )
        
        if not created:
            user_streak.current_streak = user_data['streak']
            user_streak.longest_streak = max(user_streak.longest_streak, user_data['streak'])
            user_streak.save()
        
        created_users.append(user)
    
    # Create test competitions
    competitions_data = [
        {
            'title': 'Desafio Semanal',
            'description': 'Complete o máximo de lições esta semana',
            'type': 'weekly',
            'status': 'active',
            'start_date': datetime.now() - timedelta(days=2),
            'end_date': datetime.now() + timedelta(days=5),
            'min_points_to_participate': 100,
            'first_place_prize': 'Badge especial + 500 pontos',
            'second_place_prize': '300 pontos',
            'third_place_prize': '200 pontos',
        },
        {
            'title': 'Maratona de Streak',
            'description': 'Maior sequência consecutiva vence',
            'type': 'monthly',
            'status': 'active',
            'start_date': datetime.now() - timedelta(days=7),
            'end_date': datetime.now() + timedelta(days=21),
            'min_points_to_participate': 500,
            'first_place_prize': 'Título exclusivo + 1000 pontos',
            'second_place_prize': '600 pontos',
            'third_place_prize': '400 pontos',
        }
    ]
    
    created_competitions = []
    
    for comp_data in competitions_data:
        competition, created = Competition.objects.get_or_create(
            title=comp_data['title'],
            defaults=comp_data
        )
        
        if created:
            print(f"Created competition: {competition.title}")
            
            # Add some participants
            eligible_users = [u for u in created_users if u.practice_progress.points >= competition.min_points_to_participate]
            participants_count = min(len(eligible_users), random.randint(50, 200))
            
            for i, user in enumerate(random.sample(eligible_users, min(participants_count, len(eligible_users)))):
                participant, created = CompetitionParticipant.objects.get_or_create(
                    competition=competition,
                    user=user,
                    defaults={
                        'points_earned': random.randint(10, 500),
                        'challenges_completed': random.randint(5, 50),
                        'lessons_completed': random.randint(1, 10),
                        'streak_days': random.randint(1, 15),
                        'current_rank': i + 1,
                        'best_rank': i + 1,
                    }
                )
        
        created_competitions.append(competition)
    
    print(f"\nCreated {len(created_users)} users with progress")
    print(f"Created {len(created_competitions)} competitions")
    print(f"\nLeaderboard test data created successfully!")
    
    # Show some stats
    print(f"\nStats:")
    print(f"- Total users: {User.objects.count()}")
    print(f"- Users with progress: {UserProgress.objects.count()}")
    print(f"- Users in leagues: {UserLeague.objects.count()}")
    print(f"- Active competitions: {Competition.objects.filter(status='active').count()}")
    print(f"- Competition participants: {CompetitionParticipant.objects.count()}")