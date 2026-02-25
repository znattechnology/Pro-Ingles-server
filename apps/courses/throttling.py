"""
Courses App Throttling Configuration

Defines rate limiting classes for course-related endpoints to prevent abuse.
"""

from rest_framework.throttling import UserRateThrottle


class VideoUploadThrottle(UserRateThrottle):
    """
    Rate limit for video upload URL generation.

    Prevents excessive generation of presigned URLs that could:
    - Lead to S3 abuse
    - Indicate automated/bot activity
    - Cause unnecessary API load

    Rate: 30 uploads per hour per user
    """
    rate = '30/hour'
    scope = 'video_upload'


class ImageUploadThrottle(UserRateThrottle):
    """
    Rate limit for image upload operations.

    Prevents excessive image uploads that could:
    - Fill up S3 storage
    - Indicate automated/bot activity

    Rate: 60 uploads per hour per user
    """
    rate = '60/hour'
    scope = 'image_upload'


class ResourceUploadThrottle(UserRateThrottle):
    """
    Rate limit for resource upload URL generation.

    Resources include PDFs, documents, and other learning materials.

    Rate: 100 uploads per hour per user
    """
    rate = '100/hour'
    scope = 'resource_upload'


class CourseCreationThrottle(UserRateThrottle):
    """
    Rate limit for course creation.

    Prevents teachers from creating too many courses too quickly.

    Rate: 10 courses per hour per user
    """
    rate = '10/hour'
    scope = 'course_creation'


class EnrollmentThrottle(UserRateThrottle):
    """
    Rate limit for course enrollment.

    Prevents rapid enrollment/unenrollment that could indicate abuse.

    Rate: 20 enrollments per hour per user
    """
    rate = '20/hour'
    scope = 'course_enrollment'
