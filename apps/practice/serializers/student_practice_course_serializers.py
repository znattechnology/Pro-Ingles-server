"""
Practice Lab Serializers - API data serialization

This module provides DRF serializers for the Practice Lab system,
handling data serialization for frontend-backend communication.
"""

from rest_framework import serializers
from ..models import (
    PracticeUnit, 
    PracticeLesson, 
    PracticeChallenge, 
    ChallengeOption, 
    UserProgress, 
    ChallengeProgress,
    UserLeague,
    LeaguePromotion,
    Competition,
    CompetitionParticipant,
    LeaderboardSnapshot,
    UserStreak,
    Achievement,
    UserAchievement,
    AchievementCategory,
    AchievementNotification
    # Note: AI Speaking/Listening models removed - now handled by Vapi integration
)


class ChallengeOptionSerializer(serializers.ModelSerializer):
    """
    Challenge Option serializer - for multiple choice answers.
    
    Maps to frontend challengeOptions structure from client project.
    """
    id = serializers.UUIDField(read_only=True)
    imageSrc = serializers.URLField(source='image_url', allow_null=True, required=False)
    audioSrc = serializers.URLField(source='audio_url', allow_null=True, required=False)
    
    class Meta:
        model = ChallengeOption
        fields = [
            'id', 'text', 'is_correct', 'imageSrc', 
            'audioSrc', 'order'
        ]
        extra_kwargs = {
            'is_correct': {'write_only': True},  # Don't expose correct answer to frontend
        }


class ChallengeOptionWithAnswerSerializer(serializers.ModelSerializer):
    """
    Challenge Option serializer WITH correct answers - for practice mode.
    Used when user has already completed the challenge.
    """
    id = serializers.UUIDField(read_only=True)
    imageSrc = serializers.URLField(source='image_url', allow_null=True, required=False)
    audioSrc = serializers.URLField(source='audio_url', allow_null=True, required=False)
    
    class Meta:
        model = ChallengeOption
        fields = [
            'id', 'challenge', 'text', 'is_correct', 'imageSrc', 
            'audioSrc', 'order'
        ]


class ChallengeOptionCreateSerializer(serializers.ModelSerializer):
    """
    Challenge Option creation serializer - for creating new options.
    Accepts challenge_id from frontend and maps it to challenge field.
    """
    id = serializers.UUIDField(read_only=True)
    challenge_id = serializers.UUIDField(write_only=True)
    imageSrc = serializers.URLField(source='image_url', allow_null=True, required=False)
    audioSrc = serializers.URLField(source='audio_url', allow_null=True, required=False)
    
    class Meta:
        model = ChallengeOption
        fields = [
            'id', 'challenge_id', 'text', 'is_correct', 'imageSrc', 
            'audioSrc', 'order'
        ]
    
    def create(self, validated_data):
        """Create challenge option with proper challenge mapping"""
        challenge_id = validated_data.pop('challenge_id')
        
        try:
            challenge = PracticeChallenge.objects.get(id=challenge_id)
            validated_data['challenge'] = challenge
        except PracticeChallenge.DoesNotExist:
            raise serializers.ValidationError(f"Challenge with id {challenge_id} does not exist")
        
        return super().create(validated_data)


class ChallengeProgressSerializer(serializers.ModelSerializer):
    """
    Challenge Progress serializer - tracks user completion.
    
    Maps to frontend challengeProgress structure from client project.
    """
    id = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = ChallengeProgress
        fields = ['id', 'completed', 'completed_at']


class PracticeChallengeSerializer(serializers.ModelSerializer):
    """
    Practice Challenge serializer - individual exercises.

    Maps to frontend challenges structure from client project.
    Includes challenge options and user progress.
    Options are returned in random order.
    """
    id = serializers.UUIDField(read_only=True)
    options = serializers.SerializerMethodField()
    challenge_progress = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta:
        model = PracticeChallenge
        fields = [
            'id', 'lesson', 'type', 'question', 'order',
            'options', 'challenge_progress', 'completed'
        ]

    def get_options(self, obj):
        """Get challenge options in random order, hiding correct answers unless completed."""
        import random

        user = self.context.get('request').user if self.context.get('request') else None

        # Get all options and shuffle them
        options_list = list(obj.options.all())
        random.shuffle(options_list)

        if not user:
            # Anonymous user - hide correct answers
            return ChallengeOptionSerializer(options_list, many=True).data

        # Check if user completed this challenge
        try:
            progress = ChallengeProgress.objects.get(user=user, challenge=obj)
            if progress.completed:
                # Show correct answers for completed challenges (practice mode)
                return ChallengeOptionWithAnswerSerializer(options_list, many=True).data
        except ChallengeProgress.DoesNotExist:
            pass

        # Hide correct answers for incomplete challenges
        return ChallengeOptionSerializer(options_list, many=True).data
    
    def get_challenge_progress(self, obj):
        """Get user's progress for this challenge"""
        user = self.context.get('request').user if self.context.get('request') else None
        
        if not user:
            return []
            
        try:
            progress = ChallengeProgress.objects.get(user=user, challenge=obj)
            return [ChallengeProgressSerializer(progress).data]
        except ChallengeProgress.DoesNotExist:
            return []
    
    def get_completed(self, obj):
        """Check if user completed this challenge"""
        user = self.context.get('request').user if self.context.get('request') else None
        
        if not user:
            return False
            
        try:
            progress = ChallengeProgress.objects.get(user=user, challenge=obj)
            return progress.completed
        except ChallengeProgress.DoesNotExist:
            return False


