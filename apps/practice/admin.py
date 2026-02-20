from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PracticeUnit,
    PracticeLesson,
    PracticeChallenge,
    ChallengeOption,
    UserProgress,
    ChallengeProgress,
    # Gamification models
    Achievement,
    UserAchievement,
    AchievementCategory,
    AchievementNotification,
    UserLeague,
    UserStreak,
    Competition,
    CompetitionParticipant,
    LeaderboardSnapshot,
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


# =============================================================================
# GAMIFICATION MODELS - Achievements, Leaderboard, Competitions
# =============================================================================

class UserAchievementInline(admin.TabularInline):
    model = UserAchievement
    extra = 0
    readonly_fields = ['user', 'current_progress', 'is_unlocked', 'unlocked_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = [
        'icon', 'title', 'category', 'rarity_display', 'points',
        'requirement_type', 'requirement_target', 'is_active', 'unlocked_count'
    ]
    list_filter = ['category', 'rarity', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active', 'points']
    ordering = ['category', 'order']
    inlines = [UserAchievementInline]

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('title', 'description', 'icon', 'category', 'rarity', 'points')
        }),
        ('Critérios de Desbloqueio', {
            'fields': ('requirement_type', 'requirement_target', 'requirement_unit')
        }),
        ('Configurações', {
            'fields': ('is_active', 'is_secret', 'order')
        }),
    )

    def rarity_display(self, obj):
        colors = {
            'common': '#9CA3AF',
            'rare': '#3B82F6',
            'epic': '#8B5CF6',
            'legendary': '#F59E0B'
        }
        color = colors.get(obj.rarity, '#9CA3AF')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.rarity.upper()
        )
    rarity_display.short_description = 'Raridade'

    def unlocked_count(self, obj):
        return UserAchievement.objects.filter(achievement=obj, is_unlocked=True).count()
    unlocked_count.short_description = 'Desbloqueadas'


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'current_progress', 'progress_bar', 'is_unlocked', 'unlocked_at']
    list_filter = ['is_unlocked', 'achievement__category', 'achievement__rarity']
    search_fields = ['user__name', 'user__email', 'achievement__title']
    readonly_fields = ['unlocked_at']
    ordering = ['-unlocked_at', '-current_progress']

    def progress_bar(self, obj):
        target = obj.achievement.requirement_target
        progress = min(obj.current_progress, target)
        percentage = (progress / target * 100) if target > 0 else 0
        color = 'green' if obj.is_unlocked else 'blue'
        return format_html(
            '<div style="width:100px;background:#374151;border-radius:4px;">'
            '<div style="width:{}%;background:{};height:8px;border-radius:4px;"></div>'
            '</div> {}%',
            percentage, color, int(percentage)
        )
    progress_bar.short_description = 'Progresso'


@admin.register(AchievementCategory)
class AchievementCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'icon_class', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    ordering = ['order']


@admin.register(AchievementNotification)
class AchievementNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'is_read', 'is_celebrated', 'created_at']
    list_filter = ['is_read', 'is_celebrated', 'created_at']
    search_fields = ['user__name', 'achievement__title']
    readonly_fields = ['created_at', 'read_at']


@admin.register(UserLeague)
class UserLeagueAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_league_display', 'points_when_promoted', 'promoted_at']
    list_filter = ['current_league', 'promoted_at']
    search_fields = ['user__name', 'user__email']
    ordering = ['-points_when_promoted']

    def current_league_display(self, obj):
        colors = {
            'bronze': '#CD7F32',
            'silver': '#C0C0C0',
            'gold': '#FFD700',
            'diamond': '#B9F2FF'
        }
        icons = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'diamond': '💎'
        }
        color = colors.get(obj.current_league, '#9CA3AF')
        icon = icons.get(obj.current_league, '')
        return format_html(
            '{} <span style="color: {}; font-weight: bold;">{}</span>',
            icon, color, obj.current_league.upper()
        )
    current_league_display.short_description = 'Liga'


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'last_practice_date']
    list_filter = ['last_practice_date']
    search_fields = ['user__name', 'user__email']
    ordering = ['-current_streak']


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'start_date', 'end_date', 'participant_count', 'prize']
    list_filter = ['status', 'start_date']
    search_fields = ['title', 'description']
    ordering = ['-start_date']

    def participant_count(self, obj):
        return CompetitionParticipant.objects.filter(competition=obj).count()
    participant_count.short_description = 'Participantes'


@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'competition', 'points_earned', 'current_rank', 'joined_at']
    list_filter = ['competition', 'joined_at']
    search_fields = ['user__name', 'competition__title']
    ordering = ['competition', 'current_rank']


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ['user', 'snapshot_type', 'rank', 'points', 'league', 'rank_change_display', 'snapshot_date']
    list_filter = ['snapshot_type', 'league', 'snapshot_date']
    search_fields = ['user__name', 'user__email']
    ordering = ['-snapshot_date', 'rank']
    readonly_fields = ['snapshot_date']

    def rank_change_display(self, obj):
        if obj.rank_change > 0:
            return format_html('<span style="color: green;">▲ {}</span>', obj.rank_change)
        elif obj.rank_change < 0:
            return format_html('<span style="color: red;">▼ {}</span>', abs(obj.rank_change))
        else:
            return format_html('<span style="color: gray;">━</span>')
    rank_change_display.short_description = 'Mudança'
