"""
Tests for machine learning functionality including models, recommendations, and sentiment analysis.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
import pickle
import base64
import json

from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction

User = get_user_model()


class MLModelTest(TestCase):
    """Test MLModel functionality."""
    
    def setUp(self):
        self.model_data = {
            'name': 'recommendation_engine_v1',
            'display_name': 'Braider Recommendation Engine',
            'model_type': 'recommendation',
            'version': '1.0',
            'description': 'ML model for recommending braiders to users',
            'algorithm': 'collaborative_filtering',
            'features': ['user_preferences', 'location', 'price_range', 'rating_history'],
            'hyperparameters': {
                'n_factors': 50,
                'learning_rate': 0.01,
                'regularization': 0.1
            }
        }
    
    def test_create_ml_model(self):
        """Test creating an ML model."""
        model = MLModel.objects.create(**self.model_data)
        
        self.assertEqual(model.name, 'recommendation_engine_v1')
        self.assertEqual(model.display_name, 'Braider Recommendation Engine')
        self.assertEqual(model.model_type, 'recommendation')
        self.assertEqual(model.status, 'training')
        self.assertFalse(model.is_production)
        self.assertEqual(model.prediction_count, 0)
    
    def test_model_string_representation(self):
        """Test model string representation."""
        model = MLModel.objects.create(**self.model_data)
        expected = "Braider Recommendation Engine v1.0"
        self.assertEqual(str(model), expected)
    
    def test_save_and_load_model(self):
        """Test saving and loading serialized model."""
        model = MLModel.objects.create(**self.model_data)
        
        # Create a simple mock model (dictionary)
        mock_model = {
            'weights': [0.1, 0.2, 0.3],
            'biases': [0.01, 0.02],
            'model_type': 'linear_regression'
        }
        
        # Save model
        model.save_model(mock_model)
        self.assertIsNotNone(model.model_data)
        
        # Load model
        loaded_model = model.load_model()
        self.assertEqual(loaded_model, mock_model)
        self.assertEqual(loaded_model['weights'], [0.1, 0.2, 0.3])
    
    def test_increment_usage(self):
        """Test incrementing model usage counter."""
        model = MLModel.objects.create(**self.model_data)
        
        initial_count = model.prediction_count
        initial_last_used = model.last_used
        
        model.increment_usage()
        
        self.assertEqual(model.prediction_count, initial_count + 1)
        self.assertIsNotNone(model.last_used)
        self.assertNotEqual(model.last_used, initial_last_used)
    
    def test_model_performance_metrics(self):
        """Test model performance metrics validation."""
        model = MLModel.objects.create(
            **self.model_data,
            accuracy=0.85,
            precision=0.82,
            recall=0.78,
            f1_score=0.80
        )
        
        self.assertEqual(model.accuracy, 0.85)
        self.assertEqual(model.precision, 0.82)
        self.assertEqual(model.recall, 0.78)
        self.assertEqual(model.f1_score, 0.80)
    
    def test_training_tracking(self):
        """Test training time tracking."""
        model = MLModel.objects.create(**self.model_data)
        
        # Simulate training start
        start_time = timezone.now()
        model.training_started = start_time
        model.status = 'training'
        model.save()
        
        # Simulate training completion
        end_time = start_time + timedelta(hours=2)
        model.training_completed = end_time
        model.training_duration = end_time - start_time
        model.status = 'active'
        model.is_production = True
        model.deployed_at = end_time
        model.save()
        
        self.assertEqual(model.status, 'active')
        self.assertTrue(model.is_production)
        self.assertEqual(model.training_duration, timedelta(hours=2))
    
    def test_sentiment_analysis_model(self):
        """Test creating sentiment analysis model."""
        sentiment_model = MLModel.objects.create(
            name='sentiment_analyzer_v1',
            display_name='User Review Sentiment Analyzer',
            model_type='sentiment',
            algorithm='transformer_bert',
            features=['text_tokens', 'pos_tags', 'sentiment_lexicon'],
            status='active'
        )
        
        self.assertEqual(sentiment_model.model_type, 'sentiment')
        self.assertEqual(sentiment_model.algorithm, 'transformer_bert')
    
    def test_fraud_detection_model(self):
        """Test creating fraud detection model."""
        fraud_model = MLModel.objects.create(
            name='fraud_detector_v1',
            display_name='Payment Fraud Detection',
            model_type='fraud_detection',
            algorithm='random_forest',
            features=['transaction_amount', 'user_history', 'device_info', 'location'],
            hyperparameters={
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5
            }
        )
        
        self.assertEqual(fraud_model.model_type, 'fraud_detection')
        self.assertEqual(fraud_model.hyperparameters['n_estimators'], 100)


class UserRecommendationModelTest(TestCase):
    """Test UserRecommendation model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='recommendation@test.com',
            name='Recommendation User',
            password='testpass'
        )
        
        self.ml_model = MLModel.objects.create(
            name='test_recommender',
            display_name='Test Recommender',
            model_type='recommendation',
            status='active'
        )
        
        self.recommendation_data = {
            'user': self.user,
            'recommendation_type': 'braider',
            'item_id': 'braider_123',
            'item_type': 'braider_profile',
            'title': 'Amazing Braider - Maria Silva',
            'description': 'Highly rated braider specializing in protective styles',
            'confidence_score': 0.85,
            'relevance_score': 0.92,
            'model': self.ml_model
        }
    
    def test_create_user_recommendation(self):
        """Test creating user recommendation."""
        recommendation = UserRecommendation.objects.create(**self.recommendation_data)
        
        self.assertEqual(recommendation.user, self.user)
        self.assertEqual(recommendation.recommendation_type, 'braider')
        self.assertEqual(recommendation.item_id, 'braider_123')
        self.assertEqual(recommendation.confidence_score, 0.85)
        self.assertEqual(recommendation.relevance_score, 0.92)
        self.assertFalse(recommendation.viewed)
        self.assertFalse(recommendation.clicked)
        self.assertFalse(recommendation.converted)
    
    def test_recommendation_string_representation(self):
        """Test recommendation string representation."""
        recommendation = UserRecommendation.objects.create(**self.recommendation_data)
        expected = f"Amazing Braider - Maria Silva for {self.user.email}"
        self.assertEqual(str(recommendation), expected)
    
    def test_recommendation_context_and_features(self):
        """Test recommendation context and features."""
        recommendation = UserRecommendation.objects.create(
            **self.recommendation_data,
            recommendation_context={
                'search_query': 'braids near me',
                'user_location': 'Lisbon',
                'price_preference': 'medium'
            },
            features_used=['location_distance', 'price_match', 'style_preference', 'rating_score']
        )
        
        self.assertEqual(recommendation.recommendation_context['search_query'], 'braids near me')
        self.assertIn('location_distance', recommendation.features_used)
        self.assertEqual(len(recommendation.features_used), 4)
    
    def test_track_recommendation_interactions(self):
        """Test tracking recommendation interactions."""
        recommendation = UserRecommendation.objects.create(**self.recommendation_data)
        
        # Track view
        view_time = timezone.now()
        recommendation.viewed = True
        recommendation.viewed_at = view_time
        recommendation.save()
        
        self.assertTrue(recommendation.viewed)
        self.assertEqual(recommendation.viewed_at, view_time)
        
        # Track click
        click_time = view_time + timedelta(seconds=30)
        recommendation.clicked = True
        recommendation.clicked_at = click_time
        recommendation.save()
        
        self.assertTrue(recommendation.clicked)
        self.assertEqual(recommendation.clicked_at, click_time)
        
        # Track conversion
        conversion_time = click_time + timedelta(minutes=5)
        recommendation.converted = True
        recommendation.converted_at = conversion_time
        recommendation.save()
        
        self.assertTrue(recommendation.converted)
        self.assertEqual(recommendation.converted_at, conversion_time)
    
    def test_service_recommendation(self):
        """Test service recommendation."""
        service_rec = UserRecommendation.objects.create(
            user=self.user,
            recommendation_type='service',
            item_id='service_456',
            item_type='braiding_service',
            title='Box Braids with Extensions',
            description='Professional box braids with premium extensions',
            confidence_score=0.78,
            relevance_score=0.85,
            model=self.ml_model
        )
        
        self.assertEqual(service_rec.recommendation_type, 'service')
        self.assertEqual(service_rec.item_type, 'braiding_service')
    
    def test_content_recommendation(self):
        """Test content recommendation."""
        content_rec = UserRecommendation.objects.create(
            user=self.user,
            recommendation_type='content',
            item_id='article_789',
            item_type='hair_care_article',
            title='How to Maintain Your Braids',
            description='Essential tips for keeping your braids healthy',
            confidence_score=0.72,
            relevance_score=0.80,
            model=self.ml_model
        )
        
        self.assertEqual(content_rec.recommendation_type, 'content')
        self.assertEqual(content_rec.item_type, 'hair_care_article')


