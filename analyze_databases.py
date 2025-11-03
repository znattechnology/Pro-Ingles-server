#!/usr/bin/env python3
"""
Análise profunda das estruturas das bases de dados SQLite vs PostgreSQL
"""

import os
import sys
import django
import sqlite3
import json
from pathlib import Path
from django.core.management.color import make_style

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def analyze_sqlite_structure():
    """Analyze SQLite database structure"""
    
    style = make_style()
    print(style.HTTP_INFO("🔍 Analisando estrutura do SQLite..."))
    
    sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
    if not sqlite_path.exists():
        print(style.ERROR("❌ SQLite recuperado não encontrado"))
        return None
    
    # Temporarily rename for analysis
    temp_sqlite = BASE_DIR / 'db.sqlite3'
    if temp_sqlite.exists():
        temp_sqlite.rename(BASE_DIR / 'db.sqlite3.temp')
    
    sqlite_path.rename(temp_sqlite)
    
    try:
        conn = sqlite3.connect(temp_sqlite)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        sqlite_structure = {}
        
        for table in tables:
            if table.startswith('django_') or table.startswith('sqlite_'):
                continue
                
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            
            sqlite_structure[table] = {
                'columns': [{'name': col[1], 'type': col[2], 'not_null': col[3], 'pk': col[5]} for col in columns],
                'row_count': count
            }
        
        conn.close()
        
        print(f"   📊 {len(sqlite_structure)} tabelas encontradas no SQLite")
        return sqlite_structure
        
    finally:
        # Restore file names
        if temp_sqlite.exists():
            temp_sqlite.rename(sqlite_path)
        
        temp_backup = BASE_DIR / 'db.sqlite3.temp'
        if temp_backup.exists():
            temp_backup.rename(BASE_DIR / 'db.sqlite3')

def analyze_postgresql_structure():
    """Analyze PostgreSQL database structure"""
    
    style = make_style()
    print(style.HTTP_INFO("🐘 Analisando estrutura do PostgreSQL..."))
    
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'django_%'
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        postgresql_structure = {}
        
        for table in tables:
            # Get columns info
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, [table])
            
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
            count = cursor.fetchone()[0]
            
            postgresql_structure[table] = {
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2], 'default': col[3]} for col in columns],
                'row_count': count
            }
    
    print(f"   📊 {len(postgresql_structure)} tabelas encontradas no PostgreSQL")
    return postgresql_structure

def compare_structures(sqlite_struct, postgresql_struct):
    """Compare database structures"""
    
    style = make_style()
    print(style.HTTP_INFO("🔍 Comparando estruturas..."))
    
    comparison = {
        'common_tables': [],
        'sqlite_only': [],
        'postgresql_only': [],
        'schema_differences': {},
        'data_differences': {}
    }
    
    sqlite_tables = set(sqlite_struct.keys()) if sqlite_struct else set()
    postgresql_tables = set(postgresql_struct.keys())
    
    comparison['common_tables'] = list(sqlite_tables & postgresql_tables)
    comparison['sqlite_only'] = list(sqlite_tables - postgresql_tables)
    comparison['postgresql_only'] = list(postgresql_tables - sqlite_tables)
    
    # Compare schemas for common tables
    for table in comparison['common_tables']:
        sqlite_cols = {col['name']: col for col in sqlite_struct[table]['columns']}
        postgresql_cols = {col['name']: col for col in postgresql_struct[table]['columns']}
        
        sqlite_col_names = set(sqlite_cols.keys())
        postgresql_col_names = set(postgresql_cols.keys())
        
        if sqlite_col_names != postgresql_col_names:
            comparison['schema_differences'][table] = {
                'sqlite_only_cols': list(sqlite_col_names - postgresql_col_names),
                'postgresql_only_cols': list(postgresql_col_names - sqlite_col_names),
                'common_cols': list(sqlite_col_names & postgresql_col_names)
            }
        
        # Compare data counts
        sqlite_count = sqlite_struct[table]['row_count']
        postgresql_count = postgresql_struct[table]['row_count']
        
        if sqlite_count != postgresql_count:
            comparison['data_differences'][table] = {
                'sqlite_count': sqlite_count,
                'postgresql_count': postgresql_count,
                'difference': sqlite_count - postgresql_count
            }
    
    return comparison

