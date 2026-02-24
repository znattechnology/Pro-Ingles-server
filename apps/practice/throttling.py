"""
Practice App Throttling Configuration

Defines rate limiting classes for critical endpoints to prevent abuse.
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class ChallengeProgressThrottle(UserRateThrottle):
    """
    Rate limit for challenge progress submissions.

    Prevents rapid-fire challenge submissions that could:
    - Exploit the points/hearts system
    - Cause database strain
    - Indicate automated/bot activity

    Rate: 60 submissions per minute per user
    """
    rate = '60/minute'
    scope = 'challenge_progress'


class VapiSessionThrottle(UserRateThrottle):
    """
    Rate limit for Vapi session operations.

    Prevents excessive API calls to expensive speech processing endpoints.

    Rate: 20 sessions per minute per user
    """
    rate = '20/minute'
    scope = 'vapi_session'


class CourseCreationThrottle(UserRateThrottle):
    """
    Rate limit for course creation.

    Prevents teachers from creating too many courses too quickly.

    Rate: 10 courses per hour per user
    """
    rate = '10/hour'
    scope = 'course_creation'


class ContentCreationThrottle(UserRateThrottle):
    """
    Rate limit for unit/lesson/challenge creation.

    Prevents rapid content creation that could indicate abuse.

    Rate: 100 items per hour per user
    """
    rate = '100/hour'
    scope = 'content_creation'


class HeartsRefillThrottle(UserRateThrottle):
    """
    Rate limit for hearts refill requests.

    Prevents abuse of the hearts system.

    Rate: 5 refills per hour per user
    """
    rate = '5/hour'
    scope = 'hearts_refill'


class LeaderboardThrottle(UserRateThrottle):
    """
    Rate limit for leaderboard queries.

    Prevents excessive polling of leaderboard data.

    Rate: 30 requests per minute per user
    """
    rate = '30/minute'
    scope = 'leaderboard'


class AnonAPIThrottle(AnonRateThrottle):
    """
    Rate limit for anonymous API access.

    Applied to public endpoints (like vapi_templates).

    Rate: 100 requests per hour for anonymous users
    """
    rate = '100/hour'
    scope = 'anon_api'


class VapiWebhookThrottle(AnonRateThrottle):
    """
    Rate limit for Vapi webhook requests.

    Protects webhook endpoint from abuse or DDoS.
    Uses IP-based throttling since webhooks come from Vapi servers.

    Rate: 200 requests per minute per IP (generous for real-time events)
    """
    rate = '200/minute'
    scope = 'vapi_webhook'
