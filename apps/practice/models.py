"""
Practice Lab Models - Duolingo-style learning system

This module implements the database models for the ProEnglish practice laboratory,
providing a gamified learning experience similar to Duolingo.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.courses.models import Course

User = get_user_model()


class PracticeUnit(models.Model):
    """
    Practice Unit - Groups related lessons together.
    
    Maps to Drizzle 'units' table from the client project.
    Example: "Basic Vocabulary", "Conversations", "Grammar Fundamentals"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='practice_units'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(help_text="Display order within the course")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class PracticeLesson(models.Model):
    """
    Practice Lesson - Individual learning sessions within a unit.
    
    Maps to Drizzle 'lessons' table from the client project.
    Example: "Colors and Numbers", "Introducing Yourself"
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(
        PracticeUnit, 
        on_delete=models.CASCADE, 
        related_name='lessons'
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(help_text="Display order within the unit")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['unit', 'order']
    
    def __str__(self):
        return f"{self.unit.title} - {self.title}"


class PracticeChallenge(models.Model):
    """
    Practice Challenge - Individual exercises/questions.
    
    Maps to Drizzle 'challenges' table from the client project.
    Supports different challenge types like SELECT (multiple choice) and ASSIST (translation).
    """
    CHALLENGE_TYPES = [
        ('SELECT', 'Select - Multiple Choice'),
        ('ASSIST', 'Assist - Translation/Help'),
        ('FILL_BLANK', 'Fill in the Blank'),
        ('TRANSLATION', 'Translation'),
        ('LISTENING', 'Listening Comprehension'),
        ('SPEAKING', 'Speaking/Pronunciation'),
        ('MATCH_PAIRS', 'Match Pairs'),
        ('SENTENCE_ORDER', 'Sentence Order'),
        ('TRUE_FALSE', 'True/False Questions'),
        
        # 🆕 AI SPEAKING CHALLENGE TYPES
        ('PRONUNCIATION', 'Pronunciation Practice'),
        ('CONVERSATION', 'AI Conversation'),
        ('READING_ALOUD', 'Reading Aloud'),
        ('VOCABULARY_SPEAKING', 'Vocabulary Speaking'),
        
        # 🆕 AI LISTENING CHALLENGE TYPES
        ('AUDIO_COMPREHENSION', 'Audio Comprehension'),
        ('DICTATION', 'Dictation Practice'),
        ('CONVERSATION_LISTENING', 'Conversation Listening'),
        ('ACCENT_RECOGNITION', 'Accent Recognition'),
        ('SPEED_LISTENING', 'Speed Listening'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(
        PracticeLesson, 
        on_delete=models.CASCADE, 
        related_name='challenges'
    )
    type = models.CharField(
        max_length=25, 
        choices=CHALLENGE_TYPES,
        help_text="Type of challenge exercise"
    )
    question = models.TextField(help_text="The question or prompt for the user")
    order = models.PositiveIntegerField(help_text="Display order within the lesson")
    
    # 🆕 SPEAKING CHALLENGE FIELDS
    speaking_exercise = models.ForeignKey(
        'SpeakingExercise', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='practice_challenges'
    )
    target_pronunciation = models.TextField(
        blank=True,
        help_text="Texto alvo para exercícios de pronúncia"
    )
    conversation_context = models.JSONField(
        default=dict,
        help_text="Contexto e cenário para conversação"
    )
    minimum_speaking_score = models.FloatField(
        default=70.0,
        help_text="Pontuação mínima para passar no speaking"
    )
    
    # 🆕 LISTENING CHALLENGE FIELDS
    listening_exercise = models.ForeignKey(
        'ListeningExercise', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='practice_challenges'
    )
    audio_content_url = models.URLField(
        blank=True,
        help_text="URL do áudio para exercícios de listening"
    )
    audio_transcript = models.TextField(
        blank=True,
        help_text="Transcrição do áudio para exercícios de listening"
    )
    listening_questions = models.JSONField(
        default=list,
        help_text="Perguntas de compreensão auditiva"
    )
    minimum_listening_score = models.FloatField(
        default=65.0,
        help_text="Pontuação mínima para passar no listening"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['lesson', 'order']
    
    def __str__(self):
        return f"{self.lesson.title} - Challenge {self.order}"


class ChallengeOption(models.Model):
    """
    Challenge Option - Answer choices for challenges.
    
    Maps to Drizzle 'challengeOptions' table from the client project.
    Contains text, images, audio, and correctness information.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(
        PracticeChallenge, 
        on_delete=models.CASCADE, 
        related_name='options'
    )
    text = models.CharField(max_length=200, help_text="Option text/answer")
    is_correct = models.BooleanField(
        default=False,
        help_text="Whether this option is the correct answer"
    )
    image_url = models.URLField(
        blank=True, 
        null=True,
        help_text="Optional image for visual questions (S3 URL)"
    )
    audio_url = models.URLField(
        blank=True, 
        null=True,
        help_text="Optional audio pronunciation (S3 URL)"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.challenge} - {self.text}"


