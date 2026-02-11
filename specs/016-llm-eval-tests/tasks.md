# Tasks: LLM Eval Tests

**Input**: Design documents from `/specs/016-llm-eval-tests/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: This feature IS a test suite — all tasks produce test code. TDD principle from constitution applies: tests are the deliverable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Eval test package initialization, shared fixtures, and golden query data model

- [x] T001 Create eval test package in `backend/tests/eval/__init__.py`
- [x] T002 Register `eval` pytest marker in `backend/tests/conftest.py` via `pytest_configure` hook
- [x] T003 Implement `_has_real_backend()` check (OPENROUTER_API_KEY, DATABASE_URL, DNS reachability) in `backend/tests/eval/conftest.py`
- [x] T004 Implement `pytest_collection_modifyitems` hook for auto-skip in `backend/tests/eval/conftest.py`
- [x] T005 [P] Create `GoldenQuery` dataclass in `backend/tests/eval/golden_queries.py`
- [x] T006 Create `eval_db` fixture (real PostgreSQL session) in `backend/tests/eval/conftest.py`
- [x] T007 Create `sommelier_service` fixture (real LLM + real DB) in `backend/tests/eval/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ToolCallSpy and catalog fixtures that MUST be complete before ANY user story tests

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Implement `ToolCallSpy` class with spy methods for `execute_search_wines` and `execute_semantic_search` in `backend/tests/eval/conftest.py`
- [x] T009 Create `tool_spy` fixture that attaches spy to sommelier service in `backend/tests/eval/conftest.py`
- [x] T010 [P] Create `catalog_wines` fixture (loads all wines from real catalog) in `backend/tests/eval/conftest.py`

**Checkpoint**: Foundation ready — all fixtures operational, auto-skip verified

---

## Phase 3: User Story 1 — Проверка выбора инструмента (Priority: P1) 🎯 MVP

**Goal**: Убедиться, что LLM выбирает правильный инструмент для каждого типа запроса: конкретные параметры → search_wines, абстрактные описания → semantic_search

**Independent Test**: Запустить `python -m pytest tests/eval/test_tool_selection.py -v` — 8 тестов должны пройти (при наличии инфраструктуры) или пропуститься (без инфраструктуры)

### Implementation for User Story 1

- [x] T011 [US1] Define 8 tool selection golden queries (red_dry, elegant_light, pinot_noir, steak, sparkling, refreshing, white_france, expensive) in `backend/tests/eval/golden_queries.py` as `TOOL_SELECTION_QUERIES`
- [x] T012 [US1] Implement parametrized `test_tool_selection` with assertions on `tool_spy.first_tool` in `backend/tests/eval/test_tool_selection.py`

**Checkpoint**: Tool selection tests pass — LLM correctly routes structured queries to search_wines and abstract queries to semantic_search

---

## Phase 4: User Story 2 — Проверка точности извлечения фильтров (Priority: P1)

**Goal**: Убедиться, что LLM корректно извлекает структурированные фильтры из естественного языка (тип вина, сладость, цена, сорт, страна)

**Independent Test**: Запустить `python -m pytest tests/eval/test_filter_accuracy.py -v` — 3 теста с проверкой конкретных фильтров и 20% толерантностью для числовых значений

### Implementation for User Story 2

- [x] T013 [US2] Define 3 filter accuracy golden queries (red_dry_budget, grape_malbec, country_type) with expected_filters in `backend/tests/eval/golden_queries.py` as `FILTER_ACCURACY_QUERIES`
- [x] T014 [US2] Implement parametrized `test_filter_accuracy` with string partial match and 20% numeric tolerance in `backend/tests/eval/test_filter_accuracy.py`

**Checkpoint**: Filter accuracy tests pass — LLM extracts wine_type, sweetness, price_max, grape_variety correctly

---

## Phase 5: User Story 3 — Обнаружение галлюцинаций (Priority: P1)

**Goal**: Убедиться, что LLM не выдумывает вина, которых нет в каталоге, а рекомендует только те, что вернул инструмент

**Independent Test**: Запустить `python -m pytest tests/eval/test_hallucination.py -v` — 3 теста проверяющих, что каждое упомянутое вино существует в каталоге

### Implementation for User Story 3

- [x] T015 [US3] Define 3 hallucination check queries inline in `backend/tests/eval/test_hallucination.py`
- [x] T016 [US3] Implement `test_no_hallucinated_wines` with `parse_structured_response()` parsing and catalog name fuzzy matching in `backend/tests/eval/test_hallucination.py`

