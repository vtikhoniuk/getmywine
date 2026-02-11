# Tasks: Мониторинг LLM через Langfuse

**Input**: Design documents from `/specs/017-langfuse-monitoring/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Нет автоматических тестов — это инфраструктурная/observability фича. Проверяется ручным smoke-тестом и верификацией существующих тестов.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, configuration, and env vars shared across all user stories

- [x] T001 [P] Add `langfuse` dependency to `backend/requirements.txt`
- [x] T002 [P] Add Langfuse settings (LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST, LANGFUSE_TRACING_ENABLED) to `backend/app/config.py`
- [x] T003 [P] Add Langfuse configuration section to `.env.example` with dev defaults

---

## Phase 2: User Story 3 — Langfuse как часть инфраструктуры (Priority: P1) 🎯 MVP

**Goal**: `docker compose up` запускает Langfuse со всей инфраструктурой без ручной настройки

**Independent Test**: Выполнить `docker compose up -d`, дождаться старта всех контейнеров, открыть http://localhost:3000 и убедиться, что Langfuse UI загружается

**⚠️ CRITICAL**: Без работающей инфраструктуры Langfuse невозможны US1, US2, US4

### Implementation for User Story 3

- [x] T004 [US3] Add 6 Langfuse service definitions (langfuse-web, langfuse-worker, langfuse-postgres, langfuse-clickhouse, langfuse-redis, langfuse-minio) with healthchecks to `docker-compose.yml`
- [x] T005 [US3] Add 4 Langfuse persistent volumes (langfuse_postgres_data, langfuse_clickhouse_data, langfuse_clickhouse_logs, langfuse_minio_data) to `docker-compose.yml`
- [x] T006 [US3] Configure auto-provisioning env vars (LANGFUSE_INIT_ORG_*, LANGFUSE_INIT_PROJECT_*, LANGFUSE_INIT_USER_*) with dev defaults in `docker-compose.yml`
- [x] T007 [US3] Add LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST env vars to backend and telegram-bot service environments in `docker-compose.yml`
- [ ] T008 [US3] Verify: `docker compose up -d` starts all 9 containers, Langfuse UI accessible at http://localhost:3000, auto-provisioned project exists

**Checkpoint**: Langfuse UI загружается, проект создан автоматически, можно войти с предзаданными credentials

---

## Phase 3: User Story 1 — Трейсинг LLM-запросов (Priority: P1)

**Goal**: Каждый запрос пользователя создаёт трейс в Langfuse с полной иерархией spans: LLM call → tool calls → response

**Independent Test**: Отправить сообщение Telegram-боту, открыть Langfuse UI → Traces, найти трейс и проверить наличие spans (LLM generation, tool execution)

### Implementation for User Story 1

- [x] T009 [US1] Replace `openai.AsyncOpenAI` import with `langfuse.openai.AsyncOpenAI` in `OpenRouterService.client` property in `backend/app/services/llm.py`
- [x] T010 [US1] Add `@observe()` decorator to `generate_agentic_response` method in `backend/app/services/sommelier.py`
- [x] T011 [US1] Add `@observe()` decorator to `execute_search_wines` and `execute_semantic_search` methods in `backend/app/services/sommelier.py`
- [x] T012 [US1] Add metadata propagation (session_id, user_id, tool_used, iterations) via `langfuse_context` or `update_current_observation` in `backend/app/services/sommelier.py`
- [ ] T013 [US1] Verify end-to-end: send Telegram message → Langfuse UI shows trace with root span, LLM generation(s), and tool call span(s)

**Checkpoint**: Трейсы появляются в Langfuse с полной иерархией spans — LLM calls и tool calls видны как дочерние элементы

---

## Phase 4: User Story 2 — Мониторинг стоимости и токенов (Priority: P1)

**Goal**: Langfuse Dashboard показывает стоимость, токены и латентность LLM-запросов

**Independent Test**: Отправить 3-5 запросов боту, открыть Langfuse Dashboard и проверить наличие метрик: input/output tokens, total cost, latency

### Implementation for User Story 2

- [ ] T014 [US2] Verify OpenRouter returns usage data (input_tokens, output_tokens) in LLM responses — add logging if needed in `backend/app/services/llm.py`
- [ ] T015 [US2] Verify Langfuse Dashboard shows: total tokens, cost per trace, average latency, cost aggregation by date

**Checkpoint**: Dashboard отображает стоимость и токены — разработчик может анализировать расходы на LLM API

---

## Phase 5: User Story 4 — Анализ качества ответов (Priority: P2)

**Goal**: Разработчик может фильтровать трейсы по метаданным и добавлять ручные оценки качества

**Independent Test**: Открыть конкретный трейс, добавить score вручную, проверить что оценка сохранилась и отображается в фильтрах

### Implementation for User Story 4

- [ ] T016 [US4] Verify metadata (tool_used, iterations) appears in Langfuse trace details and is filterable
- [ ] T017 [US4] Verify manual scoring: add score to a trace via Langfuse UI, confirm it persists and appears in Dashboard

**Checkpoint**: Трейсы фильтруются по метаданным, ручные оценки сохраняются и отображаются

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Resilience, persistence, and regression testing

- [ ] T018 Verify graceful degradation: stop all Langfuse containers → send message to bot → bot responds without errors (FR-005, SC-007)
- [ ] T019 Verify persistent storage: `docker compose down && docker compose up -d` → previously recorded traces are preserved in Langfuse UI (FR-006, SC-006)
- [x] T020 Verify existing tests still pass after SDK changes: `cd backend && python -m pytest tests/unit/ tests/integration/ tests/contract/ -q`
- [ ] T021 Verify latency impact: compare bot response time with and without Langfuse tracing enabled (SC-005, ≤5% increase)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US3 Infrastructure (Phase 2)**: Depends on Setup — BLOCKS all other user stories
- **US1 Tracing (Phase 3)**: Depends on US3 (Langfuse containers must be running)
- **US2 Cost Monitoring (Phase 4)**: Depends on US1 (tracing must be operational for cost data)
- **US4 Quality Analysis (Phase 5)**: Depends on US1 (tracing must produce traces with metadata)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 3 — Infrastructure (P1)**: Depends on Phase 1. BLOCKS all other stories (no Langfuse → no tracing)
- **User Story 1 — Tracing (P1)**: Depends on US3. Core SDK integration, BLOCKS US2 and US4
- **User Story 2 — Cost Monitoring (P1)**: Depends on US1. Cost data is automatically captured by OpenAI wrapper — mostly verification
- **User Story 4 — Quality Analysis (P2)**: Depends on US1. Metadata filtering and manual scoring — mostly verification

### Within Each User Story

- Configuration/dependencies FIRST (Phase 1)
- Docker infrastructure SECOND (US3)
- SDK integration THIRD (US1)
- Verification tasks LAST (US2, US4)
- Verify each checkpoint before moving on

### Parallel Opportunities

- T001, T002, T003 can run in parallel (Phase 1 — different files)
- T016, T017 can run in parallel (Phase 5 — independent UI verifications)
- T018, T019, T020, T021 can run in parallel (Phase 6 — independent verification tests)

---

## Implementation Strategy

### MVP First (US3 + US1)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: US3 Infrastructure (T004-T008)
3. **STOP and VALIDATE**: `docker compose up -d` → Langfuse UI at http://localhost:3000
4. Complete Phase 3: US1 Tracing (T009-T013)
5. **STOP and VALIDATE**: Send message → trace appears in Langfuse UI with spans

### Incremental Delivery

1. Setup + US3 → Langfuse running (infrastructure MVP)
2. Add US1 (Tracing) → Full trace hierarchy visible
3. Add US2 (Cost Monitoring) → Dashboard with costs and tokens
4. Add US4 (Quality Analysis) → Filtering and scoring
5. Polish → Resilience and regression verification

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US3 (Infrastructure) is placed before US1 despite both being P1 — logical dependency: containers before SDK
- US2 and US4 are mostly verification phases — minimal code changes
- No automated tests for this feature — it's an observability/infrastructure layer
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
