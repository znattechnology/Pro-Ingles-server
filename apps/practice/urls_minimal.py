"""
Practice app URLs - Minimal endpoints for legacy compatibility.

Most functionality has been migrated to:
- apps/courses/api/student/practice_courses/ (student endpoints)
- apps/courses/api/teacher/practice_courses/ (teacher endpoints)

This file maintains:
1. Vapi integration endpoints
2. Teacher course creation (CreateCourseView)
3. Legacy compatibility routes
"""

from django.urls import path
from django.http import JsonResponse

# Import minimal teacher dashboard views
from .views_teacher_minimal import CoursesListView, get_practice_analytics

# Import course management view
from .views_course_management import PracticeCourseManagementView

# Import CreateCourseView from essential views (only view not in new API)
from .views_essential import CreateCourseView

# Import VAPI views
from .vapi_views import (
    VapiSessionView,
    vapi_templates,
    vapi_simulate,
    vapi_webhook,
    vapi_assistant_manager,
    vapi_session_summary,
    vapi_user_progress,
    vapi_complete_session,
    vapi_dashboard_analytics,
    # Quota management
    vapi_check_quota,
    vapi_quota_status,
    vapi_available_plans,
)

# Import shared views from the NEW API (avoiding duplication)
from apps.courses.api.student.practice_courses.views import (
    get_units_with_progress,
    PracticeUnitCreateView,
    PracticeUnitUpdateView,
    get_unit_lessons,
    PracticeLessonCreateView,
    PracticeLessonUpdateView,
    PracticeChallengeCreateView,
    PracticeChallengeUpdateView,
    # Upload views for audio/image
    GetAudioUploadUrlView,
    GetImageUploadUrlView,
    ChallengeOptionUpdateView,
    # Leaderboard views
    get_global_leaderboard,
    get_leagues_info,
    get_active_competitions,
    get_user_leaderboard_position,
    join_competition,
    update_user_streak,
)

# Import AI views from dedicated file (extracted from views.py)
from .views_ai import (
    GenerateReferenceAudioView,
    GeneratePronunciationExerciseView,
    GenerateTranslationSuggestionsView,
    AITranslationValidationView,
    AIPronunciationAnalysisView,
)

# Import Teacher Achievement Management views
from .views_teacher_achievements import (
    TeacherAchievementListCreateView,
    TeacherAchievementDetailView,
    teacher_achievement_stats,
    toggle_achievement_status,
    bulk_update_achievements,
    achievement_unlock_analytics,
)


def test_view(request):
    return JsonResponse({'status': 'OK', 'message': 'Backend funcionando!'})


def vapi_test(request):
    return JsonResponse({'vapi': 'ready', 'message': 'Vapi integration ready'})


app_name = 'practice'

