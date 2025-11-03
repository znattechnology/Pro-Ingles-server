#!/usr/bin/env python
"""
Script para testar autenticação no backend de produção.
Execute: python test_production_auth.py
"""

import requests
import json
import sys

# URL do backend em produção
BASE_URL = "http://pro-english-alb-343566329.eu-west-1.elb.amazonaws.com"
API_URL = f"{BASE_URL}/api/v1"

# Usuários para teste
TEST_USERS = [
    {
        'email': 'admin@proenglish.com',
        'password': 'Admin123!',
        'role': 'admin',
        'name': 'Admin Sistema'
    },
    {
        'email': 'professor@proenglish.com',
        'password': 'Professor123!',
        'role': 'teacher',
        'name': 'João Professor'
    },
    {
        'email': 'estudante@proenglish.com',
        'password': 'Estudante123!',
        'role': 'student',
        'name': 'Maria Estudante'
    }
]

def test_health_check():
    """Testar se o backend está respondendo."""
    print("🔍 Testando Health Check...")
    
    try:
        response = requests.get(f"{API_URL}/health/", timeout=10)
        
        if response.status_code == 200:
            print("✅ Backend está online e respondendo!")
            print(f"   Status: {response.status_code}")
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}...")
            return True
        else:
            print(f"❌ Backend respondeu mas com erro: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao backend!")
        print("   Verifique se o backend está rodando")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout ao conectar ao backend!")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_auth_endpoints():
    """Testar se os endpoints de autenticação existem."""
    print("\n🔍 Testando endpoints de autenticação...")
    
    endpoints_to_test = [
        "/auth/login/",
        "/auth/logout/",
        "/auth/register/",
        "/auth/user/",
    ]
    
    available_endpoints = []
    
    for endpoint in endpoints_to_test:
        try:
            # Teste com OPTIONS para verificar se endpoint existe
            response = requests.options(f"{API_URL}{endpoint}", timeout=5)
            
            if response.status_code in [200, 405]:  # 405 = Method Not Allowed (mas endpoint existe)
                print(f"✅ Endpoint encontrado: {endpoint}")
                available_endpoints.append(endpoint)
            else:
                print(f"❌ Endpoint não encontrado: {endpoint} (Status: {response.status_code})")
                
        except Exception as e:
            print(f"❌ Erro ao testar {endpoint}: {e}")
    
    return available_endpoints

def test_login(user_data):
    """Testar login para um usuário específico."""
    print(f"\n🔐 Testando login para: {user_data['email']} ({user_data['role']})")
    
    login_data = {
        'email': user_data['email'],
        'password': user_data['password']
    }
    
    try:
        # Tentar endpoint /auth/login/
        response = requests.post(
            f"{API_URL}/auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Login realizado com sucesso!")
                
                # Verificar se retornou token
                if 'token' in data or 'access' in data or 'access_token' in data:
                    token = data.get('token') or data.get('access') or data.get('access_token')
                    print(f"   Token recebido: {token[:50]}...")
                    
                    # Testar token
                    test_token_validation(token)
                    
                    return {'success': True, 'token': token, 'data': data}
                else:
                    print("⚠️  Login OK mas sem token no response")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                    return {'success': True, 'token': None, 'data': data}
                    
            except json.JSONDecodeError:
                print("✅ Login OK mas response não é JSON")
                print(f"   Response: {response.text[:200]}...")
                return {'success': True, 'token': None, 'data': response.text}
                
        elif response.status_code == 400:
            print("❌ Credenciais inválidas ou dados malformados")
            try:
                error_data = response.json()
                print(f"   Erro: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.text}")
            return {'success': False, 'error': 'bad_request'}
            
        elif response.status_code == 401:
            print("❌ Credenciais incorretas")
            try:
                error_data = response.json()
                print(f"   Erro: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.text}")
            return {'success': False, 'error': 'unauthorized'}
            
        elif response.status_code == 404:
            print("❌ Endpoint de login não encontrado")
            print("   Tentando outros endpoints...")
            return test_alternative_login_endpoints(user_data)
            
        else:
            print(f"❌ Erro inesperado: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return {'success': False, 'error': f'http_{response.status_code}'}
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão")
        return {'success': False, 'error': 'connection'}
    except requests.exceptions.Timeout:
        print("❌ Timeout")
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return {'success': False, 'error': str(e)}

def test_alternative_login_endpoints(user_data):
    """Testar endpoints alternativos de login."""
    print("   🔄 Testando endpoints alternativos...")
    
    alternative_endpoints = [
        "/api/auth/login/",
        "/auth/jwt/create/",
        "/auth/token/",
        "/token/",
        "/login/",
    ]
    
    login_data = {
        'email': user_data['email'],
        'password': user_data['password']
    }
    
    for endpoint in alternative_endpoints:
        try:
            print(f"      Tentando: {BASE_URL}{endpoint}")
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=login_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"   ✅ Endpoint funcionando: {endpoint}")
                try:
                    data = response.json()
                    print(f"      Response: {json.dumps(data, indent=2)[:200]}...")
                    return {'success': True, 'endpoint': endpoint, 'data': data}
                except:
                    return {'success': True, 'endpoint': endpoint, 'data': response.text}
            elif response.status_code != 404:
                print(f"      Status {response.status_code}: {endpoint}")
                
        except Exception as e:
            print(f"      Erro em {endpoint}: {e}")
    
    return {'success': False, 'error': 'no_working_endpoint'}

