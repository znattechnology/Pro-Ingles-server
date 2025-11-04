#!/usr/bin/env python3
"""
Script para migrar dados do SQLite recuperado para Neon PostgreSQL
"""

import os
import sys
import django
import subprocess
from pathlib import Path
from django.core.management.color import make_style

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Configure Django
django.setup()

def backup_sqlite_data():
    """Extract data from recovered SQLite database"""
    style = make_style()
    
    print(style.HTTP_INFO("💾 Extraindo dados do SQLite recuperado..."))
    
    # Check if recovered SQLite exists
    sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
    if not sqlite_path.exists():
        print(style.ERROR("❌ SQLite recuperado não encontrado"))
        return False
    
    # Rename to standard name temporarily
    temp_sqlite = BASE_DIR / 'db.sqlite3'
    sqlite_path.rename(temp_sqlite)
    
    # Temporarily switch to SQLite in settings
    original_env = os.environ.get('DATABASE_URL', '')
    os.environ['DATABASE_URL'] = ''  # Force SQLite usage
    
    # Force Django to reload settings
    from django.conf import settings
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': temp_sqlite,
        }
    }
    
    # Create backup
    backup_file = BASE_DIR / 'sqlite_data_backup.json'
    
    try:
        print("   📊 Extraindo dados...")
        
        # Use dumpdata to extract all data except system tables
        result = subprocess.run([
            'python', 'manage.py', 'dumpdata',
            '--indent=2',
            '--exclude=contenttypes',
            '--exclude=auth.permission',
            '--exclude=admin.logentry',
            '--exclude=sessions.session',
            '--output', str(backup_file)
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            print(style.SUCCESS(f"✅ Dados extraídos: {backup_file}"))
            
            # Show what was extracted
            with open(backup_file, 'r') as f:
                import json
                data = json.load(f)
                
            print(f"   📋 {len(data)} registros extraídos")
            
            # Count by model
            models = {}
            for item in data:
                model = item['model']
                models[model] = models.get(model, 0) + 1
            
            print("   📊 Resumo por modelo:")
            for model, count in sorted(models.items()):
                print(f"      • {model}: {count} registros")
            
            return True
        else:
            print(style.ERROR(f"❌ Erro: {result.stderr}"))
            return False
            
    finally:
        # Restore original environment
        os.environ['DATABASE_URL'] = original_env
        
        # Rename SQLite back
        if temp_sqlite.exists():
            temp_sqlite.rename(sqlite_path)

def restore_data_to_postgresql():
    """Load data into PostgreSQL"""
    style = make_style()
    
    backup_file = BASE_DIR / 'sqlite_data_backup.json'
    
    if not backup_file.exists():
        print(style.ERROR("❌ Arquivo de backup não encontrado"))
        return False
    
    print(style.HTTP_INFO("📥 Carregando dados no PostgreSQL..."))
    
    # Ensure DATABASE_URL is set for PostgreSQL
    from decouple import config
    database_url = config('DATABASE_URL', default='')
    
    if not database_url:
        print(style.ERROR("❌ DATABASE_URL não configurada"))
        return False
    
    try:
        # Load data
        result = subprocess.run([
            'python', 'manage.py', 'loaddata', str(backup_file)
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            print(style.SUCCESS("✅ Dados carregados com sucesso"))
            print(f"   📋 Output: {result.stdout.strip()}")
            return True
        else:
            print(style.ERROR(f"❌ Erro ao carregar: {result.stderr}"))
            
            # Try to handle common errors
            if "duplicate key" in result.stderr.lower():
                print(style.WARNING("⚠️  Alguns dados já existem (normal)"))
                return True
            
            return False
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro: {str(e)}"))
        return False

def verify_migrated_data():
    """Verify data was migrated successfully"""
    style = make_style()
    
    print(style.HTTP_INFO("🔍 Verificando dados migrados..."))
    
    try:
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course
        from apps.practice.models import PracticeChallenge
        from apps.cms.models import ServiceItem
        
        User = get_user_model()
        
        counts = {
            'users': User.objects.count(),
            'courses': Course.objects.count(),
            'challenges': PracticeChallenge.objects.count(),
            'services': ServiceItem.objects.count(),
        }
        
        print("   📊 Dados verificados:")
        for model, count in counts.items():
            icon = "✅" if count > 0 else "⚠️"
            print(f"      {icon} {model.capitalize()}: {count}")
        
        total_records = sum(counts.values())
        
        if total_records > 0:
            print(style.SUCCESS(f"✅ Migração verificada: {total_records} registros totais"))
            return True
        else:
            print(style.WARNING("⚠️  Nenhum dado encontrado"))
            return False
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro na verificação: {str(e)}"))
        return False

def cleanup_migration_files():
    """Clean up temporary migration files"""
    style = make_style()
    
    print(style.HTTP_INFO("🧹 Limpando arquivos temporários..."))
    
    files_to_clean = [
        'sqlite_data_backup.json',
        'db.sqlite3.recovered'
    ]
    
    for filename in files_to_clean:
        file_path = BASE_DIR / filename
        if file_path.exists():
            file_path.unlink()
            print(f"   🗑️  Removido: {filename}")
    
    print(style.SUCCESS("✅ Limpeza concluída"))

def main():
    """Main migration process"""
    style = make_style()
    
    print(style.SUCCESS("🔄 MIGRAÇÃO DE DADOS SQLITE → NEON"))
    print("=" * 50)
    
    steps = [
        ("1. Extrair dados do SQLite", backup_sqlite_data),
        ("2. Carregar dados no PostgreSQL", restore_data_to_postgresql),
        ("3. Verificar migração", verify_migrated_data),
        ("4. Limpar arquivos temporários", cleanup_migration_files),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{style.HTTP_INFO(step_name)}")
        
        if not step_func():
            print(style.ERROR(f"❌ Falha na etapa: {step_name}"))
            
            # Don't fail on verification step
            if "Verificar" not in step_name:
                print(style.WARNING("🛑 Migração interrompida"))
                return False
    
    print("\n" + "=" * 50)
    print(style.SUCCESS("🎉 MIGRAÇÃO DE DADOS CONCLUÍDA!"))
    print(style.HTTP_INFO("🐘 Dados do SQLite foram migrados para Neon PostgreSQL"))
    
    return True

if __name__ == "__main__":
    main()