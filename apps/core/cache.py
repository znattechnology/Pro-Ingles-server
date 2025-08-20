"""
Cache utilities and configurations for Tuwi Beauty Platform.
"""

import hashlib
import json
from typing import Any, Optional, Union
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Centralized cache management system."""
    
    # Cache key prefixes
    PREFIX_USER = "user"
    PREFIX_BRAIDER = "braider"
    PREFIX_BOOKING = "booking"
    PREFIX_PRODUCT = "product"
    PREFIX_REVIEW = "review"
    PREFIX_ML = "ml"
    PREFIX_ANALYTICS = "analytics"
    PREFIX_SEARCH = "search"
    
    # Default timeouts (in seconds)
    TIMEOUT_SHORT = 300      # 5 minutes
    TIMEOUT_MEDIUM = 1800    # 30 minutes
    TIMEOUT_LONG = 3600      # 1 hour
    TIMEOUT_DAILY = 86400    # 24 hours
    TIMEOUT_WEEKLY = 604800  # 7 days
    
    @classmethod
    def _make_key(cls, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key with consistent format."""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (int, str)):
                key_parts.append(str(arg))
            else:
                # For complex objects, create a hash
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, sort_keys=True)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            key_parts.append(kwargs_hash)
        
        return ":".join(key_parts)
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            value = cache.get(key, default)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {str(e)}")
            return default
    
    @classmethod
    def set(cls, key: str, value: Any, timeout: int = TIMEOUT_MEDIUM) -> bool:
        """Set value in cache."""
        try:
            cache.set(key, value, timeout)
            logger.debug(f"Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {str(e)}")
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """Delete value from cache."""
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {str(e)}")
            return False
    
    @classmethod
    def clear_pattern(cls, pattern: str) -> bool:
        """Clear cache keys matching pattern."""
        try:
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
                logger.info(f"Cache CLEAR PATTERN: {pattern}")
                return True
            else:
                logger.warning("Cache backend doesn't support pattern deletion")
                return False
        except Exception as e:
            logger.error(f"Cache CLEAR PATTERN error for {pattern}: {str(e)}")
            return False
    
    @classmethod
    def get_or_set(cls, key: str, callable_func, timeout: int = TIMEOUT_MEDIUM) -> Any:
        """Get from cache or set if not exists."""
        try:
            value = cls.get(key)
            if value is None:
                value = callable_func()
                cls.set(key, value, timeout)
            return value
        except Exception as e:
            logger.error(f"Cache GET_OR_SET error for key {key}: {str(e)}")
            return callable_func()


class UserCache:
    """User-specific cache operations."""
    
    @staticmethod
    def get_user_profile_key(user_id: int) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_USER, "profile", user_id)
    
    @staticmethod
    def get_user_bookings_key(user_id: int) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_USER, "bookings", user_id)
    
    @staticmethod
    def get_user_recommendations_key(user_id: int, rec_type: str = "braider") -> str:
        return CacheManager._make_key(CacheManager.PREFIX_USER, "recommendations", user_id, rec_type)
    
    @staticmethod
    def clear_user_cache(user_id: int):
        """Clear all cache for a specific user."""
        pattern = f"{CacheManager.PREFIX_USER}:*:{user_id}:*"
        CacheManager.clear_pattern(pattern)


class BraiderCache:
    """Braider-specific cache operations."""
    
    @staticmethod
    def get_braider_profile_key(braider_id: int) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_BRAIDER, "profile", braider_id)
    
    @staticmethod
    def get_braider_services_key(braider_id: int) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_BRAIDER, "services", braider_id)
    
    @staticmethod
    def get_braider_reviews_key(braider_id: int) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_BRAIDER, "reviews", braider_id)
    
    @staticmethod
    def get_braider_availability_key(braider_id: int, date: str) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_BRAIDER, "availability", braider_id, date)
    
    @staticmethod
    def clear_braider_cache(braider_id: int):
        """Clear all cache for a specific braider."""
        pattern = f"{CacheManager.PREFIX_BRAIDER}:*:{braider_id}:*"
        CacheManager.clear_pattern(pattern)