class UserProgress(models.Model):
    """
    User Progress - Tracks overall user progress and gamification stats.
    
    Maps to Drizzle 'userProgress' table from the client project.
    Manages hearts, points, active course, and profile information.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='practice_progress'
    )
    active_course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Currently selected course for practice"
    )
    hearts = models.PositiveIntegerField(
        default=5,
        help_text="Lives/hearts (max 5, lose 1 per wrong answer)"
    )
    points = models.PositiveIntegerField(
        default=0,
        help_text="Total points earned (+10 per correct challenge)"
    )
    user_image_src = models.URLField(
        default="/mascot.jpg",
        help_text="Profile image URL"
    )
    
    # 🆕 SPEAKING PRACTICE FIELDS
    total_speaking_sessions = models.IntegerField(default=0)
    total_speaking_minutes = models.FloatField(default=0.0)
    average_pronunciation_score = models.FloatField(default=0.0)
    average_fluency_score = models.FloatField(default=0.0)
    speaking_streak_days = models.IntegerField(default=0)
    last_speaking_session = models.DateTimeField(null=True, blank=True)
    
    # 🆕 LISTENING PRACTICE FIELDS
    total_listening_sessions = models.IntegerField(default=0)
    total_listening_minutes = models.FloatField(default=0.0)
    average_comprehension_score = models.FloatField(default=0.0)
    average_dictation_score = models.FloatField(default=0.0)
    listening_streak_days = models.IntegerField(default=0)
    last_listening_session = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.name} - {self.points} pts, {self.hearts} hearts"
    
    def reduce_hearts(self):
        """Reduce hearts by 1 (minimum 0)"""
        self.hearts = max(0, self.hearts - 1)
        self.save()
    
    def add_hearts(self, amount=1):
        """Add hearts (maximum 5)"""
        self.hearts = min(5, self.hearts + amount)
        self.save()
    
    def add_points(self, amount=10):
        """Add points for correct answers"""
        self.points += amount
        self.save()
        
        # Trigger achievement progress check
        self._check_achievements_for_points()
    
    def _check_achievements_for_points(self):
        """Check and update achievements related to points"""
        from .views import check_achievement_progress
        check_achievement_progress(self.user, 'points_earned', self.points)


class ChallengeProgress(models.Model):
    """
    Challenge Progress - Tracks individual challenge completion.
    
    Maps to Drizzle 'challengeProgress' table from the client project.
    Records which challenges each user has completed.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='challenge_progress'
    )
    challenge = models.ForeignKey(
        PracticeChallenge, 
        on_delete=models.CASCADE, 
        related_name='user_progress'
    )
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Save and trigger achievement check if challenge was completed"""
        is_new_completion = self.pk is None and self.completed
        was_just_completed = False
        
        if self.pk:
            # Check if this is a new completion
            try:
                old_instance = ChallengeProgress.objects.get(pk=self.pk)
                was_just_completed = not old_instance.completed and self.completed
            except ChallengeProgress.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Trigger achievement checks for new completions
        if is_new_completion or was_just_completed:
            self._check_achievements_for_completion()
    
    def _check_achievements_for_completion(self):
        """Check and update achievements related to challenge completions"""
        from .views import check_achievement_progress
        
        # Count total challenges completed by this user
        total_completed = ChallengeProgress.objects.filter(
            user=self.user, 
            completed=True
        ).count()
        
        check_achievement_progress(self.user, 'challenges_completed', total_completed)
        
        # Also check for lessons completed (challenges can be part of lessons)
        from apps.practice.models import PracticeLesson
        completed_lessons = PracticeLesson.objects.filter(
            units__challenges__user_progress__user=self.user,
            units__challenges__user_progress__completed=True
        ).distinct().count()
        
        check_achievement_progress(self.user, 'lessons_completed', completed_lessons)
    
    class Meta:
        unique_together = ['user', 'challenge']
        indexes = [
            models.Index(fields=['user', 'completed']),
            models.Index(fields=['challenge', 'completed']),
        ]
    
    def __str__(self):
        status = "✅" if self.completed else "⏳"
        return f"{status} {self.user.name} - {self.challenge}"


class UserLeague(models.Model):
    """
    User League - Tracks user's current league based on points.
    
    Leagues provide gamification tiers: Bronze, Silver, Gold, Diamond
    Users automatically move between leagues based on their points.
    """
    LEAGUE_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'), 
        ('gold', 'Gold'),
        ('diamond', 'Diamond'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='league'
    )
    current_league = models.CharField(
        max_length=10,
        choices=LEAGUE_CHOICES,
        default='bronze'
    )
    points_when_promoted = models.PositiveIntegerField(
        default=0,
        help_text="Points when user was promoted to current league"
    )
    promoted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @classmethod
    def get_league_for_points(cls, points):
        """Determine league based on points"""
        if points >= 3000:
            return 'diamond'
        elif points >= 2000:
            return 'gold'
        elif points >= 1000:
            return 'silver'
        else:
            return 'bronze'
    
    @classmethod
    def get_league_info(cls, league):
        """Get league information"""
        league_info = {
            'bronze': {'name': 'Liga Bronze', 'icon': '🥉', 'min_points': 0, 'max_points': 999},
            'silver': {'name': 'Liga Prata', 'icon': '🥈', 'min_points': 1000, 'max_points': 1999},
            'gold': {'name': 'Liga Ouro', 'icon': '🥇', 'min_points': 2000, 'max_points': 2999},
            'diamond': {'name': 'Liga Diamante', 'icon': '💎', 'min_points': 3000, 'max_points': None}
        }
        return league_info.get(league, league_info['bronze'])
    
    def update_league(self):
        """Update user's league based on current points"""
        user_progress = self.user.practice_progress
        new_league = self.get_league_for_points(user_progress.points)
        
        if new_league != self.current_league:
            self.current_league = new_league
            self.points_when_promoted = user_progress.points
            self.save()
            
            # Create promotion record
            LeaguePromotion.objects.create(
                user=self.user,
                from_league=self.current_league,
                to_league=new_league,
                points_at_promotion=user_progress.points
            )
    
    def __str__(self):
        return f"{self.user.name} - {self.get_current_league_display()}"


