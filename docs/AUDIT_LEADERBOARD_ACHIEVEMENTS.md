# Auditoria Técnica: Leaderboard & Achievements

**Data:** 2026-02-20
**Auditor:** Claude Opus 4.5
**Escopo:** Sistema de Gamificação (Leaderboard, Achievements, Points)

---

## 1. Mapa Arquitetural

### 1.1 Fluxo de Pontos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FONTES DE PONTOS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Challenge Correto ──┬──> ChallengeProgressView.post()                      │
│  (SELECT, FILL_BLANK,│    └── user_progress.add_points(10)                  │
│   TRANSLATION, etc.) │                                                       │
│                      │                                                       │
│  Practice Mode ──────┤    └── add_points(10) + add_hearts(1)                │
│  (repetição)         │                                                       │
│                      │                                                       │
│  Achievement ────────┴──> UserAchievement.update_progress()                 │
│  Desbloqueado             └── user_progress.add_points(achievement.points)  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UserProgress.add_points()                            │
│                         apps/practice/models.py:327                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  @transaction.atomic                                                         │
│  def add_points(self, amount=10, check_achievements=True):                  │
│      UserProgress.objects.filter(pk=self.pk).update(                        │
│          points=F('points') + amount   # Atomic F() expression              │
│      )                                                                       │
│      self.refresh_from_db()                                                  │
│      if check_achievements:                                                  │
│          self._check_achievements_for_points()                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    check_achievement_progress()                              │
│                    apps/practice/achievement_utils.py                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Para cada Achievement com requirement_type='points_earned':                │
│    - Criar/Atualizar UserAchievement                                        │
│    - Se target atingido: unlock + AchievementNotification                   │
│    - Pontos do achievement adicionados (sem recursão)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Fluxo de Ranking

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LEADERBOARD QUERY                                   │
│                    GET /practice/leaderboard/global/                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Query Principal:                                                         │
│     UserProgress.objects.select_related('user').order_by('-points')[:50]    │
│                                                                              │
│  2. Para cada user (N+1 PROBLEMA):                                          │
│     └── UserLeague.objects.get_or_create(user=user)                         │
│     └── UserStreak.objects.get_or_create(user=user)                         │
│                                                                              │
│  3. Retorna top 10 + currentUser separado                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SISTEMA DE LIGAS                                     │
│                    UserLeague.get_league_for_points()                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  points >= 3000  ─────> Diamond 💎                                          │
│  points >= 2000  ─────> Gold 🥇                                             │
│  points >= 1000  ─────> Silver 🥈                                           │
│  points < 1000   ─────> Bronze 🥉                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Fluxo de Achievements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRIGGERS DE ACHIEVEMENTS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trigger                    │ Modelo/Método          │ Achievement Type     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Pontos ganhos              │ UserProgress.add_points│ 'points_earned'      │
│  Challenge completado       │ ChallengeProgress.save │ 'challenges_completed│
│  Lição completada           │ ChallengeProgress.save │ 'lessons_completed'  │
│  Streak atualizado          │ UserStreak.update_streak│ 'streak_days'       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      check_achievement_progress()                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Busca todos os Achievement com requirement_type=X e is_active=True      │
│  2. Para cada um:                                                            │
│     - get_or_create UserAchievement(user, achievement)                      │
│     - Se !is_unlocked && current >= target:                                 │
│       - is_unlocked = True                                                  │
│       - unlocked_at = now()                                                 │
│       - add_points(achievement.points, check_achievements=False)            │
│       - Criar AchievementNotification                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Modelos Envolvidos

| Modelo | Localização | Propósito |
|--------|-------------|-----------|
| `UserProgress` | `apps/practice/models.py:201` | Pontos totais, corações, curso ativo |
| `Achievement` | `apps/practice/models.py:709` | Definição de conquistas |
| `UserAchievement` | `apps/practice/models.py:781` | Progresso do usuário em conquistas |
| `AchievementCategory` | `apps/practice/models.py:850` | Categorias de conquistas |
| `AchievementNotification` | `apps/practice/models.py:875` | Notificações de unlock |
| `UserLeague` | `apps/practice/models.py:424` | Liga atual do usuário |
| `LeaderboardSnapshot` | `apps/practice/models.py:616` | Histórico de rankings |
| `UserStreak` | `apps/practice/models.py:546` | Sequência de dias |
| `Competition` | `apps/practice/models.py:579` | Competições temporárias |
| `CompetitionParticipant` | `apps/practice/models.py:598` | Participação em competições |

