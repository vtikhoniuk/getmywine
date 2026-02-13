# Tasks: Structured Output Retry with Error Feedback

**Input**: Design documents from `/specs/020-structured-output-retry/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and shared data structures needed by all user stories

- [X] T001 Add `structured_output_max_retries: int = 2` setting in `backend/app/config.py` with comment explaining it controls retry count after initial attempt (3 total). See research.md R-007
- [X] T002 [P] Create `ParseResult` dataclass in `backend/app/services/sommelier.py` with fields: `text: str`, `wine_ids: list[str]`, `error: str | None = None`, and property `ok -> bool` that returns `True` when `error is None and text.strip()`. See research.md R-004, data-model.md ParseResult
- [X] T003 [P] Create `validate_semantic_content(response: SommelierResponse) -> str | None` function in `backend/app/services/sommelier_prompts.py` — returns None if content is meaningful, error description string if semantically empty. Rules: (1) `response_type == "recommendation"` with empty `wines` → invalid, (2) empty `intro` AND empty `closing` AND no wine descriptions → invalid, (3) `response_type == "off_topic"` with empty `intro` → invalid, (4) `response_type == "informational"` with empty wines is valid. See research.md R-005

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Refactor `_parse_final_response` to return `ParseResult` — MUST be complete before retry logic can be built

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Refactor `_parse_final_response()` in `backend/app/services/sommelier.py` to return `ParseResult` instead of `tuple[str, list[str]]`. On Pydantic success: call `validate_semantic_content()` and if it returns an error, return `ParseResult(text="", wine_ids=[], error=semantic_error)`. On `json.loads` fallback success: return `ParseResult(text=rendered, wine_ids=wine_ids)`. On all parsing failure: return `ParseResult(text="", wine_ids=[], error="description of what failed")`. Preserve all existing logging
- [X] T005 Update all callers of `_parse_final_response()` in `backend/app/services/sommelier.py` to use `ParseResult` — in `generate_agentic_response()` (3 call sites: refusal handling line ~795, no-tool-calls line ~809, max-iterations line ~858) change from `return self._parse_final_response(content)` to using `result = self._parse_final_response(content)` and returning `(result.text, result.wine_ids)`. This is a transitional step — retry logic will wrap these in US1

**Checkpoint**: `_parse_final_response` returns structured results; existing behavior unchanged

---

## Phase 3: User Story 1 — Automatic Recovery from Invalid LLM Response (Priority: P1) MVP

**Goal**: When the model returns invalid structured output, automatically retry with error feedback. The user receives a valid recommendation without seeing the failure.

**Independent Test**: Simulate a malformed LLM response on first call, valid on second → user gets valid recommendation.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Write test `test_retry_on_parse_failure_succeeds` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return invalid JSON on first call (e.g., `{"broken": true}`), valid `SommelierResponse` JSON on second call. Assert: (1) `generate_with_tools` called twice, (2) second call's messages contain the invalid response as assistant message and error feedback as user message, (3) final result is the valid rendered response. See research.md R-002 for feedback message format
- [X] T007 [P] [US1] Write test `test_no_retry_on_success` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return valid `SommelierResponse` JSON on first call. Assert: (1) `generate_with_tools` called exactly once, (2) result is valid rendered response
- [X] T008 [P] [US1] Write test `test_no_retry_on_refusal` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return response with `finish_reason="refusal"`. Assert: (1) `generate_with_tools` called exactly once, (2) no retry attempted. See spec FR-004
- [X] T009 [P] [US1] Write test `test_retry_on_truncated_response` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return response with `finish_reason="length"` and truncated JSON on first call, valid response on second. Assert: retry occurs with truncation feedback message
- [X] T010 [P] [US1] Write test `test_retry_on_semantically_empty_response` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return valid JSON with `response_type="recommendation"`, empty `wines=[]`, empty `intro=""` on first call, valid response with wines on second. Assert: retry occurs because semantic validation fails. See spec FR-010

### Implementation for User Story 1

- [X] T011 [US1] Implement retry loop in `generate_agentic_response()` in `backend/app/services/sommelier.py` — extract the `_parse_final_response` call into a helper method `_attempt_parse_with_retry(content, messages, max_retries, tools_used, iteration)` that: (1) calls `_parse_final_response(content)`, (2) if `result.ok` → returns `(result.text, result.wine_ids)`, (3) if not ok and retries remaining → appends assistant message with raw content and user message with error feedback (format per research.md R-002) to messages, re-calls `generate_with_tools` with same `response_format=SOMMELIER_RESPONSE_SCHEMA`, decrements retry counter, (4) if retries exhausted → returns `("", [])`. Read `structured_output_max_retries` from config. FR-009: retry counter is independent of the tool-use `iteration` counter
- [X] T012 [US1] Replace all 3 direct `_parse_final_response` call sites in `generate_agentic_response()` with `_attempt_parse_with_retry()` — (1) refusal handling: do NOT retry refusals per FR-004, just return parse result directly, (2) truncation (`finish_reason=length`): DO retry with truncation-specific feedback, (3) normal no-tool-calls response: retry on failure, (4) max-iterations final call: retry on failure
- [X] T013 [US1] Verify all T006-T010 tests pass after implementation. Run: `python -m pytest backend/tests/unit/test_agent_loop.py -v -k "retry"`

**Checkpoint**: Retry-with-feedback works for all structured output failure types. Refusals are not retried. Tests pass.

---

## Phase 4: User Story 2 — Graceful Degradation After Retry Exhaustion (Priority: P2)

**Goal**: When all retries are exhausted, the user gets a friendly error and the conversation stays clean for the next message.

**Independent Test**: Simulate persistent invalid responses across all retry attempts → user sees error message, conversation continues normally.

### Tests for User Story 2

- [X] T014 [P] [US2] Write test `test_retry_exhaustion_returns_empty` in `backend/tests/unit/test_agent_loop.py` — mock `generate_with_tools` to return invalid JSON on ALL calls (initial + 2 retries = 3 total). Assert: (1) `generate_with_tools` called exactly 3 times (1 initial + 2 retries, per config default), (2) result is `("", [])`, (3) no exception raised
- [X] T015 [P] [US2] Write test `test_no_history_saved_on_exhaustion` in `backend/tests/unit/test_agent_loop.py` or `backend/tests/unit/test_telegram_bot.py` — mock sommelier to return empty response after exhaustion. Assert: `message_repo.create` is NOT called for the assistant message. See spec FR-005

### Implementation for User Story 2

- [X] T016 [US2] Verify that the empty-response guard in `backend/app/services/telegram_bot.py` (line ~280-297) correctly handles `response_text=""` from exhausted retries — the existing `is_empty` check should already set `response_text = ERROR_LLM_UNAVAILABLE` and skip history save. If not working, fix the guard. See spec FR-006
- [X] T017 [US2] Implement content truncation for valid long responses in `backend/app/services/telegram_bot.py` — add a `_truncate_for_storage(text: str, max_length: int = 2000) -> str` method that: (1) if `len(text) <= max_length` → return as-is, (2) find last `\n\n` within `max_length` → truncate there, (3) else find last `. ` within `max_length` → truncate there, (4) else hard-truncate at `max_length`. Apply before `message_repo.create()` for assistant messages. Replace the current `is_too_long` skip-save logic with truncate-and-save. See research.md R-006, spec FR-011
- [X] T018 [US2] Verify T014-T015 tests pass. Run: `python -m pytest backend/tests/unit/test_agent_loop.py -v -k "exhaustion or history"`

**Checkpoint**: Exhaustion returns graceful error to user. Long valid responses are truncated and saved. No history pollution.

---

## Phase 5: User Story 3 — Operational Visibility of Retry Events (Priority: P3)

**Goal**: Operators can monitor retry frequency, error types, and success rates via logs and Langfuse.

**Independent Test**: Trigger retry scenarios and verify logs and Langfuse metadata contain retry details.

### Tests for User Story 3

- [X] T019 [P] [US3] Write test `test_retry_metadata_in_langfuse` in `backend/tests/unit/test_agent_loop.py` — mock `langfuse_context.update_current_observation` and trigger a retry scenario. Assert: metadata dict contains `structured_output_retries` (int) and `structured_output_errors` (list of strings). See data-model.md Langfuse Metadata Extension

### Implementation for User Story 3

- [X] T020 [US3] Extend `_update_langfuse_metadata()` in `backend/app/services/sommelier.py` to accept and record `structured_output_retries: int = 0` and `structured_output_errors: list[str] | None = None` parameters. Add these to the metadata dict. See data-model.md
- [X] T021 [US3] Pass retry tracking data (`retry_attempt` count and `retry_errors` list) from `_attempt_parse_with_retry()` to `_update_langfuse_metadata()` at all call sites in `generate_agentic_response()`. Ensure metadata is updated even when no retries occur (retries=0, errors=[])
- [X] T022 [US3] Add structured logging with `logger.info` for each retry attempt in `_attempt_parse_with_retry()`: log message should include attempt number, max retries, and error description. Format: `"Structured output retry %d/%d: %s"`. On retry success: `"Structured output retry %d/%d succeeded"`. On exhaustion: `"Structured output retries exhausted after %d attempts"`. See spec FR-007
- [X] T023 [US3] Verify T019 test passes. Run: `python -m pytest backend/tests/unit/test_agent_loop.py -v -k "metadata"`

**Checkpoint**: All retry events are logged and traceable in Langfuse.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories

- [X] T024 Run full test suite to ensure no regressions: `python -m pytest backend/tests/ -v`
- [X] T025 Run Ruff linter on all changed files: `ruff check backend/app/services/sommelier.py backend/app/services/sommelier_prompts.py backend/app/services/telegram_bot.py backend/app/config.py backend/tests/unit/test_agent_loop.py`
- [X] T026 Run quickstart.md validation scenarios manually or describe how to verify each scenario in running environment. See quickstart.md Scenarios 1-4

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T005)
- **User Story 2 (Phase 4)**: Depends on User Story 1 (T011-T012 must exist for exhaustion to be testable)
- **User Story 3 (Phase 5)**: Depends on User Story 1 (retry logic must exist for metadata to be recorded)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 (retry mechanism must exist to test exhaustion)
- **User Story 3 (P3)**: Depends on US1 (retry mechanism must exist to observe)

### Within Each User Story

- Tests written FIRST and must FAIL before implementation (TDD per constitution)
- ParseResult dataclass before retry logic
- Retry logic before metadata/logging extensions
- Core implementation before integration

### Parallel Opportunities

**Phase 1** (all 3 tasks in parallel):
```
T001 (config.py) ║ T002 (ParseResult) ║ T003 (validate_semantic_content)
```

**Phase 3 tests** (all 5 tests in parallel):
```
T006 ║ T007 ║ T008 ║ T009 ║ T010
```

**Phase 4 tests** (2 tests in parallel):
```
T014 ║ T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: User Story 1 (T006-T013)
4. **STOP and VALIDATE**: Run retry tests, send a test message to Telegram bot
5. Deploy if ready — retry is working, user experience improved

### Incremental Delivery

1. Setup + Foundational → ParseResult and config ready
2. Add User Story 1 → Retry works → Deploy (MVP!)
3. Add User Story 2 → Graceful degradation + truncation → Deploy
4. Add User Story 3 → Observability → Deploy
5. Each story adds resilience without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD approach per project constitution: write failing tests → implement → verify green
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- No database migrations needed — all changes are in-memory/service layer
