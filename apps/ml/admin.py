from django.contrib import admin
from .models import MLModel, UserRecommendation, SentimentAnalysis, ChurnPrediction


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'model_type', 'version', 'status', 
        'is_production', 'accuracy', 'prediction_count', 'last_used'
    ]
    list_filter = ['model_type', 'status', 'is_production', 'created_at']
    search_fields = ['name', 'display_name', 'algorithm']
    readonly_fields = [
        'prediction_count', 'last_used', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'display_name', 'model_type', 'version', 'description')
        }),
        ('Model Details', {
            'fields': ('algorithm', 'features', 'hyperparameters')
        }),
        ('Performance Metrics', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score')
        }),
        ('Training Info', {
            'fields': (
                'training_data_size', 'training_started', 'training_completed',
                'training_duration'
            )
        }),
        ('Status', {
            'fields': ('status', 'is_production', 'deployed_at')
        }),
        ('Usage Stats', {
            'fields': ('prediction_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'recommendation_type', 'confidence_score',
        'viewed', 'clicked', 'converted', 'created_at'
    ]
    list_filter = [
        'recommendation_type', 'viewed', 'clicked', 'converted',
        'model', 'created_at'
    ]
    search_fields = ['title', 'user__email', 'item_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Recommendation Info', {
            'fields': (
                'user', 'recommendation_type', 'title', 'description'
            )
        }),
        ('Item Details', {
            'fields': ('item_id', 'item_type')
        }),
        ('Scoring', {
            'fields': ('confidence_score', 'relevance_score')
        }),
        ('Context', {
            'fields': ('recommendation_context', 'features_used'),
            'classes': ('collapse',)
        }),
        ('Interactions', {
            'fields': (
                'viewed', 'viewed_at', 'clicked', 'clicked_at',
                'converted', 'converted_at'
            )
        }),
        ('Model', {
            'fields': ('model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'sentiment', 'confidence_score', 'content_type',
        'user', 'model', 'created_at'
    ]
    list_filter = [
        'sentiment', 'content_type', 'model', 'created_at'
    ]
    search_fields = ['text_content', 'user__email', 'content_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Content Info', {
            'fields': ('content_type', 'content_id', 'text_content', 'user')
        }),
        ('Analysis Results', {
            'fields': (
                'sentiment', 'confidence_score',
                'positive_score', 'negative_score', 'neutral_score'
            )
        }),
        ('Additional Data', {
            'fields': ('keywords', 'emotions'),
            'classes': ('collapse',)
        }),
        ('Model', {
            'fields': ('model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChurnPrediction)
class ChurnPredictionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'churn_probability', 'risk_level',
        'actual_churned', 'retention_action_taken', 'created_at'
    ]
    list_filter = [
        'risk_level', 'actual_churned', 'model', 'created_at'
    ]
    search_fields = ['user__email', 'retention_action_taken']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Prediction', {
            'fields': ('user', 'churn_probability', 'risk_level')
        }),
        ('Analysis', {
            'fields': ('churn_factors', 'feature_importance'),
            'classes': ('collapse',)
        }),
        ('Retention', {
            'fields': ('retention_actions', 'retention_action_taken')
        }),
        ('Outcome', {
            'fields': ('actual_churned',)
        }),
        ('Model', {
            'fields': ('model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
