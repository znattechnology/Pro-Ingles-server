"""
Custom exception handlers for the API.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.http import Http404
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Add custom handling
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'An error occurred',
            'details': response.data,
            'status_code': response.status_code
        }
        
        # Check if this is a login endpoint error first
        request = context.get('request') if context else None
        is_login_endpoint = request and request.path.endswith('/login/')
        
        # Handle specific exception types
        if isinstance(exc, AuthenticationFailed):
            # Ensure AuthenticationFailed returns 401 status
            response.status_code = status.HTTP_401_UNAUTHORIZED
            custom_response_data['status_code'] = status.HTTP_401_UNAUTHORIZED
            custom_response_data['message'] = str(exc.detail)
        elif is_login_endpoint and response.status_code == 400:
            # Convert all validation errors from login endpoint to 401 for security
            # This includes empty fields, invalid formats, etc.
            response.status_code = status.HTTP_401_UNAUTHORIZED
            custom_response_data['status_code'] = status.HTTP_401_UNAUTHORIZED
            custom_response_data['message'] = 'Credenciais inválidas. Verifique seu email e senha.'
        elif isinstance(exc, Http404):
            custom_response_data['message'] = 'Resource not found'
        elif isinstance(exc, PermissionDenied):
            custom_response_data['message'] = 'Permission denied'
        elif hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                # Handle field-specific errors
                custom_response_data['message'] = 'Validation error'
            elif isinstance(exc.detail, list):
                custom_response_data['message'] = str(exc.detail[0])
            else:
                custom_response_data['message'] = str(exc.detail)
        
        response.data = custom_response_data
        
        # Log the error
        request = context.get('request')
        path = getattr(request, 'path', 'Unknown') if request else 'Unknown'
        logger.error(
            f"API Error: {custom_response_data['message']} - "
            f"Status: {response.status_code} - "
            f"Path: {path}"
        )
    
    return response


class APIException(Exception):
    """Base API exception class."""
    
    def __init__(self, message="An error occurred", status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(APIException):
    """Custom validation error."""
    
    def __init__(self, message="Validation failed", status_code=status.HTTP_400_BAD_REQUEST):
        super().__init__(message, status_code)


class NotFoundError(APIException):
    """Custom not found error."""
    
    def __init__(self, message="Resource not found", status_code=status.HTTP_404_NOT_FOUND):
        super().__init__(message, status_code)


class PermissionError(APIException):
    """Custom permission error."""
    
    def __init__(self, message="Permission denied", status_code=status.HTTP_403_FORBIDDEN):
        super().__init__(message, status_code)