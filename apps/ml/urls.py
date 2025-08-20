from django.urls import path
from . import views

app_name = 'ml'

urlpatterns = [
    # ML Models
    path('models/', views.MLModelListView.as_view(), name='models-list'),
    path('models/<int:pk>/', views.MLModelDetailView.as_view(), name='models-detail'),
    
    # Recommendations
    path('recommendations/', views.UserRecommendationListView.as_view(), name='recommendations-list'),
    path('recommendations/<int:pk>/', views.UserRecommendationDetailView.as_view(), name='recommendations-detail'),
    path('recommendations/generate/', views.generate_recommendations, name='generate-recommendations'),
    path('recommendations/<int:recommendation_id>/viewed/', views.mark_recommendation_viewed, name='mark-viewed'),
    path('recommendations/<int:recommendation_id>/clicked/', views.mark_recommendation_clicked, name='mark-clicked'),
    path('recommendations/<int:recommendation_id>/converted/', views.mark_recommendation_converted, name='mark-converted'),
    
    # Sentiment Analysis
    path('sentiment/', views.SentimentAnalysisListView.as_view(), name='sentiment-list'),
    path('sentiment/analyze/', views.analyze_text_sentiment, name='analyze-sentiment'),
    
    # Churn Prediction
    path('churn/', views.ChurnPredictionListView.as_view(), name='churn-list'),
    path('churn/<int:pk>/', views.ChurnPredictionDetailView.as_view(), name='churn-detail'),
    path('churn/predict/', views.predict_churn, name='predict-churn'),
    
    # Statistics
    path('stats/', views.ml_stats, name='ml-stats'),
]