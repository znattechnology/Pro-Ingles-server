"""
URL configuration for ProEnglish Platform.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Health Check endpoints
    path('api/', include('apps.core.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path('api/v1/users/', include('apps.users.urls')),
    
    # Admin APIs
    path('api/v1/admin/', include('apps.platform_admin.urls')),
    
    # Student APIs (organized)
    path('api/v1/student/video-courses/', include('apps.courses.api.student.video_courses.urls')),
    path('api/v1/student/practice-courses/', include('apps.courses.api.student.practice_courses.urls')),
    
    # Teacher APIs (organized)
    path('api/v1/teacher/video-courses/', include('apps.courses.api.teacher.video_courses.urls')),
    path('api/v1/teacher/practice-courses/', include('apps.courses.api.teacher.practice_courses.urls')),
    
    # Legacy endpoints (for backward compatibility)
    path('api/v1/courses/', include('apps.courses.urls')),
    path('api/v1/practice/', include('apps.practice.urls_minimal')),
    
    # Other endpoints
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/cms/', include('apps.cms.urls')),

    # Chatbot (public, no auth required)
    path('api/chatbot/', include('apps.chatbot.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
