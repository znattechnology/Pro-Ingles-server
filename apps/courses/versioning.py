"""
API versioning system for course endpoints.

This module provides versioning capabilities to maintain backward compatibility
while allowing API evolution and new feature development.
"""

from rest_framework.versioning import URLPathVersioning
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


class CourseAPIVersioning(URLPathVersioning):
    """
    Custom API versioning for course endpoints.
    
    Supports version-specific behavior while maintaining backward compatibility.
    """
    
    default_version = 'v1'
    allowed_versions = ['v1', 'v2']
    version_param = 'version'
    
    # Version-specific feature flags
    VERSION_FEATURES = {
        'v1': {
            'chapter_resources': False,     # Original API without resources
            'quiz_integration': False,      # No quiz functionality
            'advanced_progress': False,     # Basic progress tracking only
            'pagination_metadata': False,  # Simple pagination
            'field_selection': False,      # No selective field loading
        },
        'v2': {
            'chapter_resources': True,      # Full resource management
            'quiz_integration': True,       # Complete quiz system
            'advanced_progress': True,      # Detailed progress analytics
            'pagination_metadata': True,   # Enhanced pagination with metadata
            'field_selection': True,       # Selective field loading support
        }
    }
    
    def determine_version(self, request, *args, **kwargs):
        """
        Determine the API version for this request.
        
        Priority:
        1. URL path version (e.g., /api/v2/courses/)
        2. Accept header version
        3. Query parameter version
        4. Default version
        """
        # First try URL path versioning
        version = super().determine_version(request, *args, **kwargs)
        
        if version:
            return version
        
        # Try Accept header versioning
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'version=' in accept_header:
            try:
                version = accept_header.split('version=')[1].split(';')[0].strip()
                if version in self.allowed_versions:
                    return version
            except (IndexError, AttributeError):
                pass
        
        # Try query parameter versioning
        version = request.GET.get('version')
        if version and version in self.allowed_versions:
            return version
        
        # Return default version
        return self.default_version
    
    def is_allowed_version(self, version):
        """Check if the requested version is supported."""
        return version in self.allowed_versions
    
    def get_version_features(self, version):
        """Get feature flags for a specific version."""
        return self.VERSION_FEATURES.get(version, self.VERSION_FEATURES[self.default_version])


class VersionedResponseMixin:
    """
    Mixin to add version-aware response handling to views.
    """
    
    def get_version_features(self):
        """Get feature flags for the current request version."""
        if hasattr(self.request, 'version'):
            versioning = CourseAPIVersioning()
            return versioning.get_version_features(self.request.version)
        return CourseAPIVersioning.VERSION_FEATURES['v1']
    
    def get_versioned_serializer_context(self):
        """Get context with version-specific settings."""
        context = super().get_serializer_context() if hasattr(super(), 'get_serializer_context') else {}
        
        features = self.get_version_features()
        context.update({
            'version_features': features,
            'api_version': getattr(self.request, 'version', 'v1'),
            'include_resources': features.get('chapter_resources', False),
            'include_quiz_data': features.get('quiz_integration', False),
            'advanced_progress': features.get('advanced_progress', False),
            'field_selection': features.get('field_selection', False),
        })
        
        return context
    
    def get_versioned_response(self, data, message="Success", **kwargs):
        """Create a version-appropriate response format."""
        version = getattr(self.request, 'version', 'v1')
        features = self.get_version_features()
        
        if version == 'v1':
            # V1 format: Simple response structure
            response_data = {
                'message': message,
                'data': data
            }
        else:
            # V2+ format: Enhanced response with metadata
            response_data = {
                'message': message,
                'data': data,
                'meta': {
                    'api_version': version,
                    'timestamp': self._get_current_timestamp(),
                    'features': features,
                    **kwargs
                }
            }
        
        return Response(response_data)
    
    def _get_current_timestamp(self):
        """Get current timestamp in ISO format."""
        from django.utils import timezone
        return timezone.now().isoformat()