class SearchCache:
    """Search-specific cache operations."""
    
    @staticmethod
    def get_search_key(query: str, filters: dict = None, location: str = None) -> str:
        return CacheManager._make_key(
            CacheManager.PREFIX_SEARCH, 
            "braiders", 
            query, 
            location=location,
            filters=filters
        )
    
    @staticmethod
    def get_popular_searches_key() -> str:
        return CacheManager._make_key(CacheManager.PREFIX_SEARCH, "popular")


class MLCache:
    """Machine Learning cache operations."""
    
    @staticmethod
    def get_model_key(model_name: str) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_ML, "model", model_name)
    
    @staticmethod
    def get_prediction_key(model_name: str, input_hash: str) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_ML, "prediction", model_name, input_hash)
    
    @staticmethod
    def get_sentiment_key(text_hash: str) -> str:
        return CacheManager._make_key(CacheManager.PREFIX_ML, "sentiment", text_hash)


class AnalyticsCache:
    """Analytics cache operations."""
    
    @staticmethod
    def get_stats_key(stat_type: str, period: str = "daily") -> str:
        return CacheManager._make_key(CacheManager.PREFIX_ANALYTICS, "stats", stat_type, period)
    
    @staticmethod
    def get_dashboard_key(user_type: str = "admin") -> str:
        return CacheManager._make_key(CacheManager.PREFIX_ANALYTICS, "dashboard", user_type)


# Decorator for caching view results
def cache_view_result(timeout: int = CacheManager.TIMEOUT_MEDIUM, key_func=None):
    """Decorator to cache view results."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = CacheManager._make_key(
                    "view", 
                    view_func.__name__, 
                    request.method,
                    request.path,
                    **request.GET.dict()
                )
            
            # Try to get from cache
            result = CacheManager.get(cache_key)
            if result is not None:
                return result
            
            # Execute view and cache result
            result = view_func(request, *args, **kwargs)
            CacheManager.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


# Cache invalidation helpers
def invalidate_user_cache(user_id: int):
    """Invalidate all cache related to a user."""
    UserCache.clear_user_cache(user_id)
    
    # Also clear related recommendations
    pattern = f"{CacheManager.PREFIX_ML}:*:*:{user_id}:*"
    CacheManager.clear_pattern(pattern)


def invalidate_braider_cache(braider_id: int):
    """Invalidate all cache related to a braider."""
    BraiderCache.clear_braider_cache(braider_id)
    
    # Clear search results that might include this braider
    pattern = f"{CacheManager.PREFIX_SEARCH}:*"
    CacheManager.clear_pattern(pattern)


def warm_up_cache():
    """Warm up cache with frequently accessed data."""
    from django.contrib.auth import get_user_model
    from apps.braiders.models import Braider
    
    logger.info("Starting cache warm-up...")
    
    try:
        # Warm up popular braiders
        popular_braiders = Braider.objects.filter(
            is_active=True
        ).order_by('-rating')[:20]
        
        for braider in popular_braiders:
            key = BraiderCache.get_braider_profile_key(braider.id)
            CacheManager.set(key, braider, CacheManager.TIMEOUT_LONG)
        
        logger.info(f"Warmed up {len(popular_braiders)} braider profiles")
        
        # Warm up analytics
        analytics_key = AnalyticsCache.get_dashboard_key("admin")
        # This would be populated by actual analytics data
        CacheManager.set(analytics_key, {"cached": True}, CacheManager.TIMEOUT_MEDIUM)
        
        logger.info("Cache warm-up completed successfully")
        
    except Exception as e:
        logger.error(f"Cache warm-up failed: {str(e)}")


# Cache statistics
def get_cache_stats():
    """Get cache statistics."""
    try:
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'info'):
            return cache._cache.info()
        return {"status": "Cache stats not available"}
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return {"error": str(e)}