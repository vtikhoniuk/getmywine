# Tasks: Structured Output for Wine Recommendations

**Input**: Design documents from `/specs/018-structured-output/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/llm-response-schema.json

**Organization**: Tasks grouped by user story. Constitution requires TDD — tests included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Configuration changes and environment preparation

- [X] T001 Update default LLM model to `anthropic/claude-sonnet-4` in backend/app/config.py
- [X] T002 Update `LLM_MODEL=anthropic/claude-sonnet-4` in backend/.env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pydantic models, JSON schema, LLM service changes, and ParsedResponse update that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T003 Write unit tests for WineRecommendation and SommelierResponse Pydantic models (valid JSON, invalid JSON, edge cases: 0 wines, 3 wines, null guard_type) in backend/tests/unit/test_structured_output.py
- [X] T004 Write unit tests for `parse_structured_response()` handling both JSON input and legacy marker input (backward compat) in backend/tests/unit/test_structured_output.py — append after T003
- [X] T005 Write unit tests for `render_response_text()` helper (SommelierResponse → plain text for conversation history) in backend/tests/unit/test_structured_output.py — append after T003

### Implementation for Foundation

- [X] T006 Define Pydantic models `WineRecommendation` and `SommelierResponse` with JSON Schema constant `SOMMELIER_RESPONSE_SCHEMA` in backend/app/services/sommelier_prompts.py (add after existing ParsedResponse class, per contracts/llm-response-schema.json)
- [X] T007 Add `wine_names: list[str]` field to existing `ParsedResponse` dataclass in backend/app/services/sommelier_prompts.py (keep existing `wines` field for heuristic fallback)
- [X] T008 Implement `render_response_text(response: SommelierResponse) -> str` helper function in backend/app/services/sommelier_prompts.py — concatenates intro + wine descriptions + closing for conversation history (FR-011)
- [X] T009 Update `parse_structured_response()` in backend/app/services/sommelier_prompts.py: try JSON parse → `SommelierResponse.model_validate_json()` → convert to `ParsedResponse` first; fallback to existing regex/heuristic if JSON parse fails (FR-010)
- [X] T010 Add `response_format: Optional[dict] = None` parameter to `generate_with_tools()` in `OpenRouterService` and pass through to `client.chat.completions.create()` in backend/app/services/llm.py
- [X] T011 Add `response_format: Optional[dict] = None` parameter to `generate_with_tools()` in `LLMService` wrapper and pass through to provider in backend/app/services/llm.py
- [X] T012 Add `response_format: Optional[dict] = None` parameter to `generate()` in `OpenRouterService` and `LLMService` wrapper, pass through to `client.chat.completions.create()` in backend/app/services/llm.py
- [X] T013 Run unit tests from T003-T005, verify all pass after T006-T012 implementation

**Checkpoint**: Foundation ready — Pydantic models defined, LLM service accepts response_format, parse logic handles both JSON and legacy markers.

---

## Phase 3: User Story 1 — Wine Recommendation with Photos (Priority: P1) MVP

**Goal**: User sends wine request → LLM returns structured JSON → bot sends 5 separate messages with photos

**Independent Test**: Send "посоветуй вино к рыбе" to bot, verify 5 separate messages with photos arrive

### Tests for User Story 1

- [X] T014 [US1] Write integration test: mock LLM returns valid SommelierResponse JSON with 3 wines → sender sends 5 messages (intro + 3 photos + closing) in backend/tests/integration/test_structured_recommendation.py

### Implementation for User Story 1

- [X] T015 [US1] Update system prompts: replaced marker instructions with JSON structured output instructions in SYSTEM_PROMPT_BASE and SYSTEM_PROMPT_AGENTIC
- [X] T016 [US1] Changed return type of generate_response() and generate_agentic_response() to tuple[str, list[str]] with _parse_final_response() static method
- [X] T017 [US1] Pass response_format=SOMMELIER_RESPONSE_SCHEMA to generate_with_tools() with finish_reason handling for "refusal"/"length"
- [X] T018 [US1] Updated _extract_wines_from_response() with wine_names parameter for direct name lookup
- [X] T019 [US1] Updated process_message() to unpack tuple and pass wine_names
- [X] T020 [US1] Sender uses positional matching which works correctly with structured output (wine order preserved)
- [X] T021 [US1] message_handler_callback() already unpacks (response_text, wines) from process_message() — no changes needed
- [X] T022 [US1] Integration tests pass (4/4); all dependent tests pass (60/60)

**Checkpoint**: User Story 1 fully functional — wine recommendations arrive as 5 structured messages with photos.

---

## Phase 4: User Story 2 — Welcome /start Message (Priority: P1)

**Goal**: User presses /start → bot sends structured welcome with 3 wine suggestions and photos

**Independent Test**: Press /start in bot, verify 5 messages with photos arrive

### Tests for User Story 2

- [X] T023 [US2] Write integration test: mock LLM returns valid SommelierResponse JSON for welcome → start handler sends 5 messages (intro + 3 photos + closing) in backend/tests/integration/test_structured_welcome.py

### Implementation for User Story 2

- [X] T024 [US2] Update `_generate_llm_welcome()` in backend/app/services/sommelier.py: pass `response_format=SOMMELIER_RESPONSE_SCHEMA` to `llm_service.generate_wine_recommendation()`; LLM returns raw JSON which flows to sender's parse_structured_response() for reliable JSON parsing
- [X] T025 [US2] SYSTEM_PROMPT_COLD_START and SYSTEM_PROMPT_PERSONALIZED already extend SYSTEM_PROMPT_BASE which has JSON structured output instructions — no changes needed
- [X] T026 [US2] start_command() needs no changes — raw JSON flows through result["message"] → sender → parse_structured_response() → JSON path
- [X] T027 [US2] Integration tests pass (4/4); all 88 structured output + dependent tests pass

**Checkpoint**: Both P1 stories work — recommendations and welcome flow deliver structured messages.

---

## Phase 5: User Story 3 — Informational Response (Priority: P2)

**Goal**: User asks general wine question → bot sends single text message without wine cards

**Independent Test**: Ask "расскажи про пино нуар", verify single text message without photos

### Implementation for User Story 3

- [X] T028 [US3] Verified: sender.py lines 85-95 already handle `wines: []` by sending combined intro+closing as single message; covered by test_sender_handles_informational_no_wines
- [X] T029 [US3] Verified: SYSTEM_PROMPT_BASE lines 47-48 clearly define "informational" (wines=[]) vs "recommendation" (wines=1-3); SYSTEM_PROMPT_AGENTIC line 177 describes when tools are not needed
- [ ] T030 [US3] Manually test: ask bot "что такое танины?", verify single text message

**Checkpoint**: Informational responses work — general wine questions get text-only answers.

---

## Phase 6: User Story 4 — Off-topic / Guard (Priority: P2)

**Goal**: User sends off-topic request → bot redirects to wine with guard_type tracked

**Independent Test**: Send "реши уравнение x^2=4", verify redirect to wine topic

### Implementation for User Story 4

- [X] T031 [US4] Verified: parse_structured_response() JSON path (line 404) propagates guard_type to ParsedResponse; logging at line 393-396; covered by test_guard_type_off_topic in test_structured_output.py
- [X] T032 [US4] Verified: SYSTEM_PROMPT_BASE lines 77-103 use JSON fields (response_type: "off_topic", guard_type) instead of [GUARD:type] markers — fully migrated to JSON format
- [ ] T033 [US4] Manually test: send "реши уравнение x^2=4" to bot, verify wine redirect with guard type

**Checkpoint**: All 4 user stories functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tests, eval updates, cleanup

- [X] T034 [P] Updated test_hallucination.py: unpack tuple from generate_agentic_response(), use wine_names for direct catalog check (fast path), fallback to text parsing. test_tool_selection.py and test_filter_accuracy.py unchanged (don't use return value).
- [X] T035 [P] Created test_structured_output_eval.py with 9 parametrized eval tests: 3 recommendation, 2 informational, 1 off-topic query — validates wine_names list and response type routing
- [X] T036 All tests pass: 494 passed (111 structured output related), 37 pre-existing DB failures (unrelated: no such table wines/conversations in SQLite test env)
- [ ] T037 Run quickstart.md manual validation: all 4 test scenarios
- [ ] T038 Verify Langfuse traces show `response_format` parameter and JSON responses in http://localhost:3000
- [ ] T039 Compare Langfuse trace durations before/after migration to verify SC-002 (latency increase <=500ms)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP delivery
- **US2 (Phase 4)**: Depends on Foundational — can parallel with US1 (different files: start.py vs message.py, welcome vs agentic)
- **US3 (Phase 5)**: Depends on US1 (shared sender logic)
- **US4 (Phase 6)**: Depends on US1 (shared sender logic)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no other story deps. **Core MVP.**
- **US2 (P1)**: After US1 recommended (shared files: sommelier_prompts.py, sommelier.py). Can parallel only if developers coordinate on separate sections of shared files.
- **US3 (P2)**: After US1 — reuses sender logic for empty-wine handling
- **US4 (P2)**: After US1 — reuses sender logic + guard_type propagation

### Within Each User Story

- Tests (TDD) → Models/Schema → Services → Handlers → Manual verification

### Parallel Opportunities

Phase 2 parallelism:
- T003, T004, T005 (tests) are sequential (same file) — write in order
- T010, T011, T012 (LLM service changes) are in same file — sequential

Phase 3→4 (recommended sequential):
- US1 then US2 — shared files (sommelier_prompts.py, sommelier.py) make true parallel risky for solo developer

Phase 7 parallelism:
- T034 and T035 (eval test updates) can run in parallel

---

## Example: Phase 2 Foundation (sequential)

```bash
# TDD: Write tests first (sequential — same file):
Task: T003 "Unit tests for Pydantic models"
Task: T004 "Unit tests for parse_structured_response"
Task: T005 "Unit tests for render_response_text"

