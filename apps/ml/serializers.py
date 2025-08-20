"""
Serializers for ML models.
"""

from rest_framework import serializers
from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction


class MLModelSerializer(serializers.ModelSerializer):
    """ML Model serializer."""
    
    training_duration_str = serializers.SerializerMethodField()
    
    class Meta:
        model = MLModel
        fields = [
            'id', 'name', 'display_name', 'model_type', 'version',
            'description', 'algorithm', 'features', 'hyperparameters',
            'accuracy', 'precision', 'recall', 'f1_score',
            'training_data_size', 'training_started', 'training_completed',
            'training_duration', 'training_duration_str',
            'status', 'is_production', 'deployed_at',
            'prediction_count', 'last_used',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'prediction_count', 'last_used']
    
    def get_training_duration_str(self, obj):
        """Get training duration as human-readable string."""
        if obj.training_duration:
            total_seconds = obj.training_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None


class UserRecommendationSerializer(serializers.ModelSerializer):
    """User recommendation serializer."""
    
    model_name = serializers.CharField(source='model.display_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = UserRecommendation
        fields = [
            'id', 'user', 'user_email', 'recommendation_type',
            'item_id', 'item_type', 'title', 'description',
            'confidence_score', 'relevance_score',
            'recommendation_context', 'features_used',
            'viewed', 'clicked', 'converted',
            'viewed_at', 'clicked_at', 'converted_at',
            'model', 'model_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_email', 'model_name']


class UserRecommendationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user recommendation interactions."""
    
    class Meta:
        model = UserRecommendation
        fields = ['viewed', 'clicked', 'converted']


class SentimentAnalysisSerializer(serializers.ModelSerializer):
    """Sentiment analysis serializer."""
    
    model_name = serializers.CharField(source='model.display_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    sentiment_display = serializers.CharField(source='get_sentiment_display', read_only=True)
    
    class Meta:
        model = SentimentAnalysis
        fields = [
            'id', 'content_type', 'content_id', 'text_content',
            'sentiment', 'sentiment_display', 'confidence_score',
            'positive_score', 'negative_score', 'neutral_score',
            'keywords', 'emotions',
            'user', 'user_email', 'model', 'model_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_email', 'model_name', 'sentiment_display']


class SentimentAnalysisCreateSerializer(serializers.Serializer):
    """Serializer for creating sentiment analysis."""
    
    text = serializers.CharField(min_length=10, max_length=5000)
    content_type = serializers.ChoiceField(
        choices=SentimentAnalysis.CONTENT_TYPES,
        default='review'
    )
    content_id = serializers.CharField(max_length=100, required=False, allow_blank=True)


class ChurnPredictionSerializer(serializers.ModelSerializer):
    """Churn prediction serializer."""
    
    model_name = serializers.CharField(source='model.display_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = ChurnPrediction
        fields = [
            'id', 'user', 'user_email',
            'churn_probability', 'risk_level', 'risk_level_display',
            'churn_factors', 'feature_importance', 'retention_actions',
            'actual_churned', 'retention_action_taken',
            'model', 'model_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_email', 'model_name', 'risk_level_display']


class RecommendationRequestSerializer(serializers.Serializer):
    """Serializer for recommendation requests."""
    
    recommendation_type = serializers.ChoiceField(
        choices=UserRecommendation.RECOMMENDATION_TYPES,
        default='braider'
    )
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class ChurnPredictionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating churn prediction outcomes."""
    
    class Meta:
        model = ChurnPrediction
        fields = ['actual_churned', 'retention_action_taken']