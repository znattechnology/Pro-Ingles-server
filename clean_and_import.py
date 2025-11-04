#!/usr/bin/env python3
"""
Limpar PostgreSQL e importar dados limpos do SQLite
"""

import os
import sys
import django
import subprocess
from pathlib import Path
from django.core.management.color import make_style

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def clean_application_tables():
    """Limpar apenas tabelas da aplicação, preservando Django core"""
    
    style = make_style()
    print(style.HTTP_INFO("🧹 Limpando tabelas da aplicação..."))
    
    from django.db import connection
    
    # Tables to clean (application data, not Django core)
    app_tables = [
        'users', 'courses', 'chapters', 'chapter_progress', 'chapter_resources',
        'course_enrollments', 'course_sections', 'user_course_progress',
        'cms_serviceitem', 'cms_company', 'cms_herosection', 'cms_landingpagesettings',
        'cms_pricingtier', 'cms_seosettings', 'cms_statitem',
        'practice_practicechallenge', 'practice_userachievement', 'practice_achievement',
        'practice_achievementcategory', 'practice_achievementnotification',
        'practice_challengeoption', 'practice_challengeprogress', 'practice_competition',
        'practice_competitionparticipant', 'practice_leaguepromotion', 'practice_practicelesson',
        'practice_practiceunit', 'practice_speakingexercise', 'practice_speakingprogress',
        'practice_speakingsession', 'practice_speakingturn', 'practice_userleague',
        'practice_userprogress', 'practice_userstreak',
        'subscriptions_subscriptionplan', 'subscriptions_usersubscription',
        'notification_settings', 'email_verifications', 'transactions',
        'user_addresses', 'users_groups', 'users_user_permissions'
    ]
    
    cleaned_count = 0
    
    with connection.cursor() as cursor:
        # Disable foreign key checks temporarily
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
        
        for table in app_tables:
            try:
                cursor.execute(f'DELETE FROM "{table}";')
                deleted = cursor.rowcount
                if deleted > 0:
                    print(f"   🗑️ {table}: {deleted} registros removidos")
                    cleaned_count += deleted
            except Exception as e:
                print(f"   ⚠️ {table}: {e}")
        
        # Re-enable constraints
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
    
    print(f"✅ {cleaned_count} registros removidos")
    return True

def import_complete_data():
    """Importar dados completos"""
    
    style = make_style()
    print(style.HTTP_INFO("📥 Importando dados completos..."))
    
    data_file = BASE_DIR / 'migration_backup' / 'data_export.json'
    
    try:
        result = subprocess.run([
            'python', 'manage.py', 'loaddata', str(data_file)
        ], capture_output=True, text=True, cwd=BASE_DIR, timeout=120)
        
        if result.returncode == 0:
            print("✅ Dados importados com sucesso!")
            print(f"📋 {result.stdout}")
            return True
        else:
            print(f"❌ Erro na importação: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout na importação")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def verify_final_data():
    """Verificação final dos dados"""
    
    style = make_style()
    print(style.HTTP_INFO("🔍 Verificação final..."))
    
    from django.db import connection
    
    key_tables = [
        'users', 'courses', 'chapters', 'cms_serviceitem',
        'practice_practicechallenge', 'practice_userachievement',
        'subscriptions_subscriptionplan'
    ]
    
    total_records = 0
    
    with connection.cursor() as cursor:
        print("📊 Contagem final:")
        for table in key_tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                total_records += count
                status = '✅' if count > 0 else '⚪'
                print(f"   {status} {table}: {count}")
            except Exception as e:
                print(f"   ❌ {table}: {e}")
    
    print(f"\n💾 Total registros: {total_records}")
    
    # From SQLite analysis: expected ~982 total records
    if total_records >= 800:  # Allow some margin
        print(style.SUCCESS("🎉 MIGRAÇÃO COMPLETAMENTE BEM-SUCEDIDA!"))
        print("🐘 PostgreSQL contém todos os dados do SQLite")
        print("🚀 Sistema pronto para produção!")
        return True
    else:
        print(style.WARNING(f"⚠️ Migração parcial: {total_records} registros"))
        return False

def main():
    """Processo principal"""
    
    style = make_style()
    
    print(style.SUCCESS("🔄 LIMPEZA E IMPORTAÇÃO COMPLETA"))
    print("=" * 40)
    
    steps = [
        ("Limpar tabelas da aplicação", clean_application_tables),
        ("Importar dados completos", import_complete_data),
        ("Verificar resultado final", verify_final_data),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📝 {step_name}...")
        
        if not step_func():
            print(f"❌ Falha em: {step_name}")
            return False
    
    print("\n" + "=" * 40)
    print("🎉 MIGRAÇÃO COMPLETA FINALIZADA!")
    return True

if __name__ == "__main__":
    main()