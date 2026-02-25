"""
Practice App Custom Permissions

Defines permission classes for teacher-only and other specialized access control.
"""

from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    """
    Permission class that only allows teachers to access the view.

    Checks for:
    1. User is authenticated
    2. User has role='teacher' OR is_staff=True

    Usage:
        permission_classes = [IsAuthenticated, IsTeacher]
    """
    message = "Apenas professores podem realizar esta ação."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check for teacher role or staff status
        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)

        return user_role == 'teacher' or is_staff


class IsTeacherOrReadOnly(BasePermission):
    """
    Permission class that allows:
    - Teachers: Full access (GET, POST, PUT, PATCH, DELETE)
    - Others: Read-only access (GET, HEAD, OPTIONS)

    Usage:
        permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    """
    message = "Apenas professores podem modificar este recurso."

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow read-only for everyone
        if request.method in self.SAFE_METHODS:
            return True

        # Write operations require teacher role
        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)

        return user_role == 'teacher' or is_staff


class IsOwnerOrTeacher(BasePermission):
    """
    Permission class for object-level permissions.

    Allows access if:
    - User is the owner of the object (obj.user == request.user)
    - User is a teacher
    - User is staff

    Usage:
        permission_classes = [IsAuthenticated, IsOwnerOrTeacher]

    Note: The object must have a 'user' or 'teacher' attribute.
    """
    message = "Você não tem permissão para acessar este recurso."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is staff
        if getattr(request.user, 'is_staff', False):
            return True

        # Check if user is teacher
        if getattr(request.user, 'role', None) == 'teacher':
            return True

        # Check ownership
        if hasattr(obj, 'user') and obj.user == request.user:
            return True

        if hasattr(obj, 'teacher') and obj.teacher == request.user:
            return True

        return False


class IsCourseOwner(BasePermission):
    """
    Permission class that checks if user owns the course being accessed.

    Works with views that have a course_id parameter or course object.

    Usage:
        permission_classes = [IsAuthenticated, IsCourseOwner]
    """
    message = "Apenas o professor proprietário pode gerenciar este curso."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff always has access
        if getattr(request.user, 'is_staff', False):
            return True

        # Check teacher role first
        user_role = getattr(request.user, 'role', None)
        if user_role != 'teacher':
            return False

        # For object-level checks, defer to has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff always has access
        if getattr(request.user, 'is_staff', False):
            return True

        # Check if obj is a Course or has a course relationship
        course = None
        if hasattr(obj, 'teacher'):
            # obj is a Course
            course = obj
        elif hasattr(obj, 'course'):
            # obj has a course FK (Unit, etc.)
            course = obj.course
        elif hasattr(obj, 'unit') and hasattr(obj.unit, 'course'):
            # obj has unit → course (Lesson)
            course = obj.unit.course
        elif hasattr(obj, 'lesson') and hasattr(obj.lesson, 'unit'):
            # obj has lesson → unit → course (Challenge)
            course = obj.lesson.unit.course

        if course and hasattr(course, 'teacher'):
            return course.teacher == request.user

        return False