class LeaguePromotion(models.Model):
    """
    League Promotion - Historical record of league changes.
    
    Tracks when users are promoted or demoted between leagues.
    """
    LEAGUE_CHOICES = UserLeague.LEAGUE_CHOICES
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='league_promotions'
    )
    from_league = models.CharField(max_length=10, choices=LEAGUE_CHOICES)
    to_league = models.CharField(max_length=10, choices=LEAGUE_CHOICES)
    points_at_promotion = models.PositiveIntegerField()
    promoted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-promoted_at']
    
    def __str__(self):
        return f"{self.user.name}: {self.from_league} → {self.to_league}"


class Competition(models.Model):
    """
    Competition - Periodic challenges and events.
    
    Competitions provide time-limited challenges for users to participate in
    and compete against each other for rankings and prizes.
    """
    COMPETITION_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('special', 'Special Event'),
    ]
    
    COMPETITION_STATUS = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    type = models.CharField(max_length=20, choices=COMPETITION_TYPES)
    status = models.CharField(max_length=20, choices=COMPETITION_STATUS, default='upcoming')
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Competition rules
    min_points_to_participate = models.PositiveIntegerField(default=0)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    
    # Prizes
    first_place_prize = models.CharField(max_length=200, default="Badge especial + 500 pontos")
    second_place_prize = models.CharField(max_length=200, default="300 pontos")
    third_place_prize = models.CharField(max_length=200, default="200 pontos")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.title} ({self.type})"
    
    @property
    def participant_count(self):
        return self.participants.count()


class CompetitionParticipant(models.Model):
    """
    Competition Participant - User participation in competitions.
    
    Tracks which users are participating in which competitions
    and their current standings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='competition_participations'
    )
    
    # Performance metrics
    points_earned = models.PositiveIntegerField(default=0)
    challenges_completed = models.PositiveIntegerField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    
    # Ranking
    current_rank = models.PositiveIntegerField(null=True, blank=True)
    best_rank = models.PositiveIntegerField(null=True, blank=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['competition', 'user']
        ordering = ['current_rank']
    
    def __str__(self):
        return f"{self.user.name} in {self.competition.title}"


class LeaderboardSnapshot(models.Model):
    """
    Leaderboard Snapshot - Historical rankings data.
    
    Stores periodic snapshots of the leaderboard for tracking
    rank changes and historical performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Snapshot metadata
    snapshot_date = models.DateTimeField(auto_now_add=True)
    snapshot_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily'
    )
    
    # User ranking data
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ranking_history')
    rank = models.PositiveIntegerField()
    points = models.PositiveIntegerField()
    league = models.CharField(max_length=10, choices=UserLeague.LEAGUE_CHOICES)
    
    # Change indicators
    rank_change = models.IntegerField(default=0, help_text="Change from previous snapshot (+/-)")
    points_change = models.IntegerField(default=0, help_text="Points gained since last snapshot")
    
    class Meta:
        unique_together = ['user', 'snapshot_date', 'snapshot_type']
        ordering = ['-snapshot_date', 'rank']
    
    def __str__(self):
        return f"#{self.rank} {self.user.name} - {self.snapshot_date.date()}"


