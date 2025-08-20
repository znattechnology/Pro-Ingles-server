"""
Views for ML and AI features.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.rate_limiting import rate_limit_ml, rate_limit_moderate

from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction
from .serializers import (
    MLModelSerializer, UserRecommendationSerializer, UserRecommendationUpdateSerializer,
    SentimentAnalysisSerializer, SentimentAnalysisCreateSerializer,
    ChurnPredictionSerializer, ChurnPredictionUpdateSerializer,
    RecommendationRequestSerializer
)
from .services import get_user_recommendations, analyze_sentiment, predict_user_churn

User = get_user_model()


class MLModelListView(generics.ListAPIView):
    """List all ML models."""
    
    queryset = MLModel.objects.filter(status='active')
    serializer_class = MLModelSerializer
    permission_classes = [permissions.IsAuthenticated]


class MLModelDetailView(generics.RetrieveAPIView):
    """Get ML model details."""
    
    queryset = MLModel.objects.all()
    serializer_class = MLModelSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserRecommendationListView(generics.ListAPIView):
    """List user recommendations."""
    
    serializer_class = UserRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRecommendation.objects.filter(user=self.request.user).order_by('-created_at')


class UserRecommendationDetailView(generics.RetrieveUpdateAPIView):
    """Get and update user recommendation."""
    
    serializer_class = UserRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRecommendation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserRecommendationUpdateSerializer
        return UserRecommendationSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@rate_limit_ml
def generate_recommendations(request):
    """Generate recommendations for user."""
    serializer = RecommendationRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        recommendation_type = serializer.validated_data['recommendation_type']
        limit = serializer.validated_data['limit']
        
        recommendations = get_user_recommendations(
            user=request.user,
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        response_serializer = UserRecommendationSerializer(recommendations, many=True)
        return Response({
            'recommendations': response_serializer.data,
            'count': len(recommendations)
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SentimentAnalysisListView(generics.ListAPIView):
    """List sentiment analyses."""
    
    serializer_class = SentimentAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = SentimentAnalysis.objects.all().order_by('-created_at')
        
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by sentiment
        sentiment = self.request.query_params.get('sentiment')
        if sentiment:
            queryset = queryset.filter(sentiment=sentiment)
        
        # Filter by user (admin only)
        if self.request.user.is_staff:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Regular users can only see their own analyses
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@rate_limit_ml
def analyze_text_sentiment(request):
    """Analyze sentiment of text."""
    serializer = SentimentAnalysisCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        text = serializer.validated_data['text']
        content_type = serializer.validated_data['content_type']
        content_id = serializer.validated_data.get('content_id', '')
        
        analysis = analyze_sentiment(
            text=text,
            content_type=content_type,
            content_id=content_id,
            user=request.user
        )
        
        if analysis:
            response_serializer = SentimentAnalysisSerializer(analysis)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Failed to analyze sentiment'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChurnPredictionListView(generics.ListAPIView):
    """List churn predictions."""
    
    serializer_class = ChurnPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ChurnPrediction.objects.all().order_by('-created_at')
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        # Filter by user (admin only)
        if self.request.user.is_staff:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Regular users can only see their own predictions
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


class ChurnPredictionDetailView(generics.RetrieveUpdateAPIView):
    """Get and update churn prediction."""
    
    serializer_class = ChurnPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return ChurnPrediction.objects.all()
        return ChurnPrediction.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ChurnPredictionUpdateSerializer
        return ChurnPredictionSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@rate_limit_ml
def predict_churn(request):
    """Predict churn for user."""
    user_id = request.data.get('user_id')
    
    if user_id and request.user.is_staff:
        # Admin can predict for any user
        user = get_object_or_404(User, id=user_id)
    else:
        # Regular users predict for themselves
        user = request.user
    
    prediction = predict_user_churn(user)
    
    if prediction:
        serializer = ChurnPredictionSerializer(prediction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(
            {'error': 'Failed to predict churn'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def ml_stats(request):
    """Get ML system statistics."""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    stats = {
        'models': {
            'total': MLModel.objects.count(),
            'active': MLModel.objects.filter(status='active').count(),
            'production': MLModel.objects.filter(is_production=True).count(),
        },
        'recommendations': {
            'total': UserRecommendation.objects.count(),
            'viewed': UserRecommendation.objects.filter(viewed=True).count(),
            'clicked': UserRecommendation.objects.filter(clicked=True).count(),
            'converted': UserRecommendation.objects.filter(converted=True).count(),
        },
        'sentiment_analysis': {
            'total': SentimentAnalysis.objects.count(),
            'positive': SentimentAnalysis.objects.filter(sentiment='positive').count(),
            'negative': SentimentAnalysis.objects.filter(sentiment='negative').count(),
            'neutral': SentimentAnalysis.objects.filter(sentiment='neutral').count(),
        },
        'churn_predictions': {
            'total': ChurnPrediction.objects.count(),
            'high_risk': ChurnPrediction.objects.filter(risk_level__in=['high', 'critical']).count(),
            'medium_risk': ChurnPrediction.objects.filter(risk_level='medium').count(),
            'low_risk': ChurnPrediction.objects.filter(risk_level='low').count(),
        }
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_recommendation_viewed(request, recommendation_id):
    """Mark recommendation as viewed."""
    recommendation = get_object_or_404(
        UserRecommendation,
        id=recommendation_id,
        user=request.user
    )
    
    if not recommendation.viewed:
        recommendation.viewed = True
        recommendation.viewed_at = timezone.now()
        recommendation.save(update_fields=['viewed', 'viewed_at'])
    
    serializer = UserRecommendationSerializer(recommendation)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_recommendation_clicked(request, recommendation_id):
    """Mark recommendation as clicked."""
    recommendation = get_object_or_404(
        UserRecommendation,
        id=recommendation_id,
        user=request.user
    )
    
    if not recommendation.clicked:
        recommendation.clicked = True
        recommendation.clicked_at = timezone.now()
        recommendation.save(update_fields=['clicked', 'clicked_at'])
    
    serializer = UserRecommendationSerializer(recommendation)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_recommendation_converted(request, recommendation_id):
    """Mark recommendation as converted."""
    recommendation = get_object_or_404(
        UserRecommendation,
        id=recommendation_id,
        user=request.user
    )
    
    if not recommendation.converted:
        recommendation.converted = True
        recommendation.converted_at = timezone.now()
        recommendation.save(update_fields=['converted', 'converted_at'])
    
    serializer = UserRecommendationSerializer(recommendation)
    return Response(serializer.data)
