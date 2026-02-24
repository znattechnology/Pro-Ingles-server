"""
URL configuration for student practice courses API.

This module defines URL patterns for student practice course consumption,
maintaining the same structure and response format as the Express API.
"""

from django.urls import path
from . import views

app_name = 'student_practice_courses'

urlpatterns = [
    # ========================================================================
    # FRONTEND COMPATIBILITY ENDPOINTS - MUST BE FIRST to avoid conflicts
    # ========================================================================
    
    # Test endpoints for verification
    path(
        'test-units/', 
        views.test_units_simple, 
        name='test-units'
    ),
    path(
        'test-lessons/', 
        views.test_lessons_simple, 
        name='test-lessons'
    ),
    path(
        'test-challenges/', 
        views.test_challenges_simple, 
        name='test-challenges'
    ),

    # ========================================================================
    # CORE PRACTICE ENDPOINTS
    # ========================================================================

    # List all courses
    path(
        'courses/', 
        views.CoursesListView.as_view(), 
        name='courses-list'
    ),
    
    # Course units endpoint
    # Maps to getCourse query from client project
    path(
        'courses/<uuid:course_id>/units/', 
        views.CourseUnitsView.as_view(), 
        name='course-units'
    ),
    
    # Course units with progress (enhanced version)
    path(
        'courses/<uuid:course_id>/units-with-progress/', 
        views.get_units_with_progress, 
        name='course-units-with-progress'
    ),
    
    # Lesson detail for quiz page
    # Maps to getLesson query from client project
    path(
        'lessons/<uuid:lesson_id>/', 
        views.LessonDetailView.as_view(), 
        name='lesson-detail'
    ),
    
    # Lesson completion percentage
    path(
        'lessons/<uuid:lesson_id>/percentage/', 
        views.get_lesson_percentage, 
        name='lesson-percentage'
    ),
    
    # User progress management
    # Maps to getUserProgress query from client project
    path(
        'user-progress/', 
        views.UserProgressView.as_view(), 
        name='user-progress'
    ),
    
    # Challenge completion
    # Maps to upsertChallengeProgress action from client project
    path(
        'challenge-progress/', 
        views.ChallengeProgressView.as_view(), 
        name='challenge-progress'
    ),
    
    # Text answer validation for fill-blank challenges
    path(
        'validate-text-answer/',
        views.ValidateTextAnswerView.as_view(),
        name='validate-text-answer'
    ),
    
    # Hearts management
    # Maps to reduceHearts action from client project
    path(
        'reduce-hearts/', 
        views.ReduceHeartsView.as_view(), 
        name='reduce-hearts'
    ),
    
    # Hearts refill (premium feature)
    path(
        'refill-hearts/', 
        views.RefillHeartsView.as_view(), 
        name='refill-hearts'
    ),
    
    # ========================================================================
    # LEADERBOARD ENDPOINTS - Competition and ranking system
    # ========================================================================
    
    # Global leaderboard
    path(
        'leaderboard/global/', 
        views.get_global_leaderboard, 
        name='leaderboard-global'
    ),
    
    # Leagues information
    path(
        'leaderboard/leagues/', 
        views.get_leagues_info, 
        name='leaderboard-leagues'
    ),
    
    # Active competitions
    path(
        'leaderboard/competitions/', 
        views.get_active_competitions, 
        name='leaderboard-competitions'
    ),
    
    # User position in leaderboard
    path(
        'leaderboard/user-position/', 
        views.get_user_leaderboard_position, 
        name='leaderboard-user-position'
    ),
    
    # Join competition
    path(
        'leaderboard/competitions/<uuid:competition_id>/join/', 
        views.join_competition, 
        name='join-competition'
    ),
    
    # Update user streak
    path(
        'leaderboard/update-streak/', 
        views.update_user_streak, 
        name='update-user-streak'
    ),
    
    # ========================================================================
    # ACHIEVEMENT ENDPOINTS - Gamification and badge system
    # ========================================================================
    
    # Get user achievements with progress
    path(
        'achievements/',
        views.get_user_achievements,
        name='user-achievements'
    ),
    
    # Get achievement statistics
    path(
        'achievements/stats/',
        views.get_achievement_stats,
        name='achievement-stats'
    ),
    
    # Get achievement categories
    path(
        'achievements/categories/',
        views.get_achievement_categories,
        name='achievement-categories'
    ),
    
    # Get achievement notifications
    path(
        'achievements/notifications/',
        views.get_achievement_notifications,
        name='achievement-notifications'
    ),
    
    # Mark notification as read
    path(
        'achievements/notifications/<uuid:notification_id>/read/',
        views.mark_notification_read,
        name='mark-notification-read'
    ),
    
    # Mark achievement as celebrated
    path(
        'achievements/<uuid:achievement_id>/celebrate/',
        views.mark_achievement_celebrated,
        name='mark-achievement-celebrated'
    ),
    
    # ========================================================================
    # 🚀 VAPI AI CONVERSATION PRACTICE ENDPOINTS
    # ========================================================================
    # 
    # Note: Traditional speaking/listening endpoints removed in favor of unified
    # Vapi-based conversation practice which handles both speaking and listening
    # in a single, superior AI conversation experience.
    #
    # All speaking/listening functionality is now handled through:
    # - apps/practice/services/vapi_client.py
    # - apps/practice/services/conversation_ai.py  
    # - apps/practice/views/vapi_views.py
    # ========================================================================
    
    # Start Vapi conversation
    path(
        'conversations/start/',
        views.start_vapi_conversation,
        name='vapi-conversation-start'
    ),
    
    # End Vapi conversation with feedback
    path(
        'conversations/<str:conversation_id>/end/',
        views.end_vapi_conversation,
        name='vapi-conversation-end'
    ),
    
    # Get conversation feedback and analysis
    path(
        'conversations/<str:conversation_id>/feedback/',
        views.get_conversation_feedback,
        name='vapi-conversation-feedback'
    ),
    
    # AI Translation validation with detailed feedback
    path(
        'validate-ai-translation/',
        views.AITranslationValidationView.as_view(),
        name='validate-ai-translation'
    ),
    
    # AI Pronunciation analysis with detailed feedback
    path(
        'analyze-ai-pronunciation/',
        views.AIPronunciationAnalysisView.as_view(),
        name='analyze-ai-pronunciation'
    ),
]