---

## 2. Bugs Encontrados

### 🔴 CRÍTICO

| ID | Bug | Impacto | Localização |
|----|-----|---------|-------------|
| BUG-01 | `test_leaderboard_data` é público | Vazamento de PII (nome, email, avatar) de todos os usuários | `views.py:2201` |
| BUG-02 | `test_achievements_data` é público | Vazamento de dados + escrita no DB em GET anônimo | `views.py:2533` |
| BUG-03 | VAPI/SPEAKING aceita score do cliente | Usuário pode injetar score=100 e ganhar pontos sem falar | `views.py:864, 894` |

### 🟠 ALTO

| ID | Bug | Impacto | Localização |
|----|-----|---------|-------------|
| BUG-04 | `LeaderboardSnapshotCreateView` sem check de admin | Qualquer user pode criar snapshots | `views.py:2130` |
| BUG-05 | `ValidateTextAnswerView` sem `@transaction.atomic` | Race condition para pontos duplicados | `views.py:1081` |
| BUG-06 | `get_student_progress_list` expõe todos os users | PII de todos os usuários para qualquer autenticado | `views.py:1829` |
| BUG-07 | `vapi_simulate` sem auth | Qualquer um pode triggerar chamadas AI pagas | `vapi_views.py:446` |
| BUG-08 | Content CRUD sem role check | Estudantes podem criar/editar challenges | `views.py:1566-1777` |

### 🟡 MÉDIO

| ID | Bug | Impacto | Localização |
|----|-----|---------|-------------|
| BUG-09 | Practice mode dá pontos infinitos | 60 req/min × 10 pts = 3600 pts/hora | `views.py:961` |
| BUG-10 | rank_change sempre "same" | TODO não implementado | `views.py:1975` |
| BUG-11 | N+1 queries no leaderboard | 150 queries por request | `views.py:1920-1950` |
| BUG-12 | Achievement models não no Admin | Impossível gerenciar via Django Admin | `admin.py` |

---

## 3. Vulnerabilidades de Segurança

### 🔴 CRÍTICAS

#### VULN-01: Score Injection (VAPI/SPEAKING)
```python
# views.py:864 - Cliente envia score diretamente
vapi_score = request.data.get('vapi_score')
is_correct = float(vapi_score) >= 60.0  # Atacante envia 100, passa sempre
```
**Exploit:** `POST /challenge/ {"challenge_id": "X", "vapi_score": 100}`

#### VULN-02: Endpoints de Teste Públicos
```python
# views.py:2201 - Sem autenticação
@permission_classes([])  # Qualquer um acessa
def test_leaderboard_data(request):
    # Retorna nome, avatar, pontos, email de todos
```

### 🟠 ALTAS

#### VULN-03: Privilege Escalation via Content CRUD
```python
# views.py:1728 - Estudante pode modificar is_correct
class ChallengeOptionUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]  # Sem IsTeacher!
```
**Exploit:** Estudante marca sua própria resposta como correta.

#### VULN-04: Webhook Secret Opcional
```python
# vapi_views.py:558 - Se não configurado, aceita tudo
if webhook_secret:
    # valida
# else: aceita qualquer request
```

### 🟡 MÉDIAS

#### VULN-05: Race Condition em Achievements
```python
# Duas chamadas simultâneas a add_points() podem causar:
# - Double unlock de achievements
# - Notificações duplicadas
# UserAchievement.update_progress() não usa select_for_update()
```

---

## 4. Inconsistências

### Frontend vs Backend

