"""
Custom permission classes for the API.
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only granted to the owner of the object.
        return obj.user == request.user


class IsOwner(BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsBraiderOrReadOnly(BasePermission):
    """
    Custom permission for braider-specific actions.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user is authenticated and is a braider
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'braider_profile')
        )


class IsBraider(BasePermission):
    """
    Permission class for braider-only access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'braider_profile')
        )


class IsCustomerOrBraider(BasePermission):
    """
    Permission for customers and braiders (excluding admins from some actions).
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.role in ['customer', 'braider'])
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Custom permission for admin-only write access.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsAdminUser(BasePermission):
    """
    Permission class for admin-only access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class CanManageBooking(BasePermission):
    """
    Permission for managing bookings - either the customer who created it or the braider.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user == obj.user or  # Customer who made the booking
            request.user == obj.braider.user  # Braider who received the booking
        )