class UserStreak(models.Model):
    """
    User Streak - Daily practice streak tracking.
    
    Tracks consecutive days of practice activity for gamification.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='streak'
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_practice_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_streak(self):
        """Update streak based on practice activity"""
        from datetime import date, timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        if self.last_practice_date == today:
            # Already practiced today, no change needed
            return
        elif self.last_practice_date == yesterday:
            # Consecutive day, increment streak
            self.current_streak += 1
            self.longest_streak = max(self.longest_streak, self.current_streak)
        elif self.last_practice_date and self.last_practice_date < yesterday:
            # Streak broken, reset to 1
            self.current_streak = 1
        else:
            # First practice ever
            self.current_streak = 1
        
        self.last_practice_date = today
        self.save()
        
        # Trigger achievement progress check for streaks
        self._check_achievements_for_streak()
    
    def _check_achievements_for_streak(self):
        """Check and update achievements related to streaks"""
        from .views import check_achievement_progress
        check_achievement_progress(self.user, 'streak_days', self.current_streak)
    
    def __str__(self):
        return f"{self.user.name} - {self.current_streak} days streak"


class Achievement(models.Model):
    """
    Achievement - Individual achievement/badge definition.
    
    Defines what achievements are available in the system, their requirements,
    and metadata like rarity, points, and visual representation.
    """
    CATEGORY_CHOICES = [
        ('learning', 'Learning'),
        ('streak', 'Streak'),
        ('social', 'Social'),
        ('milestone', 'Milestone'),
        ('special', 'Special'),
    ]
    
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10, help_text="Emoji or unicode icon")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    points = models.PositiveIntegerField(help_text="Points awarded when unlocked")
    
    # Achievement requirements/criteria
    requirement_type = models.CharField(
        max_length=50,
        help_text="Type of requirement: lessons_completed, streak_days, points_earned, etc."
    )
    requirement_target = models.PositiveIntegerField(
        help_text="Target value to achieve (e.g., 50 for '50 lessons completed')"
    )
    requirement_unit = models.CharField(
        max_length=20,
        default="items",
        help_text="Unit for progress display (lessons, days, points, etc.)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    is_secret = models.BooleanField(
        default=False, 
        help_text="Hidden achievements not shown until unlocked"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'category', 'rarity']
    
    def __str__(self):
        return f"{self.title} ({self.category}, {self.rarity})"
    
    def get_rarity_color(self):
        """Get CSS color class for rarity"""
        color_map = {
            'common': 'text-gray-400',
            'rare': 'text-blue-400',
            'epic': 'text-purple-400',
            'legendary': 'text-yellow-400'
        }
        return color_map.get(self.rarity, 'text-gray-400')


class UserAchievement(models.Model):
    """
    User Achievement - Tracks which achievements users have unlocked.
    
    Records when a user unlocks an achievement and tracks progress
    towards achievements that are not yet unlocked.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='user_achievements'
    )
    
    # Progress tracking
    is_unlocked = models.BooleanField(default=False)
    current_progress = models.PositiveIntegerField(
        default=0,
        help_text="Current progress towards the achievement"
    )
    unlocked_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-unlocked_at', '-created_at']
    
    def __str__(self):
        status = "🏆" if self.is_unlocked else f"📈 {self.current_progress}/{self.achievement.requirement_target}"
        return f"{self.user.name} - {self.achievement.title} {status}"
    
    def get_progress_percentage(self):
        """Calculate progress percentage"""
        if self.achievement.requirement_target == 0:
            return 100 if self.is_unlocked else 0
        return min(100, (self.current_progress / self.achievement.requirement_target) * 100)
    
    def update_progress(self, new_progress):
        """Update progress and check if achievement should be unlocked"""
        from datetime import datetime
        from django.utils import timezone
        
        self.current_progress = new_progress
        
        # Check if achievement should be unlocked
        if (not self.is_unlocked and 
            self.current_progress >= self.achievement.requirement_target):
            self.is_unlocked = True
            self.unlocked_at = timezone.now()
            
            # Award points to user
            user_progress, created = UserProgress.objects.get_or_create(
                user=self.user,
                defaults={'hearts': 5, 'points': 0}
            )
            user_progress.add_points(self.achievement.points)
        
        self.save()
        return self.is_unlocked


