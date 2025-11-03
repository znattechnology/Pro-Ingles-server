# 🔄 PLANO DE MIGRAÇÃO SEGURA - COURSES APP

## 📊 **ANÁLISE DE IMPACTO**

### **CÓDIGO DUPLICADO IDENTIFICADO:**
- ✅ `apps/courses/views.py` (1.412 linhas) → **PODE SER REMOVIDO**
- ✅ `apps/courses/serializers.py` → **PODE SER REMOVIDO** 
- ✅ `apps/courses/urls_v1.py` e `apps/courses/urls_v2.py` → **PODEM SER REMOVIDOS**
- ✅ `apps/courses/urls.py` → **PODE SER SIMPLIFICADO**

### **CÓDIGO ESSENCIAL (NÃO REMOVER):**
- ❌ `apps/courses/models/` → **MANTER** (usado por toda aplicação)
- ❌ `apps/courses/middleware.py` → **MANTER** (performance monitoring)
- ❌ `apps/courses/services/` → **MANTER** (business logic)
- ❌ `apps/courses/pagination.py` → **MANTER** (usado pelo novo código)
- ❌ `apps/courses/validators.py` → **MANTER** (validações)
- ❌ `apps/courses/management/` → **MANTER** (comandos de gestão)
- ❌ `apps/courses/migrations/` → **MANTER** (migrações do banco)

## 🎯 **ESTRATÉGIA DE MIGRAÇÃO (3 FASES)**

### **FASE 1: DEPRECAÇÃO CONTROLADA (1-2 dias)**

#### 1.1 Adicionar Warnings de Deprecação
```python
# apps/courses/views.py - Adicionar no topo de cada view
import warnings

class CourseListCreateView(generics.ListCreateAPIView):
    def dispatch(self, request, *args, **kwargs):
        warnings.warn(
            "Legacy courses API is deprecated. Use /api/v1/teacher/video-courses/ or /api/v1/student/video-courses/",
            DeprecationWarning,
            stacklevel=2
        )
        return super().dispatch(request, *args, **kwargs)
```

#### 1.2 Atualizar Documentação
- Marcar endpoints antigos como `@deprecated` no Swagger
- Adicionar links para novos endpoints

#### 1.3 Monitorar Uso
- Adicionar logs para endpoints antigos
- Identificar clientes que ainda usam API antiga

### **FASE 2: REDIRECIONAMENTO SUAVE (3-5 dias)**

#### 2.1 Implementar Redirecionamento
```python
# apps/courses/urls.py - Versão simplificada
from django.urls import path, redirect
from django.http import HttpResponsePermanentRedirect

def redirect_to_teacher_api(request, **kwargs):
    # Redirecionar para API organizada baseado no usuário
    if request.user.role == 'teacher':
        return HttpResponsePermanentRedirect(
            f"/api/v1/teacher/video-courses/{request.path.split('/')[-1]}"
        )
    else:
        return HttpResponsePermanentRedirect(
            f"/api/v1/student/video-courses/{request.path.split('/')[-1]}"
        )

urlpatterns = [
    # Redirecionamentos inteligentes
    path('', redirect_to_teacher_api, name='course_list_redirect'),
    path('<uuid:courseId>/', redirect_to_teacher_api, name='course_detail_redirect'),
    # ... outros redirecionamentos
]
```

#### 2.2 Atualizar Frontend (se necessário)
- Substituir chamadas para `/api/v1/courses/` por APIs específicas
- Testar todas as funcionalidades

### **FASE 3: REMOÇÃO SEGURA (1 dia)**

#### 3.1 Remover Arquivos Obsoletos
```bash
# Arquivos seguros para remoção
rm apps/courses/views.py
rm apps/courses/serializers.py  
rm apps/courses/urls_v1.py
rm apps/courses/urls_v2.py
```

#### 3.2 Atualizar imports
```python
# apps/courses/management/commands/test_performance.py
# ANTES:
from apps.courses.views import CourseListCreateView

# DEPOIS: 
from apps.courses.api.teacher.video_courses.views import CourseListCreateView
```

