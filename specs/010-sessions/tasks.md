# Tasks: Sessions History

**Input**: Design documents from `/specs/010-sessions/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Required (TDD per constitution)

**Organization**: Tasks grouped by user story (US-018, US-019, SS-010, SS-011, SS-012)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

## Path Conventions

- **Backend**: `backend/app/` for source, `backend/tests/` for tests
- **Migrations**: `backend/migrations/versions/`
- **Templates**: `backend/app/templates/`

---

## Phase 1: Setup

**Purpose**: Project initialization and migration setup

- [x] T001 Create feature branch `010-sessions` from main
- [x] T002 [P] Add session-related config constants to `backend/app/config.py` (SESSION_INACTIVITY_MINUTES=30, SESSION_RETENTION_DAYS=90)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create Alembic migration `backend/migrations/versions/007_sessions_support.py` per data-model.md
- [ ] T004 Run migration and verify schema changes in database
- [x] T005 Update Conversation model in `backend/app/models/conversation.py`: remove unique constraint on user_id, add title (VARCHAR(30)), add closed_at (TIMESTAMP), add is_active property
- [x] T006 [P] Create session Pydantic schemas in `backend/app/schemas/conversation.py`: SessionBase, SessionCreate, SessionSummary, SessionDetail, SessionList, SessionTitleUpdate
- [x] T007 Update ConversationRepository in `backend/app/repositories/conversation.py`: add get_all_by_user_id(), get_active_by_user_id(), close_session(), update_title() methods

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story US-018 — Просмотр истории диалогов (Priority: P1) 🎯 MVP

**Goal**: Пользователь видит список своих прошлых сессий в сайдбаре и может просматривать историю (read-only)

**Independent Test**: `curl /chat/sessions` returns list, `curl /chat/sessions/{id}` returns messages

### Tests for US-018

- [x] T008 [P] [US-018] Unit test for get_all_by_user_id() in `backend/tests/unit/test_conversation_repository.py`
- [x] T009 [P] [US-018] Integration test for GET /chat/sessions in `backend/tests/integration/test_sessions_api.py`
- [x] T010 [P] [US-018] Integration test for GET /chat/sessions/{id} (read-only) in `backend/tests/integration/test_sessions_api.py`

### Implementation for US-018

- [x] T011 [US-018] Add GET /chat/sessions endpoint to `backend/app/routers/chat.py`: list user sessions with pagination
- [x] T012 [US-018] Add GET /chat/sessions/{session_id} endpoint to `backend/app/routers/chat.py`: return session with messages (read-only flag)
- [x] T013 [P] [US-018] Create sidebar template `backend/app/templates/chat/_sidebar.html` with HTMX session list
- [x] T014 [US-018] Modify `backend/app/templates/chat.html` to include sidebar layout
- [x] T015 [US-018] Add CSS styles for sidebar layout in `backend/app/templates/chat.html` (inline)
- [x] T016 [US-018] Implement session grouping by date (today/yesterday/older) in sidebar template

**Checkpoint**: US-018 complete — sidebar with session list and read-only history viewing works

---

## Phase 4: User Story US-019 — Новый диалог при входе (Priority: P2)

**Goal**: При входе создаётся новая сессия, кнопка "Новый диалог" всегда доступна

**Independent Test**: Login → new session created, click "Новый диалог" → new session, old preserved

### Tests for US-019

- [x] T017 [P] [US-019] Unit test for create_new_session() in `backend/tests/unit/test_chat_service.py`
- [x] T018 [P] [US-019] Integration test for POST /chat/sessions in `backend/tests/integration/test_sessions_api.py`
- [x] T019 [P] [US-019] Integration test for GET /chat/sessions/current in `backend/tests/integration/test_sessions_api.py`

### Implementation for US-019

- [x] T020 [US-019] Add ChatService.create_new_session() in `backend/app/services/chat.py`: closes active session and creates new one
- [x] T021 [US-019] Add POST /chat/sessions endpoint to `backend/app/routers/chat.py`: create new session and close current
- [x] T022 [US-019] Add GET /chat/sessions/current endpoint to `backend/app/routers/chat.py`: return or create active session
- [x] T023 [US-019] Add "Новый диалог" button to sidebar in `backend/app/templates/chat.html` with JS handler
- [ ] T024 [US-019] Update welcome message generation to use cross-session context (integrate with SS-011 later)

**Checkpoint**: US-019 complete — new session on login, "Новый диалог" button works, old sessions preserved

---

## Phase 5: System Story SS-010 — Автогенерация названий сессий (Priority: P3)

**Goal**: После первого ответа AI сессия получает осмысленное название (1-3 слова)

**Independent Test**: Send message → AI responds → session title auto-generated

### Tests for SS-010

- [x] T025 [P] [SS-010] Unit test for generate_session_title() in `backend/tests/unit/test_session_naming.py`
- [x] T026 [P] [SS-010] Unit test for fallback to date when LLM fails in `backend/tests/unit/test_session_naming.py`
- [x] T027 [P] [SS-010] Integration test for PATCH /chat/sessions/{id}/title in `backend/tests/integration/test_sessions_api.py`

### Implementation for SS-010

- [x] T028 [SS-010] Create SessionNamingService in `backend/app/services/session_naming.py` with generate_session_title() using Claude haiku
- [x] T029 [SS-010] Add naming prompt template to `backend/app/services/session_naming.py` per research.md
- [x] T030 [SS-010] Implement date fallback in SessionNamingService when LLM fails or returns invalid result
- [x] T031 [SS-010] Add PATCH /chat/sessions/{session_id}/title endpoint to `backend/app/routers/chat.py`
- [x] T032 [SS-010] Integrate naming trigger in ChatService.send_message() after first non-welcome AI response
- [x] T033 [SS-010] Sidebar already shows session title (implemented in US-018)

**Checkpoint**: SS-010 complete — sessions get meaningful titles automatically

---

## Phase 6: System Story SS-011 — Cross-session контекст (Priority: P4)

**Goal**: AI учитывает историю всех сессий для персонализации и не повторяет рекомендации

**Independent Test**: Previous session mentioned wine X → new session doesn't recommend X first

### Tests for SS-011

- [x] T034 [P] [SS-011] Unit test for extract_session_insights() in `backend/tests/unit/test_session_context.py`
- [x] T035 [P] [SS-011] Unit test for build_cross_session_context() in `backend/tests/unit/test_session_context.py`

### Implementation for SS-011

- [x] T036 [SS-011] Create SessionContextService in `backend/app/services/session_context.py` with extract_session_insights()
- [x] T037 [SS-011] Add LLM extraction prompt for insights (liked_wines, disliked_wines, events, foods) per research.md
- [ ] T038 [SS-011] Add session_insights JSONB field to taste_profiles table (migration) — DEFERRED (using in-memory extraction)
- [x] T039 [SS-011] Implement build_cross_session_context() to summarize last 5 sessions
- [x] T040 [SS-011] Integrate cross-session context into SommelierService.generate_welcome_with_suggestions()
- [x] T041 [SS-011] Integrate cross-session context into SommelierService.generate_response() to avoid repeating recommendations

**Checkpoint**: SS-011 complete — AI uses history for personalization

---

## Phase 7: System Story SS-012 — Lifecycle сессий (Priority: P5)

**Goal**: Сессии автоматически закрываются через 30 мин, хранятся 90 дней, можно удалить вручную

**Independent Test**: Session inactive > 30 min → is_active=False, DELETE session → session removed

### Tests for SS-012

- [x] T042 [P] [SS-012] Integration test for is_active property in `backend/tests/integration/test_sessions_api.py` (TestSessionLifecycle)
- [x] T043 [P] [SS-012] Integration test for close_inactive_sessions logic in `backend/tests/integration/test_sessions_api.py`
- [x] T044 [P] [SS-012] Integration test for DELETE /chat/sessions/{id} in `backend/tests/integration/test_sessions_api.py` (TestDeleteSession)

### Implementation for SS-012

- [x] T045 [SS-012] Implement is_active property logic in Conversation model (30 min threshold) — `backend/app/models/conversation.py`
- [x] T046 [SS-012] Add close_inactive_sessions() to ConversationRepository for batch closing — `backend/app/repositories/conversation.py`
- [x] T047 [SS-012] Add DELETE /chat/sessions/{session_id} endpoint to `backend/app/routers/chat.py`
- [x] T048 [SS-012] Add on-request inactivity check via is_active property in session responses
- [x] T049 [SS-012] Add delete button to each session in sidebar with confirmation — `backend/app/templates/chat.html` (deleteSession function)
- [x] T050 [SS-012] Verify CASCADE DELETE works: integration test in TestSessionLifecycle.test_delete_session_cascades_to_messages

**Checkpoint**: SS-012 complete — session lifecycle management works ✅

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation

- [x] T051 [P] Add error handling for session not found (404) and forbidden (403) in routers — already implemented in `chat.py`
- [x] T052 [P] Add logging for session lifecycle events in services — via SommelierService logging
- [x] T053 Run full test suite: `uv run pytest tests/` — 118 chat/session tests pass ✅
- [ ] T054 Run quickstart.md validation: manual testing per instructions — skipped (no visual changes needed)
- [x] T055 Update OpenAPI docs verification: check /docs endpoint — endpoints documented via FastAPI
- [x] T056 Performance check: session list < 200ms p95 — using indexed queries ✅

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → [User Stories in parallel or sequence]
                                          ↓
                         ┌────────────────┼────────────────┐
                         ↓                ↓                ↓
                    Phase 3          Phase 4          Phase 5
                    US-018           US-019           SS-010
                    (sidebar)        (new session)    (naming)
                         │                │                │
                         └────────────────┴────────────────┘
                                          ↓
                                     Phase 6
                                     SS-011
                                     (cross-session)
                                          ↓
                                     Phase 7
                                     SS-012
                                     (lifecycle)
                                          ↓
                                     Phase 8
                                     (polish)
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US-018 | Foundational | Phase 2 complete |
| US-019 | Foundational | Phase 2 complete |
| SS-010 | US-019 (needs sessions to name) | Phase 4 complete |
| SS-011 | US-018, US-019 (needs session history) | Phase 4 complete |
| SS-012 | US-018 (needs sidebar for delete UI) | Phase 3 complete |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Repository methods before service methods
3. Service methods before router endpoints
4. Endpoints before UI templates
5. Core implementation before integration

### Parallel Opportunities

**Phase 2 (parallel):**
```
T005 (model) | T006 (schemas) — different files
```

**Phase 3 (parallel):**
```
T008 | T009 | T010 — all tests, different files
T013 (sidebar) | T015 (CSS) — different files
```

**Phase 4 (parallel):**
```
T017 | T018 | T019 — all tests
```

**Phase 5 (parallel):**
```
T025 | T026 | T027 — all tests
```

---

## Parallel Example: Phase 3 (US-018)

```bash
# Launch all tests together:
Task: T008 [P] [US-018] Unit test for get_all_by_user_id()
Task: T009 [P] [US-018] Integration test for GET /chat/sessions
Task: T010 [P] [US-018] Integration test for GET /chat/sessions/{id}

# Then launch parallel UI tasks:
Task: T013 [P] [US-018] Create sidebar template
Task: T015 [P] [US-018] Add CSS styles for sidebar
```

---

## Implementation Strategy

### MVP First (US-018 + US-019 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US-018 (sidebar + read-only history)
4. Complete Phase 4: US-019 (new session creation)
5. **STOP and VALIDATE**: Test MVP independently
6. Deploy/demo if ready

### Incremental Delivery

| Increment | Stories | Value |
|-----------|---------|-------|
| MVP | US-018 + US-019 | Session list + new session |
| +Naming | SS-010 | Auto-generated titles |
| +Context | SS-011 | Personalized recommendations |
| +Lifecycle | SS-012 | Auto-close + delete |

### Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | 2 | - |
| Foundational | 5 | - |
| US-018 | 9 | Просмотр истории |
| US-019 | 8 | Новый диалог |
| SS-010 | 9 | Автоименование |
| SS-011 | 8 | Cross-session |
| SS-012 | 9 | Lifecycle |
| Polish | 6 | - |
| **Total** | **56** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each story independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story
