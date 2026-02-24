"""
Core Permission Classes

Centralized permission classes for the ProEnglish platform.
These permissions are used across multiple apps for consistent access control.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Permission class that only allows administrators to access the view.

    Checks for:
    1. User is authenticated
    2. User has role='admin' OR is_staff=True OR is_superuser=True

    Usage:
        permission_classes = [IsAuthenticated, IsAdmin]

    Or combined:
        permission_classes = [IsAdmin]  # IsAdmin already checks authentication
    """
    message = "Apenas administradores podem acessar este recurso."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check for admin role, staff status, or superuser
        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)
        is_superuser = getattr(request.user, 'is_superuser', False)

        return user_role == 'admin' or is_staff or is_superuser


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows:
    - Admins: Full access (GET, POST, PUT, PATCH, DELETE)
    - Others: Read-only access (GET, HEAD, OPTIONS)

    Usage:
        permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    """
    message = "Apenas administradores podem modificar este recurso."

    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow read-only for everyone authenticated
        if request.method in self.SAFE_METHODS:
            return True

        # Write operations require admin role
        user_role = getattr(request.user, 'role', None)
        is_staff = getattr(request.user, 'is_staff', False)
        is_superuser = getattr(request.user, 'is_superuser', False)

        return user_role == 'admin' or is_staff or is_superuser


class IsPlatformAdmin(BasePermission):
    """
    Stricter admin permission - only platform admins and superusers.
    Does NOT include regular staff.

    Usage:
        permission_classes = [IsPlatformAdmin]
    """
    message = "Apenas administradores da plataforma podem acessar este recurso."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, 'role', None)
        is_superuser = getattr(request.user, 'is_superuser', False)

        return user_role == 'admin' or is_superuser