def print_analysis_report(sqlite_struct, postgresql_struct, comparison):
    """Print detailed analysis report"""
    
    style = make_style()
    
    print("\n" + "=" * 60)
    print(style.SUCCESS("📋 RELATÓRIO DE ANÁLISE DAS BASES DE DADOS"))
    print("=" * 60)
    
    # Overview
    print(f"\n{style.HTTP_INFO('📊 RESUMO GERAL:')}")
    sqlite_tables = len(sqlite_struct) if sqlite_struct else 0
    postgresql_tables = len(postgresql_struct)
    
    print(f"   • SQLite: {sqlite_tables} tabelas")
    print(f"   • PostgreSQL: {postgresql_tables} tabelas")
    print(f"   • Tabelas comuns: {len(comparison['common_tables'])}")
    print(f"   • Apenas no SQLite: {len(comparison['sqlite_only'])}")
    print(f"   • Apenas no PostgreSQL: {len(comparison['postgresql_only'])}")
    
    # Data comparison
    if comparison['data_differences']:
        print(f"\n{style.WARNING('📈 DIFERENÇAS DE DADOS:')}")
        for table, diff in comparison['data_differences'].items():
            print(f"   • {table}:")
            print(f"     - SQLite: {diff['sqlite_count']} registros")
            print(f"     - PostgreSQL: {diff['postgresql_count']} registros")
            print(f"     - Diferença: {diff['difference']} registros")
    
    # Schema differences
    if comparison['schema_differences']:
        print(f"\n{style.WARNING('🔧 DIFERENÇAS DE SCHEMA:')}")
        for table, diff in comparison['schema_differences'].items():
            print(f"   • {table}:")
            if diff['sqlite_only_cols']:
                print(f"     - Colunas apenas no SQLite: {diff['sqlite_only_cols']}")
            if diff['postgresql_only_cols']:
                print(f"     - Colunas apenas no PostgreSQL: {diff['postgresql_only_cols']}")
    
    # SQLite only tables with data
    if sqlite_struct and comparison['sqlite_only']:
        print(f"\n{style.HTTP_INFO('📋 TABELAS APENAS NO SQLITE:')}")
        for table in comparison['sqlite_only']:
            count = sqlite_struct[table]['row_count']
            print(f"   • {table}: {count} registros")
    
    # Data summary from SQLite
    if sqlite_struct:
        print(f"\n{style.HTTP_INFO('📊 DADOS DISPONÍVEIS NO SQLITE:')}")
        total_records = sum(table['row_count'] for table in sqlite_struct.values())
        print(f"   💾 Total de registros: {total_records}")
        
        # Top tables by data volume
        sorted_tables = sorted(sqlite_struct.items(), key=lambda x: x[1]['row_count'], reverse=True)
        print("   🔝 Top 10 tabelas com mais dados:")
        for table, info in sorted_tables[:10]:
            if info['row_count'] > 0:
                print(f"      • {table}: {info['row_count']} registros")

def generate_migration_strategy(sqlite_struct, postgresql_struct, comparison):
    """Generate intelligent migration strategy"""
    
    style = make_style()
    print(f"\n{style.SUCCESS('🎯 ESTRATÉGIA DE MIGRAÇÃO RECOMENDADA:')}")
    
    strategy = {
        'approach': 'selective_migration',
        'steps': [],
        'risks': [],
        'benefits': []
    }
    
    # Determine best approach
    if not sqlite_struct:
        strategy['approach'] = 'fresh_start'
        strategy['steps'] = [
            "Base de dados SQLite não disponível",
            "Continuar com PostgreSQL limpo",
            "Criar dados de teste conforme necessário"
        ]
    elif len(comparison['schema_differences']) > 5:
        strategy['approach'] = 'schema_migration_required'
        strategy['steps'] = [
            "1. Aplicar todas as migrações pendentes no PostgreSQL",
            "2. Ajustar dados do SQLite para novo schema",
            "3. Migrar dados por lotes com validação",
            "4. Verificar integridade referencial"
        ]
    else:
        strategy['approach'] = 'direct_migration'
        strategy['steps'] = [
            "1. Sincronizar schemas das duas bases",
            "2. Migrar dados em ordem de dependências",
            "3. Resolver conflitos de chaves únicas",
            "4. Validar migração completa"
        ]
    
    # Add specific recommendations
    if comparison['schema_differences']:
        strategy['steps'].append("5. Reconciliar diferenças de schema identificadas")
    
    if comparison['data_differences']:
        strategy['steps'].append("6. Verificar e resolver diferenças de dados")
    
    # Print strategy
    print(f"   🎯 Abordagem: {strategy['approach']}")
    print("   📝 Passos recomendados:")
    for step in strategy['steps']:
        print(f"      {step}")
    
    return strategy

def main():
    """Main analysis function"""
    
    style = make_style()
    
    print(style.SUCCESS("🔍 ANÁLISE PROFUNDA DAS BASES DE DADOS"))
    print("=" * 50)
    
    # Analyze both databases
    sqlite_structure = analyze_sqlite_structure()
    postgresql_structure = analyze_postgresql_structure()
    
    # Compare structures
    comparison = compare_structures(sqlite_structure, postgresql_structure)
    
    # Generate report
    print_analysis_report(sqlite_structure, postgresql_structure, comparison)
    
    # Generate migration strategy
    strategy = generate_migration_strategy(sqlite_structure, postgresql_structure, comparison)
    
    # Save analysis to file
    analysis_data = {
        'sqlite_structure': sqlite_structure,
        'postgresql_structure': postgresql_structure,
        'comparison': comparison,
        'strategy': strategy
    }
    
    analysis_file = BASE_DIR / 'database_analysis.json'
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n{style.SUCCESS('✅ Análise completa salva em:')} {analysis_file}")
    
    return analysis_data

if __name__ == "__main__":
    main()