class AchievementCategory(models.Model):
    """
    Achievement Category - Metadata for achievement categories.
    
    Provides additional information and configuration for achievement categories.
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    icon_class = models.CharField(max_length=50, help_text="CSS icon class")
    color = models.CharField(max_length=50, help_text="CSS color class")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Achievement Categories"
    
    def __str__(self):
        return self.display_name


class AchievementNotification(models.Model):
    """
    Achievement Notification - Tracks achievement unlock notifications.
    
    Manages notifications when users unlock new achievements,
    allowing for celebration and recognition of progress.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievement_notifications'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification status
    is_read = models.BooleanField(default=False)
    is_celebrated = models.BooleanField(
        default=False,
        help_text="Whether the achievement popup was shown"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-created_at']
    
    def __str__(self):
        status = "📖" if self.is_read else "🔔"
        return f"{status} {self.user.name} - {self.achievement.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_celebrated(self):
        """Mark achievement as celebrated (popup shown)"""
        self.is_celebrated = True
        self.save()


# =============================================================================
# 🎙️ AI SPEAKING PRACTICE MODELS
# =============================================================================

class SpeakingExercise(models.Model):
    """
    Exercícios de conversação baseados em capítulos/lições
    """
    DIFFICULTY_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'), 
        ('ADVANCED', 'Advanced'),
    ]
    
    EXERCISE_TYPES = [
        ('PRONUNCIATION', 'Pronunciation Practice'),
        ('CONVERSATION', 'AI Conversation'),
        ('READING_ALOUD', 'Reading Aloud'),
        ('ROLE_PLAY', 'Role Playing'),
        ('STORY_TELLING', 'Story Telling'),
        ('VOCABULARY_PRACTICE', 'Vocabulary Practice'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    practice_lesson = models.ForeignKey(
        PracticeLesson, 
        on_delete=models.CASCADE, 
        related_name='speaking_exercises', 
        null=True, 
        blank=True
    )
    course = models.ForeignKey(
        'courses.Course', 
        on_delete=models.CASCADE, 
        related_name='speaking_exercises',
        null=True,
        blank=True,
        help_text="Curso específico para exercício contextualizado (opcional para exercícios genéricos)"
    )
    
    # Configurações do exercício
    title = models.CharField(max_length=200)
    description = models.TextField()
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES)
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES)
    
    # 🆕 CONTEXTUALIZAÇÃO POR CURSO
    is_course_specific = models.BooleanField(
        default=False, 
        help_text="Indica se o exercício é específico para um curso ou genérico"
    )
    lesson_context = models.CharField(
        max_length=200,
        blank=True,
        help_text="Contexto da lição específica (ex: 'Business Meetings', 'Family Vocabulary')"
    )
    auto_generated = models.BooleanField(
        default=False,
        help_text="Indica se o exercício foi gerado automaticamente baseado no conteúdo do curso"
    )
    
    # Conteúdo do exercício
    target_text = models.TextField(help_text="Texto alvo para leitura/repetição")
    conversation_prompt = models.TextField(blank=True, help_text="Prompt inicial para conversação")
    vocabulary_words = models.JSONField(default=list, help_text="Lista de palavras-chave para praticar")
    
    # Configurações de avaliação
    pronunciation_weight = models.FloatField(default=0.4, help_text="Peso da pronúncia na nota (0-1)")
    fluency_weight = models.FloatField(default=0.3, help_text="Peso da fluência na nota (0-1)")
    accuracy_weight = models.FloatField(default=0.3, help_text="Peso da precisão na nota (0-1)")
    
    # Gamificação
    points_reward = models.IntegerField(default=25)
    hearts_cost = models.IntegerField(default=1)
    minimum_score = models.FloatField(default=70.0, help_text="Pontuação mínima para passar (%)")
    
    # Metadados
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_speaking_exercises')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['difficulty', 'created_at']
        indexes = [
            models.Index(fields=['course', 'is_course_specific']),
            models.Index(fields=['is_course_specific', 'exercise_type']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_exercise_type_display()})"