urlpatterns = [
    # Basic test endpoints
    path('test/', test_view, name='test'),
    path('vapi/test/', vapi_test, name='vapi-test'),

    # Teacher dashboard endpoints
    path('courses/', CoursesListView.as_view(), name='courses-list'),
    path('analytics/', get_practice_analytics, name='analytics'),

    # Full Vapi integration endpoints
    path('vapi/session/', VapiSessionView.as_view(), name='vapi-session'),
    path('vapi/templates/', vapi_templates, name='vapi-templates'),
    path('vapi/simulate/', vapi_simulate, name='vapi-simulate'),
    path('vapi/webhook/', vapi_webhook, name='vapi-webhook'),
    path('vapi/assistants/', vapi_assistant_manager, name='vapi-assistants'),
    path('vapi/session/<str:session_id>/summary/', vapi_session_summary, name='vapi-session-summary'),

    # Progress tracking endpoints
    path('vapi/progress/', vapi_user_progress, name='vapi-user-progress'),
    path('vapi/complete/', vapi_complete_session, name='vapi-complete-session'),

    # Dashboard analytics
    path('vapi/dashboard/', vapi_dashboard_analytics, name='vapi-dashboard-analytics'),

    # Quota management endpoints
    path('vapi/quota/check/', vapi_check_quota, name='vapi-check-quota'),
    path('vapi/quota/status/', vapi_quota_status, name='vapi-quota-status'),
    path('vapi/quota/plans/', vapi_available_plans, name='vapi-available-plans'),

    # ========================================================================
    # TEACHER CRUD ENDPOINTS - Course, Unit, Lesson, Challenge management
    # ========================================================================

    # Course creation (from views_essential.py - only view not in new API)
    path('courses/create/', CreateCourseView.as_view(), name='courses-create'),
    path('courses/<uuid:course_id>/', PracticeCourseManagementView.as_view(), name='course-management'),
    path('courses/<uuid:course_id>/units-with-progress/', get_units_with_progress, name='course-units-with-progress'),

    # Units management (from new API)
    path('units/', PracticeUnitCreateView.as_view(), name='units-create'),
    path('units/<uuid:unit_id>/', PracticeUnitUpdateView.as_view(), name='units-update'),
    path('units/<uuid:unit_id>/lessons/', get_unit_lessons, name='unit-lessons'),

    # Lessons management (from new API)
    path('lessons/', PracticeLessonCreateView.as_view(), name='lessons-create'),
    path('lessons/<uuid:lesson_id>/', PracticeLessonUpdateView.as_view(), name='lessons-update'),

    # Challenges management (from new API)
    path('challenges/', PracticeChallengeCreateView.as_view(), name='challenges-create'),
    path('challenges/<uuid:challenge_id>/', PracticeChallengeUpdateView.as_view(), name='challenges-update'),

    # ========================================================================
    # MEDIA UPLOAD ENDPOINTS - Audio and Image uploads for challenges
    # ========================================================================

    # Audio upload for listening challenges
    path('challenges/<uuid:challenge_id>/get-audio-upload-url/', GetAudioUploadUrlView.as_view(), name='get-audio-upload-url'),

    # Image upload for challenges
    path('challenges/<uuid:challenge_id>/get-image-upload-url/', GetImageUploadUrlView.as_view(), name='get-image-upload-url'),

    # Challenge options update (for updating with S3 URLs after upload)
    path('challenge-options/<uuid:option_id>/', ChallengeOptionUpdateView.as_view(), name='challenge-options-update'),

    # ========================================================================
    # LEADERBOARD ENDPOINTS - Competition and ranking system (from new API)
    # ========================================================================

    path('leaderboard/global/', get_global_leaderboard, name='leaderboard-global'),
    path('leaderboard/leagues/', get_leagues_info, name='leaderboard-leagues'),
    path('leaderboard/competitions/', get_active_competitions, name='leaderboard-competitions'),
    path('leaderboard/user-position/', get_user_leaderboard_position, name='leaderboard-user-position'),
    path('leaderboard/competitions/<uuid:competition_id>/join/', join_competition, name='join-competition'),
    path('leaderboard/update-streak/', update_user_streak, name='update-user-streak'),

    # ========================================================================
    # AI PRONUNCIATION ENDPOINTS - TTS and pronunciation analysis
    # ========================================================================

    path('generate-reference-audio/', GenerateReferenceAudioView.as_view(), name='generate-reference-audio'),
    path('generate-pronunciation-exercise/', GeneratePronunciationExerciseView.as_view(), name='generate-pronunciation-exercise'),
    path('analyze-ai-pronunciation/', AIPronunciationAnalysisView.as_view(), name='analyze-ai-pronunciation'),

    # ========================================================================
    # AI TRANSLATION ENDPOINTS - Intelligent translation validation
    # ========================================================================

    path('generate-translation-suggestions/', GenerateTranslationSuggestionsView.as_view(), name='generate-translation-suggestions'),
    path('validate-ai-translation/', AITranslationValidationView.as_view(), name='validate-ai-translation'),

    # ========================================================================
    # TEACHER ACHIEVEMENT MANAGEMENT ENDPOINTS - CRUD for achievements
    # ========================================================================

    # List and create achievements
    path('teacher/achievements/', TeacherAchievementListCreateView.as_view(), name='teacher-achievements-list'),

    # Achievement statistics for dashboard
    path('teacher/achievements/stats/', teacher_achievement_stats, name='teacher-achievements-stats'),

    # Bulk operations (activate/deactivate/delete multiple)
    path('teacher/achievements/bulk-update/', bulk_update_achievements, name='teacher-achievements-bulk-update'),

    # Single achievement operations
    path('teacher/achievements/<uuid:pk>/', TeacherAchievementDetailView.as_view(), name='teacher-achievements-detail'),
    path('teacher/achievements/<uuid:achievement_id>/toggle-status/', toggle_achievement_status, name='teacher-achievements-toggle'),
    path('teacher/achievements/<uuid:achievement_id>/analytics/', achievement_unlock_analytics, name='teacher-achievements-analytics'),
]
