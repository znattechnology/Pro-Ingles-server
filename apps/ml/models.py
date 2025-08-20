"""
Machine Learning models for AI-powered features.
"""

import json
import pickle
import base64
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel

User = get_user_model()


class MLModel(BaseModel):
    """ML models registry and management."""
    
    MODEL_TYPES = [
        ('recommendation', 'Recommendation Engine'),
        ('sentiment', 'Sentiment Analysis'),
        ('fraud_detection', 'Fraud Detection'),
        ('demand_forecasting', 'Demand Forecasting'),
        ('price_optimization', 'Price Optimization'),
        ('churn_prediction', 'Churn Prediction'),
        ('clustering', 'User Clustering'),
        ('chatbot', 'Chatbot NLP'),
        ('personalization', 'Content Personalization'),
    ]
    
    STATUS_CHOICES = [
        ('training', 'Training'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    version = models.CharField(max_length=20, default='1.0')
    
    # Model metadata
    description = models.TextField(blank=True)
    algorithm = models.CharField(max_length=100, blank=True)
    features = models.JSONField(default=list, help_text="List of features used")
    hyperparameters = models.JSONField(default=dict, help_text="Model hyperparameters")
    
    # Model binary data (base64 encoded)
    model_data = models.TextField(blank=True, help_text="Serialized model")
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    precision = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    recall = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    f1_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Training info
    training_data_size = models.PositiveIntegerField(null=True, blank=True)
    training_started = models.DateTimeField(null=True, blank=True)
    training_completed = models.DateTimeField(null=True, blank=True)
    training_duration = models.DurationField(null=True, blank=True)
    
    # Status and deployment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='training')
    is_production = models.BooleanField(default=False)
    deployed_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    prediction_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_type', 'status']),
            models.Index(fields=['status', 'is_production']),
        ]
    
    def __str__(self):
        return f"{self.display_name} v{self.version}"
    
    def save_model(self, model_object):
        """Save sklearn/tensorflow model as base64 string."""
        model_bytes = pickle.dumps(model_object)
        self.model_data = base64.b64encode(model_bytes).decode()
        self.save()
    
    def load_model(self):
        """Load model from base64 string."""
        if not self.model_data:
            return None
        
        model_bytes = base64.b64decode(self.model_data.encode())
        return pickle.loads(model_bytes)
    
    def increment_usage(self):
        """Increment prediction counter."""
        self.prediction_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['prediction_count', 'last_used'])


class UserRecommendation(BaseModel):
    """User-specific recommendations."""
    
    RECOMMENDATION_TYPES = [
        ('braider', 'Braider Recommendation'),
        ('service', 'Service Recommendation'),
        ('product', 'Product Recommendation'),
        ('content', 'Content Recommendation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    
    # Recommendation details
    item_id = models.CharField(max_length=100, help_text="ID of recommended item")
    item_type = models.CharField(max_length=50, help_text="Type of recommended item")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scoring
    confidence_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    relevance_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Context
    recommendation_context = models.JSONField(default=dict, help_text="Context that generated recommendation")
    features_used = models.JSONField(default=list, help_text="Features used for this recommendation")
    
    # Interaction tracking
    viewed = models.BooleanField(default=False)
    clicked = models.BooleanField(default=False)
    converted = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    # Model reference
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='recommendations')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'recommendation_type']),
            models.Index(fields=['user', '-confidence_score']),
            models.Index(fields=['item_id', 'item_type']),
        ]
    
    def __str__(self):
        return f"{self.title} for {self.user.email}"


class SentimentAnalysis(BaseModel):
    """Sentiment analysis results for text content."""
    
    CONTENT_TYPES = [
        ('review', 'User Review'),
        ('comment', 'Comment'),
        ('message', 'Chat Message'),
        ('feedback', 'Feedback'),
        ('social_post', 'Social Media Post'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.CharField(max_length=100, help_text="ID of analyzed content")
    text_content = models.TextField()
    
    # Sentiment results
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    confidence_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Detailed scores
    positive_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    negative_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    neutral_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Additional analysis
    keywords = models.JSONField(default=list, help_text="Key phrases extracted")
    emotions = models.JSONField(default=dict, help_text="Emotion detection results")
    
    # Context
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='sentiment_analyses')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'sentiment']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['sentiment', '-confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.sentiment.title()} sentiment ({self.confidence_score:.2f})"


class ChurnPrediction(BaseModel):
    """Customer churn prediction results."""
    
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='churn_predictions')
    
    # Prediction results
    churn_probability = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    
    # Contributing factors
    churn_factors = models.JSONField(default=list, help_text="Factors contributing to churn risk")
    feature_importance = models.JSONField(default=dict, help_text="Feature importance scores")
    
    # Retention recommendations
    retention_actions = models.JSONField(default=list, help_text="Recommended retention actions")
    
    # Outcome tracking
    actual_churned = models.BooleanField(null=True, blank=True)
    retention_action_taken = models.CharField(max_length=200, blank=True)
    
    # Model reference
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='churn_predictions')
    
    class Meta:
        ordering = ['-churn_probability']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['risk_level', '-churn_probability']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.churn_probability:.2f} churn risk"
