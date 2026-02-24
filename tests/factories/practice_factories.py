"""
Factory classes for Practice-related models.
"""

import factory
from factory.django import DjangoModelFactory

from apps.practice.models import (
    PracticeLesson, PracticeUnit, PracticeChallenge,
    UserStreak, Achievement
    # Note: SpeakingExercise and ListeningExercise removed - now handled by Vapi integration
)
from .user_factories import StudentFactory, TeacherFactory


class PracticeLessonFactory(DjangoModelFactory):
    """Factory for creating PracticeLesson instances."""
    
    class Meta:
        model = PracticeLesson
        django_get_or_create = ('title',)
    
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph', nb_sentences=2)
    difficulty = factory.Iterator(['easy', 'medium', 'hard'])
    category = factory.Iterator(['pronunciation', 'listening', 'speaking', 'vocabulary'])
    points_reward = factory.Faker('random_int', min=5, max=50)
    hearts_cost = factory.Faker('random_int', min=1, max=3)
    is_active = True
    created_by = factory.SubFactory(TeacherFactory)


class PracticeExerciseFactory(DjangoModelFactory):
    """Factory for creating PracticeExercise instances."""
    
    class Meta:
        model = PracticeExercise
        django_get_or_create = ('lesson', 'order')
    
    lesson = factory.SubFactory(PracticeLessonFactory)
    question_text = factory.Faker('sentence', nb_words=8)
    exercise_type = factory.Iterator(['multiple_choice', 'fill_blank', 'pronunciation'])
    data = factory.LazyFunction(lambda: {
        'options': ['Option A', 'Option B', 'Option C', 'Option D'],
        'correct_answer': 'Option A'
    })
    order = factory.Sequence(lambda n: n + 1)
    is_active = True


# Note: SpeakingExerciseFactory and ListeningExerciseFactory have been removed
# as they are now handled by Vapi AI conversation practice integration
# For conversation practice testing, use Vapi SDK test factories instead


class UserStreakFactory(DjangoModelFactory):
    """Factory for creating UserStreak instances."""
    
    class Meta:
        model = UserStreak
        django_get_or_create = ('user',)
    
    user = factory.SubFactory(StudentFactory)
    current_streak = factory.Faker('random_int', min=0, max=100)
    longest_streak = factory.Faker('random_int', min=0, max=100)
    total_lessons_completed = factory.Faker('random_int', min=0, max=500)
    last_activity_date = factory.Faker('date_this_year')
    
    @factory.post_generation
    def ensure_longest_streak(self, create, extracted, **kwargs):
        """Ensure longest_streak >= current_streak."""
        if create and self.longest_streak < self.current_streak:
            self.longest_streak = self.current_streak
            self.save()


class AchievementFactory(DjangoModelFactory):
    """Factory for creating Achievement instances."""
    
    class Meta:
        model = Achievement
        django_get_or_create = ('name',)
    
    name = factory.Faker('catch_phrase')
    description = factory.Faker('paragraph', nb_sentences=1)
    category = factory.Iterator(['streak', 'lessons', 'pronunciation', 'listening'])
    requirement = factory.LazyFunction(lambda: {
        'type': 'streak_days',
        'value': 7
    })
    badge_icon = factory.Faker('emoji')
    points_reward = factory.Faker('random_int', min=50, max=200)
    is_active = True
    created_by = factory.SubFactory(TeacherFactory)