class SentimentAnalysisModelTest(TestCase):
    """Test SentimentAnalysis model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='sentiment@test.com',
            name='Sentiment User',
            password='testpass'
        )
        
        self.sentiment_model = MLModel.objects.create(
            name='sentiment_analyzer',
            display_name='Review Sentiment Analyzer',
            model_type='sentiment',
            status='active'
        )
        
        self.sentiment_data = {
            'content_type': 'review',
            'content_id': 'review_123',
            'text_content': 'Amazing service! The braider was so professional and the result looks fantastic.',
            'sentiment': 'positive',
            'confidence_score': 0.92,
            'positive_score': 0.92,
            'negative_score': 0.05,
            'neutral_score': 0.03,
            'user': self.user,
            'model': self.sentiment_model
        }
    
    def test_create_sentiment_analysis(self):
        """Test creating sentiment analysis."""
        analysis = SentimentAnalysis.objects.create(**self.sentiment_data)
        
        self.assertEqual(analysis.content_type, 'review')
        self.assertEqual(analysis.sentiment, 'positive')
        self.assertEqual(analysis.confidence_score, 0.92)
        self.assertEqual(analysis.positive_score, 0.92)
        self.assertEqual(analysis.user, self.user)
        self.assertEqual(analysis.model, self.sentiment_model)
    
    def test_sentiment_string_representation(self):
        """Test sentiment analysis string representation."""
        analysis = SentimentAnalysis.objects.create(**self.sentiment_data)
        expected = "Positive sentiment (0.92)"
        self.assertEqual(str(analysis), expected)
    
    def test_negative_sentiment_analysis(self):
        """Test negative sentiment analysis."""
        negative_analysis = SentimentAnalysis.objects.create(
            content_type='review',
            content_id='review_456',
            text_content='Terrible experience. The braider was late and the work was sloppy.',
            sentiment='negative',
            confidence_score=0.88,
            positive_score=0.08,
            negative_score=0.88,
            neutral_score=0.04,
            model=self.sentiment_model
        )
        
        self.assertEqual(negative_analysis.sentiment, 'negative')
        self.assertEqual(negative_analysis.negative_score, 0.88)
        self.assertGreater(negative_analysis.negative_score, negative_analysis.positive_score)
    
    def test_neutral_sentiment_analysis(self):
        """Test neutral sentiment analysis."""
        neutral_analysis = SentimentAnalysis.objects.create(
            content_type='comment',
            content_id='comment_789',
            text_content='The appointment was scheduled for 2 PM.',
            sentiment='neutral',
            confidence_score=0.75,
            positive_score=0.15,
            negative_score=0.10,
            neutral_score=0.75,
            model=self.sentiment_model
        )
        
        self.assertEqual(neutral_analysis.sentiment, 'neutral')
        self.assertEqual(neutral_analysis.neutral_score, 0.75)
    
    def test_sentiment_with_keywords_and_emotions(self):
        """Test sentiment analysis with keywords and emotions."""
        analysis = SentimentAnalysis.objects.create(
            **self.sentiment_data,
            keywords=['amazing', 'professional', 'fantastic', 'service'],
            emotions={
                'joy': 0.85,
                'trust': 0.78,
                'surprise': 0.12,
                'fear': 0.02,
                'anger': 0.01,
                'sadness': 0.03
            }
        )
        
        self.assertIn('amazing', analysis.keywords)
        self.assertIn('professional', analysis.keywords)
        self.assertEqual(analysis.emotions['joy'], 0.85)
        self.assertEqual(analysis.emotions['trust'], 0.78)
    
    def test_chat_message_sentiment(self):
        """Test sentiment analysis for chat messages."""
        chat_sentiment = SentimentAnalysis.objects.create(
            content_type='message',
            content_id='msg_101',
            text_content='Thank you so much for your help! 😊',
            sentiment='positive',
            confidence_score=0.89,
            positive_score=0.89,
            negative_score=0.03,
            neutral_score=0.08,
            model=self.sentiment_model
        )
        
        self.assertEqual(chat_sentiment.content_type, 'message')
        self.assertEqual(chat_sentiment.sentiment, 'positive')
    
    def test_social_post_sentiment(self):
        """Test sentiment analysis for social media posts."""
        social_sentiment = SentimentAnalysis.objects.create(
            content_type='social_post',
            content_id='post_202',
            text_content='Just got my hair done at @TuwiBeauty and I love it! #braids #hairgoals',
            sentiment='positive',
            confidence_score=0.91,
            positive_score=0.91,
            negative_score=0.02,
            neutral_score=0.07,
            keywords=['love', 'hairgoals', 'braids'],
            model=self.sentiment_model
        )
        
        self.assertEqual(social_sentiment.content_type, 'social_post')
        self.assertIn('#braids', social_sentiment.text_content)
        self.assertIn('love', social_sentiment.keywords)


class ChurnPredictionModelTest(TestCase):
    """Test ChurnPrediction model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='churn@test.com',
            name='Churn User',
            password='testpass'
        )
        
        self.churn_model = MLModel.objects.create(
            name='churn_predictor',
            display_name='Customer Churn Predictor',
            model_type='churn_prediction',
            status='active'
        )
        
        self.churn_data = {
            'user': self.user,
            'churn_probability': 0.75,
            'risk_level': 'high',
            'model': self.churn_model
        }
    
    def test_create_churn_prediction(self):
        """Test creating churn prediction."""
        prediction = ChurnPrediction.objects.create(**self.churn_data)
        
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.churn_probability, 0.75)
        self.assertEqual(prediction.risk_level, 'high')
        self.assertEqual(prediction.model, self.churn_model)
        self.assertIsNone(prediction.actual_churned)
    
    def test_churn_prediction_string_representation(self):
        """Test churn prediction string representation."""
        prediction = ChurnPrediction.objects.create(**self.churn_data)
        expected = f"{self.user.email} - 0.75 churn risk"
        self.assertEqual(str(prediction), expected)
    
    def test_churn_factors_and_feature_importance(self):
        """Test churn factors and feature importance."""
        prediction = ChurnPrediction.objects.create(
            **self.churn_data,
            churn_factors=[
                'Low booking frequency (last 3 months)',
                'No recent app usage',
                'Negative review sentiment',
                'High price sensitivity'
            ],
            feature_importance={
                'booking_frequency': 0.35,
                'app_usage': 0.28,
                'review_sentiment': 0.22,
                'price_sensitivity': 0.15
            }
        )
        
        self.assertEqual(len(prediction.churn_factors), 4)
        self.assertIn('Low booking frequency (last 3 months)', prediction.churn_factors)
        self.assertEqual(prediction.feature_importance['booking_frequency'], 0.35)
        self.assertEqual(prediction.feature_importance['app_usage'], 0.28)
    
    def test_retention_recommendations(self):
        """Test retention action recommendations."""
        prediction = ChurnPrediction.objects.create(
            **self.churn_data,
            retention_actions=[
                'Send personalized discount code (20% off)',
                'Recommend highly-rated braiders in user area',
                'Send hair care tips and tutorials',
                'Offer loyalty program enrollment'
            ]
        )
        
        self.assertEqual(len(prediction.retention_actions), 4)
        self.assertIn('Send personalized discount code (20% off)', prediction.retention_actions)
        self.assertIn('Offer loyalty program enrollment', prediction.retention_actions)
    
    def test_low_risk_churn_prediction(self):
        """Test low risk churn prediction."""
        low_risk = ChurnPrediction.objects.create(
            user=self.user,
            churn_probability=0.15,
            risk_level='low',
            model=self.churn_model,
            churn_factors=['Active user', 'Recent positive reviews'],
            retention_actions=['Continue current engagement strategy']
        )
        
        self.assertEqual(low_risk.risk_level, 'low')
        self.assertEqual(low_risk.churn_probability, 0.15)
        self.assertIn('Active user', low_risk.churn_factors)
    
    def test_critical_risk_churn_prediction(self):
        """Test critical risk churn prediction."""
        critical_risk = ChurnPrediction.objects.create(
            user=self.user,
            churn_probability=0.95,
            risk_level='critical',
            model=self.churn_model,
            churn_factors=[
                'No bookings in 6 months',
                'Multiple cancelled appointments',
                'Negative feedback submitted'
            ],
            retention_actions=[
                'Immediate personal outreach by customer success',
                'Offer significant discount or free service',
                'Schedule feedback call to understand issues'
            ]
        )
        
        self.assertEqual(critical_risk.risk_level, 'critical')
        self.assertEqual(critical_risk.churn_probability, 0.95)
        self.assertIn('Immediate personal outreach by customer success', critical_risk.retention_actions)
    
    def test_track_churn_outcome(self):
        """Test tracking actual churn outcome."""
        prediction = ChurnPrediction.objects.create(**self.churn_data)
        
        # Track that retention action was taken
        prediction.retention_action_taken = 'Sent 20% discount code via email'
        prediction.save()
        
        # Track actual outcome (user did not churn)
        prediction.actual_churned = False
        prediction.save()
        
        self.assertEqual(prediction.retention_action_taken, 'Sent 20% discount code via email')
        self.assertFalse(prediction.actual_churned)