def test_token_validation(token):
    """Testar se o token é válido."""
    print(f"   🔍 Validando token...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Tentar endpoints que requerem autenticação
    protected_endpoints = [
        "/auth/user/",
        "/user/profile/",
        "/me/",
    ]
    
    for endpoint in protected_endpoints:
        try:
            response = requests.get(
                f"{API_URL}{endpoint}",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"   ✅ Token válido! Endpoint: {endpoint}")
                try:
                    data = response.json()
                    print(f"      User data: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"      Response: {response.text[:100]}...")
                return True
            elif response.status_code == 401:
                print(f"   ❌ Token inválido ou expirado")
                return False
                
        except Exception as e:
            continue
    
    print("   ⚠️  Não foi possível validar o token (endpoints não encontrados)")
    return None

def test_courses_api():
    """Testar se a API de cursos está funcionando."""
    print("\n📚 Testando API de cursos...")
    
    course_endpoints = [
        "/student/video-courses/",
        "/student/practice-courses/courses/",
        "/courses/",
    ]
    
    for endpoint in course_endpoints:
        try:
            response = requests.get(f"{API_URL}{endpoint}", timeout=5)
            
            print(f"   Endpoint: {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data:
                        courses = data['data']
                        print(f"   ✅ {len(courses)} cursos encontrados")
                        if courses:
                            print(f"      Exemplo: {courses[0].get('title', 'Sem título')}")
                    elif isinstance(data, list):
                        print(f"   ✅ {len(data)} cursos encontrados")
                        if data:
                            print(f"      Exemplo: {data[0].get('title', 'Sem título')}")
                    else:
                        print("   ✅ Response recebido (formato não padrão)")
                except:
                    print("   ✅ Response recebido (não JSON)")
            elif response.status_code == 401:
                print("   ⚠️  Endpoint requer autenticação")
            elif response.status_code == 404:
                print("   ❌ Endpoint não encontrado")
            else:
                print(f"   ❌ Erro: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

def main():
    """Função principal."""
    print("🚀 TESTE DE AUTENTICAÇÃO EM PRODUÇÃO")
    print("=" * 60)
    print(f"Backend: {BASE_URL}")
    print(f"API: {API_URL}")
    print("=" * 60)
    
    # 1. Testar health check
    if not test_health_check():
        print("\n❌ Backend não está acessível. Abortando testes.")
        return
    
    # 2. Testar endpoints de autenticação
    available_endpoints = test_auth_endpoints()
    
    # 3. Testar login para cada usuário
    login_results = []
    for user in TEST_USERS:
        result = test_login(user)
        login_results.append({
            'user': user,
            'result': result
        })
    
    # 4. Testar API de cursos
    test_courses_api()
    
    # 5. Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    successful_logins = [r for r in login_results if r['result']['success']]
    failed_logins = [r for r in login_results if not r['result']['success']]
    
    print(f"✅ Logins bem-sucedidos: {len(successful_logins)}/{len(TEST_USERS)}")
    for result in successful_logins:
        user = result['user']
        print(f"   - {user['email']} ({user['role']})")
    
    if failed_logins:
        print(f"\n❌ Logins falharam: {len(failed_logins)}")
        for result in failed_logins:
            user = result['user']
            error = result['result']['error']
            print(f"   - {user['email']} ({user['role']}): {error}")
    
    print(f"\n🌐 URLs para teste manual:")
    print(f"   Frontend: https://pro-ingles-client-nine.vercel.app")
    print(f"   Backend Health: {API_URL}/health/")
    print(f"   Admin Django: {BASE_URL}/admin/")
    
    if successful_logins:
        print(f"\n🎉 Sistema de autenticação funcionando!")
    else:
        print(f"\n⚠️  Sistema de autenticação precisa de ajustes")

if __name__ == '__main__':
    main()