#### 3.3 Simplificar URLs principais
```python
# apps/courses/urls.py - Versão final limpa
from django.urls import path, include

app_name = 'courses'

urlpatterns = [
    # Redirecionar tudo para APIs organizadas
    path('', include([
        path('', lambda r: HttpResponsePermanentRedirect('/api/v1/teacher/video-courses/')),
    ])),
]
```

## ⚡ **EXECUÇÃO RÁPIDA (ALTERNATIVA)**

Se preferir uma migração mais direta:

### **Opção A: Remoção Imediata (30 minutos)**
```bash
# 1. Atualizar comando de teste
# 2. Remover arquivos duplicados
# 3. Simplificar URLs
# 4. Testar aplicação
```

### **Opção B: Manter Compatibilidade**
```python
# apps/courses/urls.py - Proxy para nova estrutura
from django.urls import path, include

urlpatterns = [
    # Proxy todos os requests para teacher API (por enquanto)
    path('', include('apps.courses.api.teacher.video_courses.urls')),
]
```

## 🧪 **TESTES DE VALIDAÇÃO**

### **Antes da Remoção:**
```bash
# 1. Verificar se aplicação inicia
python manage.py check

# 2. Executar migrações
python manage.py migrate --dry-run

# 3. Testar endpoints essenciais
curl /api/v1/teacher/video-courses/
curl /api/v1/student/video-courses/

# 4. Verificar admin funciona
python manage.py runserver
# Acessar /admin/
```

### **Após Remoção:**
```bash
# 1. Verificar imports
python manage.py check

# 2. Testar comando de performance  
python manage.py test_performance

# 3. Testar criação de curso
# POST /api/v1/teacher/video-courses/

# 4. Testar listagem de cursos
# GET /api/v1/student/video-courses/
```

## 📋 **CHECKLIST DE MIGRAÇÃO**

### **PREPARAÇÃO:**
- [ ] Backup do código atual
- [ ] Verificar se há clientes usando API antiga
- [ ] Documentar todos os endpoints afetados

### **EXECUÇÃO:**
- [ ] Atualizar `test_performance.py`
- [ ] Remover `views.py` antigo
- [ ] Remover `serializers.py` antigo
- [ ] Remover `urls_v1.py` e `urls_v2.py`
- [ ] Simplificar `urls.py` principal

### **VALIDAÇÃO:**
- [ ] Aplicação inicia sem erros
- [ ] Todos os testes passam
- [ ] APIs teacher e student funcionam
- [ ] Admin continua funcional
- [ ] Comandos de gestão funcionam

## 🚨 **RISCOS E MITIGAÇÕES**

### **RISCO BAIXO:**
- Código duplicado 100% - remoção é segura
- Apenas 1 dependência identificada
- Novos endpoints já funcionais

### **MITIGAÇÕES:**
- Backup antes da alteração
- Teste incremental
- Rollback plan preparado

### **ROLLBACK PLAN:**
```bash
# Em caso de problema, restaurar da branch:
git checkout HEAD~1 apps/courses/views.py
git checkout HEAD~1 apps/courses/serializers.py
git checkout HEAD~1 apps/courses/urls.py
```

## 🎯 **RESULTADO ESPERADO**

### **ANTES:**
- 📁 `apps/courses/` com 15+ arquivos
- 🔄 Código duplicado em múltiplos lugares
- 😵 Confusão entre APIs antigas e novas

### **DEPOIS:**
- 📁 `apps/courses/` organizado e limpo
- ✨ Apenas código novo organizado por roles
- 🎯 APIs claras: `/teacher/` e `/student/`
- 📉 Redução de ~50% no código duplicado

---

## ⚡ **EXECUÇÃO IMEDIATA RECOMENDADA**

Baseado na análise, a migração pode ser feita **HOJE** com risco mínimo:

1. **5 min**: Atualizar `test_performance.py`
2. **2 min**: Remover arquivos duplicados
3. **3 min**: Simplificar URLs
4. **5 min**: Testar aplicação

**Total: 15 minutos para código mais limpo e organizado!**