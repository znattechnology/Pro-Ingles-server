"""
Admin API URLs for ProEnglish Platform

Endpoints específicos para administradores:
- /admin/dashboard/ - Dashboard principal com estatísticas agregadas
- /admin/users/ - Gestão de utilizadores
- /admin/stats/ - Estatísticas detalhadas
- /admin/system/health/ - Saúde do sistema
"""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Gestão de utilizadores
    path('users/', views.admin_users_list, name='admin_users_list'),
    path('users/<str:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('users/<str:user_id>/status/', views.admin_user_status, name='admin_user_status'),
    path('users/<str:user_id>/role/', views.admin_user_role, name='admin_user_role'),
    path('users/<str:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    
    # Estatísticas
    path('stats/', views.admin_stats, name='admin_stats'),
    
    # Sistema
    path('system/health/', views.admin_system_health, name='admin_system_health'),
]