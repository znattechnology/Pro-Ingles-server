#!/usr/bin/env python3
"""
Importação manual de dados com melhor tratamento de erros
"""

import os
import sys
import django
import json
import subprocess
from pathlib import Path
from django.core.management.color import make_style

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def disable_foreign_key_checks():
    """Desabilitar verificações de FK temporariamente"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # PostgreSQL doesn't have a global FK disable, but we can defer constraints
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
    
    print("   🔓 Constraints deferidas temporariamente")

def enable_foreign_key_checks():
    """Reabilitar verificações de FK"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
    
    print("   🔒 Constraints reabilitadas")

def import_data_by_model():
    """Importar dados modelo por modelo com melhor tratamento de erros"""
    
    style = make_style()
    
    print(style.SUCCESS("📥 IMPORTAÇÃO MANUAL DE DADOS"))
    print("=" * 40)
    
    data_file = BASE_DIR / 'migration_backup' / 'data_export.json'
    
    if not data_file.exists():
        print(style.ERROR("❌ Arquivo de dados não encontrado"))
        return False
    
    try:
        # Load the data
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 {len(data)} registros carregados do arquivo")
        
        # Group by model
        models_data = {}
        for item in data:
            model = item['model']
            if model not in models_data:
                models_data[model] = []
            models_data[model].append(item)
        
        print(f"🔍 {len(models_data)} modelos encontrados")
        
        # Sort models by dependency (users first, then others)
        priority_models = ['users.user', 'courses.course', 'subscriptions.subscriptionplan']
        other_models = [m for m in models_data.keys() if m not in priority_models]
        
        import_order = []
        for model in priority_models:
            if model in models_data:
                import_order.append(model)
        import_order.extend(other_models)
        
        # Disable FK checks
        disable_foreign_key_checks()
        
        success_count = 0
        error_count = 0
        
        # Import each model
        for model in import_order:
            items = models_data[model]
            print(f"\n🔄 Importando {model}: {len(items)} registros")
            
            try:
                # Create temporary file for this model
                temp_file = BASE_DIR / f"temp_{model.replace('.', '_')}.json"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(items, f, indent=2)
                
                # Try to load this model's data
                result = subprocess.run([
                    'python', 'manage.py', 'loaddata', str(temp_file)
                ], capture_output=True, text=True, cwd=BASE_DIR, timeout=60)
                
                if result.returncode == 0:
                    print(f"   ✅ {model}: {len(items)} registros importados")
                    success_count += len(items)
                else:
                    print(f"   ❌ {model}: Erro - {result.stderr}")
                    print(f"   📋 Stdout: {result.stdout}")
                    error_count += len(items)
                
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()
                
            except subprocess.TimeoutExpired:
                print(f"   ⏰ {model}: Timeout na importação")
                error_count += len(items)
            except Exception as e:
                print(f"   ❌ {model}: Erro inesperado - {str(e)}")
                error_count += len(items)
        
        # Re-enable FK checks
        enable_foreign_key_checks()
        
        print(f"\n{'='*40}")
        print(f"📊 RESULTADO DA IMPORTAÇÃO:")
        print(f"   ✅ Sucessos: {success_count}")
        print(f"   ❌ Erros: {error_count}")
        print(f"   📈 Taxa de sucesso: {(success_count/(success_count+error_count)*100):.1f}%")
        
        return success_count > 0
        
    except Exception as e:
        print(style.ERROR(f"❌ Erro crítico: {str(e)}"))
        return False

def verify_imported_data():
    """Verificar dados importados"""
    
    style = make_style()
    print(f"\n{style.HTTP_INFO('🔍 VERIFICAÇÃO FINAL:')}")
    
    from django.db import connection
    
    key_tables = ['users', 'courses', 'cms_serviceitem', 'practice_practicechallenge']
    total_records = 0
    
    for table in key_tables:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                total_records += count
                if count > 0:
                    print(f"   ✅ {table}: {count} registros")
                else:
                    print(f"   ⚪ {table}: 0 registros")
        except Exception as e:
            print(f"   ❌ {table}: Erro - {e}")
    
    if total_records > 0:
        print(style.SUCCESS(f"\n🎉 MIGRAÇÃO FINALIZADA: {total_records}+ registros"))
        return True
    else:
        print(style.WARNING("\n⚠️ Nenhum dado encontrado nas tabelas principais"))
        return False

def main():
    """Processo principal"""
    
    style = make_style()
    
    print(style.SUCCESS("🔧 IMPORTAÇÃO MANUAL COM TRATAMENTO DE ERROS"))
    print("=" * 50)
    
    # Step 1: Import data by model
    if not import_data_by_model():
        print("❌ Falha na importação")
        return False
    
    # Step 2: Verify
    if not verify_imported_data():
        print("❌ Verificação falhou")
        return False
    
    print("\n🎉 IMPORTAÇÃO MANUAL CONCLUÍDA COM SUCESSO!")
    return True

if __name__ == "__main__":
    main()