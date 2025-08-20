"""
Rate limiting system for Tuwi Beauty Platform.
"""

import time
import hashlib
from typing import Optional, Dict, Any
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.response import Response
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self, cache_backend=None):
        self.cache = cache_backend or cache
        self.default_period = 3600  # 1 hour
        self.default_limit = 1000   # 1000 requests per hour
    
    def _get_cache_key(self, identifier: str, endpoint: str) -> str:
        """Generate cache key for rate limiting."""
        key_string = f"rate_limit:{endpoint}:{identifier}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_window_start(self, period: int) -> int:
        """Get the start of the current time window."""
        return int(time.time()) // period * period
    
    def is_allowed(self, identifier: str, endpoint: str, limit: int, period: int) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed.
        Returns (is_allowed, rate_info)
        """
        try:
            cache_key = self._get_cache_key(identifier, endpoint)
            window_start = self._get_window_start(period)
            
            # Get current count for this window
            current_data = self.cache.get(cache_key, {})
            current_window = current_data.get('window', 0)
            current_count = current_data.get('count', 0)
            
            # Check if we're in a new window
            if current_window != window_start:
                current_count = 0
                current_window = window_start
            
            # Calculate remaining requests and reset time
            remaining = max(0, limit - current_count)
            reset_time = window_start + period
            
            rate_info = {
                'limit': limit,
                'remaining': remaining,
                'reset': reset_time,
                'reset_human': timezone.datetime.fromtimestamp(reset_time).isoformat(),
                'period': period,
            }
            
            # Check if request is allowed
            if current_count >= limit:
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    endpoint=endpoint,
                    limit=limit,
                    count=current_count
                )
                return False, rate_info
            
            # Increment counter
            new_count = current_count + 1
            new_data = {
                'window': current_window,
                'count': new_count,
            }
            
            # Store with TTL slightly longer than the period
            self.cache.set(cache_key, new_data, period + 60)
            
            # Update remaining count
            rate_info['remaining'] = max(0, limit - new_count)
            
            return True, rate_info
            
        except Exception as e:
            logger.error("Rate limiting error", error=str(e))
            # On error, allow the request (fail open)
            return True, {
                'limit': limit,
                'remaining': limit,
                'reset': int(time.time()) + period,
                'period': period,
                'error': str(e),
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_identifier(request) -> str:
    """Get client identifier for rate limiting."""
    # Prefer authenticated user ID
    if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
        return f"user:{request.user.id}"
    
    # Fall back to IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    return f"ip:{ip}"


def rate_limit(limit: int = None, period: int = None, endpoint: str = None):
    """
    Rate limiting decorator.
    
    Args:
        limit: Maximum number of requests allowed
        period: Time period in seconds
        endpoint: Custom endpoint identifier
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Use defaults if not specified
            actual_limit = limit or rate_limiter.default_limit
            actual_period = period or rate_limiter.default_period
            actual_endpoint = endpoint or f"{view_func.__module__}.{view_func.__name__}"
            
            # Get client identifier
            identifier = get_client_identifier(request)
            
            # Check rate limit
            is_allowed, rate_info = rate_limiter.is_allowed(
                identifier, actual_endpoint, actual_limit, actual_period
            )
            
            # Add rate limit headers to response
            def add_rate_limit_headers(response):
                if hasattr(response, '__setitem__'):  # Django response
                    response['X-RateLimit-Limit'] = str(rate_info['limit'])
                    response['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                    response['X-RateLimit-Reset'] = str(rate_info['reset'])
                elif hasattr(response, 'headers'):  # DRF response
                    response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                    response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                    response.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                return response
            
            # If rate limit exceeded, return 429
            if not is_allowed:
                if hasattr(request, 'accepted_renderer'):  # DRF request
                    response = Response(
                        {
                            'error': 'Rate limit exceeded',
                            'detail': f'Too many requests. Limit: {rate_info["limit"]} per {rate_info["period"]} seconds',
                            'rate_limit': rate_info,
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                else:  # Django request
                    response = JsonResponse(
                        {
                            'error': 'Rate limit exceeded',
                            'detail': f'Too many requests. Limit: {rate_info["limit"]} per {rate_info["period"]} seconds',
                            'rate_limit': rate_info,
                        },
                        status=429
                    )
                
                return add_rate_limit_headers(response)
            
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Add rate limit headers to successful response
            return add_rate_limit_headers(response)
        
        return wrapper
    return decorator


# Predefined rate limit decorators for common use cases
def rate_limit_strict(view_func):
    """Strict rate limit: 100 requests per hour."""
    return rate_limit(limit=100, period=3600)(view_func)


def rate_limit_moderate(view_func):
    """Moderate rate limit: 500 requests per hour."""
    return rate_limit(limit=500, period=3600)(view_func)


def rate_limit_lenient(view_func):
    """Lenient rate limit: 2000 requests per hour."""
    return rate_limit(limit=2000, period=3600)(view_func)


def rate_limit_api_key(view_func):
    """Rate limit for API key usage: 5000 requests per hour."""
    return rate_limit(limit=5000, period=3600)(view_func)


def rate_limit_auth(view_func):
    """Rate limit for authentication endpoints: 10 requests per 15 minutes."""
    return rate_limit(limit=10, period=900)(view_func)


def rate_limit_ml(view_func):
    """Rate limit for ML endpoints: 50 requests per hour."""
    return rate_limit(limit=50, period=3600)(view_func)


class RateLimitMiddleware:
    """
    Middleware for global rate limiting.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.global_limits = {
            '/api/v1/auth/': {'limit': 20, 'period': 900},  # 20 per 15 min
            '/api/v1/ml/': {'limit': 100, 'period': 3600},  # 100 per hour
            '/api/v1/analytics/': {'limit': 200, 'period': 3600},  # 200 per hour
        }
    
    def __call__(self, request):
        # Check if path matches any global limits
        for path_prefix, limits in self.global_limits.items():
            if request.path.startswith(path_prefix):
                identifier = get_client_identifier(request)
                is_allowed, rate_info = rate_limiter.is_allowed(
                    identifier, 
                    f"global:{path_prefix}",
                    limits['limit'],
                    limits['period']
                )
                
                if not is_allowed:
                    return JsonResponse(
                        {
                            'error': 'Rate limit exceeded',
                            'detail': f'Global rate limit for {path_prefix} exceeded',
                            'rate_limit': rate_info,
                        },
                        status=429,
                        headers={
                            'X-RateLimit-Limit': str(rate_info['limit']),
                            'X-RateLimit-Remaining': str(rate_info['remaining']),
                            'X-RateLimit-Reset': str(rate_info['reset']),
                        }
                    )
        
        response = self.get_response(request)
        return response


class IPWhitelist:
    """Manage IP whitelist for rate limiting exemptions."""
    
    def __init__(self):
        self.whitelist_key = 'rate_limit_whitelist'
        self.default_whitelist = [
            '127.0.0.1',
            'localhost',
            '::1',
        ]
    
    def get_whitelist(self) -> list:
        """Get current IP whitelist."""
        whitelist = cache.get(self.whitelist_key, self.default_whitelist)
        return whitelist
    
    def add_ip(self, ip: str) -> bool:
        """Add IP to whitelist."""
        try:
            whitelist = self.get_whitelist()
            if ip not in whitelist:
                whitelist.append(ip)
                cache.set(self.whitelist_key, whitelist, 86400)  # 24 hours
                logger.info("IP added to whitelist", ip=ip)
            return True
        except Exception as e:
            logger.error("Failed to add IP to whitelist", ip=ip, error=str(e))
            return False
    
    def remove_ip(self, ip: str) -> bool:
        """Remove IP from whitelist."""
        try:
            whitelist = self.get_whitelist()
            if ip in whitelist:
                whitelist.remove(ip)
                cache.set(self.whitelist_key, whitelist, 86400)
                logger.info("IP removed from whitelist", ip=ip)
            return True
        except Exception as e:
            logger.error("Failed to remove IP from whitelist", ip=ip, error=str(e))
            return False
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        whitelist = self.get_whitelist()
        return ip in whitelist


# Global IP whitelist instance
ip_whitelist = IPWhitelist()


def rate_limit_with_whitelist(limit: int = None, period: int = None, endpoint: str = None):
    """Rate limiting decorator that respects IP whitelist."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if IP is whitelisted
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            if ip_whitelist.is_whitelisted(ip):
                # Skip rate limiting for whitelisted IPs
                return view_func(request, *args, **kwargs)
            
            # Apply normal rate limiting
            return rate_limit(limit, period, endpoint)(view_func)(request, *args, **kwargs)
        
        return wrapper
    return decorator