# Implement models (sequential — same file):
Task: T006 "Define WineRecommendation + SommelierResponse"
Task: T007 "Add wine_names to ParsedResponse"
Task: T008 "Implement render_response_text()"
Task: T009 "Update parse_structured_response()"

# LLM service (sequential — same file):
Task: T010-T012 "Add response_format to LLM service"
```

## Example: Sequential US1 → US2

```bash
# US1 (message flow) — MVP:
Task: T014-T022 "Agentic prompts → sommelier → telegram_bot → sender → handler"

# US2 (start flow) — after US1:
Task: T023-T027 "Welcome test → sommelier welcome → cold start prompts → start handler"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T013) — CRITICAL
3. Complete Phase 3: US1 (T014-T022)
4. **STOP and VALIDATE**: Send "посоветуй вино к рыбе" — verify 5 messages with photos
5. Deploy if ready — this alone fixes the main user complaint (80% value)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (T014-T022) → Test → Deploy (MVP — 80% of user value)
3. Add US2 (T023-T027) → Test → Deploy (complete P1 coverage)
4. Add US3 (T028-T030) + US4 (T031-T033) → Test → Deploy (P2 coverage)
5. Polish (T034-T039) → Final deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- FR-010 preserved: heuristic fallback stays in parse_structured_response() for models without structured output
- FR-011 implemented via render_response_text() — JSON → text for history
- Existing WINE_TOOLS (search_wines, semantic_search) unchanged
- Database schema unchanged
- Rollback: change LLM_MODEL back to openai/gpt-4.1, heuristic parser activates automatically
