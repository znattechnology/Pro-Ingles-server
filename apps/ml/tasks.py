"""
Machine Learning background tasks.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from celery import shared_task
from celery.utils.log import get_task_logger

from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction
from .services import predict_user_churn, get_user_recommendations, analyze_sentiment

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_batch_predictions(self):
    """Process batch ML predictions for all users."""
    try:
        logger.info("Starting batch ML predictions")
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get active users who haven't had predictions in the last 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        users_needing_predictions = User.objects.filter(
            is_active=True,
            last_login__gte=timezone.now() - timedelta(days=30)  # Active in last 30 days
        ).exclude(
            churn_predictions__created_at__gte=cutoff_time
        )[:50]  # Limit to 50 users per batch
        
        predictions_created = 0
        recommendations_created = 0
        
        for user in users_needing_predictions:
            try:
                # Generate churn prediction
                churn_prediction = predict_user_churn(user)
                if churn_prediction:
                    predictions_created += 1
                
                # Generate recommendations
                recommendations = get_user_recommendations(user, limit=3)
                recommendations_created += len(recommendations)
                
            except Exception as e:
                logger.warning(f"Failed to process predictions for user {user.id}: {str(e)}")
        
        logger.info(f"Batch predictions completed: {predictions_created} churn predictions, {recommendations_created} recommendations")
        
        return {
            "status": "success",
            "users_processed": len(users_needing_predictions),
            "predictions_created": predictions_created,
            "recommendations_created": recommendations_created
        }
        
    except Exception as exc:
        logger.error(f"Batch predictions failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=2)
def analyze_pending_content(self):
    """Analyze sentiment for pending reviews and comments."""
    try:
        logger.info("Starting sentiment analysis for pending content")
        
        from apps.ratings.models import Review
        
        # Get reviews without sentiment analysis
        pending_reviews = Review.objects.filter(
            ~Q(id__in=SentimentAnalysis.objects.filter(
                content_type='review'
            ).values_list('content_id', flat=True))
        )[:100]  # Limit to 100 reviews per batch
        
        analyses_created = 0
        
        for review in pending_reviews:
            try:
                if review.comment and len(review.comment.strip()) > 10:
                    analysis = analyze_sentiment(
                        text=review.comment,
                        content_type='review',
                        content_id=str(review.id),
                        user=review.user
                    )
                    if analysis:
                        analyses_created += 1
                        
            except Exception as e:
                logger.warning(f"Failed to analyze sentiment for review {review.id}: {str(e)}")
        
        logger.info(f"Sentiment analysis completed: {analyses_created} analyses created")
        
        return {
            "status": "success",
            "reviews_processed": len(pending_reviews),
            "analyses_created": analyses_created
        }
        
    except Exception as exc:
        logger.error(f"Sentiment analysis failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=180, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=2)
def cleanup_old_predictions(self):
    """Clean up old ML predictions and recommendations."""
    try:
        logger.info("Starting cleanup of old ML data")
        
        # Delete old recommendations (older than 30 days)
        old_recommendations = UserRecommendation.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=30)
        )
        recommendations_deleted = old_recommendations.count()
        old_recommendations.delete()
        
        # Delete old sentiment analyses (older than 90 days)
        old_sentiments = SentimentAnalysis.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=90)
        )
        sentiments_deleted = old_sentiments.count()
        old_sentiments.delete()
        
        # Delete old churn predictions (keep latest for each user, delete others older than 7 days)
        old_churn_predictions = ChurnPrediction.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=7)
        ).exclude(
            id__in=ChurnPrediction.objects.values('user').annotate(
                latest_id=models.Max('id')
            ).values_list('latest_id', flat=True)
        )
        churn_deleted = old_churn_predictions.count()
        old_churn_predictions.delete()
        
        logger.info(f"ML cleanup completed: {recommendations_deleted} recommendations, {sentiments_deleted} sentiments, {churn_deleted} churn predictions deleted")
        
        return {
            "status": "success",
            "recommendations_deleted": recommendations_deleted,
            "sentiments_deleted": sentiments_deleted,
            "churn_predictions_deleted": churn_deleted
        }
        
    except Exception as exc:
        logger.error(f"ML cleanup failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=1)
def train_model(model_name, training_data=None):
    """Train or retrain an ML model."""
    try:
        logger.info(f"Starting model training: {model_name}")
        
        # Get or create the model
        ml_model, created = MLModel.objects.get_or_create(
            name=model_name,
            defaults={
                'display_name': f"{model_name.title()} Model",
                'status': 'training',
                'training_started': timezone.now()
            }
        )
        
        if not created:
            ml_model.status = 'training'
            ml_model.training_started = timezone.now()
            ml_model.save()
        
        # Simulate model training (replace with actual training logic)
        import time
        import random
        
        # Simulate training time
        training_duration = random.randint(30, 120)  # 30-120 seconds
        time.sleep(training_duration)
        
        # Simulate training completion
        ml_model.training_completed = timezone.now()
        ml_model.training_duration = ml_model.training_completed - ml_model.training_started
        ml_model.status = 'active'
        ml_model.accuracy = random.uniform(0.7, 0.95)  # Random accuracy
        ml_model.precision = random.uniform(0.65, 0.9)
        ml_model.recall = random.uniform(0.6, 0.85)
        ml_model.f1_score = 2 * (ml_model.precision * ml_model.recall) / (ml_model.precision + ml_model.recall)
        ml_model.save()
        
        logger.info(f"Model training completed: {model_name} (accuracy: {ml_model.accuracy:.3f})")
        
        return {
            "status": "success",
            "model_name": model_name,
            "accuracy": ml_model.accuracy,
            "training_duration": str(ml_model.training_duration)
        }
        
    except Exception as exc:
        logger.error(f"Model training failed for {model_name}: {str(exc)}")
        
        # Update model status to failed
        try:
            ml_model = MLModel.objects.get(name=model_name)
            ml_model.status = 'failed'
            ml_model.save()
        except MLModel.DoesNotExist:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=600, exc=exc)  # Retry after 10 minutes
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True)
def update_model_metrics(self):
    """Update performance metrics for all active ML models."""
    try:
        logger.info("Starting model metrics update")
        
        active_models = MLModel.objects.filter(status='active')
        updated_models = 0
        
        for model in active_models:
            try:
                # Calculate recent performance metrics based on actual usage
                if model.model_type == 'recommendation':
                    # Calculate recommendation performance
                    recent_recommendations = UserRecommendation.objects.filter(
                        model=model,
                        created_at__gte=timezone.now() - timedelta(days=7)
                    )
                    
                    if recent_recommendations.exists():
                        total_recommendations = recent_recommendations.count()
                        clicked_recommendations = recent_recommendations.filter(clicked=True).count()
                        converted_recommendations = recent_recommendations.filter(converted=True).count()
                        
                        click_rate = clicked_recommendations / total_recommendations if total_recommendations > 0 else 0
                        conversion_rate = converted_recommendations / total_recommendations if total_recommendations > 0 else 0
                        
                        # Update model performance (using click rate as proxy for accuracy)
                        model.accuracy = click_rate
                        model.precision = conversion_rate
                        model.save(update_fields=['accuracy', 'precision'])
                        
                elif model.model_type == 'churn_prediction':
                    # Calculate churn prediction accuracy (if we have actual churn data)
                    recent_predictions = ChurnPrediction.objects.filter(
                        model=model,
                        created_at__gte=timezone.now() - timedelta(days=30),
                        actual_churned__isnull=False  # Only predictions with known outcomes
                    )
                    
                    if recent_predictions.exists():
                        correct_predictions = 0
                        total_predictions = recent_predictions.count()
                        
                        for prediction in recent_predictions:
                            # High churn probability should predict actual churn
                            predicted_churn = prediction.churn_probability > 0.5
                            if predicted_churn == prediction.actual_churned:
                                correct_predictions += 1
                        
                        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
                        model.accuracy = accuracy
                        model.save(update_fields=['accuracy'])
                
                updated_models += 1
                
            except Exception as e:
                logger.warning(f"Failed to update metrics for model {model.id}: {str(e)}")
        
        logger.info(f"Model metrics update completed: {updated_models} models updated")
        
        return {
            "status": "success",
            "models_updated": updated_models
        }
        
    except Exception as exc:
        logger.error(f"Model metrics update failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True)
def generate_ml_reports(self):
    """Generate ML performance reports."""
    try:
        logger.info("Starting ML reports generation")
        
        from django.core.cache import cache
        
        # Generate overall ML system stats
        stats = {
            'timestamp': timezone.now().isoformat(),
            'models': {
                'total': MLModel.objects.count(),
                'active': MLModel.objects.filter(status='active').count(),
                'training': MLModel.objects.filter(status='training').count(),
                'failed': MLModel.objects.filter(status='failed').count(),
            },
            'predictions': {
                'recommendations_7d': UserRecommendation.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'sentiment_analyses_7d': SentimentAnalysis.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'churn_predictions_7d': ChurnPrediction.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
            },
            'performance': {
                'avg_model_accuracy': MLModel.objects.filter(
                    status='active',
                    accuracy__isnull=False
                ).aggregate(avg_accuracy=models.Avg('accuracy'))['avg_accuracy'] or 0,
            }
        }
        
        # Cache the report
        cache.set('ml_weekly_report', stats, 604800)  # 7 days
        
        logger.info("ML reports generation completed")
        
        return {
            "status": "success",
            "report": stats
        }
        
    except Exception as exc:
        logger.error(f"ML reports generation failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}