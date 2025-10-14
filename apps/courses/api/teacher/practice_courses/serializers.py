"""
Teacher practice courses serializers - redirects to practice app functionality.
"""

from apps.practice import serializers as practice_serializers

# Re-export practice serializers for teacher use
# The practice app already has all necessary serializers
PracticeUnitSerializer = practice_serializers.PracticeUnitSerializer
PracticeLessonSerializer = practice_serializers.PracticeLessonSerializer
PracticeChallengeSerializer = practice_serializers.PracticeChallengeSerializer