"""
Decorators for teacher API security.
"""

from functools import wraps
from rest_framework.exceptions import PermissionDenied


def teacher_required(view_func):
    """
    Decorator that ensures only teachers can access the endpoint.
    Should be used after @permission_classes([IsAuthenticated]) decorator.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated (should be handled by permission_classes)
        if not request.user.is_authenticated:
            raise PermissionDenied("Autenticação obrigatória")
        
        # Check if user has teacher role
        if getattr(request.user, 'role', None) != 'teacher':
            raise PermissionDenied("Apenas professores podem acessar este endpoint")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def course_owner_required(view_func):
    """
    Decorator that ensures only course owner can access the endpoint.
    Requires courseId parameter in URL.
    Should be used after @teacher_required decorator.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        course_id = kwargs.get('courseId')
        if not course_id:
            raise PermissionDenied("ID do curso é obrigatório")
        
        try:
            from apps.courses.models import Course
            course = Course.objects.get(id=course_id)
            
            if course.teacher != request.user:
                raise PermissionDenied("Apenas o professor proprietário pode acessar este curso")
                
        except Course.DoesNotExist:
            raise PermissionDenied("Curso não encontrado")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view