class MLIntegrationTest(TestCase):
    """Test ML system integration scenarios."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='ml_integration@test.com',
            name='ML Integration User',
            password='testpass'
        )
        
        # Create ML models
        self.recommendation_model = MLModel.objects.create(
            name='integrated_recommender',
            display_name='Integrated Recommendation Engine',
            model_type='recommendation',
            status='active',
            is_production=True
        )
        
        self.sentiment_model = MLModel.objects.create(
            name='integrated_sentiment',
            display_name='Integrated Sentiment Analyzer',
            model_type='sentiment',
            status='active',
            is_production=True
        )
        
        self.churn_model = MLModel.objects.create(
            name='integrated_churn',
            display_name='Integrated Churn Predictor',
            model_type='churn_prediction',
            status='active',
            is_production=True
        )
    
    def test_recommendation_to_sentiment_pipeline(self):
        """Test pipeline from recommendation to sentiment analysis."""
        # User receives recommendation
        recommendation = UserRecommendation.objects.create(
            user=self.user,
            recommendation_type='braider',
            item_id='braider_456',
            item_type='braider_profile',
            title='Excellent Braider - Ana Costa',
            confidence_score=0.88,
            relevance_score=0.91,
            model=self.recommendation_model
        )
        
        # User views and clicks recommendation
        recommendation.viewed = True
        recommendation.clicked = True
        recommendation.viewed_at = timezone.now()
        recommendation.clicked_at = timezone.now() + timedelta(seconds=10)
        recommendation.save()
        
        # User leaves review (simulate conversion)
        review_text = "Great recommendation! Ana was amazing and I love my new braids."
        
        # Analyze sentiment of review
        sentiment = SentimentAnalysis.objects.create(
            content_type='review',
            content_id=f'review_for_{recommendation.item_id}',
            text_content=review_text,
            sentiment='positive',
            confidence_score=0.91,
            positive_score=0.91,
            negative_score=0.04,
            neutral_score=0.05,
            user=self.user,
            model=self.sentiment_model
        )
        
        # Mark recommendation as converted
        recommendation.converted = True
        recommendation.converted_at = timezone.now() + timedelta(minutes=30)
        recommendation.save()
        
        # Verify integration
        self.assertTrue(recommendation.converted)
        self.assertEqual(sentiment.sentiment, 'positive')
        self.assertGreater(sentiment.confidence_score, 0.9)
        
        # Update model usage
        self.recommendation_model.increment_usage()
        self.sentiment_model.increment_usage()
        
        self.assertEqual(self.recommendation_model.prediction_count, 1)
        self.assertEqual(self.sentiment_model.prediction_count, 1)
    
    def test_sentiment_to_churn_prediction_pipeline(self):
        """Test pipeline from sentiment analysis to churn prediction."""
        # Analyze negative sentiment
        negative_sentiment = SentimentAnalysis.objects.create(
            content_type='review',
            content_id='review_negative_123',
            text_content='Very disappointed with the service. Will not be coming back.',
            sentiment='negative',
            confidence_score=0.89,
            positive_score=0.05,
            negative_score=0.89,
            neutral_score=0.06,
            user=self.user,
            model=self.sentiment_model,
            keywords=['disappointed', 'not coming back'],
            emotions={'anger': 0.72, 'sadness': 0.58}
        )
        
        # Generate churn prediction based on negative sentiment
        churn_prediction = ChurnPrediction.objects.create(
            user=self.user,
            churn_probability=0.82,
            risk_level='high',
            churn_factors=[
                'Recent negative review sentiment',
                'Expressed intent not to return',
                'High anger emotion detected'
            ],
            feature_importance={
                'sentiment_score': 0.45,
                'review_frequency': 0.30,
                'emotion_analysis': 0.25
            },
            retention_actions=[
                'Personal apology from customer service',
                'Offer refund or service credit',
                'Schedule follow-up call to address concerns'
            ],
            model=self.churn_model
        )
        
        # Verify pipeline
        self.assertEqual(negative_sentiment.sentiment, 'negative')
        self.assertEqual(churn_prediction.risk_level, 'high')
        self.assertIn('Recent negative review sentiment', churn_prediction.churn_factors)
        self.assertEqual(churn_prediction.feature_importance['sentiment_score'], 0.45)
    
    def test_multi_model_user_profile(self):
        """Test complete user profile with multiple ML predictions."""
        # Create recommendations
        braider_rec = UserRecommendation.objects.create(
            user=self.user,
            recommendation_type='braider',
            item_id='braider_789',
            item_type='braider_profile',
            title='Top Rated Braider',
            confidence_score=0.92,
            relevance_score=0.89,
            model=self.recommendation_model
        )
        
        service_rec = UserRecommendation.objects.create(
            user=self.user,
            recommendation_type='service',
            item_id='service_101',
            item_type='braiding_service',
            title='Protective Style Package',
            confidence_score=0.85,
            relevance_score=0.88,
            model=self.recommendation_model
        )
        
        # Create sentiment analyses
        positive_sentiment = SentimentAnalysis.objects.create(
            content_type='review',
            content_id='review_pos_1',
            text_content='Love the app! Great recommendations.',
            sentiment='positive',
            confidence_score=0.91,
            positive_score=0.91,
            negative_score=0.04,
            neutral_score=0.05,
            user=self.user,
            model=self.sentiment_model
        )
        
        # Create churn prediction
        churn_prediction = ChurnPrediction.objects.create(
            user=self.user,
            churn_probability=0.25,
            risk_level='low',
            churn_factors=['Active user', 'Positive sentiment'],
            model=self.churn_model
        )
        
        # Verify complete profile
        user_recommendations = UserRecommendation.objects.filter(user=self.user)
        user_sentiments = SentimentAnalysis.objects.filter(user=self.user)
        user_churn = ChurnPrediction.objects.filter(user=self.user)
        
        self.assertEqual(user_recommendations.count(), 2)
        self.assertEqual(user_sentiments.count(), 1)
        self.assertEqual(user_churn.count(), 1)
        
        # Check risk assessment
        self.assertEqual(churn_prediction.risk_level, 'low')
        self.assertEqual(positive_sentiment.sentiment, 'positive')


class MLAPITest(APITestCase):
    """Test ML API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='ml_api@test.com',
            name='ML API User',
            password='testpass'
        )
        
        self.ml_model = MLModel.objects.create(
            name='api_test_model',
            display_name='API Test Model',
            model_type='recommendation',
            status='active'
        )
        
        # Create test recommendations
        for i in range(3):
            UserRecommendation.objects.create(
                user=self.user,
                recommendation_type='braider',
                item_id=f'braider_{i}',
                item_type='braider_profile',
                title=f'Recommended Braider {i}',
                confidence_score=0.8 + (i * 0.05),
                relevance_score=0.85 + (i * 0.03),
                model=self.ml_model
            )
        
        self.client.force_authenticate(user=self.user)
    
    def test_get_user_recommendations(self):
        """Test getting user recommendations."""
        url = reverse('ml:user-recommendations')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['recommendation_type'], 'braider')
    
    def test_track_recommendation_interaction(self):
        """Test tracking recommendation interaction."""
        recommendation = UserRecommendation.objects.filter(user=self.user).first()
        
        url = reverse('ml:track-recommendation', kwargs={'recommendation_id': recommendation.id})
        data = {'action': 'view'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        recommendation.refresh_from_db()
        self.assertTrue(recommendation.viewed)
        self.assertIsNotNone(recommendation.viewed_at)
    
    def test_sentiment_analysis_request(self):
        """Test requesting sentiment analysis."""
        url = reverse('ml:analyze-sentiment')
        data = {
            'text': 'I absolutely love my new braids! The stylist was amazing.',
            'content_type': 'review'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('sentiment', response.data)
        self.assertIn('confidence_score', response.data)
    
    def test_get_churn_risk(self):
        """Test getting user churn risk."""
        # Create churn prediction
        ChurnPrediction.objects.create(
            user=self.user,
            churn_probability=0.65,
            risk_level='medium',
            model=self.ml_model
        )
        
        url = reverse('ml:churn-risk')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['risk_level'], 'medium')
        self.assertEqual(float(response.data['churn_probability']), 0.65)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to ML endpoints."""
        self.client.force_authenticate(user=None)
        
        url = reverse('ml:user-recommendations')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)