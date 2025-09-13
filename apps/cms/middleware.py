"""
CMS Middleware for caching and optimization
"""
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import json


class CMSCacheMiddleware(MiddlewareMixin):
    """
    Middleware to handle CMS caching and optimization
    """
    
    def process_request(self, request):
        # Skip caching for admin and non-CMS requests
        if request.path.startswith('/admin/') or '/cms/' not in request.path:
            return None
        
        # Skip caching for authenticated users making changes
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return None
        
        # Generate cache key based on request
        cache_key = self.get_cache_key(request)
        
        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            response = JsonResponse(cached_response)
            response['X-Cache'] = 'HIT'
            response['X-Cache-Key'] = cache_key
            return response
        
        return None
    
    def process_response(self, request, response):
        # Only cache successful CMS API responses
        if (
            '/cms/' in request.path and 
            request.method == 'GET' and 
            response.status_code == 200 and
            response.get('Content-Type', '').startswith('application/json')
        ):
            cache_key = self.get_cache_key(request)
            
            # Cache for 15 minutes by default
            cache_timeout = getattr(settings, 'CMS_CACHE_TIMEOUT', 900)
            
            try:
                response_data = json.loads(response.content)
                cache.set(cache_key, response_data, cache_timeout)
                response['X-Cache'] = 'MISS'
                response['X-Cache-Key'] = cache_key
                response['X-Cache-Timeout'] = str(cache_timeout)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        # Add cache control headers for static content
        if '/cms/' in request.path:
            response['Cache-Control'] = 'public, max-age=900'  # 15 minutes
            response['Vary'] = 'Accept-Encoding'
        
        return response
    
    def get_cache_key(self, request):
        """Generate cache key for request"""
        path = request.get_full_path()
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:50]  # Limit to 50 chars
        
        # Include user type in cache key for personalized content
        user_type = 'anonymous'
        if request.user.is_authenticated:
            if request.user.is_staff:
                user_type = 'staff'
            else:
                user_type = 'user'
        
        return f"cms_cache:{hash(path)}:{hash(user_agent)}:{user_type}"


class CMSPerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to track CMS performance metrics
    """
    
    def process_request(self, request):
        if '/cms/' in request.path:
            request._cms_start_time = time.time()
    
    def process_response(self, request, response):
        if '/cms/' in request.path and hasattr(request, '_cms_start_time'):
            duration = time.time() - request._cms_start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # Log slow requests
            if duration > 1.0:  # Requests taking more than 1 second
                import logging
                logger = logging.getLogger('cms.performance')
                logger.warning(
                    f"Slow CMS request: {request.method} {request.get_full_path()} "
                    f"took {duration:.3f}s"
                )
        
        return response


class CMSMaintenanceMiddleware(MiddlewareMixin):
    """
    Middleware to handle maintenance mode
    """
    
    def process_request(self, request):
        # Skip maintenance mode for admin users
        if request.user.is_authenticated and request.user.is_staff:
            return None
        
        # Check maintenance mode from cache first
        maintenance_mode = cache.get('cms_maintenance_mode')
        if maintenance_mode is None:
            # Fallback to database check
            try:
                from .models import LandingPageSettings
                settings_obj = LandingPageSettings.objects.filter(is_active=True).first()
                maintenance_mode = settings_obj.maintenance_mode if settings_obj else False
                
                # Cache for 5 minutes
                cache.set('cms_maintenance_mode', maintenance_mode, 300)
            except Exception:
                maintenance_mode = False
        
        if maintenance_mode:
            maintenance_message = cache.get('cms_maintenance_message')
            if maintenance_message is None:
                try:
                    from .models import LandingPageSettings
                    settings_obj = LandingPageSettings.objects.filter(is_active=True).first()
                    maintenance_message = (
                        settings_obj.maintenance_message if settings_obj and settings_obj.maintenance_message
                        else "Site em manutenção. Voltamos em breve!"
                    )
                    cache.set('cms_maintenance_message', maintenance_message, 300)
                except Exception:
                    maintenance_message = "Site em manutenção. Voltamos em breve!"
            
            return JsonResponse({
                'maintenance_mode': True,
                'message': maintenance_message,
                'retry_after': 1800  # 30 minutes
            }, status=503)
        
        return None