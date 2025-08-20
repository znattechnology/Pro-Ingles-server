"""
Machine Learning services for AI-powered features.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from textblob import TextBlob
import logging

from django.utils import timezone
from django.db.models import Q, Count, Avg, F
from django.contrib.auth import get_user_model

from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction

User = get_user_model()
logger = logging.getLogger(__name__)


class RecommendationEngine:
    """AI-powered recommendation system."""
    
    def __init__(self):
        self.model = self._get_or_create_model('braider_recommendation')
    
    def _get_or_create_model(self, name):
        """Get or create ML model."""
        model, created = MLModel.objects.get_or_create(
            name=name,
            defaults={
                'display_name': 'Braider Recommendation Engine',
                'model_type': 'recommendation',
                'algorithm': 'RandomForest',
                'status': 'active',
                'is_production': True
            }
        )
        return model
    
    def generate_braider_recommendations(self, user, limit=5):
        """Generate braider recommendations for user."""
        try:
            from apps.braiders.models import Braider
            from apps.bookings.models import Booking
            
            # Get user's booking history
            user_bookings = Booking.objects.filter(user=user, status='completed')
            
            if not user_bookings.exists():
                # New user - recommend top-rated braiders
                top_braiders = Braider.objects.filter(
                    is_active=True
                ).annotate(
                    avg_rating=Avg('reviews__overall_rating'),
                    booking_count=Count('bookings')
                ).order_by('-avg_rating', '-booking_count')[:limit]
                
                recommendations = []
                for braider in top_braiders:
                    rec = UserRecommendation.objects.create(
                        user=user,
                        recommendation_type='braider',
                        item_id=str(braider.id),
                        item_type='braider',
                        title=f"Recomendado: {braider.business_name}",
                        description=f"Braider top-rated com {braider.avg_rating:.1f} estrelas",
                        confidence_score=0.8,
                        relevance_score=0.9,
                        model=self.model,
                        recommendation_context={
                            'reason': 'top_rated_new_user',
                            'avg_rating': float(braider.avg_rating or 0),
                            'booking_count': braider.booking_count
                        }
                    )
                    recommendations.append(rec)
                
                return recommendations
            
            # Existing user - collaborative filtering
            similar_users = self._find_similar_users(user)
            recommended_braiders = self._get_collaborative_recommendations(
                user, similar_users, limit
            )
            
            return recommended_braiders
            
        except Exception as e:
            logger.error(f"Error generating braider recommendations: {str(e)}")
            return []
    
    def _find_similar_users(self, user, limit=10):
        """Find users with similar booking patterns."""
        from apps.bookings.models import Booking
        
        # Get user's preferred services and locations
        user_bookings = Booking.objects.filter(user=user, status='completed')
        user_services = set(user_bookings.values_list('service_type', flat=True))
        
        # Find users with overlapping preferences
        similar_users = User.objects.filter(
            bookings__service_type__in=user_services,
            bookings__status='completed'
        ).exclude(id=user.id).annotate(
            common_services=Count('bookings__service_type')
        ).order_by('-common_services')[:limit]
        
        return similar_users
    
    def _get_collaborative_recommendations(self, user, similar_users, limit):
        """Get recommendations based on similar users."""
        from apps.braiders.models import Braider
        from apps.bookings.models import Booking
        
        # Get braiders used by similar users
        similar_braiders = Braider.objects.filter(
            bookings__user__in=similar_users,
            bookings__status='completed'
        ).exclude(
            bookings__user=user
        ).annotate(
            usage_count=Count('bookings'),
            avg_rating=Avg('reviews__overall_rating')
        ).order_by('-usage_count', '-avg_rating')[:limit]
        
        recommendations = []
        for braider in similar_braiders:
            rec = UserRecommendation.objects.create(
                user=user,
                recommendation_type='braider',
                item_id=str(braider.id),
                item_type='braider',
                title=f"Você pode gostar: {braider.business_name}",
                description="Baseado em usuários com gostos similares",
                confidence_score=0.75,
                relevance_score=0.8,
                model=self.model,
                recommendation_context={
                    'reason': 'collaborative_filtering',
                    'usage_count': braider.usage_count,
                    'avg_rating': float(braider.avg_rating or 0)
                }
            )
            recommendations.append(rec)
        
        return recommendations


class SentimentAnalyzer:
    """AI-powered sentiment analysis."""
    
    def __init__(self):
        self.model = self._get_or_create_model('sentiment_analyzer')
    
    def _get_or_create_model(self, name):
        """Get or create ML model."""
        model, created = MLModel.objects.get_or_create(
            name=name,
            defaults={
                'display_name': 'Sentiment Analysis Engine',
                'model_type': 'sentiment',
                'algorithm': 'TextBlob',
                'status': 'active',
                'is_production': True
            }
        )
        return model
    
    def analyze_text(self, text, content_type='review', content_id='', user=None):
        """Analyze sentiment of text content."""
        try:
            # Use TextBlob for sentiment analysis
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Determine sentiment
            if polarity > 0.1:
                sentiment = 'positive'
            elif polarity < -0.1:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            # Calculate confidence score
            confidence = abs(polarity)
            
            # Extract keywords
            keywords = [word.lower() for word in blob.words if len(word) > 3][:10]
            
            # Create sentiment analysis record
            analysis = SentimentAnalysis.objects.create(
                content_type=content_type,
                content_id=content_id,
                text_content=text,
                sentiment=sentiment,
                confidence_score=confidence,
                positive_score=max(0, polarity),
                negative_score=max(0, -polarity),
                neutral_score=1 - abs(polarity),
                keywords=keywords,
                emotions={'subjectivity': subjectivity},
                user=user,
                model=self.model
            )
            
            self.model.increment_usage()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return None
    
    def analyze_review(self, review):
        """Analyze sentiment of a review."""
        return self.analyze_text(
            text=review.comment,
            content_type='review',
            content_id=str(review.id),
            user=review.user
        )


class ChurnPredictor:
    """AI-powered churn prediction."""
    
    def __init__(self):
        self.model = self._get_or_create_model('churn_predictor')
    
    def _get_or_create_model(self, name):
        """Get or create ML model."""
        model, created = MLModel.objects.get_or_create(
            name=name,
            defaults={
                'display_name': 'Churn Prediction Model',
                'model_type': 'churn_prediction',
                'algorithm': 'RandomForest',
                'status': 'active',
                'is_production': True
            }
        )
        return model
    
    def predict_churn(self, user):
        """Predict churn probability for user."""
        try:
            from apps.bookings.models import Booking
            from apps.analytics.models import UserActivity
            
            # Calculate user features
            features = self._extract_user_features(user)
            
            # Simple rule-based prediction (can be replaced with trained model)
            churn_probability = self._calculate_churn_probability(features)
            
            # Determine risk level
            if churn_probability >= 0.8:
                risk_level = 'critical'
            elif churn_probability >= 0.6:
                risk_level = 'high'
            elif churn_probability >= 0.4:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Identify churn factors
            churn_factors = self._identify_churn_factors(features)
            
            # Generate retention actions
            retention_actions = self._generate_retention_actions(churn_factors, risk_level)
            
            # Create prediction record
            prediction = ChurnPrediction.objects.create(
                user=user,
                churn_probability=churn_probability,
                risk_level=risk_level,
                churn_factors=churn_factors,
                feature_importance=features,
                retention_actions=retention_actions,
                model=self.model
            )
            
            self.model.increment_usage()
            return prediction
            
        except Exception as e:
            logger.error(f"Error predicting churn for user {user.email}: {str(e)}")
            return None
    
    def _extract_user_features(self, user):
        """Extract features for churn prediction."""
        from apps.bookings.models import Booking
        from apps.analytics.models import UserActivity
        
        now = timezone.now()
        
        # Booking features
        total_bookings = Booking.objects.filter(user=user).count()
        recent_bookings = Booking.objects.filter(
            user=user,
            created_at__gte=now - timezone.timedelta(days=30)
        ).count()
        
        last_booking = Booking.objects.filter(user=user).order_by('-created_at').first()
        days_since_last_booking = (
            (now - last_booking.created_at).days if last_booking else 365
        )
        
        # Activity features
        total_activities = UserActivity.objects.filter(user=user).count()
        recent_activities = UserActivity.objects.filter(
            user=user,
            timestamp__gte=now - timezone.timedelta(days=7)
        ).count()
        
        last_activity = UserActivity.objects.filter(user=user).order_by('-timestamp').first()
        days_since_last_activity = (
            (now - last_activity.timestamp).days if last_activity else 365
        )
        
        # Account features
        account_age_days = (now - user.date_joined).days
        
        return {
            'total_bookings': total_bookings,
            'recent_bookings': recent_bookings,
            'days_since_last_booking': days_since_last_booking,
            'total_activities': total_activities,
            'recent_activities': recent_activities,
            'days_since_last_activity': days_since_last_activity,
            'account_age_days': account_age_days
        }
    
    def _calculate_churn_probability(self, features):
        """Calculate churn probability based on features."""
        score = 0.0
        
        # Days since last booking
        if features['days_since_last_booking'] > 90:
            score += 0.4
        elif features['days_since_last_booking'] > 60:
            score += 0.2
        
        # Recent activity
        if features['recent_activities'] == 0:
            score += 0.3
        elif features['recent_activities'] < 3:
            score += 0.1
        
        # Days since last activity
        if features['days_since_last_activity'] > 30:
            score += 0.3
        elif features['days_since_last_activity'] > 14:
            score += 0.1
        
        # Total engagement
        if features['total_bookings'] == 0:
            score += 0.2
        
        return min(score, 1.0)
    
    def _identify_churn_factors(self, features):
        """Identify factors contributing to churn."""
        factors = []
        
        if features['days_since_last_booking'] > 60:
            factors.append('Inactive booking behavior')
        
        if features['recent_activities'] < 3:
            factors.append('Low recent engagement')
        
        if features['total_bookings'] < 2:
            factors.append('Low lifetime usage')
        
        if features['days_since_last_activity'] > 14:
            factors.append('Recent inactivity')
        
        return factors
    
    def _generate_retention_actions(self, factors, risk_level):
        """Generate retention action recommendations."""
        actions = []
        
        if risk_level in ['high', 'critical']:
            actions.append('Send personalized re-engagement email')
            actions.append('Offer discount on next booking')
        
        if 'Inactive booking behavior' in factors:
            actions.append('Recommend popular braiders')
            actions.append('Send service reminders')
        
        if 'Low recent engagement' in factors:
            actions.append('Share platform updates and new features')
        
        if 'Low lifetime usage' in factors:
            actions.append('Provide onboarding assistance')
            actions.append('Highlight platform benefits')
        
        return actions


# Convenience functions
def get_user_recommendations(user, recommendation_type='braider', limit=5):
    """Get recommendations for user."""
    engine = RecommendationEngine()
    
    if recommendation_type == 'braider':
        return engine.generate_braider_recommendations(user, limit)
    
    return []


def analyze_sentiment(text, content_type='review', content_id='', user=None):
    """Analyze sentiment of text."""
    analyzer = SentimentAnalyzer()
    return analyzer.analyze_text(text, content_type, content_id, user)


def predict_user_churn(user):
    """Predict churn for user."""
    predictor = ChurnPredictor()
    return predictor.predict_churn(user)