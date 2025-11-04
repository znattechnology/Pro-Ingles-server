#!/usr/bin/env python3
"""
Script para filtrar e carregar dados do SQLite sem conflitos
"""

import json
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def filter_json_data():
    """Filter JSON to remove potentially conflicting data"""
    
    input_file = BASE_DIR / 'sqlite_data_backup.json'
    output_file = BASE_DIR / 'filtered_data.json'
    
    if not input_file.exists():
        print("❌ sqlite_data_backup.json não encontrado")
        return False
    
    print("🔄 Filtrando dados...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter out potentially problematic models
    excluded_models = {
        'auth.permission',
        'auth.group',
        'contenttypes.contenttype',
        'admin.logentry',
        'sessions.session',
    }
    
    filtered_data = []
    excluded_count = 0
    
    for item in data:
        if item['model'] not in excluded_models:
            filtered_data.append(item)
        else:
            excluded_count += 1
    
    print(f"   📊 Dados originais: {len(data)}")
    print(f"   🚫 Excluídos: {excluded_count}")
    print(f"   ✅ Filtrados: {len(filtered_data)}")
    
    # Count by model
    models = {}
    for item in filtered_data:
        model = item['model']
        models[model] = models.get(model, 0) + 1
    
    print("\n   📋 Dados a serem importados:")
    for model, count in sorted(models.items()):
        print(f"      • {model}: {count}")
    
    # Save filtered data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Dados filtrados salvos: {output_file}")
    return True

def load_filtered_data():
    """Load filtered data into PostgreSQL"""
    
    filtered_file = BASE_DIR / 'filtered_data.json'
    
    if not filtered_file.exists():
        print("❌ filtered_data.json não encontrado")
        return False
    
    print("\n📥 Carregando dados no PostgreSQL...")
    
    # Import Django management utilities
    from django.core.management import call_command
    from io import StringIO
    
    try:
        # Capture output
        out = StringIO()
        call_command('loaddata', str(filtered_file), stdout=out)
        
        output = out.getvalue()
        print(f"✅ Dados carregados com sucesso")
        if output.strip():
            print(f"   📋 {output.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {str(e)}")
        return False

def verify_loaded_data():
    """Verify that data was loaded successfully"""
    
    print("\n🔍 Verificando dados carregados...")
    
    try:
        from django.contrib.auth import get_user_model
        from apps.courses.models import Course
        from apps.practice.models import PracticeChallenge
        from apps.cms.models import ServiceItem
        
        User = get_user_model()
        
        counts = {
            'Usuários': User.objects.count(),
            'Cursos': Course.objects.count(),
            'Desafios Practice': PracticeChallenge.objects.count(),
            'Serviços CMS': ServiceItem.objects.count(),
        }
        
        print("   📊 Resumo dos dados:")
        total = 0
        for name, count in counts.items():
            icon = "✅" if count > 0 else "⚠️"
            print(f"      {icon} {name}: {count}")
            total += count
        
        if total > 0:
            print(f"\n🎉 Total de registros importados: {total}")
            return True
        else:
            print("\n⚠️ Nenhum dado foi importado")
            return False
            
    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False

def cleanup_files():
    """Clean up temporary files"""
    
    print("\n🧹 Limpando arquivos temporários...")
    
    files_to_clean = [
        'sqlite_data_backup.json',
        'filtered_data.json',
        'db.sqlite3.recovered'
    ]
    
    for filename in files_to_clean:
        file_path = BASE_DIR / filename
        if file_path.exists():
            file_path.unlink()
            print(f"   🗑️ Removido: {filename}")
    
    print("✅ Limpeza concluída")

def main():
    """Main process"""
    
    print("🚀 IMPORTAÇÃO DE DADOS SQLITE → NEON")
    print("=" * 45)
    
    steps = [
        ("Filtrar dados JSON", filter_json_data),
        ("Carregar dados filtrados", load_filtered_data),
        ("Verificar importação", verify_loaded_data),
        ("Limpar arquivos temporários", cleanup_files),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📝 {step_name}...")
        
        if not step_func():
            print(f"❌ Falha em: {step_name}")
            # Don't stop on verification failure
            if "Verificar" not in step_name:
                return False
    
    print("\n" + "=" * 45)
    print("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print("🐘 Dados do SQLite foram migrados para Neon PostgreSQL")
    
    return True

if __name__ == "__main__":
    main()