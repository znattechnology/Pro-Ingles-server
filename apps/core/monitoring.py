"""
Advanced monitoring system for Tuwi Beauty Platform.
"""

import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from django.core.management.base import BaseCommand
import structlog

logger = structlog.get_logger(__name__)


class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                network_metrics = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv,
                }
            except Exception:
                network_metrics = {}
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'timestamp': timezone.now().isoformat(),
                'uptime': time.time() - self.start_time,
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free,
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100,
                },
                'network': network_metrics,
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process.cpu_percent(),
                },
            }
        except Exception as e:
            logger.error("Failed to get system metrics", error=str(e))
            return {'error': str(e)}


class DatabaseMonitor:
    """Database performance monitoring."""
    
    @staticmethod
    def get_database_metrics() -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            connection_time = (time.time() - start_time) * 1000  # ms
            
            # Get database size (PostgreSQL specific)
            db_config = settings.DATABASES['default']
            metrics = {
                'connection_time_ms': connection_time,
                'engine': db_config['ENGINE'],
                'connections': {
                    'total': connection.queries_logged if hasattr(connection, 'queries_logged') else 0,
                },
            }
            
            if 'postgresql' in db_config['ENGINE']:
                try:
                    with connection.cursor() as cursor:
                        # Database size
                        cursor.execute(
                            "SELECT pg_size_pretty(pg_database_size(%s))",
                            [db_config['NAME']]
                        )
                        db_size = cursor.fetchone()[0]
                        metrics['database_size'] = db_size
                        
                        # Active connections
                        cursor.execute(
                            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                        )
                        active_connections = cursor.fetchone()[0]
                        metrics['connections']['active'] = active_connections
                        
                except Exception as e:
                    logger.warning("Could not get PostgreSQL specific metrics", error=str(e))
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get database metrics", error=str(e))
            return {'error': str(e)}


class CacheMonitor:
    """Cache performance monitoring."""
    
    @staticmethod
    def get_cache_metrics() -> Dict[str, Any]:
        """Get cache performance metrics."""
        try:
            # Test cache connectivity
            start_time = time.time()
            test_key = 'monitor_test'
            cache.set(test_key, 'test_value', 60)
            cache.get(test_key)
            cache.delete(test_key)
            response_time = (time.time() - start_time) * 1000  # ms
            
            metrics = {
                'response_time_ms': response_time,
                'backend': getattr(cache, '_cache', {}).get('_server', 'unknown'),
            }
            
            # Try to get Redis-specific stats
            try:
                if hasattr(cache, '_cache') and hasattr(cache._cache, '_client'):
                    redis_client = cache._cache._client.get_client()
                    redis_info = redis_client.info()
                    
                    metrics.update({
                        'redis': {
                            'connected_clients': redis_info.get('connected_clients', 0),
                            'used_memory': redis_info.get('used_memory', 0),
                            'used_memory_human': redis_info.get('used_memory_human', '0B'),
                            'keyspace_hits': redis_info.get('keyspace_hits', 0),
                            'keyspace_misses': redis_info.get('keyspace_misses', 0),
                            'total_commands_processed': redis_info.get('total_commands_processed', 0),
                        }
                    })
                    
                    # Calculate hit rate
                    hits = redis_info.get('keyspace_hits', 0)
                    misses = redis_info.get('keyspace_misses', 0)
                    if hits + misses > 0:
                        metrics['redis']['hit_rate'] = hits / (hits + misses)
            
            except Exception as e:
                logger.warning("Could not get Redis specific metrics", error=str(e))
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get cache metrics", error=str(e))
            return {'error': str(e)}


