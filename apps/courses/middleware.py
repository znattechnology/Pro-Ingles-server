"""
Performance monitoring middleware for course API endpoints.

Provides query debugging, performance metrics, and monitoring capabilities.
"""

import time
import logging
from django.db import connection
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger('courses.performance')


class QueryDebugMiddleware(MiddlewareMixin):
    """
    Middleware to log and monitor database query performance.
    
    Features:
    - Query count tracking
    - Slow query detection and logging
    - N+1 query pattern detection
    - Performance metrics collection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ENABLE_QUERY_DEBUG', settings.DEBUG)
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.5)  # 500ms
        self.max_queries_warning = getattr(settings, 'MAX_QUERIES_WARNING', 50)
        super().__init__(get_response)
    
    def process_request(self, request):
        """Initialize performance tracking for the request."""
        if not self.enabled:
            return None
        
        # Store initial query count and start time
        request._debug_start_time = time.time()
        request._debug_start_queries = len(connection.queries)
        request._debug_queries = []
        
        return None
    
    def process_response(self, request, response):
        """Process and log performance metrics after response."""
        if not self.enabled or not hasattr(request, '_debug_start_time'):
            return response
        
        # Calculate metrics
        end_time = time.time()
        request_time = end_time - request._debug_start_time
        query_count = len(connection.queries) - request._debug_start_queries
        
        # Get queries executed during this request
        queries = connection.queries[request._debug_start_queries:]
        
        # Analyze queries
        slow_queries = []
        duplicate_queries = {}
        total_query_time = 0
        
        for query in queries:
            query_time = float(query.get('time', 0))
            total_query_time += query_time
            
            # Check for slow queries
            if query_time >= self.slow_query_threshold:
                slow_queries.append({
                    'sql': query['sql'][:200] + '...' if len(query['sql']) > 200 else query['sql'],
                    'time': query_time
                })
            
            # Check for duplicate queries (potential N+1)
            sql_normalized = self._normalize_sql(query['sql'])
            if sql_normalized in duplicate_queries:
                duplicate_queries[sql_normalized]['count'] += 1
            else:
                duplicate_queries[sql_normalized] = {'count': 1, 'time': query_time}
        
        # Detect N+1 patterns
        n_plus_one_patterns = {
            sql: data for sql, data in duplicate_queries.items() 
            if data['count'] > 5  # More than 5 identical queries suggests N+1
        }
        
        # Log performance metrics
        log_data = {
            'path': request.path,
            'method': request.method,
            'request_time': round(request_time, 3),
            'query_count': query_count,
            'total_query_time': round(total_query_time, 3),
            'slow_queries': len(slow_queries),
            'n_plus_one_patterns': len(n_plus_one_patterns)
        }
        
        # Log warnings for performance issues
        if query_count > self.max_queries_warning:
            logger.warning(f"High query count detected: {query_count} queries for {request.path}")
        
        if slow_queries:
            logger.warning(f"Slow queries detected for {request.path}: {len(slow_queries)} queries")
            for query in slow_queries[:3]:  # Log first 3 slow queries
                logger.warning(f"Slow query ({query['time']}s): {query['sql']}")
        
        if n_plus_one_patterns:
            logger.warning(f"Potential N+1 queries detected for {request.path}")
            for sql, data in list(n_plus_one_patterns.items())[:2]:  # Log first 2 patterns
                logger.warning(f"N+1 pattern ({data['count']} times): {sql[:100]}...")
        
        # Add debug headers if in debug mode
        if settings.DEBUG and request.GET.get('debug') == 'true':
            response['X-Debug-Query-Count'] = str(query_count)
            response['X-Debug-Query-Time'] = str(round(total_query_time, 3))
            response['X-Debug-Request-Time'] = str(round(request_time, 3))
            response['X-Debug-Slow-Queries'] = str(len(slow_queries))
            response['X-Debug-N-Plus-One'] = str(len(n_plus_one_patterns))
        
        # Log general performance info
        if settings.DEBUG or query_count > 20 or request_time > 1.0:
            logger.info(f"Performance: {request.path} - "
                       f"{query_count} queries, {round(request_time, 3)}s total, "
                       f"{round(total_query_time, 3)}s DB")
        
        return response
    
    def _normalize_sql(self, sql):
        """
        Normalize SQL query to detect patterns.
        Replace parameters with placeholders to identify similar queries.
        """
        import re
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Replace numeric parameters
        sql = re.sub(r'\b\d+\b', '?', sql)
        
        # Replace string parameters (simplified)
        sql = re.sub(r"'[^']*'", "'?'", sql)
        
        # Replace UUID patterns
        sql = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '?', sql, flags=re.IGNORECASE)
        
        return sql


class PerformanceMetricsMiddleware(MiddlewareMixin):
    """
    Middleware to collect and expose performance metrics.
    
    Provides endpoints for monitoring query performance and identifying bottlenecks.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ENABLE_PERFORMANCE_METRICS', settings.DEBUG)
        super().__init__(get_response)
    
    def process_request(self, request):
        """Handle performance metrics requests."""
        if not self.enabled:
            return None
        
        # Expose performance metrics endpoint
        if request.path == '/api/v1/courses/_metrics/' and request.method == 'GET':
            return self._get_performance_metrics(request)
        
        return None
    
    def _get_performance_metrics(self, request):
        """Return current performance metrics."""
        from django.db import connection
        from django.core.cache import cache
        
        # Get database connection info
        db_queries = len(connection.queries) if settings.DEBUG else 'N/A (DEBUG=False)'
        
        # Get cache stats (if available)
        cache_info = getattr(cache, '_cache', {})
        
        metrics = {
            'database': {
                'total_queries': db_queries,
                'connection_status': 'healthy' if connection.connection else 'disconnected'
            },
            'cache': {
                'backend': cache.__class__.__name__,
                'status': 'available'
            },
            'courses': self._get_course_metrics(),
            'performance_tips': self._get_performance_tips()
        }
        
        return JsonResponse({
            'message': 'Performance metrics retrieved successfully',
            'data': metrics
        })
    
    def _get_course_metrics(self):
        """Get course-specific performance metrics."""
        from .models import Course, CourseEnrollment, Transaction
        from django.db.models import Count, Avg
        
        try:
            course_stats = Course.objects.aggregate(
                total_courses=Count('id'),
                avg_enrollments=Avg('enrollments__id')
            )
            
            enrollment_count = CourseEnrollment.objects.count()
            transaction_count = Transaction.objects.count()
            
            return {
                'total_courses': course_stats.get('total_courses', 0),
                'total_enrollments': enrollment_count,
                'total_transactions': transaction_count,
                'avg_enrollments_per_course': round(course_stats.get('avg_enrollments', 0) or 0, 2)
            }
        except Exception as e:
            logger.error(f"Error getting course metrics: {e}")
            return {'error': 'Unable to retrieve course metrics'}
    
    def _get_performance_tips(self):
        """Get performance optimization tips based on current state."""
        tips = []
        
        if not settings.DEBUG:
            tips.append("Consider enabling query debugging in development for better optimization insights")
        
        tips.extend([
            "Use select_related() for foreign keys to avoid N+1 queries",
            "Use prefetch_related() for many-to-many and reverse foreign key relationships",
            "Implement pagination for large datasets",
            "Add database indexes for frequently filtered fields",
            "Use optimized serializers with selective field loading"
        ])
        
        return tips


