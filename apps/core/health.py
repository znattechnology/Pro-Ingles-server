"""
Health Check Views for Tuwi-Backend
Endpoints para monitoramento e verificação de saúde da aplicação
"""

import os
import time
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from django.core.mail import mail_admins
import logging

logger = logging.getLogger(__name__)

@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint para Kubernetes e load balancers
    Retorna 200 se a aplicação está funcionando
    """
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": getattr(settings, 'VERSION', '1.0.0'),
        "environment": os.environ.get('ENVIRONMENT', 'unknown'),
        "checks": {}
    }
    
    # 1. Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "type": "postgresql",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # 2. Cache Check (se configurado)
    if hasattr(settings, 'CACHES') and 'default' in settings.CACHES:
        try:
            cache_start = time.time()
            cache.set('health_check', 'ok', 30)
            result = cache.get('health_check')
            if result == 'ok':
                health_status["checks"]["cache"] = {
                    "status": "healthy",
                    "latency_ms": round((time.time() - cache_start) * 1000, 2)
                }
            else:
                health_status["checks"]["cache"] = {
                    "status": "unhealthy",
                    "error": "Cache read/write failed"
                }
        except Exception as e:
            health_status["checks"]["cache"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
    
    # 3. Disk Space Check
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        
        health_status["checks"]["disk"] = {
            "status": "healthy" if free_percent > 10 else "warning",
            "free_percent": round(free_percent, 2),
            "free_gb": round(free / (1024**3), 2)
        }
        
        if free_percent < 5:
            health_status["status"] = "unhealthy"
            
    except Exception as e:
        health_status["checks"]["disk"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # 4. Memory Check
    try:
        import psutil
        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "usage_percent": memory.percent,
            "available_gb": round(memory.available / (1024**3), 2)
        }
        
        if memory.percent > 95:
            health_status["status"] = "unhealthy"
            
    except ImportError:
        # psutil não está instalado
        health_status["checks"]["memory"] = {
            "status": "unknown",
            "note": "psutil not available"
        }
    except Exception as e:
        health_status["checks"]["memory"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # Response time total
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Determinar status code HTTP
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JsonResponse(health_status, status=status_code)


@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check para Kubernetes
    Verifica se a aplicação está pronta para receber tráfego
    """
    checks = {}
    is_ready = True
    
    # 1. Database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migration_count = cursor.fetchone()[0]
            checks["database"] = {
                "ready": True,
                "migrations_applied": migration_count
            }
    except Exception as e:
        is_ready = False
        checks["database"] = {
            "ready": False,
            "error": str(e)
        }
    
    # 2. Essential models check
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Verificar se consegue fazer uma query básica
        User.objects.exists()
        checks["models"] = {"ready": True}
        
    except Exception as e:
        is_ready = False
        checks["models"] = {
            "ready": False,
            "error": str(e)
        }
    
    # 3. Settings check
    try:
        essential_settings = [
            'SECRET_KEY',
            'DATABASE_URL' if 'DATABASE_URL' in os.environ else 'DATABASES',
        ]
        
        for setting in essential_settings:
            if setting in os.environ:
                continue
            if not hasattr(settings, setting):
                raise Exception(f"Missing essential setting: {setting}")
        
        checks["settings"] = {"ready": True}
        
    except Exception as e:
        is_ready = False
        checks["settings"] = {
            "ready": False,
            "error": str(e)
        }
    
    response_data = {
        "ready": is_ready,
        "checks": checks,
        "timestamp": time.time()
    }
    
    status_code = 200 if is_ready else 503
    return JsonResponse(response_data, status=status_code)


@never_cache
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check para Kubernetes
    Verifica se a aplicação está "viva" (não travada)
    """
    # Check básico - se chegou até aqui, está vivo
    return JsonResponse({
        "alive": True,
        "timestamp": time.time(),
        "pid": os.getpid()
    })


@never_cache
@require_http_methods(["GET"])
def metrics(request):
    """
    Métricas básicas para Prometheus (se necessário)
    """
    metrics_data = {
        "django_info": {
            "version": getattr(settings, 'VERSION', '1.0.0'),
            "environment": os.environ.get('ENVIRONMENT', 'unknown'),
            "debug": settings.DEBUG
        }
    }
    
    # Database metrics
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_connections,
                    SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            row = cursor.fetchone()
            metrics_data["database"] = {
                "total_connections": row[0],
                "active_connections": row[1]
            }
    except Exception as e:
        metrics_data["database"] = {"error": str(e)}
    
    # Application metrics
    try:
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course
        
        User = get_user_model()
        
        metrics_data["application"] = {
            "total_users": User.objects.count(),
            "total_courses": Course.objects.count(),
            "active_users_24h": User.objects.filter(
                last_login__gte=time.time() - 86400
            ).count() if hasattr(User, 'last_login') else 0
        }
    except Exception as e:
        metrics_data["application"] = {"error": str(e)}
    
    return JsonResponse(metrics_data)


@never_cache
@require_http_methods(["GET"])
def debug_info(request):
    """
    Informações de debug (apenas para ambientes não-produção)
    """
    if not settings.DEBUG and os.environ.get('ENVIRONMENT') == 'production':
        return JsonResponse({"error": "Debug info not available in production"}, status=403)
    
    debug_data = {
        "django": {
            "version": getattr(settings, 'VERSION', '1.0.0'),
            "debug": settings.DEBUG,
            "allowed_hosts": settings.ALLOWED_HOSTS,
            "installed_apps": settings.INSTALLED_APPS,
            "time_zone": settings.TIME_ZONE,
            "language_code": settings.LANGUAGE_CODE
        },
        "environment": dict(os.environ),
        "database": {},
        "system": {
            "python_version": os.sys.version,
            "platform": os.sys.platform
        }
    }
    
    # Database connection info
    try:
        db_settings = settings.DATABASES['default']
        debug_data["database"] = {
            "engine": db_settings.get('ENGINE'),
            "name": db_settings.get('NAME'),
            "host": db_settings.get('HOST'),
            "port": db_settings.get('PORT'),
        }
        
        # Remove senha por segurança
        if 'PASSWORD' in debug_data["database"]:
            debug_data["database"]['PASSWORD'] = '[HIDDEN]'
            
    except Exception as e:
        debug_data["database"] = {"error": str(e)}
    
    # Sanitizar informações sensíveis do environment
    sensitive_keys = ['SECRET_KEY', 'DATABASE_URL', 'PASSWORD', 'TOKEN', 'KEY']
    for key in debug_data["environment"]:
        if any(sensitive in key.upper() for sensitive in sensitive_keys):
            debug_data["environment"][key] = '[HIDDEN]'
    
    return JsonResponse(debug_data)