class ApplicationMonitor:
    """Application-specific monitoring."""
    
    @staticmethod
    def get_application_metrics() -> Dict[str, Any]:
        """Get application performance metrics."""
        try:
            from django.contrib.auth import get_user_model
            from apps.bookings.models import Booking
            from apps.braiders.models import Braider
            
            User = get_user_model()
            
            # Get basic counts
            metrics = {
                'users': {
                    'total': User.objects.count(),
                    'active': User.objects.filter(is_active=True).count(),
                    'registered_today': User.objects.filter(
                        date_joined__gte=timezone.now().date()
                    ).count(),
                },
                'braiders': {
                    'total': Braider.objects.count(),
                    'active': Braider.objects.filter(is_active=True).count(),
                },
                'bookings': {
                    'total': Booking.objects.count(),
                    'today': Booking.objects.filter(
                        created_at__gte=timezone.now().date()
                    ).count(),
                    'pending': Booking.objects.filter(status='pending').count(),
                    'confirmed': Booking.objects.filter(status='confirmed').count(),
                },
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get application metrics", error=str(e))
            return {'error': str(e)}


class PerformanceTracker:
    """Track performance metrics over time."""
    
    def __init__(self):
        self.metrics_cache_key = 'performance_metrics'
        self.retention_hours = 24
    
    def record_metrics(self):
        """Record current metrics to cache."""
        try:
            timestamp = timezone.now()
            
            # Collect all metrics
            system_metrics = SystemMonitor().get_system_metrics()
            db_metrics = DatabaseMonitor.get_database_metrics()
            cache_metrics = CacheMonitor.get_cache_metrics()
            app_metrics = ApplicationMonitor.get_application_metrics()
            
            metric_point = {
                'timestamp': timestamp.isoformat(),
                'system': system_metrics,
                'database': db_metrics,
                'cache': cache_metrics,
                'application': app_metrics,
            }
            
            # Get existing metrics
            existing_metrics = cache.get(self.metrics_cache_key, [])
            
            # Add new metric point
            existing_metrics.append(metric_point)
            
            # Keep only last 24 hours
            cutoff_time = timestamp - timedelta(hours=self.retention_hours)
            existing_metrics = [
                m for m in existing_metrics
                if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            # Store back to cache
            cache.set(self.metrics_cache_key, existing_metrics, 86400)  # 24 hours
            
            logger.info("Performance metrics recorded", metrics_count=len(existing_metrics))
            
        except Exception as e:
            logger.error("Failed to record performance metrics", error=str(e))
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics."""
        try:
            metrics = cache.get(self.metrics_cache_key, [])
            
            if hours < 24:
                cutoff_time = timezone.now() - timedelta(hours=hours)
                metrics = [
                    m for m in metrics
                    if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > cutoff_time
                ]
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get metrics history", error=str(e))
            return []


class AlertManager:
    """Manage system alerts based on metrics."""
    
    def __init__(self):
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'db_connection_time_ms': 1000,
            'cache_response_time_ms': 100,
        }
        self.alert_cache_key = 'system_alerts'
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against thresholds and generate alerts."""
        alerts = []
        
        try:
            # Check CPU usage
            if 'system' in metrics and 'cpu' in metrics['system']:
                cpu_percent = metrics['system']['cpu'].get('percent', 0)
                if cpu_percent > self.alert_thresholds['cpu_percent']:
                    alerts.append({
                        'type': 'cpu_high',
                        'level': 'warning',
                        'message': f'High CPU usage: {cpu_percent}%',
                        'value': cpu_percent,
                        'threshold': self.alert_thresholds['cpu_percent'],
                    })
            
            # Check memory usage
            if 'system' in metrics and 'memory' in metrics['system']:
                memory_percent = metrics['system']['memory'].get('percent', 0)
                if memory_percent > self.alert_thresholds['memory_percent']:
                    alerts.append({
                        'type': 'memory_high',
                        'level': 'warning',
                        'message': f'High memory usage: {memory_percent}%',
                        'value': memory_percent,
                        'threshold': self.alert_thresholds['memory_percent'],
                    })
            
            # Check disk usage
            if 'system' in metrics and 'disk' in metrics['system']:
                disk_percent = metrics['system']['disk'].get('percent', 0)
                if disk_percent > self.alert_thresholds['disk_percent']:
                    alerts.append({
                        'type': 'disk_high',
                        'level': 'critical',
                        'message': f'High disk usage: {disk_percent:.1f}%',
                        'value': disk_percent,
                        'threshold': self.alert_thresholds['disk_percent'],
                    })
            
            # Check database connection time
            if 'database' in metrics:
                db_time = metrics['database'].get('connection_time_ms', 0)
                if db_time > self.alert_thresholds['db_connection_time_ms']:
                    alerts.append({
                        'type': 'db_slow',
                        'level': 'warning',
                        'message': f'Slow database connection: {db_time:.1f}ms',
                        'value': db_time,
                        'threshold': self.alert_thresholds['db_connection_time_ms'],
                    })
            
            # Check cache response time
            if 'cache' in metrics:
                cache_time = metrics['cache'].get('response_time_ms', 0)
                if cache_time > self.alert_thresholds['cache_response_time_ms']:
                    alerts.append({
                        'type': 'cache_slow',
                        'level': 'warning',
                        'message': f'Slow cache response: {cache_time:.1f}ms',
                        'value': cache_time,
                        'threshold': self.alert_thresholds['cache_response_time_ms'],
                    })
            
            # Store alerts in cache
            if alerts:
                existing_alerts = cache.get(self.alert_cache_key, [])
                timestamp = timezone.now().isoformat()
                
                for alert in alerts:
                    alert['timestamp'] = timestamp
                
                existing_alerts.extend(alerts)
                
                # Keep only last 100 alerts
                existing_alerts = existing_alerts[-100:]
                cache.set(self.alert_cache_key, existing_alerts, 86400)
                
                logger.warning("System alerts generated", alert_count=len(alerts))
            
            return alerts
            
        except Exception as e:
            logger.error("Failed to check alerts", error=str(e))
            return []
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        try:
            alerts = cache.get(self.alert_cache_key, [])
            
            # Filter alerts from last hour
            cutoff_time = timezone.now() - timedelta(hours=1)
            active_alerts = [
                alert for alert in alerts
                if datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            return active_alerts
            
        except Exception as e:
            logger.error("Failed to get active alerts", error=str(e))
            return []


# Global instances
performance_tracker = PerformanceTracker()
alert_manager = AlertManager()