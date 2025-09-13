from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'settings', views.LandingPageSettingsViewSet)
router.register(r'hero', views.HeroSectionViewSet)
router.register(r'stats', views.StatItemViewSet)
router.register(r'companies', views.CompanyViewSet)
router.register(r'services', views.ServiceItemViewSet)
router.register(r'pricing', views.PricingTierViewSet)
router.register(r'features', views.FeatureViewSet)
router.register(r'testimonials', views.TestimonialViewSet)
router.register(r'faqs', views.FAQItemViewSet)
router.register(r'ctas', views.CallToActionViewSet)
router.register(r'seo', views.SeoSettingsViewSet)

# Custom URL patterns
urlpatterns = [
    # Router URLs (CRUD endpoints)
    path('', include(router.urls)),
    
    # Custom endpoints
    path('landing-page-data/', views.landing_page_data, name='landing-page-data'),
    path('clear-cache/', views.clear_cache, name='clear-cache'),
    path('stats-summary/', views.landing_page_stats, name='stats-summary'),
    path('health/', views.health_check, name='health-check'),
    path('preview/', views.preview_changes, name='preview-changes'),
]

app_name = 'cms'