from django.contrib import admin
from .models import (
    PracticeUnit, 
    PracticeLesson, 
    PracticeChallenge, 
    ChallengeOption, 
    UserProgress, 
    ChallengeProgress
)


class ChallengeOptionInline(admin.TabularInline):
    model = ChallengeOption
    extra = 0
    fields = ['text', 'is_correct', 'image_url', 'audio_url', 'order']


class PracticeChallengeInline(admin.TabularInline):
    model = PracticeChallenge
    extra = 0
    fields = ['type', 'question', 'instruction', 'order']


class PracticeLessonInline(admin.TabularInline):
    model = PracticeLesson
    extra = 0
    fields = ['title', 'order']


@admin.register(PracticeUnit)
class PracticeUnitAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'description']
    inlines = [PracticeLessonInline]
    ordering = ['course', 'order']


@admin.register(PracticeLesson)
class PracticeLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'order', 'created_at']
    list_filter = ['unit__course', 'created_at']
    search_fields = ['title']
    inlines = [PracticeChallengeInline]
    ordering = ['unit__course', 'unit__order', 'order']


@admin.register(PracticeChallenge)
class PracticeChallengeAdmin(admin.ModelAdmin):
    list_display = ['question', 'type', 'lesson', 'order', 'created_at']
    list_filter = ['type', 'lesson__unit__course', 'created_at']
    search_fields = ['question']
    inlines = [ChallengeOptionInline]
    ordering = ['lesson__unit__course', 'lesson__unit__order', 'lesson__order', 'order']


@admin.register(ChallengeOption)
class ChallengeOptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'challenge', 'is_correct', 'order']
    list_filter = ['is_correct', 'challenge__type']
    search_fields = ['text']
    ordering = ['challenge__lesson__unit__course', 'challenge__order', 'order']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'active_course', 'get_hearts', 'points', 'updated_at']
    list_filter = ['active_course', 'updated_at']
    search_fields = ['user__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'get_hearts']

    @admin.display(description='Hearts')
    def get_hearts(self, obj):
        """Display hearts from subscription system."""
        return obj.hearts


@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'completed', 'completed_at']
    list_filter = ['completed', 'challenge__type', 'completed_at']
    search_fields = ['user__name', 'challenge__question']
    readonly_fields = ['completed_at', 'updated_at']


# =============================================================================
# VAPI AI CONVERSATION SESSIONS
# =============================================================================

from django.utils.html import format_html
from .models import VapiSession


@admin.register(VapiSession)
class VapiSessionAdmin(admin.ModelAdmin):
    """
    Histórico de Sessões de Conversação
    """
    list_display = [
        'session_id_short',
        'user',
        'level',
        'domain',
        'duration_display',
        'overall_score_display',
        'created_at',
    ]
    list_filter = ['level', 'domain', 'date', 'created_at']
    search_fields = ['session_id', 'user__email', 'user__first_name']
    readonly_fields = [
        'session_id', 'user', 'level', 'domain', 'duration_minutes',
        'fluency_score', 'pronunciation_score', 'grammar_score',
        'vocabulary_score', 'overall_score', 'total_words',
        'words_per_minute', 'corrections_count', 'improvement_from_last',
        'streak_days', 'created_at', 'date'
    ]
    date_hierarchy = 'date'
    ordering = ['-created_at']

    fieldsets = (
        ('Sessão', {
            'fields': ('session_id', 'user', 'level', 'domain', 'duration_minutes', 'date')
        }),
        ('Pontuações', {
            'fields': ('fluency_score', 'pronunciation_score', 'grammar_score',
                      'vocabulary_score', 'overall_score')
        }),
        ('Métricas de Fala', {
            'fields': ('total_words', 'words_per_minute', 'corrections_count')
        }),
        ('Progresso', {
            'fields': ('improvement_from_last', 'streak_days')
        }),
    )

    def session_id_short(self, obj):
        return obj.session_id[:20] + '...' if len(obj.session_id) > 20 else obj.session_id
    session_id_short.short_description = 'Session ID'

    def duration_display(self, obj):
        return f'{obj.duration_minutes} min'
    duration_display.short_description = 'Duração'

    def overall_score_display(self, obj):
        score = obj.overall_score
        if score >= 80:
            color = 'green'
        elif score >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, score)
    overall_score_display.short_description = 'Score'

    def has_add_permission(self, request):
        return False  # Sessões são criadas automaticamente

    def has_change_permission(self, request, obj=None):
        return False  # Sessões são read-only
