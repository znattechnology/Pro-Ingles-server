"""
Practice app URLs - Full Vapi integration with minimal teacher dashboard endpoints.
"""

from django.urls import path
from django.http import JsonResponse

# Import VAPI views from views/ directory
from .views.vapi_views import (
    VapiSessionView,
    vapi_templates,
    vapi_simulate,
    vapi_webhook,
    vapi_assistant_manager,
    vapi_session_summary,
    vapi_user_progress,
    vapi_complete_session,
    vapi_dashboard_analytics
)

# Import minimal teacher dashboard views
from .views_teacher_minimal import CoursesListView, get_practice_analytics


def test_view(request):
    return JsonResponse({'status': 'OK', 'message': 'Backend funcionando!'})


def vapi_test(request):
    return JsonResponse({'vapi': 'ready', 'message': 'Vapi integration ready'})


app_name = 'practice'

urlpatterns = [
    # Basic test endpoints
    path('test/', test_view, name='test'),
    path('vapi/test/', vapi_test, name='vapi-test'),

    # Teacher dashboard endpoints (minimal - only what's needed)
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

    # Comprehensive dashboard analytics (for sidebar progress page)
    path('vapi/dashboard/', vapi_dashboard_analytics, name='vapi-dashboard-analytics'),
]