class APIDeprecationMixin:
    """
    Mixin to handle API deprecation warnings and sunset notices.
    """
    
    # Deprecation schedule
    DEPRECATION_SCHEDULE = {
        'v1': {
            'deprecated_since': '2024-01-01',
            'sunset_date': '2024-12-31',
            'replacement_version': 'v2',
            'deprecation_message': 'API v1 is deprecated. Please migrate to v2.'
        }
    }
    
    def add_deprecation_headers(self, response):
        """Add deprecation headers to the response."""
        version = getattr(self.request, 'version', 'v1')
        
        if version in self.DEPRECATION_SCHEDULE:
            deprecation_info = self.DEPRECATION_SCHEDULE[version]
            
            # Add standard deprecation headers
            response['Deprecation'] = deprecation_info['sunset_date']
            response['Sunset'] = deprecation_info['sunset_date']
            response['Link'] = f'</api/{deprecation_info["replacement_version"]}/courses/>; rel="successor-version"'
            
            # Add custom warning header
            response['Warning'] = f'299 - "{deprecation_info["deprecation_message"]}"'
        
        return response
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Override to add deprecation headers to all responses."""
        response = super().finalize_response(request, response, *args, **kwargs)
        return self.add_deprecation_headers(response)


class VersionAwareSerializer:
    """
    Mixin for serializers that need to behave differently based on API version.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get version from context
        context = kwargs.get('context', {})
        self.api_version = context.get('api_version', 'v1')
        self.version_features = context.get('version_features', {})
        
        # Remove version-specific fields for older versions
        self._remove_version_specific_fields()
    
    def _remove_version_specific_fields(self):
        """Remove fields that aren't supported in the current version."""
        if self.api_version == 'v1':
            # V1 doesn't support certain fields
            fields_to_remove = []
            
            if not self.version_features.get('chapter_resources', False):
                fields_to_remove.extend(['resources', 'resource_count'])
            
            if not self.version_features.get('quiz_integration', False):
                fields_to_remove.extend(['quiz_data', 'quiz_enabled'])
            
            if not self.version_features.get('advanced_progress', False):
                fields_to_remove.extend(['detailed_progress', 'time_spent', 'completion_analytics'])
            
            # Remove fields that don't exist in this version
            for field_name in fields_to_remove:
                self.fields.pop(field_name, None)
    
    def to_representation(self, instance):
        """Override to provide version-specific data representation."""
        data = super().to_representation(instance)
        
        # V1 compatibility transformations
        if self.api_version == 'v1':
            data = self._transform_for_v1_compatibility(data)
        
        return data
    
    def _transform_for_v1_compatibility(self, data):
        """Transform data for V1 API compatibility."""
        # Convert new field names to legacy names if needed
        field_mappings = {
            'created_at': 'dateCreated',
            'updated_at': 'dateModified',
            # Add more mappings as needed
        }
        
        for new_field, old_field in field_mappings.items():
            if new_field in data:
                data[old_field] = data[new_field]
                # Keep both for transition period
        
        return data


def get_api_version_from_request(request):
    """Utility function to get API version from request."""
    versioning = CourseAPIVersioning()
    return versioning.determine_version(request)


def requires_version(min_version):
    """
    Decorator to enforce minimum API version for view methods.
    
    Usage:
    @requires_version('v2')
    def create_quiz(self, request):
        # This endpoint only available in v2+
        pass
    """
    def decorator(view_func):
        def wrapped_view(self, request, *args, **kwargs):
            current_version = getattr(request, 'version', 'v1')
            
            # Simple version comparison (assumes v1, v2, v3 format)
            current_version_num = int(current_version.replace('v', ''))
            min_version_num = int(min_version.replace('v', ''))
            
            if current_version_num < min_version_num:
                return Response({
                    'error': f'This feature requires API version {min_version} or higher',
                    'current_version': current_version,
                    'required_version': min_version,
                    'upgrade_url': f'/api/{min_version}/courses/'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return view_func(self, request, *args, **kwargs)
        
        return wrapped_view
    return decorator


class VersionTransitionHelper:
    """
    Helper class for managing data transformations between API versions.
    """
    
    @staticmethod
    def transform_course_data_v1_to_v2(v1_data):
        """Transform course data from v1 format to v2 format."""
        v2_data = v1_data.copy()
        
        # Add new fields with default values
        v2_data.update({
            'resource_count': 0,
            'quiz_enabled': False,
            'detailed_progress': {},
            'completion_analytics': {}
        })
        
        return v2_data
    
    @staticmethod
    def transform_course_data_v2_to_v1(v2_data):
        """Transform course data from v2 format to v1 format."""
        v1_data = v2_data.copy()
        
        # Remove v2-specific fields
        v2_only_fields = [
            'resource_count', 'quiz_enabled', 'detailed_progress', 
            'completion_analytics', 'quiz_data'
        ]
        
        for field in v2_only_fields:
            v1_data.pop(field, None)
        
        return v1_data


# Version-specific constants
class APIVersionConstants:
    """Constants that vary by API version."""
    
    V1_CONSTANTS = {
        'DEFAULT_PAGE_SIZE': 20,
        'MAX_PAGE_SIZE': 100,
        'SUPPORTED_FORMATS': ['json'],
        'RATE_LIMIT': 1000,  # requests per hour
    }
    
    V2_CONSTANTS = {
        'DEFAULT_PAGE_SIZE': 12,  # Optimized for frontend grids
        'MAX_PAGE_SIZE': 200,     # Higher limit for v2
        'SUPPORTED_FORMATS': ['json', 'xml'],
        'RATE_LIMIT': 2000,       # Higher limit for v2
    }
    
    @classmethod
    def get_constants_for_version(cls, version):
        """Get version-specific constants."""
        if version == 'v2':
            return cls.V2_CONSTANTS
        return cls.V1_CONSTANTS