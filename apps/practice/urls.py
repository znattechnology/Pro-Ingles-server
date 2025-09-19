"""
Practice Lab URLs - URL routing

URL patterns for the Practice Lab API endpoints.
Maps client project routes to Django views.
"""

from django.urls import path
from . import views

app_name = 'practice'

urlpatterns = [
    # List all courses
    path(
        'courses/', 
        views.CoursesListView.as_view(), 
        name='courses-list'
    ),
    
    # Create new course (redirect to main courses app)
    path(
        'courses/create/', 
        views.CreateCourseView.as_view(), 
        name='courses-create'
    ),
    
    # Course management (delete/publish/unpublish)
    path(
        'courses/<uuid:course_id>/', 
        views.PracticeCourseManagementView.as_view(), 
        name='course-management'
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
    # TEACHER MANAGEMENT ENDPOINTS - CRUD operations for practice content
    # ========================================================================
    
    # Units management
    path(
        'units/', 
        views.PracticeUnitCreateView.as_view(), 
        name='units-create'
    ),
    path(
        'units/<uuid:unit_id>/', 
        views.PracticeUnitUpdateView.as_view(), 
        name='units-update'
    ),
    path(
        'units/<uuid:unit_id>/lessons/', 
        views.get_unit_lessons, 
        name='unit-lessons'
    ),
    
    # Lessons management
    path(
        'lessons/', 
        views.PracticeLessonCreateView.as_view(), 
        name='lessons-create'
    ),
    path(
        'lessons/<uuid:lesson_id>/update/', 
        views.PracticeLessonUpdateView.as_view(), 
        name='lessons-update'
    ),
    
    # Challenges management
    path(
        'challenges/', 
        views.PracticeChallengeCreateView.as_view(), 
        name='challenges-create'
    ),
    path(
        'challenges/<uuid:challenge_id>/', 
        views.PracticeChallengeUpdateView.as_view(), 
        name='challenges-update'
    ),
    
    # Audio upload for listening challenges
    path(
        'challenges/<uuid:challenge_id>/get-audio-upload-url/',
        views.GetAudioUploadUrlView.as_view(),
        name='get-audio-upload-url'
    ),
    
    # Image upload for listening challenges
    path(
        'challenges/<uuid:challenge_id>/get-image-upload-url/',
        views.GetImageUploadUrlView.as_view(),
        name='get-image-upload-url'
    ),
    
    # Challenge options management
    path(
        'challenge-options/', 
        views.ChallengeOptionCreateView.as_view(), 
        name='challenge-options-create'
    ),
    path(
        'challenge-options/<uuid:option_id>/', 
        views.ChallengeOptionUpdateView.as_view(), 
        name='challenge-options-update'
    ),
    
    # Analytics endpoints for teacher dashboard
    path(
        'analytics/', 
        views.get_practice_analytics, 
        name='analytics'
    ),
    path(
        'student-progress/', 
        views.get_student_progress_list, 
        name='student-progress-list'
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
    
    # Create leaderboard snapshot
    path(
        'leaderboard/snapshot/', 
        views.LeaderboardSnapshotCreateView.as_view(), 
        name='leaderboard-snapshot'
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
    # AI SPEAKING PRACTICE ENDPOINTS - AI-powered conversation and pronunciation
    # ========================================================================
    
    # Speaking exercises
    path(
        'speaking/exercises/',
        views.SpeakingExerciseListView.as_view(),
        name='speaking-exercises-list'
    ),
    path(
        'speaking/exercises/<uuid:pk>/',
        views.SpeakingExerciseDetailView.as_view(),
        name='speaking-exercises-detail'
    ),
    
    # Speaking sessions
    path(
        'speaking/sessions/',
        views.SpeakingSessionListView.as_view(),
        name='speaking-sessions-list'
    ),
    path(
        'speaking/sessions/create/',
        views.SpeakingSessionCreateView.as_view(),
        name='speaking-sessions-create'
    ),
    path(
        'speaking/sessions/<uuid:pk>/',
        views.SpeakingSessionDetailView.as_view(),
        name='speaking-sessions-detail'
    ),
    path(
        'speaking/sessions/<uuid:session_id>/complete/',
        views.complete_speaking_session,
        name='speaking-sessions-complete'
    ),
    
    # Speaking turns
    path(
        'speaking/turns/',
        views.SpeakingTurnCreateView.as_view(),
        name='speaking-turns-create'
    ),
    
    # Speech analysis
    path(
        'speaking/analyze/',
        views.analyze_speech,
        name='speaking-analyze'
    ),
    
    # Progress and statistics
    path(
        'speaking/progress/',
        views.speaking_progress_stats,
        name='speaking-progress'
    ),
    path(
        'speaking/dashboard/',
        views.speaking_dashboard_stats,
        name='speaking-dashboard'
    ),
    
    # TTS generation
    path(
        'speaking/tts/',
        views.generate_tts_audio,
        name='speaking-tts'
    ),
    
    # ========================================================================
    # AI LISTENING PRACTICE ENDPOINTS - AI-powered comprehension and analysis
    # ========================================================================
    
    # Listening exercises
    path(
        'listening/exercises/',
        views.ListeningExerciseListView.as_view(),
        name='listening-exercises-list'
    ),
    path(
        'listening/exercises/<uuid:id>/',
        views.ListeningExerciseDetailView.as_view(),
        name='listening-exercises-detail'
    ),
    
    # Listening sessions
    path(
        'listening/sessions/',
        views.ListeningSessionCreateView.as_view(),
        name='listening-sessions-create'
    ),
    path(
        'listening/sessions/<uuid:id>/',
        views.ListeningSessionDetailView.as_view(),
        name='listening-sessions-detail'
    ),
    path(
        'listening/sessions/<uuid:session_id>/complete/',
        views.complete_listening_session,
        name='listening-sessions-complete'
    ),
    
    # Listening attempts
    path(
        'listening/attempts/',
        views.ListeningAttemptCreateView.as_view(),
        name='listening-attempts-create'
    ),
    
    # Listening analysis
    path(
        'listening/analyze/',
        views.analyze_listening_comprehension,
        name='listening-analyze'
    ),
    
    # Progress and statistics
    path(
        'listening/progress/',
        views.get_listening_progress,
        name='listening-progress'
    ),
    path(
        'listening/stats/',
        views.get_listening_stats,
        name='listening-stats'
    ),
    
    # ========================================================================
    # AI TRANSLATION ENDPOINTS - Intelligent translation validation
    # ========================================================================
    
    # AI-powered translation validation with detailed feedback
    path(
        'validate-ai-translation/',
        views.AITranslationValidationView.as_view(),
        name='validate-ai-translation'
    ),
    
    # Generate multiple correct translation alternatives for teachers
    path(
        'generate-translation-suggestions/',
        views.GenerateTranslationSuggestionsView.as_view(),
        name='generate-translation-suggestions'
    ),
    
    # Generate complete translation exercises with AI
    path(
        'generate-translation-exercise/',
        views.GenerateTranslationExerciseView.as_view(),
        name='generate-translation-exercise'
    ),
    
    # ========================================================================
    # AI PRONUNCIATION ENDPOINTS - Intelligent pronunciation analysis
    # ========================================================================
    
    # AI-powered pronunciation analysis with detailed feedback
    path(
        'analyze-ai-pronunciation/',
        views.AIPronunciationAnalysisView.as_view(),
        name='analyze-ai-pronunciation'
    ),
    
    # Generate pronunciation exercises with AI
    path(
        'generate-pronunciation-exercise/',
        views.GeneratePronunciationExerciseView.as_view(),
        name='generate-pronunciation-exercise'
    ),
    
    # Generate reference audio for pronunciation practice
    path(
        'generate-reference-audio/',
        views.GenerateReferenceAudioView.as_view(),
        name='generate-reference-audio'
    ),
    
    # ========================================================================
    # 🆕 COURSE-SPECIFIC PRACTICE ENDPOINTS - Práticas contextualizadas por curso
    # ========================================================================
    
    # Speaking exercises for specific course
    path(
        'courses/<uuid:course_id>/speaking/',
        views.CourseSpeakingExercisesView.as_view(),
        name='course-speaking-exercises'
    ),
    
    # Listening exercises for specific course
    path(
        'courses/<uuid:course_id>/listening/',
        views.CourseListeningExercisesView.as_view(),
        name='course-listening-exercises'
    ),
    
    # Practice progress for specific course
    path(
        'courses/<uuid:course_id>/progress/',
        views.CoursePracticeProgressView.as_view(),
        name='course-practice-progress'
    ),
    
    # ========================================================================
    # TEACHER ACHIEVEMENT MANAGEMENT ENDPOINTS
    # ========================================================================
    
    # List and create achievements (Teacher only)
    path(
        'teacher/achievements/',
        views.TeacherAchievementListCreateView.as_view(),
        name='teacher-achievements-list-create'
    ),
    
    # Update/delete specific achievement (Teacher only)
    path(
        'teacher/achievements/<uuid:pk>/',
        views.TeacherAchievementDetailView.as_view(),
        name='teacher-achievement-detail'
    ),
    
    # Achievement statistics for teacher dashboard
    path(
        'teacher/achievements/stats/',
        views.teacher_achievement_stats,
        name='teacher-achievement-stats'
    ),
    
    # Toggle achievement active/inactive status
    path(
        'teacher/achievements/<uuid:achievement_id>/toggle-status/',
        views.toggle_achievement_status,
        name='toggle-achievement-status'
    ),
    
    # Bulk operations on achievements
    path(
        'teacher/achievements/bulk-update/',
        views.bulk_update_achievements,
        name='bulk-update-achievements'
    ),
    
    # Achievement unlock analytics
    path(
        'teacher/achievements/<uuid:achievement_id>/analytics/',
        views.achievement_unlock_analytics,
        name='achievement-unlock-analytics'
    ),
    
    # ========================================================================
    # STUDENT ACHIEVEMENT ENDPOINTS
    # ========================================================================
    
    # List user achievements with progress
    path(
        'achievements/',
        views.StudentAchievementListView.as_view(),
        name='student-achievements-list'
    ),
    
    # Achievement statistics for student
    path(
        'achievements/stats/',
        views.student_achievement_stats,
        name='student-achievement-stats'
    ),
    
    # Achievement categories for student
    path(
        'achievements/categories/',
        views.student_achievement_categories,
        name='student-achievement-categories'
    ),
    
    # Achievement notifications for student
    path(
        'achievements/notifications/',
        views.student_achievement_notifications,
        name='student-achievement-notifications'
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
]