| Item | Frontend | Backend | Status |
|------|----------|---------|--------|
| Teacher Achievements API | Hooks mockados | Views arquivadas | ❌ Não funcional |
| Achievement CRUD | UI completa | Sem endpoints vivos | ❌ Não funcional |
| Rank Change | Exibe up/down/same | Retorna sempre "same" | ⚠️ Parcial |
| Leaderboard Cache | Assume cache | Sem cache | ⚠️ Performance |

### Cursos vs Laboratório

| Métrica | Video Courses | Practice Lab | Fonte de Verdade |
|---------|---------------|--------------|-------------------|
| Pontos | Não dá pontos | +10 por challenge | `UserProgress.points` |
| Achievements | Não triggera | Triggera | `achievement_utils.py` |
| Progresso | `CourseProgress` | `ChallengeProgress` | Separados |

### Pontuação vs Conquistas

| Cenário | Comportamento | Correto? |
|---------|---------------|----------|
| Achievement dá pontos | Sim, `achievement.points` | ✅ |
| Pontos triggeram achievement | Sim, `points_earned` type | ✅ |
| Loop infinito possível? | Não, `check_achievements=False` | ✅ |
| Pontos duplicados possíveis? | Sim, via race condition | ❌ |

---

## 5. Análise de Performance

### Leaderboard - N+1 Query Problem

```python
# Código atual (views.py:1920-1950)
users_with_progress = UserProgress.objects.select_related('user').order_by('-points')[:50]

for user_progress in users_with_progress:
    # 2 queries POR usuário!
    user_league, _ = UserLeague.objects.get_or_create(user=user_progress.user)
    user_streak, _ = UserStreak.objects.get_or_create(user=user_progress.user)
```

**Queries por request:** 1 (principal) + 50×2 (league+streak) = **101 queries**

### Solução Recomendada

```python
# Otimizado com prefetch
users_with_progress = UserProgress.objects.select_related(
    'user'
).prefetch_related(
    Prefetch('user__user_league'),
    Prefetch('user__user_streak'),
).order_by('-points')[:50]
```

### Escalabilidade

| Usuários | Queries Atuais | Com Cache (5min) | Com Prefetch |
|----------|----------------|------------------|--------------|
| 1,000 | 101/request | 101/5min | 3/request |
| 10,000 | 101/request | 101/5min | 3/request |
| 100,000 | 101/request | 101/5min | 3/request |

---

## 6. Gestão Admin/Teacher

### Estado Atual

| Funcionalidade | API Existe? | Permissões | URL Ativa? |
|----------------|-------------|------------|------------|
| Criar Achievement | Sim (arquivada) | `IsTeacher` | ❌ Não |
| Editar Achievement | Sim (arquivada) | `IsTeacher` | ❌ Não |
| Deletar Achievement | Sim (arquivada) | `IsTeacher` | ❌ Não |
| Toggle Achievement | Sim (arquivada) | `IsAuthenticated` ⚠️ | ❌ Não |
| Bulk Update | Sim (arquivada) | `IsAuthenticated` ⚠️ | ❌ Não |
| Reset Rankings | ❌ Não existe | - | - |
| Ajustar Pontos | Só Django Admin | `is_superuser` | ✅ Sim |
| Criar Competition | Sim (arquivada) | `IsTeacher` | ❌ Não |

### Django Admin - Modelos Não Registrados

```python
# apps/practice/admin.py - FALTAM:
# - Achievement
# - UserAchievement
# - AchievementCategory
# - AchievementNotification
# - UserLeague
# - LeaguePromotion
# - Competition
# - CompetitionParticipant
# - LeaderboardSnapshot
# - UserStreak
```

---

## 7. Recomendações

### 🔴 P0 — Correção Imediata (24h)

| # | Ação | Arquivo | Esforço |
|---|------|---------|---------|
| 1 | Remover `test_leaderboard_data` e `test_achievements_data` | `views.py` | 5 min |
| 2 | Mover validação de VAPI/SPEAKING score para server-side | `views.py:864, 894` | 2h |
| 3 | Adicionar `IsAdminUser` em `LeaderboardSnapshotCreateView` | `views.py:2130` | 5 min |
| 4 | Adicionar `is_staff` check em `get_student_progress_list` | `views.py:1829` | 5 min |

