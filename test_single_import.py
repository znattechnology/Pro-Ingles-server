#!/usr/bin/env python3
"""
Teste de importação de um único registro para diagnóstico
"""

import os
import sys
import django
import json
import subprocess
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def main():
    print("🧪 TESTE DE IMPORTAÇÃO INDIVIDUAL")
    print("=" * 35)
    
    # Load the exported data
    data_file = BASE_DIR / 'migration_backup' / 'data_export.json'
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 {len(data)} registros no arquivo")
    
    # Count by model
    models = {}
    for item in data:
        model = item['model']
        models[model] = models.get(model, 0) + 1
    
    print("\n📋 Modelos disponíveis:")
    for model, count in sorted(models.items()):
        print(f"   • {model}: {count}")
    
    # Test with just one user record
    users_data = [item for item in data if item['model'] == 'users.user']
    
    if users_data:
        print(f"\n🧪 Testando importação de 1 usuário...")
        
        # Create a single user test file
        test_data = [users_data[0]]  # Just the first user
        test_file = BASE_DIR / 'single_user_test.json'
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"📝 Arquivo teste criado: {test_file}")
        
        # Try to load this single record
        try:
            result = subprocess.run([
                'python', 'manage.py', 'loaddata', str(test_file)
            ], capture_output=True, text=True, cwd=BASE_DIR, timeout=30)
            
            print(f"\n📋 Resultado do loaddata:")
            print(f"   Return code: {result.returncode}")
            print(f"   Stdout: {result.stdout}")
            print(f"   Stderr: {result.stderr}")
            
            if result.returncode == 0:
                print("✅ Importação de teste bem-sucedida")
                
                # Check if it actually got imported
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user_count = User.objects.count()
                print(f"👥 Usuários no banco: {user_count}")
                
            else:
                print("❌ Falha na importação de teste")
            
        except subprocess.TimeoutExpired:
            print("⏰ Timeout na importação")
        except Exception as e:
            print(f"❌ Erro: {e}")
        
        # Clean up
        if test_file.exists():
            test_file.unlink()
    
    else:
        print("❌ Nenhum dado de usuário encontrado")

if __name__ == "__main__":
    main()