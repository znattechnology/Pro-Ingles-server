"""
Core background tasks for Tuwi Beauty Platform.
"""

import os
import logging
import datetime
from datetime import timedelta
from django.core.management import call_command
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from celery import shared_task
from celery.utils.log import get_task_logger

from .cache import warm_up_cache, get_cache_stats

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_tokens(self):
    """Clean up expired JWT tokens and sessions."""
    try:
        logger.info("Starting cleanup of expired tokens")
        
        # Clean up expired sessions
        call_command('clearsessions')
        
        # Clear expired cache keys (if supported by backend)
        from django.core.cache import cache
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('*:expired:*')
        
        logger.info("Successfully cleaned up expired tokens")
        return {"status": "success", "message": "Expired tokens cleaned up"}
        
    except Exception as exc:
        logger.error(f"Error cleaning up expired tokens: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=3)
def cleanup_old_logs(self):
    """Clean up old log files."""
    try:
        logger.info("Starting cleanup of old logs")
        
        log_dir = settings.BASE_DIR / 'logs'
        if not log_dir.exists():
            return {"status": "success", "message": "No log directory found"}
        
        # Delete logs older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        cleaned_files = 0
        
        for log_file in log_dir.glob('*.log*'):
            try:
                if log_file.is_file():
                    file_time = datetime.datetime.fromtimestamp(
                        log_file.stat().st_mtime,
                        tz=timezone.get_current_timezone()
                    )
                    if file_time < cutoff_date:
                        log_file.unlink()
                        cleaned_files += 1
            except Exception as e:
                logger.warning(f"Could not delete log file {log_file}: {str(e)}")
        
        logger.info(f"Successfully cleaned up {cleaned_files} old log files")
        return {
            "status": "success", 
            "message": f"Cleaned up {cleaned_files} old log files"
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old logs: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=2)
def backup_database(self):
    """Create database backup."""
    try:
        logger.info("Starting database backup")
        
        # Create backup directory if it doesn't exist
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"tuwi_backup_{timestamp}.sql"
        backup_path = backup_dir / backup_filename
        
        # Perform backup based on database type
        db_config = settings.DATABASES['default']
        
        if db_config['ENGINE'] == 'django.db.backends.sqlite3':
            # SQLite backup
            import shutil
            db_path = db_config['NAME']
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_dir / f"tuwi_backup_{timestamp}.sqlite3")
                backup_size = os.path.getsize(backup_dir / f"tuwi_backup_{timestamp}.sqlite3")
            else:
                raise FileNotFoundError(f"Database file not found: {db_path}")
        
        elif db_config['ENGINE'] == 'django.db.backends.postgresql':
            # PostgreSQL backup using pg_dump
            import subprocess
            
            dump_cmd = [
                'pg_dump',
                '-h', db_config.get('HOST', 'localhost'),
                '-p', str(db_config.get('PORT', 5432)),
                '-U', db_config['USER'],
                '-d', db_config['NAME'],
                '-f', str(backup_path),
                '--no-password'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['PASSWORD']
            
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            backup_size = os.path.getsize(backup_path)
        
        else:
            raise Exception(f"Unsupported database engine: {db_config['ENGINE']}")
        
        # Clean up old backups (keep last 7 days)
        cutoff_date = timezone.now() - timedelta(days=7)
        cleaned_backups = 0
        
        for backup_file in backup_dir.glob('tuwi_backup_*'):
            try:
                file_time = datetime.datetime.fromtimestamp(
                    backup_file.stat().st_mtime,
                    tz=timezone.get_current_timezone()
                )
                if file_time < cutoff_date:
                    backup_file.unlink()
                    cleaned_backups += 1
            except Exception as e:
                logger.warning(f"Could not delete backup file {backup_file}: {str(e)}")
        
        logger.info(f"Database backup completed: {backup_filename} ({backup_size} bytes)")
        logger.info(f"Cleaned up {cleaned_backups} old backup files")
        
        return {
            "status": "success",
            "backup_file": backup_filename,
            "backup_size": backup_size,
            "cleaned_backups": cleaned_backups
        }
        
    except Exception as exc:
        logger.error(f"Database backup failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=exc)  # Retry after 5 minutes
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True)
def warm_up_cache_task(self):
    """Warm up application cache."""
    try:
        logger.info("Starting cache warm-up")
        
        # Use the cache warm-up function
        warm_up_cache()
        
        # Get cache statistics
        stats = get_cache_stats()
        
        logger.info("Cache warm-up completed successfully")
        return {
            "status": "success",
            "message": "Cache warmed up successfully",
            "stats": stats
        }
        
    except Exception as exc:
        logger.error(f"Cache warm-up failed: {str(exc)}")
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=3)
def optimize_database(self):
    """Optimize database performance."""
    try:
        logger.info("Starting database optimization")
        
        db_config = settings.DATABASES['default']
        optimizations_performed = []
        
        if db_config['ENGINE'] == 'django.db.backends.postgresql':
            # PostgreSQL optimizations
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Analyze tables for better query planning
                cursor.execute("ANALYZE;")
                optimizations_performed.append("ANALYZE")
                
                # Update table statistics
                cursor.execute("VACUUM ANALYZE;")
                optimizations_performed.append("VACUUM ANALYZE")
        
        elif db_config['ENGINE'] == 'django.db.backends.sqlite3':
            # SQLite optimizations
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Analyze database
                cursor.execute("ANALYZE;")
                optimizations_performed.append("ANALYZE")
                
                # Vacuum database
                cursor.execute("VACUUM;")
                optimizations_performed.append("VACUUM")
        
        logger.info(f"Database optimization completed: {optimizations_performed}")
        return {
            "status": "success",
            "optimizations": optimizations_performed
        }
        
    except Exception as exc:
        logger.error(f"Database optimization failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=exc)
        return {"status": "error", "message": str(exc)}


@shared_task(bind=True, max_retries=3)
def health_check(self):
    """Perform system health check."""
    try:
        logger.info("Starting system health check")
        
        health_status = {
            "database": "unknown",
            "cache": "unknown",
            "celery": "unknown",
            "disk_space": "unknown",
            "memory": "unknown"
        }
        
        # Check database connection
        try:
            from django.db import connection
            connection.ensure_connection()
            health_status["database"] = "healthy"
        except Exception as e:
            health_status["database"] = f"unhealthy: {str(e)}"
        
        # Check cache connection
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 60)
            if cache.get('health_check') == 'ok':
                health_status["cache"] = "healthy"
            else:
                health_status["cache"] = "unhealthy: cache set/get failed"
        except Exception as e:
            health_status["cache"] = f"unhealthy: {str(e)}"
        
        # Check Celery worker
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            if active_workers:
                health_status["celery"] = "healthy"
            else:
                health_status["celery"] = "unhealthy: no active workers"
        except Exception as e:
            health_status["celery"] = f"unhealthy: {str(e)}"
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            free_percent = (free / total) * 100
            if free_percent > 20:
                health_status["disk_space"] = f"healthy: {free_percent:.1f}% free"
            else:
                health_status["disk_space"] = f"warning: {free_percent:.1f}% free"
        except Exception as e:
            health_status["disk_space"] = f"unknown: {str(e)}"
        
        # Check memory usage
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent < 80:
                health_status["memory"] = f"healthy: {memory.percent:.1f}% used"
            else:
                health_status["memory"] = f"warning: {memory.percent:.1f}% used"
        except ImportError:
            health_status["memory"] = "unknown: psutil not installed"
        except Exception as e:
            health_status["memory"] = f"unknown: {str(e)}"
        
        # Determine overall health
        unhealthy_components = [
            k for k, v in health_status.items() 
            if v.startswith('unhealthy')
        ]
        
        if unhealthy_components:
            overall_status = "unhealthy"
            logger.warning(f"Health check found issues: {unhealthy_components}")
        else:
            overall_status = "healthy"
            logger.info("System health check passed")
        
        return {
            "status": overall_status,
            "components": health_status,
            "timestamp": timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Health check failed: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        return {
            "status": "error", 
            "message": str(exc),
            "timestamp": timezone.now().isoformat()
        }


@shared_task
def send_admin_notification(message, level="info"):
    """Send notification to administrators."""
    try:
        from apps.notifications.models import Notification
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title="System Notification",
                message=message,
                notification_type="system",
                priority="high" if level == "error" else "medium"
            )
        
        logger.info(f"Admin notification sent: {message}")
        return {"status": "success", "recipients": len(admin_users)}
        
    except Exception as exc:
        logger.error(f"Failed to send admin notification: {str(exc)}")
        return {"status": "error", "message": str(exc)}