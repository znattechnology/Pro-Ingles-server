from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('providers/', views.IntegrationProviderListView.as_view(), name='providers'),
    path('sms/send/', views.send_sms_view, name='send-sms'),
    path('geocode/', views.geocode_view, name='geocode'),
    path('stats/', views.integration_stats, name='stats'),
]