#!/usr/bin/env python3
"""
Script para testar conexão com Neon PostgreSQL Database
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Configure Django
django.setup()

from django.db import connection
from django.core.management.color import make_style
from decouple import config

def test_neon_connection():
    """Test connection to Neon PostgreSQL database"""
    
    style = make_style()
    
    print(style.HTTP_INFO("🐘 Testando conexão com Neon PostgreSQL..."))
    print()
    
    # Check if PostgreSQL is enabled
    use_postgresql = config('USE_POSTGRESQL', default=False, cast=bool)
    database_url = config('DATABASE_URL', default='')
    
    print(f"USE_POSTGRESQL: {use_postgresql}")
    print(f"DATABASE_URL configurada: {'✅ Sim' if database_url else '❌ Não'}")
    print()
    
    if not database_url:
        print(style.ERROR("❌ DATABASE_URL não configurada no arquivo .env"))
        print(style.WARNING("💡 Copie .env.example para .env e configure as credenciais"))
        return False
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
        print(style.SUCCESS("✅ Conexão com Neon estabelecida com sucesso!"))
        print(f"📊 Versão PostgreSQL: {version}")
        print()
        
        # Test database info
        db_settings = connection.settings_dict
        print(style.HTTP_INFO("🔧 Configurações da Base de Dados:"))
        print(f"   • Engine: {db_settings['ENGINE']}")
        print(f"   • Host: {db_settings['HOST']}")
        print(f"   • Port: {db_settings['PORT']}")
        print(f"   • Database: {db_settings['NAME']}")
        print(f"   • User: {db_settings['USER']}")
        print()
        
        # Test table creation capability
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_test (
                    id SERIAL PRIMARY KEY,
                    test_message VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                INSERT INTO connection_test (test_message) 
                VALUES ('Teste de conexão realizado com sucesso');
            """)
            
            cursor.execute("SELECT COUNT(*) FROM connection_test;")
            count = cursor.fetchone()[0]
            
            cursor.execute("DROP TABLE connection_test;")
            
        print(style.SUCCESS(f"✅ Teste de criação/inserção de tabela: {count} registro(s)"))
        print(style.SUCCESS("🎉 Neon PostgreSQL está pronto para uso!"))
        
        return True
        
    except Exception as e:
        print(style.ERROR(f"❌ Erro na conexão: {str(e)}"))
        print()
        print(style.WARNING("🔧 Possíveis soluções:"))
        print("   1. Verifique se DATABASE_URL está correta no .env")
        print("   2. Confirme se o projeto Neon está ativo")
        print("   3. Verifique conectividade de internet")
        print("   4. Execute: pip install psycopg2-binary")
        
        return False

if __name__ == "__main__":
    test_neon_connection()