class PracticeLessonSerializer(serializers.ModelSerializer):
    """
    Practice Lesson serializer - learning sessions.

    Maps to frontend lessons structure from client project.
    Includes challenges and completion status.
    Challenges are returned in random order for students.
    """
    id = serializers.UUIDField(read_only=True)
    challenges = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta:
        model = PracticeLesson
        fields = ['id', 'unit', 'title', 'order', 'challenges', 'completed']

    def get_challenges(self, obj):
        """Get challenges in random order."""
        import random

        challenges_list = list(obj.challenges.all())
        random.shuffle(challenges_list)

        return PracticeChallengeSerializer(
            challenges_list,
            many=True,
            context=self.context
        ).data

    def get_completed(self, obj):
        """Check if user completed all challenges in this lesson"""
        user = self.context.get('request').user if self.context.get('request') else None

        if not user:
            return False

        if obj.challenges.count() == 0:
            return False

        # Check if all challenges are completed
        completed_count = ChallengeProgress.objects.filter(
            user=user,
            challenge__lesson=obj,
            completed=True
        ).count()

        return completed_count == obj.challenges.count()


class PracticeUnitSerializer(serializers.ModelSerializer):
    """
    Practice Unit serializer - groups of lessons.
    
    Maps to frontend units structure from client project.
    Includes lessons with progress tracking.
    """
    id = serializers.UUIDField(read_only=True)
    lessons = PracticeLessonSerializer(many=True, read_only=True)
    
    class Meta:
        model = PracticeUnit
        fields = ['id', 'course', 'title', 'description', 'order', 'lessons']


class UserProgressSerializer(serializers.ModelSerializer):
    """
    User Progress serializer - gamification stats.
    
    Maps to frontend userProgress structure from client project.
    Manages hearts, points, and active course.
    """
    active_course = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProgress
        fields = [
            'hearts', 'points', 'user_image_src', 
            'active_course', 'created_at', 'updated_at'
        ]
    
    def get_active_course(self, obj):
        """Get active course details"""
        if obj.active_course:
            return {
                'id': str(obj.active_course.id),
                'title': obj.active_course.title,
                'image': obj.active_course.image,
            }
        return None


class ChallengeProgressCreateSerializer(serializers.ModelSerializer):
    """
    Challenge Progress creation serializer - for completing challenges.
    
    Used when user submits an answer to a challenge.
    """
    class Meta:
        model = ChallengeProgress
        fields = ['challenge', 'completed']
        
    def create(self, validated_data):
        """Create or update challenge progress"""
        user = self.context['request'].user
        challenge = validated_data['challenge']
        
        progress, created = ChallengeProgress.objects.get_or_create(
            user=user,
            challenge=challenge,
            defaults={'completed': validated_data['completed']}
        )
        
        if not created:
            progress.completed = validated_data['completed']
            progress.save()
            
        return progress


class UserProgressUpdateSerializer(serializers.ModelSerializer):
    """
    User Progress update serializer - for hearts/points management.
    
    Used when updating user hearts and points after challenges.
    """
    class Meta:
        model = UserProgress
        fields = ['hearts', 'points', 'active_course']
        
    def update(self, instance, validated_data):
        """Update user progress with validation"""
        # Ensure hearts don't exceed 5 or go below 0
        if 'hearts' in validated_data:
            validated_data['hearts'] = max(0, min(5, validated_data['hearts']))
            
        return super().update(instance, validated_data)