### 🟠 P1 — Melhorias Críticas (1 semana)

| # | Ação | Arquivo | Esforço |
|---|------|---------|---------|
| 5 | Adicionar `@transaction.atomic` em `ValidateTextAnswerView` | `views.py:1081` | 10 min |
| 6 | Adicionar `IsTeacher` em todos os Content CRUD views | `views.py:1566-1777` | 30 min |
| 7 | Proteger `vapi_simulate` e `vapi_templates` | `vapi_views.py` | 30 min |
| 8 | Tornar `VAPI_WEBHOOK_SECRET` obrigatório | `vapi_views.py:558` | 15 min |
| 9 | Adicionar cache no leaderboard (5 min TTL) | `views.py:1907` | 1h |
| 10 | Registrar modelos de gamificação no Admin | `admin.py` | 30 min |

### 🟡 P2 — Refactor Arquitetural (2-4 semanas)

| # | Ação | Descrição | Esforço |
|---|------|-----------|---------|
| 11 | Reativar Teacher Achievement APIs | Mover de `_views_archived` para `views.py`, configurar URLs | 4h |
| 12 | Corrigir N+1 queries | Usar `prefetch_related` para UserLeague e UserStreak | 2h |
| 13 | Implementar rank_change | Usar `LeaderboardSnapshot` para calcular mudanças | 4h |
| 14 | Limitar pontos de practice mode | Máximo diário ou só primeira vez | 2h |
| 15 | Adicionar `select_for_update` em achievement unlock | Prevenir race conditions | 2h |
| 16 | Criar endpoint de reset de rankings | Para admins | 2h |
| 17 | Unificar serializers duplicados | Mover para arquivo único | 2h |

---

## 8. Resposta às Perguntas Finais

### O sistema de ranking e conquistas é justo, consistente, auditável e resistente a manipulação?

| Critério | Status | Nota |
|----------|--------|------|
| **Justo** | ⚠️ Parcial | Score injection permite fraude |
| **Consistente** | ⚠️ Parcial | Race conditions possíveis |
| **Auditável** | ⚠️ Parcial | LeaderboardSnapshot existe mas rank_change não implementado |
| **Resistente a Manipulação** | ❌ Não | Múltiplos vetores de ataque |

### Se 10.000 usuários começarem a competir, o sistema se mantém íntegro?

| Aspecto | Status | Problema |
|---------|--------|----------|
| **Performance** | ❌ | N+1 queries = 101 queries/request |
| **Concorrência** | ⚠️ | Race conditions em achievements |
| **Fraude** | ❌ | Score injection, practice mode farming |
| **Cache** | ❌ | Nenhum cache implementado |

**Conclusão:** O sistema **NÃO** está pronto para competição em escala. As vulnerabilidades P0 devem ser corrigidas **antes** de qualquer evento competitivo.

---

## 9. Arquivos Auditados

```
Backend:
├── apps/practice/
│   ├── models.py (Achievement, UserAchievement, UserProgress, UserLeague, etc.)
│   ├── admin.py (registros incompletos)
│   ├── achievement_utils.py (check_achievement_progress)
│   ├── serializers.py (duplicados em 4 arquivos)
│   ├── vapi_views.py (vulnerabilidades de auth)
│   ├── throttling.py (throttles definidos mas não aplicados)
│   └── _views_archived_20260203.py (teacher APIs arquivadas)
├── apps/courses/api/student/practice_courses/
│   ├── views.py (endpoints principais)
│   ├── serializers.py
│   └── urls.py
└── apps/subscriptions/
    └── models.py (hearts unificado)

Frontend:
├── app/(dashboard)/user/laboratory/
│   ├── leaderboard/page.tsx
│   └── achievements/page.tsx
├── app/(dashboard)/teacher/laboratory/
│   ├── leaderboard/page.tsx
│   └── achievements/page.tsx (APIs mockadas)
└── src/domains/student/
    ├── leaderboard/api/studentLeaderboardApiSlice.ts
    └── achievements/api/studentAchievementsApiSlice.ts
```

---

**Fim do Relatório de Auditoria**
