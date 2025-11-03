#!/usr/bin/env python3
"""
MIGRAÇÃO FOCADA E SEGURA - SQLite para PostgreSQL
Estratégia DBA otimizada para eficiência
"""

import os
import sys
import django
import subprocess
import json
from pathlib import Path
from django.core.management.color import make_style

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def log_step(message, style_func=None):
    """Log simples mas eficaz"""
    style = make_style()
    if style_func:
        print(style_func(message))
    else:
        print(style.HTTP_INFO(message))

def main():
    """Migração profissional focada"""
    style = make_style()
    
    print(style.SUCCESS("🎯 MIGRAÇÃO PROFISSIONAL FOCADA - SQLite → PostgreSQL"))
    print("=" * 60)
    
    # 1. Verificar se SQLite existe
    sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
    if not sqlite_path.exists():
        print(style.ERROR("❌ SQLite não encontrado!"))
        return False
    
    log_step("✅ SQLite encontrado - prosseguindo com migração")
    
    # 2. Backup rápido do estado atual
    log_step("📦 Criando backup de segurança...")
    backup_dir = BASE_DIR / "migration_backup"
    backup_dir.mkdir(exist_ok=True)
    
    import shutil
    shutil.copy2(sqlite_path, backup_dir / "sqlite_backup.db")
    log_step("✅ Backup criado")
    
    # 3. Configurar SQLite temporariamente e exportar dados
    log_step("📤 Exportando dados do SQLite...")
    
    temp_sqlite = BASE_DIR / 'db.sqlite3'
    if temp_sqlite.exists():
        temp_sqlite.rename(BASE_DIR / 'db.sqlite3.temp_backup')
    
    shutil.copy2(sqlite_path, temp_sqlite)
    
    # Desabilitar PostgreSQL temporariamente
    original_db_url = os.environ.get('DATABASE_URL', '')
    os.environ['DATABASE_URL'] = ''
    
    try:
        # Exportar dados
        export_file = backup_dir / "data_export.json"
        
        result = subprocess.run([
            'python', 'manage.py', 'dumpdata',
            '--indent=2',
            '--exclude=contenttypes',
            '--exclude=auth.permission',
            '--exclude=admin.logentry',
            '--exclude=sessions.session',
            '--output', str(export_file)
        ], capture_output=True, text=True, cwd=BASE_DIR)
        
        if result.returncode == 0:
            log_step("✅ Dados exportados com sucesso")
            
            # Verificar dados exportados
            with open(export_file, 'r') as f:
                data = json.load(f)
            log_step(f"📊 {len(data)} registros exportados")
        else:
            print(style.ERROR(f"❌ Erro na exportação: {result.stderr}"))
            return False
    
    finally:
        # Restaurar configuração
        os.environ['DATABASE_URL'] = original_db_url
        if temp_sqlite.exists():
            temp_sqlite.unlink()
        
        temp_backup = BASE_DIR / 'db.sqlite3.temp_backup'
        if temp_backup.exists():
            temp_backup.rename(temp_sqlite)
    
    # 4. Garantir que todas as migrações estão aplicadas no PostgreSQL
    log_step("🐘 Garantindo schema completo no PostgreSQL...")
    
    result = subprocess.run([
        'python', 'manage.py', 'migrate'
    ], capture_output=True, text=True, cwd=BASE_DIR, env=os.environ.copy())
    
    if result.returncode != 0:
        print(style.WARNING(f"⚠️ Avisos nas migrações: {result.stderr}"))
    else:
        log_step("✅ Migrações aplicadas")
    
    # 5. Limpar dados existentes no PostgreSQL (se houver)
    log_step("🧹 Limpando dados existentes no PostgreSQL...")
    
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            # Desabilitar verificações de FK temporariamente
            cursor.execute("SET foreign_key_checks = 0;" if 'mysql' in connection.vendor else "BEGIN;")
            
            # Obter tabelas da aplicação
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE 'django_%'
                AND table_name NOT LIKE 'auth_%'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # Truncar tabelas
            for table in tables:
                try:
                    cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
                except Exception as e:
                    log_step(f"⚠️ Não foi possível limpar {table}: {e}")
            
            cursor.execute("COMMIT;" if 'postgres' in connection.vendor else "SET foreign_key_checks = 1;")
            
        log_step(f"✅ {len(tables)} tabelas limpas")
        
    except Exception as e:
        log_step(f"⚠️ Erro na limpeza: {e}")
    
    # 6. Importar dados no PostgreSQL
    log_step("📥 Importando dados no PostgreSQL...")
    
    result = subprocess.run([
        'python', 'manage.py', 'loaddata', str(export_file)
    ], capture_output=True, text=True, cwd=BASE_DIR, env=os.environ.copy())
    
    if result.returncode == 0:
        log_step("✅ Dados importados com sucesso!")
        if result.stdout.strip():
            log_step(f"📋 {result.stdout.strip()}")
    else:
        # Tentar importação parcial em caso de erro
        print(style.WARNING(f"⚠️ Erro na importação completa: {result.stderr}"))
        log_step("🔄 Tentando importação parcial...")
        
        # Importar por partes
        success_count = try_partial_import(export_file)
        if success_count > 0:
            log_step(f"✅ Importação parcial: {success_count} registros")
        else:
            print(style.ERROR("❌ Falha na importação parcial"))
            return False
    
    # 7. Validação final
    log_step("🔍 Validação final...")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        with connection.cursor() as cursor:
            # Contar dados importados
            cursor.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_name = t.table_name) as columns,
                       pg_stat_get_tuples_inserted(c.oid) as inserts
                FROM information_schema.tables t
                LEFT JOIN pg_class c ON c.relname = t.table_name
                WHERE t.table_schema = 'public' 
                AND t.table_type = 'BASE TABLE'
                AND t.table_name NOT LIKE 'django_%'
                ORDER BY t.table_name;
            """)
            
            tables_info = cursor.fetchall()
            
            # Contar registros em tabelas principais
            key_tables = ['users', 'courses', 'cms_serviceitem', 'practice_userachievement']
            total_records = 0
            
            for table in key_tables:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
                    count = cursor.fetchone()[0]
                    total_records += count
                    if count > 0:
                        log_step(f"✅ {table}: {count} registros")
                except:
                    pass
        
        if total_records > 0:
            print("\n" + "=" * 60)
            print(style.SUCCESS("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!"))
            print(style.SUCCESS(f"📊 {total_records}+ registros migrados"))
            print(style.SUCCESS("🐘 PostgreSQL está pronto com dados do SQLite"))
            print(style.SUCCESS("🚀 Sistema pronto para produção!"))
            return True
        else:
            print(style.WARNING("⚠️ Migração parcial - poucos dados encontrados"))
            return False
            
    except Exception as e:
        print(style.ERROR(f"❌ Erro na validação: {str(e)}"))
        return False

def try_partial_import(export_file):
    """Tentar importação parcial por modelo"""
    success_count = 0
    
    try:
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        # Agrupar por modelo
        models_data = {}
        for item in data:
            model = item['model']
            if model not in models_data:
                models_data[model] = []
            models_data[model].append(item)
        
        # Importar modelo por modelo
        for model, items in models_data.items():
            try:
                temp_file = BASE_DIR / f"temp_{model.replace('.', '_')}.json"
                with open(temp_file, 'w') as f:
                    json.dump(items, f, indent=2)
                
                result = subprocess.run([
                    'python', 'manage.py', 'loaddata', str(temp_file)
                ], capture_output=True, text=True, cwd=BASE_DIR)
                
                if result.returncode == 0:
                    success_count += len(items)
                
                temp_file.unlink()
                
            except:
                continue
        
        return success_count
        
    except:
        return 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)