#!/usr/bin/env python3
"""
Verificação rápida da migração para PostgreSQL
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def verify_postgresql_data():
    """Verificar dados no PostgreSQL"""
    
    from django.db import connection
    from django.contrib.auth import get_user_model
    from django.core.management.color import make_style
    
    style = make_style()
    
    print(style.SUCCESS("🔍 VERIFICAÇÃO DETALHADA DO POSTGRESQL"))
    print("=" * 50)
    
    try:
        # Get user model
        User = get_user_model()
        
        # Basic counts
        print(f"\n{style.HTTP_INFO('📊 CONTAGEM GERAL:')}")
        user_count = User.objects.count()
        print(f"   👥 Usuários Django: {user_count}")
        
        # Database connection info
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   🐘 PostgreSQL: {version.split()[0]} {version.split()[1]}")
            
            # Count tables
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            print(f"   📊 Total de tabelas: {table_count}")
            
            # Check migrations
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migrations = cursor.fetchone()[0]
            print(f"   📝 Migrações aplicadas: {migrations}")
            
            # Check specific application tables
            app_tables = [
                'users_user', 'courses_course', 'practice_practicechallenge', 
                'cms_serviceitem', 'subscriptions_subscriptionplan'
            ]
            
            print(f"\n{style.HTTP_INFO('📋 TABELAS PRINCIPAIS:')}")
            total_app_data = 0
            
            for table in app_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cursor.fetchone()[0]
                    print(f"   • {table}: {count} registros")
                    total_app_data += count
                except Exception as e:
                    print(f"   • {table}: ❌ Erro - {e}")
            
            print(f"\n   💾 Total dados aplicação: {total_app_data}")
            
            # Check Django system tables for comparison
            system_tables = ['django_migrations', 'django_content_type', 'auth_permission']
            print(f"\n{style.HTTP_INFO('🔧 TABELAS DO SISTEMA:')}")
            
            for table in system_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cursor.fetchone()[0]
                    print(f"   • {table}: {count} registros")
                except Exception as e:
                    print(f"   • {table}: ❌ Erro - {e}")
        
        # Try to import and test models
        print(f"\n{style.HTTP_INFO('🧪 TESTE DE MODELOS:')}")
        
        try:
            from apps.courses.models import Course
            course_count = Course.objects.count()
            print(f"   📚 Cursos (via modelo): {course_count}")
        except Exception as e:
            print(f"   📚 Cursos: ❌ {e}")
        
        try:
            from apps.cms.models import ServiceItem
            service_count = ServiceItem.objects.count()
            print(f"   🌐 Serviços CMS: {service_count}")
        except Exception as e:
            print(f"   🌐 Serviços CMS: ❌ {e}")
        
        # Final assessment
        print(f"\n{style.HTTP_INFO('📋 RESULTADO DA VERIFICAÇÃO:')}")
        
        if total_app_data > 0:
            print(style.SUCCESS(f"   ✅ Migração bem-sucedida: {total_app_data} registros encontrados"))
            return True
        else:
            print(style.WARNING("   ⚠️ Dados da aplicação não encontrados"))
            print("   🔍 Schema criado mas dados não migraram")
            return False
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro na verificação: {str(e)}"))
        return False

if __name__ == "__main__":
    verify_postgresql_data()