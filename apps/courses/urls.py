"""
URL configuration for courses app with versioning support.

This module defines URL patterns with version routing for backward compatibility
and API evolution. Maintains Express API compatibility in v1 while adding
new features in v2.
"""

from django.urls import path, include
from . import views

app_name = 'courses'

# Version-specific URL patterns
urlpatterns = [
    # API v1 - Backward compatibility with original Express API
    path('v1/', include('apps.courses.urls_v1', namespace='v1')),
    
    # API v2 - Enhanced features and new functionality
    path('v2/', include('apps.courses.urls_v2', namespace='v2')),
    
    # Default routes (v1 for backward compatibility)
    # These maintain compatibility with existing frontend code
    
    # Course management - matches Express /courses endpoints
    path('', views.CourseListCreateView.as_view(), name='course_list_create'),
    path('<uuid:courseId>/', views.CourseDetailView.as_view(), name='course_detail'),
    
    # Course sections - for course management
    path('<uuid:courseId>/sections/', views.CourseSectionListCreateView.as_view(), name='section_list_create'),
    path('sections/<uuid:sectionId>/', views.CourseSectionDetailView.as_view(), name='section_detail'),
    
    # Course chapters - for course management
    path('sections/<uuid:sectionId>/chapters/', views.ChapterListCreateView.as_view(), name='chapter_list_create'),
    path('chapters/<uuid:chapterId>/', views.ChapterDetailView.as_view(), name='chapter_detail'),
    
    # Chapter comments
    path('chapters/<uuid:chapterId>/comments/', views.ChapterCommentListCreateView.as_view(), name='chapter_comments'),
    
    # Transactions - matches Express /transactions endpoints
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.create_transaction, name='transaction_create'),
    
    # User course progress - matches Express /users/course-progress endpoints
    path('users/<uuid:userId>/enrolled/', views.get_user_enrolled_courses, name='user_enrolled_courses'),
    path('users/<uuid:userId>/progress/<uuid:courseId>/', views.get_user_course_progress, name='user_course_progress'),
    path('users/<uuid:userId>/progress/<uuid:courseId>/update/', views.update_user_course_progress, name='update_user_course_progress'),
    
    # Stripe payments - matches Express /transactions/stripe-payment-intent
    path('payments/stripe/intent/', views.create_stripe_payment_intent, name='stripe_payment_intent'),
    
    # Video upload - matches Express /:courseId/sections/:sectionId/chapters/:chapterId/get-upload-url
    path('<uuid:courseId>/sections/<uuid:sectionId>/chapters/<uuid:chapterId>/get-upload-url/', 
         views.get_upload_video_url, name='get_upload_video_url'),
    
    # Image upload for course cover
    path('<uuid:courseId>/upload-image/', views.upload_course_image, name='upload_course_image'),
    
    # Chapter resources (Phase 1 Bridge - maintained for compatibility)
    path('chapters/<uuid:chapterId>/resources/', 
         views.ChapterResourceListCreateView.as_view(), name='chapter_resources'),
    path('chapters/<uuid:chapterId>/resources/<uuid:resourceId>/', 
         views.ChapterResourceDetailView.as_view(), name='chapter_resource_detail'),
    
    # Chapter quizzes (Phase 1 Bridge - maintained for compatibility)
    path('chapters/<uuid:chapterId>/quiz/', 
         views.ChapterQuizListCreateView.as_view(), name='chapter_quiz'),
    path('chapters/<uuid:chapterId>/quiz/<uuid:quizId>/', 
         views.ChapterQuizDetailView.as_view(), name='chapter_quiz_detail'),
    
    # Quiz attempts (Phase 1 Bridge - maintained for compatibility)
    path('chapters/<uuid:chapterId>/quiz/attempts/', 
         views.StudentQuizAttemptListCreateView.as_view(), name='quiz_attempts'),
    path('chapters/<uuid:chapterId>/quiz/summary/', 
         views.get_student_quiz_summary, name='quiz_summary'),
]

