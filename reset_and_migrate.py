#!/usr/bin/env python3
"""
Script para reset completo da base de dados e migração limpa
"""

import os
import sys
import django
import subprocess
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def reset_database():
    """Reset database completely"""
    
    print("🗑️ Resetando base de dados PostgreSQL...")
    
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            # Get all table names
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"   📋 Removendo {len(tables)} tabelas...")
                
                # Drop all tables
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                    print(f"      🗑️ {table}")
                
                print("✅ Base de dados limpa")
            else:
                print("   ℹ️ Base de dados já está vazia")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def apply_migrations():
    """Apply all migrations from scratch"""
    
    print("\n🔄 Aplicando migrações...")
    
    try:
        # Run migrations
        result = subprocess.run([
            'python', 'manage.py', 'migrate'
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            print("✅ Migrações aplicadas com sucesso")
            return True
        else:
            print(f"❌ Erro nas migrações: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def load_data():
    """Load the filtered data"""
    
    print("\n📥 Carregando dados...")
    
    filtered_file = BASE_DIR / 'filtered_data.json'
    
    if not filtered_file.exists():
        print("❌ filtered_data.json não encontrado")
        return False
    
    try:
        result = subprocess.run([
            'python', 'manage.py', 'loaddata', str(filtered_file)
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            print("✅ Dados carregados com sucesso")
            if result.stdout.strip():
                print(f"   📋 {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Erro ao carregar: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def verify_data():
    """Final verification"""
    
    print("\n🔍 Verificação final...")
    
    try:
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course
        from apps.practice.models import PracticeChallenge
        from apps.cms.models import ServiceItem
        
        User = get_user_model()
        
        counts = {
            'Usuários': User.objects.count(),
            'Cursos': Course.objects.count(),
            'Desafios': PracticeChallenge.objects.count(),
            'Serviços CMS': ServiceItem.objects.count(),
        }
        
        print("   📊 Dados importados:")
        total = 0
        for name, count in counts.items():
            icon = "✅" if count > 0 else "⚪"
            print(f"      {icon} {name}: {count}")
            total += count
        
        print(f"\n   🎯 Total: {total} registros")
        
        return total > 0
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def main():
    """Main process"""
    
    print("🔄 RESET E MIGRAÇÃO COMPLETA")
    print("=" * 35)
    
    steps = [
        ("Reset da base de dados", reset_database),
        ("Aplicar migrações", apply_migrations),
        ("Carregar dados", load_data),
        ("Verificar resultado", verify_data),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📝 {step_name}...")
        
        if not step_func():
            print(f"❌ Falha em: {step_name}")
            return False
    
    print("\n" + "=" * 35)
    print("🎉 MIGRAÇÃO COMPLETA REALIZADA!")
    print("🐘 Base de dados Neon pronta com dados do SQLite")
    
    return True

if __name__ == "__main__":
    main()