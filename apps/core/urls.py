"""
Core URLs - Health Checks e Endpoints do Sistema
"""

from django.urls import path
from . import health

app_name = 'core'

urlpatterns = [
    # Health Check Endpoints para Kubernetes
    path('health/', health.health_check, name='health_check'),
    path('ready/', health.readiness_check, name='readiness_check'),  
    path('live/', health.liveness_check, name='liveness_check'),
    
    # Metrics para Prometheus
    path('metrics/', health.metrics, name='metrics'),
    
    # Debug Info (apenas para desenvolvimento)
    path('debug/', health.debug_info, name='debug_info'),
]