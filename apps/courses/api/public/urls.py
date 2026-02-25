"""
URL configuration for public certificate verification API.

These endpoints are publicly accessible without authentication.
"""

from django.urls import path
from . import views

app_name = 'public_certificates'

urlpatterns = [
    # Certificate verification (public)
    path('verify/<str:verification_code>/', views.verify_certificate, name='verify_certificate'),
]
