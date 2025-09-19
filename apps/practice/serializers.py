"""
Practice Lab Serializers - API data serialization

This module provides DRF serializers for the Practice Lab system,
handling data serialization for frontend-backend communication.
"""

from rest_framework import serializers
from .models import (
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
    AchievementNotification,
    # AI Speaking Practice Models
    SpeakingExercise,
    SpeakingSession,
    SpeakingTurn,
    SpeakingProgress,
    # AI Listening Practice Models
    ListeningExercise,
    ListeningSession,
    ListeningAttempt,
    ListeningProgress,
    AudioSegment
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
        """Get challenge options, hiding correct answers unless completed"""
        user = self.context.get('request').user if self.context.get('request') else None
        
        if not user:
            # Anonymous user - hide correct answers
            return ChallengeOptionSerializer(obj.options.all(), many=True).data
            
        # Check if user completed this challenge
        try:
            progress = ChallengeProgress.objects.get(user=user, challenge=obj)
            if progress.completed:
                # Show correct answers for completed challenges (practice mode)
                return ChallengeOptionWithAnswerSerializer(obj.options.all(), many=True).data
        except ChallengeProgress.DoesNotExist:
            pass
            
        # Hide correct answers for incomplete challenges
        return ChallengeOptionSerializer(obj.options.all(), many=True).data
    
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
    """
    id = serializers.UUIDField(read_only=True)
    challenges = PracticeChallengeSerializer(many=True, read_only=True)
    completed = serializers.SerializerMethodField()
    
    class Meta:
        model = PracticeLesson
        fields = ['id', 'unit', 'title', 'order', 'challenges', 'completed']
    
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
    """
    id = serializers.UUIDField(read_only=True)
    challenges = PracticeChallengeSerializer(many=True, read_only=True)
    unit = serializers.SerializerMethodField()
    
    class Meta:
        model = PracticeLesson
        fields = ['id', 'title', 'order', 'unit', 'challenges']
    
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
# AI SPEAKING PRACTICE SERIALIZERS
# =============================================================================

class SpeakingExerciseSerializer(serializers.ModelSerializer):
    """
    Speaking Exercise serializer - individual speaking exercises.
    
    Maps speaking exercises for frontend display and interaction.
    """
    id = serializers.UUIDField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    practice_lesson_title = serializers.CharField(source='practice_lesson.title', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    exercise_type_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    
    class Meta:
        model = SpeakingExercise
        fields = [
            'id', 'title', 'description', 'exercise_type', 'exercise_type_display',
            'difficulty', 'difficulty_display', 'target_text', 'conversation_prompt',
            'vocabulary_words', 'pronunciation_weight', 'fluency_weight', 'accuracy_weight',
            'points_reward', 'hearts_cost', 'minimum_score', 'is_active',
            'course_title', 'practice_lesson_title', 'created_at'
        ]


class SpeakingTurnSerializer(serializers.ModelSerializer):
    """
    Speaking Turn serializer - individual conversation turns.
    
    Tracks each user speech input and AI response in a session.
    """
    id = serializers.UUIDField(read_only=True)
    turn_type_display = serializers.CharField(source='get_turn_type_display', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = SpeakingTurn
        fields = [
            'id', 'turn_number', 'turn_type', 'turn_type_display', 'timestamp',
            'audio_url', 'transcribed_text', 'target_text', 'ai_response_text',
            'pronunciation_score', 'fluency_score', 'accuracy_score', 'confidence_score',
            'words_analysis', 'pronunciation_errors', 'grammar_errors', 
            'duration', 'duration_seconds'
        ]
    
    def get_duration_seconds(self, obj):
        """Convert duration to seconds for frontend display"""
        if obj.duration:
            return obj.duration.total_seconds()
        return None


class SpeakingSessionSerializer(serializers.ModelSerializer):
    """
    Speaking Session serializer - complete speaking practice sessions.
    
    Tracks full speaking practice sessions with turns and scores.
    """
    id = serializers.UUIDField(read_only=True)
    exercise = SpeakingExerciseSerializer(read_only=True)
    turns = SpeakingTurnSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = SpeakingSession
        fields = [
            'id', 'exercise', 'status', 'status_display', 'started_at', 'completed_at',
            'total_duration', 'total_duration_minutes', 'turns_count', 'overall_score',
            'pronunciation_score', 'fluency_score', 'accuracy_score', 'points_earned',
            'hearts_used', 'is_passed', 'ai_feedback', 'improvement_suggestions', 'turns'
        ]
    
    def get_total_duration_minutes(self, obj):
        """Convert total duration to minutes for frontend display"""
        if obj.total_duration:
            return round(obj.total_duration.total_seconds() / 60, 1)
        return None


class SpeakingSessionCreateSerializer(serializers.ModelSerializer):
    """
    Speaking Session creation serializer - for starting new sessions.
    
    Used when user starts a new speaking practice session.
    """
    class Meta:
        model = SpeakingSession
        fields = ['exercise']
    
    def create(self, validated_data):
        """Create new speaking session"""
        user = self.context['request'].user
        exercise = validated_data['exercise']
        
        session = SpeakingSession.objects.create(
            user=user,
            exercise=exercise,
            status='ACTIVE'
        )
        
        return session


class SpeakingTurnCreateSerializer(serializers.ModelSerializer):
    """
    Speaking Turn creation serializer - for recording user speech.
    
    Used when user completes a speaking turn in a session.
    """
    audio_file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = SpeakingTurn
        fields = [
            'session', 'turn_type', 'transcribed_text', 'target_text',
            'audio_file', 'pronunciation_score', 'fluency_score', 
            'accuracy_score', 'confidence_score', 'words_analysis',
            'pronunciation_errors', 'grammar_errors', 'duration'
        ]
    
    def create(self, validated_data):
        """Create new speaking turn with automatic turn number"""
        session = validated_data['session']
        
        # Auto-increment turn number
        last_turn = SpeakingTurn.objects.filter(session=session).order_by('-turn_number').first()
        turn_number = (last_turn.turn_number + 1) if last_turn else 1
        
        # Handle audio file if provided
        audio_file = validated_data.pop('audio_file', None)
        if audio_file:
            # In production, upload to S3 and store URL
            # For now, we'll store locally and create URL
            validated_data['audio_url'] = f'/media/speaking/{session.id}/turn_{turn_number}.wav'
        
        validated_data['turn_number'] = turn_number
        
        turn = SpeakingTurn.objects.create(**validated_data)
        
        # Update session turn count
        session.turns_count = turn_number
        session.save()
        
        return turn


class SpeakingProgressSerializer(serializers.ModelSerializer):
    """
    Speaking Progress serializer - user's overall speaking progress.
    
    Tracks comprehensive speaking learning analytics and progress.
    """
    id = serializers.UUIDField(read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = SpeakingProgress
        fields = [
            'id', 'user_name', 'total_sessions', 'total_hours_practiced',
            'total_words_spoken', 'average_pronunciation', 'average_fluency',
            'average_accuracy', 'overall_average', 'beginner_sessions',
            'intermediate_sessions', 'advanced_sessions', 'current_streak',
            'longest_streak', 'weak_phonemes', 'strong_areas',
            'practice_recommendations', 'last_session_date', 'created_at', 'updated_at'
        ]


class SpeakingAnalysisSerializer(serializers.Serializer):
    """
    Speaking Analysis serializer - for AI analysis results.
    
    Represents the output from AI speech analysis services.
    """
    overall_score = serializers.FloatField()
    pronunciation_score = serializers.FloatField()
    fluency_score = serializers.FloatField()
    accuracy_score = serializers.FloatField()
    confidence_score = serializers.FloatField()
    
    transcribed_text = serializers.CharField()
    target_text = serializers.CharField()
    
    word_analysis = serializers.ListField(child=serializers.DictField())
    phoneme_analysis = serializers.ListField(child=serializers.DictField())
    grammar_errors = serializers.ListField(child=serializers.DictField())
    
    feedback_text = serializers.CharField()
    improvement_suggestions = serializers.ListField(child=serializers.CharField())
    next_exercises = serializers.ListField(child=serializers.CharField())


class SpeakingStatsSerializer(serializers.Serializer):
    """
    Speaking Statistics serializer - for dashboard analytics.
    
    Provides aggregated speaking practice statistics for user dashboard.
    """
    total_sessions = serializers.IntegerField()
    total_hours = serializers.FloatField()
    average_score = serializers.FloatField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    sessions_this_week = serializers.IntegerField()
    minutes_this_week = serializers.FloatField()
    improvement_trend = serializers.CharField()  # 'up', 'down', 'stable'
    favorite_exercise_type = serializers.CharField()
    weak_areas = serializers.ListField(child=serializers.CharField())
    strong_areas = serializers.ListField(child=serializers.CharField())


class SpeakingExerciseListSerializer(serializers.ModelSerializer):
    """
    Simplified Speaking Exercise serializer for listing views.
    
    Used for exercise selection screens and recommendations.
    """
    id = serializers.UUIDField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    exercise_type_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    estimated_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = SpeakingExercise
        fields = [
            'id', 'title', 'description', 'exercise_type', 'exercise_type_display',
            'difficulty', 'difficulty_display', 'points_reward', 'hearts_cost',
            'course_title', 'estimated_duration'
        ]
    
    def get_estimated_duration(self, obj):
        """Estimate exercise duration based on type"""
        duration_map = {
            'PRONUNCIATION': 5,
            'CONVERSATION': 10,
            'READING_ALOUD': 7,
            'VOCABULARY_SPEAKING': 8
        }
        return duration_map.get(obj.exercise_type, 5)


class QuickSpeakingFeedbackSerializer(serializers.Serializer):
    """
    Quick Speaking Feedback serializer - for real-time feedback.
    
    Used for real-time audio analysis feedback during recording.
    """
    confidence = serializers.FloatField()
    volume = serializers.FloatField()
    clarity = serializers.FloatField()
    timestamp = serializers.DateTimeField()


# =============================================================================
# 🎧 AI LISTENING PRACTICE SERIALIZERS
# =============================================================================

class AudioSegmentSerializer(serializers.ModelSerializer):
    """
    Audio Segment serializer - for segmented audio content.
    
    Represents specific portions of listening exercises for focused practice.
    """
    id = serializers.UUIDField(read_only=True)
    listening_exercise_title = serializers.CharField(source='listening_exercise.title', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    vocabulary_complexity_display = serializers.CharField(source='get_vocabulary_complexity_display', read_only=True)
    
    class Meta:
        model = AudioSegment
        fields = [
            'id', 'title', 'start_time', 'end_time', 'segment_transcript',
            'difficulty_rating', 'speech_rate', 'vocabulary_complexity', 
            'vocabulary_complexity_display', 'focused_grammar_points',
            'key_phrases', 'cultural_context', 'listening_exercise_title',
            'duration_seconds'
        ]
    
    def get_duration_seconds(self, obj):
        """Get segment duration in seconds"""
        duration = obj.get_duration()
        if duration:
            return duration.total_seconds()
        return None


class ListeningExerciseSerializer(serializers.ModelSerializer):
    """
    Listening Exercise serializer - comprehensive listening exercises.
    
    Maps listening exercises for frontend display with all audio content.
    """
    id = serializers.UUIDField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    practice_lesson_title = serializers.CharField(source='practice_lesson.title', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    exercise_type_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    accent_type_display = serializers.CharField(source='get_accent_type_display', read_only=True)
    audio_segments = AudioSegmentSerializer(many=True, read_only=True)
    audio_duration_minutes = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ListeningExercise
        fields = [
            'id', 'title', 'description', 'exercise_type', 'exercise_type_display',
            'difficulty', 'difficulty_display', 'accent_type', 'accent_type_display',
            'audio_url', 'audio_duration', 'audio_duration_minutes', 'transcript',
            'allow_replay', 'max_replays', 'playback_speeds', 'questions',
            'correct_answers', 'question_count', 'key_vocabulary', 'vocabulary_definitions',
            'points_reward', 'hearts_cost', 'minimum_score', 'is_active',
            'course_title', 'practice_lesson_title', 'audio_segments', 'created_at'
        ]
    
    def get_audio_duration_minutes(self, obj):
        """Convert audio duration to minutes for display"""
        if obj.audio_duration:
            return round(obj.audio_duration.total_seconds() / 60, 1)
        return None
    
    def get_question_count(self, obj):
        """Get number of comprehension questions"""
        return len(obj.questions) if obj.questions else 0


class ListeningAttemptSerializer(serializers.ModelSerializer):
    """
    Listening Attempt serializer - individual question attempts.
    
    Tracks each attempt to answer listening comprehension questions.
    """
    id = serializers.UUIDField(read_only=True)
    attempt_type_display = serializers.CharField(source='get_attempt_type_display', read_only=True)
    time_to_answer_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ListeningAttempt
        fields = [
            'id', 'attempt_number', 'attempt_type', 'attempt_type_display',
            'timestamp', 'question_text', 'question_index', 'user_answer',
            'correct_answer', 'is_correct', 'partial_credit', 'similarity_score',
            'time_to_answer', 'time_to_answer_seconds', 'audio_replays_before_answer',
            'feedback_text', 'hints_used'
        ]
    
    def get_time_to_answer_seconds(self, obj):
        """Convert time to answer to seconds"""
        if obj.time_to_answer:
            return obj.time_to_answer.total_seconds()
        return None


class ListeningSessionSerializer(serializers.ModelSerializer):
    """
    Listening Session serializer - complete listening practice sessions.
    
    Tracks full listening sessions with attempts and comprehensive scoring.
    """
    id = serializers.UUIDField(read_only=True)
    exercise = ListeningExerciseSerializer(read_only=True)
    attempts = ListeningAttemptSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_duration_minutes = serializers.SerializerMethodField()
    accuracy_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ListeningSession
        fields = [
            'id', 'exercise', 'status', 'status_display', 'started_at', 'completed_at',
            'total_duration', 'total_duration_minutes', 'audio_replays_used',
            'playback_speed_used', 'user_answers', 'dictation_attempts',
            'comprehension_score', 'accuracy_score', 'vocabulary_score',
            'overall_score', 'accuracy_percentage', 'points_earned', 'hearts_used',
            'is_passed', 'detailed_feedback', 'improvement_areas', 'attempts'
        ]
    
    def get_total_duration_minutes(self, obj):
        """Convert total duration to minutes"""
        if obj.total_duration:
            return round(obj.total_duration.total_seconds() / 60, 1)
        return None
    
    def get_accuracy_percentage(self, obj):
        """Calculate accuracy percentage from attempts"""
        if obj.attempts.exists():
            correct_attempts = obj.attempts.filter(is_correct=True).count()
            total_attempts = obj.attempts.count()
            return round((correct_attempts / total_attempts) * 100, 1)
        return None


class ListeningSessionCreateSerializer(serializers.ModelSerializer):
    """
    Listening Session creation serializer - for starting new sessions.
    
    Used when user starts a new listening practice session.
    """
    class Meta:
        model = ListeningSession
        fields = ['exercise']
    
    def create(self, validated_data):
        """Create new listening session"""
        user = self.context['request'].user
        exercise = validated_data['exercise']
        
        session = ListeningSession.objects.create(
            user=user,
            exercise=exercise,
            status='ACTIVE'
        )
        
        return session


class ListeningAttemptCreateSerializer(serializers.ModelSerializer):
    """
    Listening Attempt creation serializer - for recording user answers.
    
    Used when user submits an answer to a listening question.
    """
    class Meta:
        model = ListeningAttempt
        fields = [
            'session', 'attempt_type', 'question_text', 'question_index',
            'user_answer', 'correct_answer', 'is_correct', 'partial_credit',
            'similarity_score', 'time_to_answer', 'audio_replays_before_answer',
            'feedback_text', 'hints_used'
        ]
    
    def create(self, validated_data):
        """Create new listening attempt with automatic attempt number"""
        session = validated_data['session']
        
        # Auto-increment attempt number
        last_attempt = ListeningAttempt.objects.filter(session=session).order_by('-attempt_number').first()
        attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1
        
        validated_data['attempt_number'] = attempt_number
        
        attempt = ListeningAttempt.objects.create(**validated_data)
        
        return attempt


class ListeningProgressSerializer(serializers.ModelSerializer):
    """
    Listening Progress serializer - user's overall listening progress.
    
    Tracks comprehensive listening learning analytics and progress.
    """
    id = serializers.UUIDField(read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    comfort_speed_range = serializers.SerializerMethodField()
    preferred_exercise_types = serializers.SerializerMethodField()
    
    class Meta:
        model = ListeningProgress
        fields = [
            'id', 'user_name', 'total_sessions', 'total_hours_listened',
            'total_audio_content', 'avg_comprehension_score', 'avg_dictation_score',
            'avg_vocabulary_score', 'overall_listening_score', 'beginner_sessions',
            'intermediate_sessions', 'advanced_sessions', 'american_sessions',
            'british_sessions', 'other_accents_sessions', 'preferred_speed',
            'comfort_speed_range', 'speeds_comfort_level', 'strong_exercise_types',
            'weak_exercise_types', 'preferred_exercise_types', 'difficult_vocabulary',
            'mastered_vocabulary', 'recommended_exercises', 'suggested_focus_areas',
            'current_listening_streak', 'longest_listening_streak',
            'perfect_comprehension_count', 'last_session_date', 'created_at', 'updated_at'
        ]
    
    def get_comfort_speed_range(self, obj):
        """Get comfortable speed range from speeds_comfort_level"""
        if not obj.speeds_comfort_level:
            return None
        
        comfortable_speeds = [
            speed for speed, comfort in obj.speeds_comfort_level.items()
            if comfort >= 70  # 70% comfort threshold
        ]
        
        if comfortable_speeds:
            speeds = sorted([float(s) for s in comfortable_speeds])
            return f"{speeds[0]}x - {speeds[-1]}x"
        return None
    
    def get_preferred_exercise_types(self, obj):
        """Get top 3 preferred exercise types based on performance"""
        if not obj.strong_exercise_types:
            return []
        return obj.strong_exercise_types[:3]


class ListeningAnalysisSerializer(serializers.Serializer):
    """
    Listening Analysis serializer - for AI analysis results.
    
    Represents the output from listening comprehension analysis.
    """
    overall_score = serializers.FloatField()
    comprehension_score = serializers.FloatField()
    accuracy_score = serializers.FloatField()
    vocabulary_score = serializers.FloatField()
    speed_adaptation_score = serializers.FloatField()
    
    user_answers = serializers.ListField(child=serializers.CharField())
    correct_answers = serializers.ListField(child=serializers.CharField())
    answer_analysis = serializers.ListField(child=serializers.DictField())
    
    vocabulary_gaps = serializers.ListField(child=serializers.DictField())
    comprehension_patterns = serializers.ListField(child=serializers.DictField())
    
    feedback_text = serializers.CharField()
    improvement_suggestions = serializers.ListField(child=serializers.CharField())
    recommended_exercises = serializers.ListField(child=serializers.CharField())


class ListeningStatsSerializer(serializers.Serializer):
    """
    Listening Statistics serializer - for dashboard analytics.
    
    Provides aggregated listening practice statistics for user dashboard.
    """
    total_sessions = serializers.IntegerField()
    total_hours = serializers.FloatField()
    average_score = serializers.FloatField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    sessions_this_week = serializers.IntegerField()
    minutes_this_week = serializers.FloatField()
    improvement_trend = serializers.CharField()  # 'up', 'down', 'stable'
    favorite_accent = serializers.CharField()
    comfortable_speed = serializers.CharField()
    strong_areas = serializers.ListField(child=serializers.CharField())
    improvement_areas = serializers.ListField(child=serializers.CharField())


class ListeningExerciseListSerializer(serializers.ModelSerializer):
    """
    Simplified Listening Exercise serializer for listing views.
    
    Used for exercise selection screens and recommendations.
    """
    id = serializers.UUIDField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    exercise_type_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    accent_type_display = serializers.CharField(source='get_accent_type_display', read_only=True)
    audio_duration_minutes = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ListeningExercise
        fields = [
            'id', 'title', 'description', 'exercise_type', 'exercise_type_display',
            'difficulty', 'difficulty_display', 'accent_type', 'accent_type_display',
            'audio_duration_minutes', 'question_count', 'points_reward', 'hearts_cost',
            'course_title'
        ]
    
    def get_audio_duration_minutes(self, obj):
        """Convert audio duration to minutes"""
        if obj.audio_duration:
            return round(obj.audio_duration.total_seconds() / 60, 1)
        return None
    
    def get_question_count(self, obj):
        """Get number of questions"""
        return len(obj.questions) if obj.questions else 0


class QuickListeningFeedbackSerializer(serializers.Serializer):
    """
    Quick Listening Feedback serializer - for real-time feedback.
    
    Used for live feedback during listening exercises.
    """
    current_question = serializers.IntegerField()
    questions_remaining = serializers.IntegerField()
    current_score = serializers.FloatField()
    time_elapsed = serializers.IntegerField()  # seconds
    replays_used = serializers.IntegerField()
    replays_remaining = serializers.IntegerField()
    current_speed = serializers.FloatField()
    timestamp = serializers.DateTimeField()