#!/usr/bin/env python3
"""
Script para configurar Neon PostgreSQL com migrações do zero
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
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"   ✅ {line}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        if e.stderr:
            print(style.ERROR(f"   ❌ Erro: {e.stderr.strip()}"))
        if e.stdout:
            print(f"   ℹ️  Output: {e.stdout.strip()}")
        return False

def setup_fresh_database():
    """Setup fresh PostgreSQL database"""
    style = make_style()
    
    print(style.HTTP_INFO("🐘 Configurando base de dados PostgreSQL..."))
    
    # Apply migrations
    if not run_command("python manage.py makemigrations", "Criando migrações"):
        return False
    
    if not run_command("python manage.py migrate", "Aplicando migrações"):
        return False
    
    print(style.SUCCESS("✅ Base de dados PostgreSQL configurada"))
    return True

def create_superuser():
    """Create superuser interactively"""
    style = make_style()
    
    print(style.HTTP_INFO("👤 Criando superusuário..."))
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if User.objects.filter(is_superuser=True).exists():
        print(style.WARNING("⚠️  Superusuário já existe"))
        return True
    
    print("   📝 Crie um superusuário para acessar o admin:")
    
    try:
        result = subprocess.run(
            "python manage.py createsuperuser", 
            shell=True, 
            cwd=BASE_DIR
        )
        
        if result.returncode == 0:
            print(style.SUCCESS("✅ Superusuário criado"))
            return True
        else:
            print(style.WARNING("⚠️  Criação de superusuário cancelada"))
            return True  # Not critical
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro: {str(e)}"))
        return True  # Not critical

def verify_setup():
    """Verify database setup"""
    style = make_style()
    
    print(style.HTTP_INFO("🔍 Verificando configuração..."))
    
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
        
        print(f"   📊 PostgreSQL: {version.split(',')[0]}")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"   📋 Tabelas criadas: {len(tables)}")
        
        for table in tables[:5]:  # Show first 5 tables
            print(f"      • {table[0]}")
        
        if len(tables) > 5:
            print(f"      • ... e mais {len(tables) - 5} tabelas")
        
        print(style.SUCCESS("✅ Configuração verificada"))
        return True
        
    except Exception as e:
        print(style.ERROR(f"❌ Erro na verificação: {str(e)}"))
        return False

def update_gitignore():
    """Update .gitignore to exclude SQLite files"""
    style = make_style()
    
    print(style.HTTP_INFO("📝 Atualizando .gitignore..."))
    
    gitignore_path = BASE_DIR / '.gitignore'
    
    entries_to_add = [
        '# Database files',
        'db.sqlite3',
        'db.sqlite3.*',
        '*.sqlite3',
        '',
        '# Environment files',
        '.env',
        '.env.local',
        '.env.production',
        '',
        '# Backup files',
        '*.backup',
        'sqlite_backup.json',
    ]
    
    try:
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        new_entries = []
        for entry in entries_to_add:
            if entry and entry not in content:
                new_entries.append(entry)
        
        if new_entries:
            with open(gitignore_path, 'a') as f:
                f.write('\n' + '\n'.join(new_entries) + '\n')
            
            print(f"   ✅ Adicionados {len([e for e in new_entries if e])} novos entries")
        else:
            print("   ℹ️  .gitignore já está atualizado")
        
        return True
        
    except Exception as e:
        print(style.ERROR(f"❌ Erro: {str(e)}"))
        return False

def main():
    """Main setup process"""
    style = make_style()
    
    print(style.SUCCESS("🚀 CONFIGURAÇÃO NEON POSTGRESQL"))
    print("=" * 40)
    
    steps = [
        ("1. Configuração da base de dados", setup_fresh_database),
        ("2. Verificação do setup", verify_setup),
        ("3. Atualização do .gitignore", update_gitignore),
        ("4. Criação de superusuário", create_superuser),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{style.HTTP_INFO(step_name)}")
        
        if not step_func():
            print(style.ERROR(f"❌ Falha na etapa: {step_name}"))
            return False
    
    print("\n" + "=" * 40)
    print(style.SUCCESS("🎉 CONFIGURAÇÃO CONCLUÍDA!"))
    print(style.HTTP_INFO("🐘 Neon PostgreSQL está pronto para uso"))
    print()
    print(style.WARNING("📋 Próximos passos:"))
    print("   1. Teste a aplicação: python manage.py runserver")
    print("   2. Acesse o admin: http://localhost:8000/admin/")
    print("   3. Configure os dados iniciais conforme necessário")
    
    return True

if __name__ == "__main__":
    main()