**Checkpoint**: Hallucination tests pass — all wine names in [WINE:N] sections exist in the real catalog

---

## Phase 6: User Story 4 — Проверка качества семантического поиска (Priority: P2)

**Goal**: Убедиться, что семантический поиск (pgvector embeddings) возвращает релевантные результаты с приемлемыми показателями сходства

**Independent Test**: Запустить `python -m pytest tests/eval/test_semantic_quality.py -v` — 5 тестов: 3 relevance, 1 ordering, 1 differentiation

### Implementation for User Story 4

- [x] T017 [US4] Define 3 semantic search golden queries (romantic, unusual, berry_notes) in `backend/tests/eval/golden_queries.py` as `SEMANTIC_QUERIES`
- [x] T018 [P] [US4] Implement parametrized `test_semantic_search_relevance` (similarity > 0.25, min_results check) in `backend/tests/eval/test_semantic_quality.py`
- [x] T019 [P] [US4] Implement `test_semantic_search_ordering` (descending similarity scores) in `backend/tests/eval/test_semantic_quality.py`
- [x] T020 [P] [US4] Implement `test_semantic_vs_structured_differentiation` ("ягодные ноты" vs "минеральное белое") in `backend/tests/eval/test_semantic_quality.py`

**Checkpoint**: Semantic quality tests pass — search returns relevant, ordered, differentiated results

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation and documentation

- [x] T021 Verify all 19 eval tests skip correctly when infrastructure is unavailable (run without PostgreSQL/API key)
- [x] T022 Verify existing unit tests (467+) still pass after all changes: `python -m pytest tests/unit/ tests/integration/ tests/contract/ -q`
- [x] T023 Run full eval suite 2-3 times and verify: completion under 5 minutes (SC-007), stable pass rates (SC-002 ≥75%, SC-003 ≥90%, SC-004 100%): `python -m pytest tests/eval/ -v`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1-US3 (P1 stories) can proceed in parallel
  - US4 (P2) can proceed in parallel with P1 stories
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 — Tool Selection (P1)**: Depends on Phase 2 (ToolCallSpy). No dependencies on other stories
- **User Story 2 — Filter Accuracy (P1)**: Depends on Phase 2 (ToolCallSpy). No dependencies on other stories
- **User Story 3 — Hallucination (P1)**: Depends on Phase 2 (catalog_wines fixture). No dependencies on other stories
- **User Story 4 — Semantic Quality (P2)**: Depends on Phase 1 (eval_db fixture). No dependencies on other stories. Does NOT use ToolCallSpy — tests WineRepository directly

### Within Each User Story

- Define golden queries in `golden_queries.py` FIRST
- Then implement test functions
- Verify tests pass (or skip) before moving on

### Parallel Opportunities

- T005, T006, T007 can run in parallel (Phase 1 — different files/sections)
- T008, T009, T010 — T010 can run in parallel with T008+T009 (Phase 2)
- Phases 3, 4, 5, 6 can all run in parallel once Phase 2 is complete
- T018, T019, T020 can run in parallel (different test functions, same file but independent)

---

## Parallel Example: All User Stories

```bash
# After Phase 2 completes, launch all user stories in parallel:
Task: "Define 8 tool selection queries + test in tests/eval/"         # US1
Task: "Define 3 filter accuracy queries + test in tests/eval/"        # US2
Task: "Define 3 hallucination queries + test in tests/eval/"          # US3
Task: "Define 3 semantic queries + 3 tests in tests/eval/"            # US4
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational — ToolCallSpy (T008-T010)
3. Complete Phase 3: User Story 1 — Tool Selection (T011-T012)
4. **STOP and VALIDATE**: Run `python -m pytest tests/eval/test_tool_selection.py -v`
5. 8 tests should pass — MVP demonstrates eval test infrastructure works

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 (Tool Selection) → 8 tests → Validate MVP
3. Add US2 (Filter Accuracy) → +3 tests → Validate
4. Add US3 (Hallucination) → +3 tests → Validate
5. Add US4 (Semantic Quality) → +5 tests → Validate
6. Polish → Verify all 19 tests, ensure auto-skip, check timing

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T010)
2. Once Foundational is done:
   - Developer A: US1 (Tool Selection) + US2 (Filter Accuracy)
   - Developer B: US3 (Hallucination) + US4 (Semantic Quality)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All tests auto-skip without infrastructure (FR-006)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