def debug_queries_context_processor(request):
    """
    Context processor to add query debug info to templates.
    Only works when DEBUG=True.
    """
    if not settings.DEBUG:
        return {}
    
    return {
        'debug_queries': len(connection.queries),
        'debug_enabled': True
    }


class QueryOptimizationMixin:
    """
    Mixin class for views that provides query optimization utilities.
    """
    
    def get_optimized_queryset(self, queryset, optimization_level='standard'):
        """
        Apply query optimizations based on the level specified.
        
        Args:
            queryset: Base QuerySet to optimize
            optimization_level: 'minimal', 'standard', or 'aggressive'
        
        Returns:
            Optimized QuerySet
        """
        if optimization_level == 'minimal':
            return queryset.select_related()
        
        elif optimization_level == 'standard':
            return queryset.select_related().prefetch_related()
        
        elif optimization_level == 'aggressive':
            # Apply all possible optimizations
            return (queryset
                   .select_related()
                   .prefetch_related()
                   .defer('description', 'content')  # Defer large text fields
                   .distinct())
        
        return queryset
    
    def log_query_performance(self, queryset, operation_name):
        """
        Log performance metrics for a specific queryset operation.
        """
        if not settings.DEBUG:
            return
        
        start_queries = len(connection.queries)
        start_time = time.time()
        
        # Force evaluation
        list(queryset)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        query_count = end_queries - start_queries
        execution_time = end_time - start_time
        
        logger.info(f"Query performance for {operation_name}: "
                   f"{query_count} queries in {round(execution_time, 3)}s")