class LessonDetailSerializer(serializers.ModelSerializer):
    """
    Detailed lesson serializer - for quiz page.

    Used for the lesson/quiz page, includes all challenges with options.
    Maps to the getLesson query from client project.
    Challenges are returned in random order.
    """
    id = serializers.UUIDField(read_only=True)
    challenges = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    class Meta:
        model = PracticeLesson
        fields = ['id', 'title', 'order', 'unit', 'challenges']

    def get_challenges(self, obj):
        """Get challenges in random order."""
        import random

        challenges_list = list(obj.challenges.all())
        random.shuffle(challenges_list)

        return PracticeChallengeSerializer(
            challenges_list,
            many=True,
            context=self.context
        ).data

    def get_unit(self, obj):
        """Get unit details"""
        return {
            'id': str(obj.unit.id),
            'title': obj.unit.title,
            'description': obj.unit.description,
        }


# Leaderboard Serializers

class UserStreakSerializer(serializers.ModelSerializer):
    """User Streak serializer for leaderboard data"""
    class Meta:
        model = UserStreak
        fields = ['current_streak', 'longest_streak', 'last_practice_date']


class UserLeagueSerializer(serializers.ModelSerializer):
    """User League serializer for leaderboard data"""
    league_info = serializers.SerializerMethodField()
    
    class Meta:
        model = UserLeague
        fields = ['current_league', 'points_when_promoted', 'promoted_at', 'league_info']
    
    def get_league_info(self, obj):
        """Get detailed league information"""
        return UserLeague.get_league_info(obj.current_league)


class LeaderboardEntrySerializer(serializers.Serializer):
    """Leaderboard entry serializer for ranking display"""
    id = serializers.CharField()
    rank = serializers.IntegerField()
    username = serializers.CharField()
    avatar = serializers.CharField(required=False, allow_null=True)
    points = serializers.IntegerField()
    streak = serializers.IntegerField()
    league = serializers.CharField()
    change = serializers.CharField()  # 'up', 'down', 'same', 'new'
    changeAmount = serializers.IntegerField(required=False, allow_null=True)
    isCurrentUser = serializers.BooleanField(default=False)


class LeagueInfoSerializer(serializers.Serializer):
    """League information serializer"""
    id = serializers.CharField()
    name = serializers.CharField()
    icon = serializers.CharField()
    color = serializers.CharField()
    minPoints = serializers.IntegerField()
    maxPoints = serializers.IntegerField(allow_null=True)
    participants = serializers.IntegerField()


class CompetitionSerializer(serializers.ModelSerializer):
    """Competition serializer for competition display"""
    participants = serializers.SerializerMethodField()
    currentPosition = serializers.SerializerMethodField()
    startDate = serializers.SerializerMethodField()
    endDate = serializers.SerializerMethodField()
    prize = serializers.SerializerMethodField()
    
    class Meta:
        model = Competition
        fields = [
            'id', 'title', 'description', 'type', 'status',
            'participants', 'currentPosition', 'startDate', 'endDate', 'prize'
        ]
    
    def get_participants(self, obj):
        """Get number of participants"""
        return obj.participant_count
    
    def get_currentPosition(self, obj):
        """Get current user's position in competition"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
            
        try:
            participant = CompetitionParticipant.objects.get(
                competition=obj, 
                user=request.user
            )
            return participant.current_rank
        except CompetitionParticipant.DoesNotExist:
            return None
    
    def get_startDate(self, obj):
        """Format start date for display"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.start_date
        
        if diff.days == 0:
            return "hoje"
        elif diff.days == 1:
            return "ontem"
        elif diff.days < 0:
            return f"em {abs(diff.days)} dias"
        else:
            return f"{diff.days} dias atrás"
    
    def get_endDate(self, obj):
        """Format end date for display"""
        from django.utils import timezone
        now = timezone.now()
        diff = obj.end_date - now
        
        if diff.days == 0:
            return "hoje"
        elif diff.days == 1:
            return "amanhã"
        elif diff.days < 0:
            return "terminado"
        else:
            return f"em {diff.days} dias"
    
    def get_prize(self, obj):
        """Get prize based on user's potential position"""
        return obj.first_place_prize  # For now, show top prize


class CompetitionParticipantSerializer(serializers.ModelSerializer):
    """Competition participant serializer"""
    username = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = CompetitionParticipant
        fields = [
            'id', 'username', 'points_earned', 'challenges_completed',
            'lessons_completed', 'streak_days', 'current_rank', 'best_rank'
        ]


class LeaderboardSnapshotSerializer(serializers.ModelSerializer):
    """Leaderboard snapshot serializer for historical data"""
    username = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = LeaderboardSnapshot
        fields = [
            'id', 'username', 'rank', 'points', 'league',
            'rank_change', 'points_change', 'snapshot_date', 'snapshot_type'
        ]


