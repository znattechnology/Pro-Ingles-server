# Deprecated Code Archive - Practice App

## Archive Date: 2026-02-03

### Files Archived

#### `_views_archived_20260203.py` (5852 lines)

**Previously:** `_views_deprecated.py`

**Contents:**
- Legacy views from the original practice app implementation
- Speaking and Listening exercise views (models removed in migration 0008)
- Older implementations of pronunciation analysis, translation validation
- Various unused/duplicate endpoints

**Migration Status:**
All active functionality has been migrated to:
- `apps/practice/views_ai.py` - AI-powered endpoints (pronunciation, translation)
- `apps/practice/vapi_views.py` - Vapi conversation integration
- `apps/courses/api/student/practice_courses/views.py` - Student practice endpoints
- `apps/courses/api/teacher/practice_courses/views.py` - Teacher practice endpoints

**Key Migrations Completed:**
1. `AIPronunciationAnalysisView` -> `views_ai.py` (POST /api/v1/practice/analyze-ai-pronunciation/)
2. `AITranslationValidationView` -> `views_ai.py` (already migrated)
3. `GeneratePronunciationExerciseView` -> `views_ai.py` (already migrated)
4. `GenerateReferenceAudioView` -> `views_ai.py` (already migrated)

**Removal Schedule:**
- Archive retained until: 2026-02-17 (2 weeks)
- Safe to delete after verification that production is stable

---

### Serializers Removed (2026-02-03)

**File:** `apps/practice/serializers.py`

**Lines Removed:** 619-1202 (~580 lines)

**Removed Serializers:**
- `SpeakingExerciseSerializer`
- `SpeakingTurnSerializer`
- `SpeakingSessionSerializer`
- `SpeakingProgressSerializer`
- `ListeningExerciseSerializer`
- `ListeningAttemptSerializer`
- `ListeningSessionSerializer`
- `ListeningProgressSerializer`
- `AudioSegmentSerializer`
- Related nested serializers

**Reason:** These serializers referenced models removed in migration 0008 (SpeakingExercise, ListeningExercise, etc.)

---

### Services Created (2026-02-03)

**File:** `apps/practice/services/text_validation.py`

**Class:** `TextValidationService`

**Purpose:** Unified text validation with 85% typo tolerance across all challenge types (FILL_BLANK, TRANSLATION, etc.)

**Used By:**
- `ValidateTextAnswerView` in `apps/courses/api/student/practice_courses/views.py`
- `ChallengeProgressView` in `apps/courses/api/student/practice_courses/views.py`
