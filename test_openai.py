#!/usr/bin/env python3
"""
Script de teste para verificar configuração OpenAI
Execute: python test_openai.py
"""

import os
import sys
import django
from pathlib import Path

# Adicionar diretório do projeto ao Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_openai_config():
    """Testa configuração da OpenAI"""
    
    print("🔍 Verificando configuração OpenAI...")
    
    # 1. Verificar variáveis de ambiente
    from django.conf import settings
    
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        print("❌ ERRO: OPENAI_API_KEY não configurada!")
        print("📝 Configure no arquivo .env:")
        print("   OPENAI_API_KEY=sk-proj-sua-chave-aqui")
        return False
    
    if api_key == "sk-proj-your-openai-key-here":
        print("❌ ERRO: Chave OpenAI ainda é o exemplo!")
        print("📝 Substitua no arquivo .env pela sua chave real")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:15]}...")
    
    # 2. Testar conexão
    try:
        import openai
        client = openai.Client(api_key=api_key)
        
        print("🔄 Testando conexão com OpenAI...")
        
        # Teste simples com o modelo mais barato
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello! This is a connection test."}],
            max_tokens=10
        )
        
        print("✅ Conexão OpenAI funcionando!")
        print(f"📝 Resposta de teste: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO na conexão OpenAI: {e}")
        print("🔧 Verifique:")
        print("   - Chave API está correta")
        print("   - Billing está configurado na OpenAI")
        print("   - Conexão com internet")
        return False

def test_ai_speaking_settings():
    """Testa configurações específicas do AI Speaking"""
    
    print("\n🎤 Verificando configurações AI Speaking...")
    
    from django.conf import settings
    
    if not hasattr(settings, 'AI_SPEAKING_SETTINGS'):
        print("❌ ERRO: AI_SPEAKING_SETTINGS não encontrada!")
        return False
    
    ai_settings = settings.AI_SPEAKING_SETTINGS
    
    print("✅ Configurações AI Speaking encontradas:")
    print(f"   - Modelo Chat: {ai_settings['MODELS']['CHAT']}")
    print(f"   - Modelo Whisper: {ai_settings['MODELS']['WHISPER']}")
    print(f"   - Modelo TTS: {ai_settings['MODELS']['TTS']}")
    print(f"   - Score mínimo: {ai_settings['MINIMUM_SCORES']['OVERALL']}%")
    
    return True

def main():
    """Função principal do teste"""
    
    print("🚀 TESTE DE CONFIGURAÇÃO OPENAI")
    print("=" * 50)
    
    success = True
    
    # Teste 1: Configuração OpenAI
    if not test_openai_config():
        success = False
    
    # Teste 2: Configurações AI Speaking
    if not test_ai_speaking_settings():
        success = False
    
    print("\n" + "=" * 50)
    
    if success:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("🎉 O sistema AI Speaking Practice está pronto!")
        print("\n📋 Próximos passos:")
        print("   1. Rodar o servidor Django")
        print("   2. Testar endpoints via API")
        print("   3. Implementar frontend")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("🔧 Corrija os problemas listados acima")
        
    return success

if __name__ == "__main__":
    main()