class SpeakingSession(models.Model):
    """
    Sessão de prática de conversação individual
    """
    SESSION_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('PAUSED', 'Paused'),
        ('ABANDONED', 'Abandoned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='speaking_sessions')
    exercise = models.ForeignKey(SpeakingExercise, on_delete=models.CASCADE, related_name='sessions')
    
    # Status da sessão
    status = models.CharField(max_length=15, choices=SESSION_STATUS, default='ACTIVE')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Métricas da sessão
    total_duration = models.DurationField(null=True, blank=True)
    turns_count = models.IntegerField(default=0, help_text="Número de falas do usuário")
    
    # Pontuações finais
    overall_score = models.FloatField(null=True, blank=True)
    pronunciation_score = models.FloatField(null=True, blank=True)
    fluency_score = models.FloatField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    
    # Gamificação
    points_earned = models.IntegerField(default=0)
    hearts_used = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    
    # Feedback da IA
    ai_feedback = models.TextField(blank=True)
    improvement_suggestions = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.exercise.title} ({self.status})"


class SpeakingTurn(models.Model):
    """
    Individual speaking turn within a session
    """
    TURN_TYPES = [
        ('USER_SPEECH', 'User Speech'),
        ('AI_RESPONSE', 'AI Response'),
        ('SYSTEM_PROMPT', 'System Prompt'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    session = models.ForeignKey(SpeakingSession, on_delete=models.CASCADE, related_name='turns')
    
    # Configurações da vez
    turn_number = models.IntegerField()
    turn_type = models.CharField(max_length=15, choices=TURN_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Conteúdo
    audio_url = models.URLField(blank=True, help_text="URL do arquivo de áudio gravado")
    transcribed_text = models.TextField(blank=True, help_text="Texto transcrito da fala")
    target_text = models.TextField(blank=True, help_text="Texto alvo para comparação")
    ai_response_text = models.TextField(blank=True, help_text="Resposta da IA")
    
    # Análise da fala (apenas para USER_SPEECH)
    pronunciation_score = models.FloatField(null=True, blank=True)
    fluency_score = models.FloatField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    
    # Detalhes da análise
    words_analysis = models.JSONField(default=dict, help_text="Análise palavra por palavra")
    pronunciation_errors = models.JSONField(default=list)
    grammar_errors = models.JSONField(default=list)
    
    # Duração
    duration = models.DurationField(null=True, blank=True)
    
    class Meta:
        ordering = ['turn_number']
        unique_together = ['session', 'turn_number']
    
    def __str__(self):
        return f"Turn {self.turn_number} - {self.get_turn_type_display()}"


class SpeakingProgress(models.Model):
    """
    Progresso geral do usuário em speaking practice
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamento
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='speaking_progress')
    
    # Estatísticas gerais
    total_sessions = models.IntegerField(default=0)
    total_hours_practiced = models.FloatField(default=0.0)
    total_words_spoken = models.IntegerField(default=0)
    
    # Pontuações médias
    average_pronunciation = models.FloatField(default=0.0)
    average_fluency = models.FloatField(default=0.0)
    average_accuracy = models.FloatField(default=0.0)
    overall_average = models.FloatField(default=0.0)
    
    # Progressão por dificuldade
    beginner_sessions = models.IntegerField(default=0)
    intermediate_sessions = models.IntegerField(default=0)
    advanced_sessions = models.IntegerField(default=0)
    
    # Conquistas
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    
    # Áreas de melhoria
    weak_phonemes = models.JSONField(default=list)
    strong_areas = models.JSONField(default=list)
    practice_recommendations = models.JSONField(default=list)
    
    # Metadados
    last_session_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.name} - Speaking Progress"


# =============================================================================
# 🎧 AI LISTENING PRACTICE MODELS
# =============================================================================

class ListeningExercise(models.Model):
    """
    Exercícios de compreensão auditiva baseados em conteúdo de áudio
    """
    DIFFICULTY_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'), 
        ('ADVANCED', 'Advanced'),
    ]
    
    EXERCISE_TYPES = [
        ('AUDIO_COMPREHENSION', 'Audio Comprehension'),
        ('DICTATION', 'Dictation Practice'),
        ('CONVERSATION_LISTENING', 'Conversation Listening'),
        ('ACCENT_RECOGNITION', 'Accent Recognition'),
        ('SPEED_LISTENING', 'Speed Listening'),
        ('STORY_LISTENING', 'Story Listening'),
        ('NEWS_LISTENING', 'News Listening'),
    ]
    
    ACCENT_TYPES = [
        ('AMERICAN', 'American English'),
        ('BRITISH', 'British English'),
        ('CANADIAN', 'Canadian English'),
        ('AUSTRALIAN', 'Australian English'),
        ('NEUTRAL', 'Neutral/International'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    practice_lesson = models.ForeignKey(
        PracticeLesson, 
        on_delete=models.CASCADE, 
        related_name='listening_exercises', 
        null=True, 
        blank=True
    )
    course = models.ForeignKey(
        'courses.Course', 
        on_delete=models.CASCADE, 
        related_name='listening_exercises',
        null=True,
        blank=True,
        help_text="Curso específico para exercício contextualizado (opcional para exercícios genéricos)"
    )
    
    # Configurações do exercício
    title = models.CharField(max_length=200)
    description = models.TextField()
    exercise_type = models.CharField(max_length=25, choices=EXERCISE_TYPES)
    difficulty = models.CharField(max_length=15, choices=DIFFICULTY_CHOICES)
    accent_type = models.CharField(max_length=15, choices=ACCENT_TYPES, default='NEUTRAL')
    
    # 🆕 CONTEXTUALIZAÇÃO POR CURSO
    is_course_specific = models.BooleanField(
        default=False, 
        help_text="Indica se o exercício é específico para um curso ou genérico"
    )
    lesson_context = models.CharField(
        max_length=200,
        blank=True,
        help_text="Contexto da lição específica (ex: 'Business Meetings', 'Family Vocabulary')"
    )
    auto_generated = models.BooleanField(
        default=False,
        help_text="Indica se o exercício foi gerado automaticamente baseado no conteúdo do curso"
    )
    
    # Conteúdo de áudio
    audio_url = models.URLField(help_text="URL do arquivo de áudio principal")
    audio_duration = models.DurationField(help_text="Duração do áudio em segundos")
    transcript = models.TextField(help_text="Transcrição completa do áudio")
    
    # Configurações de reprodução
    allow_replay = models.BooleanField(default=True)
    max_replays = models.IntegerField(default=3, help_text="Máximo de reproduções (-1 para ilimitado)")
    playback_speeds = models.JSONField(
        default=list,
        help_text="Velocidades disponíveis: [0.5, 0.75, 1.0, 1.25, 1.5]"
    )
    
    # Perguntas e respostas
    questions = models.JSONField(
        default=list,
        help_text="Lista de perguntas de compreensão"
    )
    correct_answers = models.JSONField(
        default=list,
        help_text="Respostas corretas correspondentes"
    )
    
    # Vocabulário focado
    key_vocabulary = models.JSONField(
        default=list, 
        help_text="Palavras-chave presentes no áudio"
    )
    vocabulary_definitions = models.JSONField(
        default=dict,
        help_text="Definições das palavras-chave"
    )
    
    # Gamificação
    points_reward = models.IntegerField(default=20)
    hearts_cost = models.IntegerField(default=1)
    minimum_score = models.FloatField(default=65.0, help_text="Pontuação mínima para passar (%)")
    
    # Metadados
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_listening_exercises')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['difficulty', 'created_at']
        indexes = [
            models.Index(fields=['course', 'is_course_specific']),
            models.Index(fields=['is_course_specific', 'exercise_type']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_exercise_type_display()})"


class ListeningSession(models.Model):
    """
    Sessão individual de prática de compreensão auditiva
    """
    SESSION_STATUS = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('PAUSED', 'Paused'),
        ('ABANDONED', 'Abandoned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listening_sessions')
    exercise = models.ForeignKey(ListeningExercise, on_delete=models.CASCADE, related_name='sessions')
    
    # Status da sessão
    status = models.CharField(max_length=15, choices=SESSION_STATUS, default='ACTIVE')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Métricas da sessão
    total_duration = models.DurationField(null=True, blank=True)
    audio_replays_used = models.IntegerField(default=0)
    playback_speed_used = models.FloatField(default=1.0)
    
    # Respostas do usuário
    user_answers = models.JSONField(default=list)
    dictation_attempts = models.JSONField(default=list)
    
    # Pontuações
    comprehension_score = models.FloatField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    vocabulary_score = models.FloatField(null=True, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    
    # Gamificação
    points_earned = models.IntegerField(default=0)
    hearts_used = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    
    # Feedback e análise
    detailed_feedback = models.JSONField(default=dict)
    improvement_areas = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.exercise.title} ({self.status})"


class ListeningAttempt(models.Model):
    """
    Tentativa individual de resposta dentro de uma sessão de listening
    """
    ATTEMPT_TYPES = [
        ('COMPREHENSION_QUESTION', 'Comprehension Question'),
        ('DICTATION_SENTENCE', 'Dictation Sentence'),
        ('VOCABULARY_IDENTIFICATION', 'Vocabulary Identification'),
        ('AUDIO_SEGMENT_REPLAY', 'Audio Segment Replay'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    session = models.ForeignKey(ListeningSession, on_delete=models.CASCADE, related_name='attempts')
    
    # Configurações da tentativa
    attempt_number = models.IntegerField()
    attempt_type = models.CharField(max_length=25, choices=ATTEMPT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Pergunta e resposta
    question_text = models.TextField()
    question_index = models.IntegerField(help_text="Índice da pergunta no exercício")
    user_answer = models.TextField()
    correct_answer = models.TextField()
    
    # Análise da resposta
    is_correct = models.BooleanField(default=False)
    partial_credit = models.FloatField(default=0.0, help_text="Crédito parcial (0.0-1.0)")
    similarity_score = models.FloatField(null=True, blank=True, help_text="Similaridade semântica")
    
    # Tempo de resposta
    time_to_answer = models.DurationField(null=True, blank=True)
    audio_replays_before_answer = models.IntegerField(default=0)
    
    # Feedback específico
    feedback_text = models.TextField(blank=True)
    hints_used = models.JSONField(default=list)
    
    class Meta:
        ordering = ['attempt_number']
        unique_together = ['session', 'attempt_number']
    
    def __str__(self):
        return f"Attempt {self.attempt_number} - {self.get_attempt_type_display()}"


class ListeningProgress(models.Model):
    """
    Progresso geral do usuário em listening practice
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamento
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='listening_progress')
    
    # Estatísticas gerais
    total_sessions = models.IntegerField(default=0)
    total_hours_listened = models.FloatField(default=0.0)
    total_audio_content = models.IntegerField(default=0, help_text="Total de conteúdo de áudio em minutos")
    
    # Pontuações médias por tipo de exercício
    avg_comprehension_score = models.FloatField(default=0.0)
    avg_dictation_score = models.FloatField(default=0.0)
    avg_vocabulary_score = models.FloatField(default=0.0)
    overall_listening_score = models.FloatField(default=0.0)
    
    # Progressão por dificuldade
    beginner_sessions = models.IntegerField(default=0)
    intermediate_sessions = models.IntegerField(default=0)
    advanced_sessions = models.IntegerField(default=0)
    
    # Estatísticas por sotaque
    american_sessions = models.IntegerField(default=0)
    british_sessions = models.IntegerField(default=0)
    other_accents_sessions = models.IntegerField(default=0)
    
    # Velocidades de áudio preferidas
    preferred_speed = models.FloatField(default=1.0)
    speeds_comfort_level = models.JSONField(
        default=dict,
        help_text="Nível de conforto por velocidade: {0.5: 95, 1.0: 80, 1.5: 45}"
    )
    
    # Áreas de força e fraqueza
    strong_exercise_types = models.JSONField(default=list)
    weak_exercise_types = models.JSONField(default=list)
    difficult_vocabulary = models.JSONField(default=list)
    mastered_vocabulary = models.JSONField(default=list)
    
    # Recomendações personalizadas
    recommended_exercises = models.JSONField(default=list)
    suggested_focus_areas = models.JSONField(default=list)
    
    # Conquistas de listening
    current_listening_streak = models.IntegerField(default=0)
    longest_listening_streak = models.IntegerField(default=0)
    perfect_comprehension_count = models.IntegerField(default=0)
    
    # Metadados
    last_session_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.name} - Listening Progress"


class AudioSegment(models.Model):
    """
    Segmentos específicos de áudio para práticas focalizadas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamento
    listening_exercise = models.ForeignKey(
        ListeningExercise,
        on_delete=models.CASCADE,
        related_name='audio_segments'
    )
    
    # Configurações do segmento
    title = models.CharField(max_length=100)
    start_time = models.DurationField(help_text="Tempo de início no áudio principal")
    end_time = models.DurationField(help_text="Tempo de fim no áudio principal")
    segment_transcript = models.TextField()
    
    # Dificuldade específica do segmento
    difficulty_rating = models.FloatField(
        default=1.0,
        help_text="Rating de dificuldade (1.0-5.0)"
    )
    speech_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="Palavras por minuto neste segmento"
    )
    
    # Características linguísticas
    vocabulary_complexity = models.CharField(
        max_length=20,
        choices=[
            ('BASIC', 'Basic'),
            ('INTERMEDIATE', 'Intermediate'),
            ('ADVANCED', 'Advanced'),
            ('SPECIALIZED', 'Specialized'),
        ],
        default='BASIC'
    )
    
    # Elementos focais
    focused_grammar_points = models.JSONField(default=list)
    key_phrases = models.JSONField(default=list)
    cultural_context = models.TextField(blank=True)
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.listening_exercise.title} - {self.title}"
    
    def get_duration(self):
        """Retorna a duração do segmento"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
