#!/usr/bin/env python3
"""
Script para migrar dados do SQLite para Neon PostgreSQL
Preserva todos os dados e aplica migrações
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

def run_command(command, description=""):
    """Execute shell command and handle errors"""
    style = make_style()
    
    if description:
        print(style.HTTP_INFO(f"🔄 {description}"))
    
    print(f"   Executando: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=BASE_DIR
        )
        
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(style.ERROR(f"   ❌ Erro: {e.stderr.strip()}"))
        return False

def backup_sqlite_data():
    """Create backup of SQLite data"""
    style = make_style()
    
    print(style.HTTP_INFO("💾 Criando backup dos dados SQLite..."))
    
    # Check if SQLite database exists
    sqlite_path = BASE_DIR / 'db.sqlite3'
    if not sqlite_path.exists():
        print(style.WARNING("⚠️  Base de dados SQLite não encontrada"))
        return False
    
    # Create backup using Django's dumpdata
    backup_file = BASE_DIR / 'sqlite_backup.json'
    
    command = f"python manage.py dumpdata --indent=2 --exclude=contenttypes --exclude=auth.permission > {backup_file}"
    
    if run_command(command, "Exportando dados do SQLite"):
        print(style.SUCCESS(f"✅ Backup criado: {backup_file}"))
        return True
    
    return False

def setup_postgresql_database():
    """Setup PostgreSQL database with migrations"""
    style = make_style()
    
    print(style.HTTP_INFO("🐘 Configurando base de dados PostgreSQL..."))
    
    # Apply migrations
    if not run_command("python manage.py makemigrations", "Criando migrações"):
        return False
    
    if not run_command("python manage.py migrate", "Aplicando migrações"):
        return False
    
    print(style.SUCCESS("✅ Base de dados PostgreSQL configurada"))
    return True

def restore_data_to_postgresql():
    """Restore data from SQLite backup to PostgreSQL"""
    style = make_style()
    
    backup_file = BASE_DIR / 'sqlite_backup.json'
    
    if not backup_file.exists():
        print(style.WARNING("⚠️  Arquivo de backup não encontrado"))
        return False
    
    print(style.HTTP_INFO("📥 Restaurando dados no PostgreSQL..."))
    
    # Load data into PostgreSQL
    if run_command(f"python manage.py loaddata {backup_file}", "Carregando dados"):
        print(style.SUCCESS("✅ Dados restaurados com sucesso"))
        return True
    
    return False

def verify_migration():
    """Verify that migration was successful"""
    style = make_style()
    
    print(style.HTTP_INFO("🔍 Verificando migração..."))
    
    from django.contrib.auth import get_user_model
    from apps.courses.models import Course
    from apps.practice.models import PracticeChallenge
    
    User = get_user_model()
    
    try:
        user_count = User.objects.count()
        course_count = Course.objects.count()
        challenge_count = PracticeChallenge.objects.count()
        
        print(f"   👥 Usuários: {user_count}")
        print(f"   📚 Cursos: {course_count}")
        print(f"   🎯 Desafios: {challenge_count}")
        
        if user_count > 0 or course_count > 0 or challenge_count > 0:
            print(style.SUCCESS("✅ Migração verificada com sucesso!"))
            return True
        else:
            print(style.WARNING("⚠️  Nenhum dado encontrado"))
            return False
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro na verificação: {str(e)}"))
        return False

def cleanup_files():
    """Clean up temporary files"""
    style = make_style()
    
    print(style.HTTP_INFO("🧹 Limpando arquivos temporários..."))
    
    backup_file = BASE_DIR / 'sqlite_backup.json'
    if backup_file.exists():
        backup_file.unlink()
        print("   🗑️  Removido: sqlite_backup.json")
    
    # Move SQLite to backup location
    sqlite_path = BASE_DIR / 'db.sqlite3'
    if sqlite_path.exists():
        backup_sqlite = BASE_DIR / 'db.sqlite3.backup'
        sqlite_path.rename(backup_sqlite)
        print(f"   📦 SQLite movido para: {backup_sqlite}")
    
    print(style.SUCCESS("✅ Limpeza concluída"))

def main():
    """Main migration process"""
    style = make_style()
    
    print(style.SUCCESS("🚀 MIGRAÇÃO SQLITE → NEON POSTGRESQL"))
    print("=" * 50)
    
    steps = [
        ("1. Backup dos dados SQLite", backup_sqlite_data),
        ("2. Configuração PostgreSQL", setup_postgresql_database),
        ("3. Restauração dos dados", restore_data_to_postgresql),
        ("4. Verificação da migração", verify_migration),
        ("5. Limpeza de arquivos", cleanup_files),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{style.HTTP_INFO(step_name)}")
        
        if not step_func():
            print(style.ERROR(f"❌ Falha na etapa: {step_name}"))
            print(style.WARNING("🛑 Migração interrompida"))
            return False
    
    print("\n" + "=" * 50)
    print(style.SUCCESS("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!"))
    print(style.HTTP_INFO("🐘 Sua aplicação agora está usando Neon PostgreSQL"))
    print(style.WARNING("💡 Lembre-se de adicionar db.sqlite3* ao .gitignore"))
    
    return True

if __name__ == "__main__":
    main()