# Achievement Serializers

class AchievementSerializer(serializers.ModelSerializer):
    """Achievement serializer for achievement definitions"""
    rarity_color = serializers.CharField(source='get_rarity_color', read_only=True)
    unlocked_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Achievement
        fields = [
            'id', 'title', 'description', 'icon', 'category', 'rarity',
            'points', 'requirement_type', 'requirement_target', 'requirement_unit',
            'is_active', 'is_secret', 'order', 'created_at', 'rarity_color', 'unlocked_count'
        ]
    
    def get_unlocked_count(self, obj):
        """Get count of users who unlocked this achievement"""
        return obj.user_achievements.filter(is_unlocked=True).count()


class UserAchievementSerializer(serializers.ModelSerializer):
    """User achievement serializer with progress tracking"""
    achievement = AchievementSerializer(read_only=True)
    progress_percentage = serializers.FloatField(source='get_progress_percentage', read_only=True)
    unlocked_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAchievement
        fields = [
            'id', 'achievement', 'is_unlocked', 'current_progress',
            'unlocked_at', 'unlocked_at_formatted', 'progress_percentage'
        ]
    
    def get_unlocked_at_formatted(self, obj):
        """Format unlock date for display"""
        if not obj.unlocked_at:
            return None
            
        from datetime import datetime
        from django.utils import timezone
        
        now = timezone.now()
        diff = now - obj.unlocked_at
        
        if diff.days == 0:
            return "hoje"
        elif diff.days == 1:
            return "1 dia atrás"
        elif diff.days < 7:
            return f"{diff.days} dias atrás"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} semana{'s' if weeks > 1 else ''} atrás"
        else:
            months = diff.days // 30
            return f"{months} mês{'es' if months > 1 else ''} atrás"


class AchievementStatsSerializer(serializers.Serializer):
    """Serializer for achievement statistics"""
    totalUnlocked = serializers.IntegerField()
    totalAvailable = serializers.IntegerField()
    totalPoints = serializers.IntegerField()
    rareAchievements = serializers.IntegerField()
    recentUnlocked = serializers.IntegerField()


class AchievementCategorySerializer(serializers.ModelSerializer):
    """Achievement category serializer"""
    achievement_count = serializers.SerializerMethodField()
    unlocked_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AchievementCategory
        fields = [
            'name', 'display_name', 'description', 'icon_class',
            'color', 'order', 'achievement_count', 'unlocked_count'
        ]
    
    def get_achievement_count(self, obj):
        """Get total achievements in this category"""
        return Achievement.objects.filter(category=obj.name, is_active=True).count()
    
    def get_unlocked_count(self, obj):
        """Get unlocked achievements in this category for current user"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
            
        return UserAchievement.objects.filter(
            user=request.user,
            achievement__category=obj.name,
            is_unlocked=True
        ).count()


class AchievementNotificationSerializer(serializers.ModelSerializer):
    """Achievement notification serializer"""
    achievement = AchievementSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = AchievementNotification
        fields = [
            'id', 'achievement', 'is_read', 'is_celebrated',
            'created_at', 'time_ago'
        ]
    
    def get_time_ago(self, obj):
        """Get time since notification was created"""
        from datetime import datetime
        from django.utils import timezone
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.total_seconds() < 60:
            return "agora"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes} min atrás"
        elif diff.days == 0:
            hours = int(diff.total_seconds() // 3600)
            return f"{hours}h atrás"
        elif diff.days == 1:
            return "ontem"
        else:
            return f"{diff.days} dias atrás"


class DetailedAchievementSerializer(serializers.Serializer):
    """Detailed achievement data for frontend page"""
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    icon = serializers.CharField()
    category = serializers.CharField()
    rarity = serializers.CharField()
    points = serializers.IntegerField()
    isUnlocked = serializers.BooleanField()
    unlockedAt = serializers.CharField(allow_null=True)
    progress = serializers.DictField(allow_null=True)




# =============================================================================
# 🚫 DEPRECATED: AI SPEAKING & LISTENING PRACTICE SERIALIZERS  
# =============================================================================
# 
# NOTICE: All speaking and listening practice serializers have been removed
# as they are now handled by Vapi AI conversation practice integration.
#
# For conversation practice serialization, see the Vapi conversation serializers
# in the main practice_courses/serializers.py file instead.
#
# Removed serializers (now obsolete):
# - SpeakingExerciseSerializer, SpeakingSessionSerializer, SpeakingTurnSerializer
# - ListeningExerciseSerializer, ListeningSessionSerializer, ListeningAttemptSerializer  
# - And all related progress and analysis serializers
#
# =============================================================================
