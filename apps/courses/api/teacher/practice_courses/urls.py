"""
URL configuration for teacher practice courses API.
Redirects to practice app endpoints.
"""

from django.urls import path, include

app_name = 'teacher_practice_courses'

# Redirect to practice app URLs - the practice app already handles course management
urlpatterns = [
    path('', include('apps.practice.urls')),
]