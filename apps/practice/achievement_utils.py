"""
Achievement utility functions.

Extracted from views.py to reduce coupling and file size.
"""

from .models import Achievement, UserAchievement, AchievementNotification


def check_achievement_progress(user, achievement_type, current_value):
    """
    Helper function to check and update achievement progress.

    Called from other parts of the system when user actions occur.

    Args:
        user: The user whose achievement progress to check
        achievement_type: The type of achievement to check
        current_value: The current progress value

    Returns:
        List of newly unlocked achievements
    """
    # Get achievements of the specified type
    achievements = Achievement.objects.filter(
        requirement_type=achievement_type,
        is_active=True
    )

    newly_unlocked = []

    for achievement in achievements:
        # Get or create user achievement
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={'current_progress': 0}
        )

        # Update progress if not already unlocked
        if not user_achievement.is_unlocked:
            was_unlocked = user_achievement.update_progress(current_value)

            if was_unlocked:
                # Create notification
                notification, created = AchievementNotification.objects.get_or_create(
                    user=user,
                    achievement=achievement
                )
                newly_unlocked.append(achievement)

    return newly_unlocked
