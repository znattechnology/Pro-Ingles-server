"""
URL configuration for teacher video courses API.

This module defines URL patterns for teacher video course management,
maintaining the same structure and response format as the Express API.
"""

from django.urls import path
from . import views

app_name = 'teacher_video_courses'

urlpatterns = [
    # Course management for teachers
    path('', views.CourseListCreateView.as_view(), name='course_list'),
    path('<uuid:courseId>/', views.CourseDetailView.as_view(), name='course_detail'),
    
    # Course sections (for teachers)
    path('<uuid:courseId>/sections/', views.CourseSectionListCreateView.as_view(), name='section_list'),
    path('sections/<uuid:sectionId>/', views.CourseSectionDetailView.as_view(), name='section_detail'),
    
    # Course chapters (for teachers)
    path('sections/<uuid:sectionId>/chapters/', views.ChapterListCreateView.as_view(), name='chapter_list'),
    path('chapters/<uuid:chapterId>/', views.ChapterDetailView.as_view(), name='chapter_detail'),
    
    # Chapter comments
    path('chapters/<uuid:chapterId>/comments/', views.ChapterCommentListCreateView.as_view(), name='chapter_comments'),
    
    # Transactions (Teachers can view transaction lists for their courses)
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    
    # Chapter resources (for teachers)
    path('chapters/<uuid:chapterId>/resources/', 
         views.ChapterResourceListCreateView.as_view(), name='chapter_resources'),
    path('chapters/<uuid:chapterId>/resources/<uuid:resourceId>/', 
         views.ChapterResourceDetailView.as_view(), name='chapter_resource_detail'),
    
    # Chapter quizzes (for teachers)
    path('chapters/<uuid:chapterId>/quiz/', 
         views.ChapterQuizListCreateView.as_view(), name='chapter_quiz'),
    path('chapters/<uuid:chapterId>/quiz/<uuid:quizId>/', 
         views.ChapterQuizDetailView.as_view(), name='chapter_quiz_detail'),
    
    # Quiz attempts and summaries moved to student API
]