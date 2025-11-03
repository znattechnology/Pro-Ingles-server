# 🏗️ Diagnóstico de Arquitetura Django - Tuwi Backend

**Data:** 19 de Outubro de 2025  
**Analista:** Engenheiro Sênior Django  
**Foco:** Análise da arquitetura e dependências do app `practice`

---

## 📋 Resumo Executivo

A aplicação Tuwi Backend é uma plataforma Django 4.2.24 para ensino de inglês que passou por uma **transição arquitetural significativa**. O app `practice` foi movido para dentro da estrutura `apps/courses/api/` mantendo a **mesma base de models** mas reorganizando as APIs por roles (student/teacher).

### 🔴 **PROBLEMA CRÍTICO IDENTIFICADO:**
O app `practice` foi removido fisicamente mas suas **dependências de models e migrações permanecem ativas** no app `courses`, criando um estado inconsistente que impede a execução de testes e migrações.

---

## 🗂️ Estrutura de Apps Atual

```
apps/
├── core/           # Modelos base, health checks
├── users/          # Autenticação, JWT, roles (student/teacher)
├── courses/        # HÍBRIDO: video + practice courses
│   ├── models/     # Compartilhados entre video E practice
│   └── api/
│       ├── student/
│       │   ├── video_courses/    # 823 linhas
│       │   └── practice_courses/ # 3792 linhas (!!!)
│       └── teacher/
│           ├── video_courses/
│           └── practice_courses/
├── subscriptions/  # Planos, limites de uso
├── cms/           # Conteúdo dinâmico
└── practice/      # ❌ REMOVIDO mas dependências ativas
```

---

## 🔗 Análise de Dependências Practice

### 1. **Models com Foreign Keys para Practice**

#### apps/courses/models/core.py:
```python
# LINHA 280-285 - Chapter model
practice_lesson = models.ForeignKey(
    'practice.PracticeLesson',
    null=True, blank=True,
    on_delete=models.SET_NULL,
    help_text="Connected Practice Lab lesson for gamified quizzes"
)
```

#### apps/courses/models/quizzes.py:
```python
# LINHA 39-43 - ChapterQuiz model
practice_lesson = models.ForeignKey(
    'practice.PracticeLesson',
    on_delete=models.CASCADE,
    help_text="Connected Practice Lab lesson"
)

# LINHA 270-275 - StudentQuizAttempt model
practice_progress = models.ForeignKey(
    'practice.ChallengeProgress',
    null=True, blank=True,
    on_delete=models.SET_NULL,
    help_text="Related Practice Lab challenge progress"
)
```

### 2. **Migrações com Dependências Practice**

**MIGRAÇÃO CRÍTICA:** `0004_chapter_practice_lesson_chapter_quiz_enabled_and_more.py`
```python
dependencies = [
    ('practice', '0004_achievement_achievementcategory_userachievement_and_more'),
    # ⬆️ Esta dependência quebra o sistema quando practice app é removido
]
```

**Outras migrações afetadas:**
- `0005_add_performance_indexes.py`
- `0007_course_course_type.py` 
- `0008_usercourseprogress_avg_listening_score_and_more.py`
- `0010_add_quiz_data_practice_selection.py`
- `0011_alter_course_template.py`

### 3. **Views Importando Practice Models**

```python
# apps/courses/api/student/practice_courses/views.py (3792 linhas!)
from apps.practice.models import (
    PracticeUnit, PracticeLesson, PracticeChallenge,
    UserProgress, ChallengeProgress, UserLeague,
    Achievement, SpeakingExercise, ListeningExercise
    # ... mais 20+ models
)
```

---

## 🏛️ Padrões Arquiteturais Identificados

### ✅ **Pontos Fortes:**

1. **Separation of Concerns por Role:**
   ```
   /api/v1/student/video-courses/    # Consumo de conteúdo
   /api/v1/teacher/video-courses/    # Gestão de conteúdo
   ```

2. **Models Modulares:**
   ```python
   courses/models/
   ├── core.py        # Course, Section, Chapter
   ├── enrollment.py  # Progress tracking
   ├── quizzes.py     # Assessments
   └── resources.py   # Materials
   ```

3. **Factory Pattern para Testes:**
   ```python
   tests/factories/
   ├── user_factories.py
   ├── course_factories.py
   └── practice_factories.py
   ```

