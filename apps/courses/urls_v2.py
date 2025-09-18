"""
URL configuration for courses app - API Version 2.

This module defines all URL patterns for course-related endpoints in API v2,
including new features like resources, quizzes, and enhanced functionality.
"""

from django.urls import path
from . import views

app_name = 'courses_v2'

urlpatterns = [
    # Course management - enhanced with v2 features
    path('', views.CourseListCreateView.as_view(), name='course_list_create'),
    path('<uuid:courseId>/', views.CourseDetailView.as_view(), name='course_detail'),
    
    # Course sections - enhanced with better organization
    path('<uuid:courseId>/sections/', views.CourseSectionListCreateView.as_view(), name='section_list_create'),
    path('sections/<uuid:sectionId>/', views.CourseSectionDetailView.as_view(), name='section_detail'),
    
    # Course chapters - enhanced with resources and quizzes
    path('sections/<uuid:sectionId>/chapters/', views.ChapterListCreateView.as_view(), name='chapter_list_create'),
    path('chapters/<uuid:chapterId>/', views.ChapterDetailView.as_view(), name='chapter_detail'),
    
    # Chapter comments - enhanced with threading and moderation
    path('chapters/<uuid:chapterId>/comments/', views.ChapterCommentListCreateView.as_view(), name='chapter_comments'),
    
    # 🆕 NEW IN V2: Chapter Resources
    path('chapters/<uuid:chapterId>/resources/', 
         views.ChapterResourceListCreateView.as_view(), name='chapter_resources'),
    path('chapters/<uuid:chapterId>/resources/<uuid:resourceId>/', 
         views.ChapterResourceDetailView.as_view(), name='chapter_resource_detail'),
    
    # 🆕 NEW IN V2: Chapter Quizzes
    path('chapters/<uuid:chapterId>/quiz/', 
         views.ChapterQuizListCreateView.as_view(), name='chapter_quiz'),
    path('chapters/<uuid:chapterId>/quiz/<uuid:quizId>/', 
         views.ChapterQuizDetailView.as_view(), name='chapter_quiz_detail'),
    
    # 🆕 NEW IN V2: Quiz Attempts and Analytics
    path('chapters/<uuid:chapterId>/quiz/attempts/', 
         views.StudentQuizAttemptListCreateView.as_view(), name='quiz_attempts'),
    path('chapters/<uuid:chapterId>/quiz/summary/', 
         views.get_student_quiz_summary, name='quiz_summary'),
    
    # Transactions - enhanced with better tracking
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.create_transaction, name='transaction_create'),
    
    # 🆕 NEW IN V2: Enhanced User Progress Tracking
    path('users/<uuid:userId>/enrolled/', views.get_user_enrolled_courses, name='user_enrolled_courses'),
    path('users/<uuid:userId>/progress/<uuid:courseId>/', views.get_user_course_progress, name='user_course_progress'),
    path('users/<uuid:userId>/progress/<uuid:courseId>/update/', views.update_user_course_progress, name='update_user_course_progress'),
    
    # Enhanced payments with Stripe
    path('payments/stripe/intent/', views.create_stripe_payment_intent, name='stripe_payment_intent'),
    
    # Enhanced file uploads
    path('<uuid:courseId>/sections/<uuid:sectionId>/chapters/<uuid:chapterId>/get-upload-url/', 
         views.get_upload_video_url, name='get_upload_video_url'),
    path('<uuid:courseId>/upload-image/', views.upload_course_image, name='upload_course_image'),
]