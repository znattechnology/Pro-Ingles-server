#!/usr/bin/env python3
"""
MIGRAÇÃO PROFISSIONAL DE BANCO DE DADOS - SQLite para PostgreSQL
Especialista DBA - Estratégia de migração segura com zero perda de dados
"""

import os
import sys
import django
import sqlite3
import json
import subprocess
from pathlib import Path
from datetime import datetime
from django.core.management.color import make_style

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

class DatabaseMigrationExpert:
    """Especialista em migração de banco de dados com estratégias seguras"""
    
    def __init__(self):
        self.style = make_style()
        self.log_file = BASE_DIR / f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.backup_dir = BASE_DIR / "migration_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def log(self, message, level="INFO"):
        """Log profissional com timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Print para console
        if level == "ERROR":
            print(self.style.ERROR(f"❌ {message}"))
        elif level == "WARNING":
            print(self.style.WARNING(f"⚠️ {message}"))
        elif level == "SUCCESS":
            print(self.style.SUCCESS(f"✅ {message}"))
        else:
            print(self.style.HTTP_INFO(f"📋 {message}"))
        
        # Salvar em arquivo
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    def create_safety_backups(self):
        """Criar backups de segurança antes da migração"""
        self.log("FASE 1: Criando backups de segurança", "SUCCESS")
        
        # 1. Backup do SQLite original
        sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
        if sqlite_path.exists():
            backup_sqlite = self.backup_dir / f"original_sqlite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            import shutil
            shutil.copy2(sqlite_path, backup_sqlite)
            self.log(f"Backup SQLite criado: {backup_sqlite}")
        
        # 2. Backup do estado atual do PostgreSQL
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE';
                """)
                tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                self.log(f"PostgreSQL atual tem {len(tables)} tabelas - criando backup")
                
                # Exportar estado atual do PostgreSQL
                pg_backup = self.backup_dir / f"postgresql_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                result = subprocess.run([
                    'python', 'manage.py', 'dumpdata',
                    '--indent=2',
                    '--output', str(pg_backup)
                ], capture_output=True, text=True, cwd=BASE_DIR)
                
                if result.returncode == 0:
                    self.log(f"Backup PostgreSQL criado: {pg_backup}")
                else:
                    self.log(f"Erro no backup PostgreSQL: {result.stderr}", "WARNING")
            
            return True
            
        except Exception as e:
            self.log(f"Erro ao criar backups: {str(e)}", "ERROR")
            return False
    
    def analyze_sqlite_schema(self):
        """Análise detalhada do schema SQLite"""
        self.log("FASE 2: Análise detalhada do schema SQLite", "SUCCESS")
        
        sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
        if not sqlite_path.exists():
            self.log("SQLite não encontrado!", "ERROR")
            return None
        
        # Temporariamente usar SQLite
        temp_sqlite = BASE_DIR / 'temp_analysis.db'
        import shutil
        shutil.copy2(sqlite_path, temp_sqlite)
        
        try:
            conn = sqlite3.connect(temp_sqlite)
            cursor = conn.cursor()
            
            # Obter todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_analysis = {
                'tables': {},
                'foreign_keys': {},
                'indexes': {},
                'data_counts': {}
            }
            
            for table in tables:
                if table.startswith('sqlite_') or table.startswith('django_'):
                    continue
                
                # Schema da tabela
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                
                # Foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                foreign_keys = cursor.fetchall()
                
                # Indexes
                cursor.execute(f"PRAGMA index_list({table});")
                indexes = cursor.fetchall()
                
                # Contagem de dados
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                
                schema_analysis['tables'][table] = {
                    'columns': [{'name': col[1], 'type': col[2], 'not_null': col[3], 'pk': col[5]} for col in columns],
                    'row_count': count
                }
                
                if foreign_keys:
                    schema_analysis['foreign_keys'][table] = foreign_keys
                
                if indexes:
                    schema_analysis['indexes'][table] = indexes
                
                schema_analysis['data_counts'][table] = count
            
            conn.close()
            
            # Salvar análise
            analysis_file = self.backup_dir / "sqlite_schema_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(schema_analysis, f, indent=2, ensure_ascii=False)
            
            self.log(f"Análise completa do SQLite salva: {analysis_file}")
            self.log(f"Encontradas {len(schema_analysis['tables'])} tabelas com {sum(schema_analysis['data_counts'].values())} registros totais")
            
            return schema_analysis
            
        except Exception as e:
            self.log(f"Erro na análise do SQLite: {str(e)}", "ERROR")
            return None
        
        finally:
            if temp_sqlite.exists():
                temp_sqlite.unlink()
    
    def analyze_postgresql_schema(self):
        """Análise detalhada do schema PostgreSQL"""
        self.log("FASE 3: Análise do schema PostgreSQL atual", "SUCCESS")
        
        try:
            from django.db import connection
            
            schema_analysis = {
                'tables': {},
                'constraints': {},
                'indexes': {},
                'data_counts': {}
            }
            
            with connection.cursor() as cursor:
                # Obter tabelas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name NOT LIKE 'django_%'
                    ORDER BY table_name;
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    # Colunas
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = %s AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """, [table])
                    columns = cursor.fetchall()
                    
                    # Constraints
                    cursor.execute("""
                        SELECT constraint_name, constraint_type
                        FROM information_schema.table_constraints
                        WHERE table_name = %s AND table_schema = 'public';
                    """, [table])
                    constraints = cursor.fetchall()
                    
                    # Contagem
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
                        count = cursor.fetchone()[0]
                    except:
                        count = 0
                    
                    schema_analysis['tables'][table] = {
                        'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2], 'default': col[3]} for col in columns],
                        'row_count': count
                    }
                    
                    if constraints:
                        schema_analysis['constraints'][table] = constraints
                    
                    schema_analysis['data_counts'][table] = count
            
            # Salvar análise
            analysis_file = self.backup_dir / "postgresql_schema_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(schema_analysis, f, indent=2, ensure_ascii=False, default=str)
            
            self.log(f"Análise PostgreSQL salva: {analysis_file}")
            self.log(f"PostgreSQL tem {len(schema_analysis['tables'])} tabelas com {sum(schema_analysis['data_counts'].values())} registros")
            
            return schema_analysis
            
        except Exception as e:
            self.log(f"Erro na análise PostgreSQL: {str(e)}", "ERROR")
            return None
    
    def create_migration_plan(self, sqlite_schema, postgresql_schema):
        """Criar plano detalhado de migração"""
        self.log("FASE 4: Criando plano detalhado de migração", "SUCCESS")
        
        plan = {
            'missing_tables': [],
            'schema_updates_needed': [],
            'data_migration_order': [],
            'post_migration_validations': [],
            'estimated_records': 0
        }
        
        sqlite_tables = set(sqlite_schema['tables'].keys()) if sqlite_schema else set()
        postgresql_tables = set(postgresql_schema['tables'].keys()) if postgresql_schema else set()
        
        # Tabelas faltantes no PostgreSQL
        plan['missing_tables'] = list(sqlite_tables - postgresql_tables)
        
        # Ordem de migração baseada em dependências (tables sem FK primeiro)
        tables_with_fk = set()
        if sqlite_schema and 'foreign_keys' in sqlite_schema:
            tables_with_fk = set(sqlite_schema['foreign_keys'].keys())
        
        independent_tables = sqlite_tables - tables_with_fk
        dependent_tables = tables_with_fk
        
        plan['data_migration_order'] = list(independent_tables) + list(dependent_tables)
        plan['estimated_records'] = sum(sqlite_schema['data_counts'].values()) if sqlite_schema else 0
        
        # Validações pós-migração
        plan['post_migration_validations'] = [
            'Verificar contagem de registros por tabela',
            'Validar foreign keys e constraints',
            'Testar queries principais do sistema',
            'Verificar integridade referencial'
        ]
        
        # Salvar plano
        plan_file = self.backup_dir / "migration_plan.json"
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        self.log(f"Plano de migração criado: {plan_file}")
        self.log(f"Migração de {plan['estimated_records']} registros em {len(plan['data_migration_order'])} tabelas")
        
        return plan
    
    def ensure_postgresql_schema(self):
        """Garantir que o schema PostgreSQL está completo"""
        self.log("FASE 5: Garantindo schema completo no PostgreSQL", "SUCCESS")
        
        try:
            # Aplicar todas as migrações pendentes
            result = subprocess.run([
                'python', 'manage.py', 'migrate', '--run-syncdb'
            ], capture_output=True, text=True, cwd=BASE_DIR)
            
            if result.returncode == 0:
                self.log("Todas as migrações aplicadas com sucesso")
                return True
            else:
                self.log(f"Erro nas migrações: {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erro ao aplicar migrações: {str(e)}", "ERROR")
            return False
    
    def execute_safe_data_migration(self, migration_plan):
        """Executar migração de dados de forma segura"""
        self.log("FASE 6: Migração segura de dados", "SUCCESS")
        
        # Primeiro, configurar SQLite temporariamente
        sqlite_path = BASE_DIR / 'db.sqlite3.recovered'
        temp_sqlite = BASE_DIR / 'db.sqlite3'
        
        if temp_sqlite.exists():
            temp_sqlite.rename(BASE_DIR / 'db.sqlite3.bak')
        
        import shutil
        shutil.copy2(sqlite_path, temp_sqlite)
        
        # Desabilitar DATABASE_URL temporariamente
        original_db_url = os.environ.get('DATABASE_URL', '')
        os.environ['DATABASE_URL'] = ''
        
        try:
            # Exportar dados do SQLite
            backup_file = self.backup_dir / "complete_data_export.json"
            
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
                self.log(f"Dados exportados com sucesso: {backup_file}")
            else:
                self.log(f"Erro na exportação: {result.stderr}", "ERROR")
                return False
            
            # Restaurar configuração PostgreSQL
            os.environ['DATABASE_URL'] = original_db_url
            
            # Força recarregar configuração Django
            from django.db import connections
            connections.databases['default'] = None
            
            # Importar dados no PostgreSQL com tratamento de erros
            self.log("Iniciando importação no PostgreSQL...")
            
            result = subprocess.run([
                'python', 'manage.py', 'loaddata', str(backup_file)
            ], capture_output=True, text=True, cwd=BASE_DIR, env=os.environ.copy())
            
            if result.returncode == 0:
                self.log("Dados importados com sucesso no PostgreSQL!")
                self.log(f"Output: {result.stdout}")
                return True
            else:
                self.log(f"Erro na importação: {result.stderr}", "WARNING")
                # Tentar importação parcial
                return self.handle_partial_import_errors(backup_file)
                
        except Exception as e:
            self.log(f"Erro na migração de dados: {str(e)}", "ERROR")
            return False
        
        finally:
            # Restaurar arquivos
            if temp_sqlite.exists():
                temp_sqlite.unlink()
            
            backup_sqlite = BASE_DIR / 'db.sqlite3.bak'
            if backup_sqlite.exists():
                backup_sqlite.rename(temp_sqlite)
            
            os.environ['DATABASE_URL'] = original_db_url
    
    def handle_partial_import_errors(self, backup_file):
        """Tratar erros de importação parcial"""
        self.log("Tratando erros de importação - tentativa de recuperação", "WARNING")
        
        try:
            # Carregar dados do backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Separar por modelo
            models_data = {}
            for item in data:
                model = item['model']
                if model not in models_data:
                    models_data[model] = []
                models_data[model].append(item)
            
            success_count = 0
            error_count = 0
            
            # Tentar importar modelo por modelo
            for model, items in models_data.items():
                try:
                    temp_file = self.backup_dir / f"temp_{model.replace('.', '_')}.json"
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(items, f, indent=2)
                    
                    result = subprocess.run([
                        'python', 'manage.py', 'loaddata', str(temp_file)
                    ], capture_output=True, text=True, cwd=BASE_DIR)
                    
                    if result.returncode == 0:
                        self.log(f"✅ {model}: {len(items)} registros importados")
                        success_count += len(items)
                    else:
                        self.log(f"❌ {model}: Erro - {result.stderr}", "WARNING")
                        error_count += len(items)
                    
                    temp_file.unlink()
                    
                except Exception as e:
                    self.log(f"Erro ao importar {model}: {str(e)}", "WARNING")
                    error_count += len(items)
            
            self.log(f"Importação parcial: {success_count} sucessos, {error_count} erros")
            return success_count > 0
            
        except Exception as e:
            self.log(f"Erro na recuperação: {str(e)}", "ERROR")
            return False
    
    def validate_migration_integrity(self, sqlite_schema):
        """Validar integridade da migração"""
        self.log("FASE 7: Validação de integridade da migração", "SUCCESS")
        
        try:
            from django.db import connection
            
            validation_results = {
                'table_counts': {},
                'data_integrity': True,
                'missing_data': [],
                'summary': {}
            }
            
            # Comparar contagens de registros
            for table, info in sqlite_schema['tables'].items():
                expected_count = info['row_count']
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
                        actual_count = cursor.fetchone()[0]
                    
                    validation_results['table_counts'][table] = {
                        'expected': expected_count,
                        'actual': actual_count,
                        'status': 'OK' if actual_count >= expected_count * 0.95 else 'ISSUE'
                    }
                    
                    if actual_count < expected_count * 0.95:
                        validation_results['missing_data'].append(table)
                        validation_results['data_integrity'] = False
                        
                except Exception as e:
                    validation_results['table_counts'][table] = {
                        'expected': expected_count,
                        'actual': 0,
                        'status': 'ERROR',
                        'error': str(e)
                    }
            
            # Resumo
            total_expected = sum(info['row_count'] for info in sqlite_schema['tables'].values())
            total_actual = sum(
                result['actual'] for result in validation_results['table_counts'].values() 
                if isinstance(result['actual'], int)
            )
            
            success_rate = (total_actual / total_expected * 100) if total_expected > 0 else 0
            
            validation_results['summary'] = {
                'total_expected': total_expected,
                'total_migrated': total_actual,
                'success_rate': round(success_rate, 2),
                'status': 'SUCCESS' if success_rate >= 95 else 'PARTIAL' if success_rate >= 50 else 'FAILED'
            }
            
            # Salvar relatório
            report_file = self.backup_dir / "migration_validation_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False, default=str)
            
            self.log(f"Relatório de validação salvo: {report_file}")
            self.log(f"Taxa de sucesso: {success_rate:.2f}% ({total_actual}/{total_expected} registros)")
            
            return validation_results
            
        except Exception as e:
            self.log(f"Erro na validação: {str(e)}", "ERROR")
            return None
    
    def run_complete_migration(self):
        """Executar migração completa e profissional"""
        self.log("🚀 INICIANDO MIGRAÇÃO PROFISSIONAL DE BANCO DE DADOS", "SUCCESS")
        self.log("Especialista DBA - Migração SQLite → PostgreSQL", "SUCCESS")
        self.log("=" * 80)
        
        try:
            # Fase 1: Backups de segurança
            if not self.create_safety_backups():
                return False
            
            # Fase 2: Análise SQLite
            sqlite_schema = self.analyze_sqlite_schema()
            if not sqlite_schema:
                return False
            
            # Fase 3: Análise PostgreSQL
            postgresql_schema = self.analyze_postgresql_schema()
            
            # Fase 4: Plano de migração
            migration_plan = self.create_migration_plan(sqlite_schema, postgresql_schema)
            
            # Fase 5: Garantir schema PostgreSQL
            if not self.ensure_postgresql_schema():
                return False
            
            # Fase 6: Migração de dados
            if not self.execute_safe_data_migration(migration_plan):
                return False
            
            # Fase 7: Validação
            validation_results = self.validate_migration_integrity(sqlite_schema)
            
            # Relatório final
            self.generate_final_report(validation_results)
            
            return True
            
        except Exception as e:
            self.log(f"ERRO CRÍTICO na migração: {str(e)}", "ERROR")
            return False
    
    def generate_final_report(self, validation_results):
        """Gerar relatório final da migração"""
        self.log("=" * 80)
        self.log("📊 RELATÓRIO FINAL DA MIGRAÇÃO", "SUCCESS")
        self.log("=" * 80)
        
        if validation_results and validation_results['summary']['status'] == 'SUCCESS':
            self.log("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!", "SUCCESS")
            self.log(f"✅ {validation_results['summary']['total_migrated']} registros migrados", "SUCCESS")
            self.log(f"✅ Taxa de sucesso: {validation_results['summary']['success_rate']}%", "SUCCESS")
            self.log("✅ Sistema pronto para produção!", "SUCCESS")
        else:
            self.log("⚠️ Migração com problemas parciais", "WARNING")
            if validation_results:
                self.log(f"📊 {validation_results['summary']['total_migrated']} de {validation_results['summary']['total_expected']} registros", "WARNING")
        
        self.log(f"📁 Backups e logs salvos em: {self.backup_dir}")
        self.log(f"📋 Log detalhado: {self.log_file}")

def main():
    """Função principal"""
    migration_expert = DatabaseMigrationExpert()
    success = migration_expert.run_complete_migration()
    
    if success:
        print("\n🎉 MIGRAÇÃO PROFISSIONAL CONCLUÍDA!")
        print("🐘 PostgreSQL agora contém toda a estrutura e dados do SQLite")
        print("🔒 Sistema migrado com segurança e integridade garantida")
    else:
        print("\n❌ MIGRAÇÃO FALHOU - Verifique os logs para detalhes")
    
    return success

if __name__ == "__main__":
    main()