### 🔴 **Problemas Críticos:**

1. **Single Responsibility Violation:**
   - App `courses` gerencia TANTO video courses QUANTO practice courses
   - Models híbridos servem dois contextos diferentes

2. **Dependency Hell:**
   - Models em `courses` dependem de models em `practice` (removido)
   - Migrações em deadlock

3. **Code Duplication:**
   - Practice functionality duplicada entre `apps/practice/` e `apps/courses/api/student/practice_courses/`

---

## 📊 Análise Quantitativa

| Métrica | Video Courses | Practice Courses | Razão |
|---------|---------------|------------------|-------|
| **Linhas de código (views)** | 823 | 3792 | 4.6x |
| **Complexidade API** | Simples | Alta | 4.6x |
| **Models específicos** | 3-4 | 20+ | 5x+ |
| **Endpoints** | ~15 | ~50+ | 3x+ |

**CONCLUSÃO:** Practice courses são **significativamente mais complexos** que video courses.

---

## 🎯 Tipos de Course Identificados

### 1. **Video Courses (`course_type='video'`)**
- **Foco:** Consumo de vídeo aulas
- **Estrutura:** Course → Section → Chapter (Video)
- **Features:** Player, progresso, quizzes simples

### 2. **Practice Courses (`course_type='practice'`)**
- **Foco:** Gamificação estilo Duolingo
- **Estrutura:** Course → PracticeUnit → PracticeLesson → Challenge
- **Features:** XP, hearts, streaks, leaderboards, AI speaking/listening

---

## 🚨 Impacto no Sistema de Testes

### **Estado Atual:**
```bash
$ pytest apps/courses/api/tests/
# ERROR: NodeNotFoundError: Migration courses.0004_chapter_practice_lesson 
# dependencies reference nonexistent parent node ('practice', '0004_...')
```

### **Causas:**
1. **App `practice` removido** do `INSTALLED_APPS`
2. **Migrações dependentes** ainda existem
3. **Models com ForeignKeys** para practice
4. **Imports diretos** para practice views

---

## 🔧 Estratégias de Resolução

### **Opção A: Restauração Temporária (Recomendada para testes)**
```python
# settings.py
LOCAL_APPS = [
    'apps.courses',
    'apps.practice',  # Restaurar temporariamente
]
```
**Prós:** Permite executar testes imediatamente  
**Contras:** Não resolve o problema arquitetural

### **Opção B: Migração Completa (Solução definitiva)**
1. **Mover models practice** para `apps.courses.models.practice`
2. **Criar migrações de transição** 
3. **Atualizar todas as referências**
4. **Remover app practice** definitivamente

### **Opção C: Separação Definitiva**
1. **Manter practice como app independente**
2. **Remover dependências cruzadas**
3. **APIs separadas** mas models independentes

---

## 📈 Recomendações Imediatas

### **🔥 Prioridade ALTA (24h):**
1. **Restaurar app practice temporariamente** para destravar testes
2. **Executar suite de testes completa** para mapear funcionalidades
3. **Documentar dependências reais** vs. desnecessárias

### **📋 Prioridade MÉDIA (1 semana):**
1. **Definir estratégia arquitetural definitiva**
2. **Criar plano de migração detalhado**
3. **Implementar testes end-to-end** para validar funcionalidades

### **🎯 Prioridade BAIXA (1 mês):**
1. **Refatorar arquitetura escolhida**
2. **Otimizar performance** dos endpoints practice
3. **Implementar monitoring** de funcionalidades críticas

---

## 🎯 Conclusões Técnicas

### **Estado Atual:**
❌ **Sistema em estado inconsistente**  
❌ **Testes não executam**  
❌ **Dependências circulares**  
✅ **Funcionalidades core preservadas**  

### **Próximos Passos:**
1. **IMEDIATO:** Restaurar practice app para testes
2. **CURTO PRAZO:** Definir arquitetura target  
3. **MÉDIO PRAZO:** Migração controlada
4. **LONGO PRAZO:** Otimização e monitoramento

---

**📝 Nota do Analista:**  
*A aplicação demonstra boa arquitetura Django em muitos aspectos, mas a transição do app practice foi interrompida em estado intermediário. A prioridade deve ser estabilizar o ambiente de testes antes de prosseguir com refatorações.*