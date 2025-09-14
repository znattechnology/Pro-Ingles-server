"""
Base service class with common functionality for all course services.

Provides shared utilities, error handling, and common patterns
used across all business logic services.
"""

import logging
from typing import Any, Dict, Optional, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


logger = logging.getLogger('courses.services')


class ServiceError(Exception):
    """Base exception for service layer errors."""
    pass


class BusinessLogicError(ServiceError):
    """Raised when business logic rules are violated."""
    pass


class PermissionError(ServiceError):
    """Raised when user doesn't have permission for the action."""
    pass


class NotFoundError(ServiceError):
    """Raised when a required resource is not found."""
    pass


class BaseService:
    """
    Base service class providing common functionality for all services.
    
    Features:
    - Consistent error handling
    - Logging support
    - Transaction management
    - Permission checking utilities
    - Data validation helpers
    """
    
    def __init__(self, user=None):
        """
        Initialize the service with optional user context.
        
        Args:
            user: The user making the request (for permissions and logging)
        """
        self.user = user
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
    
    def log_action(self, action: str, details: str = "", level: str = "info"):
        """
        Log a service action with user context.
        
        Args:
            action: The action being performed
            details: Additional details about the action
            level: Log level (debug, info, warning, error)
        """
        user_info = f"User {self.user.id}" if self.user else "Anonymous"
        message = f"{user_info} - {action}"
        if details:
            message += f" - {details}"
        
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)
    
    def require_user(self):
        """Ensure a user is set for this service instance."""
        if not self.user:
            raise PermissionError("User authentication required for this operation")
    
    def require_permission(self, permission_check, error_message="Permission denied"):
        """
        Check a permission condition and raise error if false.
        
        Args:
            permission_check: Boolean or callable that returns boolean
            error_message: Error message to display if permission denied
        """
        if callable(permission_check):
            has_permission = permission_check()
        else:
            has_permission = permission_check
        
        if not has_permission:
            self.log_action("Permission denied", error_message, "warning")
            raise PermissionError(error_message)
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str]):
        """
        Validate that required fields are present in data.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    @transaction.atomic
    def atomic_operation(self, operation, *args, **kwargs):
        """
        Execute an operation within a database transaction.
        
        Args:
            operation: Callable to execute
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            The result of the operation
        """
        try:
            self.log_action("Starting atomic operation", f"{operation.__name__}")
            result = operation(*args, **kwargs)
            self.log_action("Completed atomic operation", f"{operation.__name__}")
            return result
        except Exception as e:
            self.log_action("Failed atomic operation", f"{operation.__name__}: {str(e)}", "error")
            raise
    
    def get_current_timestamp(self):
        """Get the current timestamp."""
        return timezone.now()
    
    def format_error_response(self, error: Exception, context: Dict[str, Any] = None):
        """
        Format an error into a consistent response structure.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Dictionary with error details
        """
        error_data = {
            'error': True,
            'error_type': error.__class__.__name__,
            'message': str(error),
            'timestamp': self.get_current_timestamp().isoformat(),
        }
        
        if context:
            error_data['context'] = context
        
        return error_data
    
    def paginate_queryset(self, queryset, page: int = 1, page_size: int = 20):
        """
        Paginate a queryset with consistent results.
        
        Args:
            queryset: Django QuerySet to paginate
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dictionary with paginated results and metadata
        """
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        
        paginator = Paginator(queryset, page_size)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        return {
            'results': list(page_obj.object_list),
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
    
    def cache_key(self, *parts):
        """
        Generate a consistent cache key from parts.
        
        Args:
            *parts: Parts to join into a cache key
            
        Returns:
            String cache key
        """
        return ':'.join(str(part) for part in parts)
    
    def get_from_cache(self, key: str, default=None):
        """
        Get a value from cache with fallback.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        try:
            from django.core.cache import cache
            return cache.get(key, default)
        except Exception as e:
            self.log_action("Cache get failed", f"Key: {key}, Error: {str(e)}", "warning")
            return default
    
    def set_cache(self, key: str, value: Any, timeout: int = 300):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds (default: 5 minutes)
        """
        try:
            from django.core.cache import cache
            cache.set(key, value, timeout)
        except Exception as e:
            self.log_action("Cache set failed", f"Key: {key}, Error: {str(e)}", "warning")
    
    def invalidate_cache(self, pattern: str = None):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match for cache invalidation
        """
        try:
            from django.core.cache import cache
            if pattern:
                # This would require a cache backend that supports pattern matching
                # For now, just log the intent
                self.log_action("Cache invalidation requested", f"Pattern: {pattern}")
            else:
                cache.clear()
        except Exception as e:
            self.log_action("Cache invalidation failed", f"Error: {str(e)}", "warning")
    
    def send_notification(self, notification_type: str, recipients: List[Any], data: Dict[str, Any]):
        """
        Send a notification to users.
        
        Args:
            notification_type: Type of notification to send
            recipients: List of users to notify
            data: Notification data
        """
        # Placeholder for notification system integration
        self.log_action(
            "Notification sent", 
            f"Type: {notification_type}, Recipients: {len(recipients)}"
        )
    
    def track_event(self, event_name: str, properties: Dict[str, Any] = None):
        """
        Track an analytics event.
        
        Args:
            event_name: Name of the event to track
            properties: Additional event properties
        """
        # Placeholder for analytics integration
        self.log_action(
            "Event tracked", 
            f"Event: {event_name}, Properties: {properties}"
        )