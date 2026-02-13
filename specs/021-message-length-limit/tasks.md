# Tasks: Message Length Limit Adjustment

**Input**: Design documents from `/specs/021-message-length-limit/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Foundational — Database Migration

**Purpose**: Drop the CHECK constraint on `messages.content`. This MUST complete before any code changes, per constitution principle "Database First".

- [X] T001 Create Alembic migration `backend/migrations/versions/015_drop_message_content_length_constraint.py` — revision `"015"`, down_revision `"014"`. Upgrade: `op.drop_constraint("ck_messages_content_length", "messages", type_="check")`. Downgrade: `op.create_check_constraint("ck_messages_content_length", "messages", "char_length(content) <= 2000")`. See data-model.md Migration section, research.md R-002
- [X] T002 Apply migration and verify: run `cd backend && alembic upgrade head`. Verify constraint is removed by checking `alembic current` shows `015`. See quickstart.md Scenario 1

**Checkpoint**: CHECK constraint removed from DB. All existing data remains valid (FR-008).

---

## Phase 2: User Story 1 — Full Assistant Responses Stored in History (Priority: P1) MVP

**Goal**: LLM responses are stored in full without truncation. The user receives complete context in follow-up messages.

**Independent Test**: Send a message triggering a long response. Verify the full response is stored in DB (not truncated at 2000 chars).

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation (TDD per constitution)**

- [X] T003 [US1] Write test `test_truncate_for_storage_preserves_normal_responses` in `backend/tests/unit/test_telegram_bot.py` — import `TelegramBotService._truncate_for_storage`, call with a 5000-char string, assert the result is NOT truncated (full 5000 chars returned). This test MUST FAIL with the current `max_length=2000` default. See spec acceptance scenario 1
- [X] T004 [US1] Write test `test_truncate_for_storage_safety_net_for_extreme_input` in `backend/tests/unit/test_telegram_bot.py` — call `_truncate_for_storage` with a 100000-char string, assert the result is truncated to 50000 chars. This verifies the safety net (FR-007). This test MUST FAIL with the current `max_length=2000` default

### Implementation for User Story 1

- [X] T005 [US1] Update `_truncate_for_storage()` default `max_length` parameter from `2000` to `50000` in `backend/app/services/telegram_bot.py` (line ~312). Also update the comment on line ~280 from `# DB constraint: char_length(content) <= 2000` to `# Safety-net truncation only (no DB constraint)`. See research.md R-003
- [ ] T006 [US1] Verify T003-T004 tests pass: `python -m pytest backend/tests/unit/test_telegram_bot.py -v -k "truncate_for_storage"`

**Checkpoint**: Assistant responses up to 50000 chars are stored in full. Safety net remains for extreme cases. Tests pass.

---

## Phase 3: User Story 2 — Hardcoded Limits Removed or Aligned (Priority: P2)

**Goal**: All artificial 2000-char limits in code are updated to match actual platform constraints. Web UI shows 4096-char counter. Pydantic validation updated to 4096.

**Independent Test**: Search all hardcoded "2000" references related to message length. Verify each is removed, updated, or documented.

### Tests for User Story 2

> **NOTE: Write tests FIRST, ensure they FAIL before implementation (TDD per constitution)**

- [X] T007 [P] [US2] Update test `test_send_message_request_validation` in `backend/tests/unit/test_chat_models.py` (line ~118-120) — change the "too long" assertion from `"x" * 2001` to `"x" * 4097`. Add a new assertion that `SendMessageRequest(content="x" * 4096)` succeeds (does NOT raise). The new 4096-char acceptance test MUST FAIL with the current `max_length=2000`. See research.md R-006
- [X] T008 [P] [US2] Update test `test_too_long_message_returns_422` in `backend/tests/contract/test_chat_messages.py` (line ~78-96) — change docstring from "2000 chars" to "4096 chars", change `"x" * 2001` to `"x" * 4097`. See research.md R-006

### Implementation for User Story 2

- [X] T009 [US2] Update `SendMessageRequest.content` in `backend/app/schemas/chat.py` (line ~13) — change `max_length=2000` to `max_length=4096`. See research.md R-005, data-model.md Pydantic Schema section
- [X] T010 [US2] Update web UI character counter in `backend/app/templates/chat.html` — 4 changes: (1) line ~489: change `maxlength="2000"` to `maxlength="4096"`, (2) line ~493: change `0 / 2000` to `0 / 4096`, (3) line ~522: change `` `${len} / 2000` `` to `` `${len} / 4096` `` and warning threshold from `len > 1900` to `len > 3900`, (4) line ~775: change `'0 / 2000'` to `'0 / 4096'`. See research.md R-004
- [X] T011 [US2] Verify T007-T008 tests pass: `python -m pytest backend/tests/unit/test_chat_models.py::TestChatSchemas -v && python -m pytest backend/tests/contract/test_chat_messages.py::TestChatMessagesContract::test_too_long_message_returns_422 -v`

**Checkpoint**: All hardcoded 2000-char message length references are updated to 4096 (user input) or 50000 (safety net). Platform limits (Telegram 4096/1024) untouched. Tests pass.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories

- [X] T012 Run full test suite to ensure no regressions: `python -m pytest backend/tests/ -v`
- [X] T013 Run Ruff linter on all changed files: `ruff check backend/app/schemas/chat.py backend/app/services/telegram_bot.py backend/migrations/versions/015_drop_message_content_length_constraint.py`
- [X] T014 Verify unchanged files are indeed unchanged: confirm `backend/app/config.py` still has `llm_max_tokens: int = 2000`, `backend/app/bot/sender.py` still has `[:1024]` caption truncation, `backend/app/models/message.py` has no changes. See research.md R-007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately. BLOCKS all user stories (DB First principle)
- **User Story 1 (Phase 2)**: Depends on Foundational (migration applied)
- **User Story 2 (Phase 3)**: Depends on Foundational (migration applied). Independent of US1 (different files)
- **Polish (Phase 4)**: Depends on both user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 1 — No dependencies on US2
- **User Story 2 (P2)**: Can start after Phase 1 — No dependencies on US1

### Within Each User Story

- Tests written FIRST and must FAIL before implementation (TDD per constitution)
- Implementation changes the code to make tests pass
- Verification confirms green tests

### Parallel Opportunities

**Phase 1** (sequential — migration must be applied before verification):
```
T001 → T002
```

**Phase 2 tests + Phase 3 tests** (can run in parallel since they're in different files):
```
T003, T004 (telegram_bot tests) ║ T007, T008 (schema/contract tests)
```

**Phase 2 impl + Phase 3 impl** (parallel — different files):
```
T005 (telegram_bot.py) ║ T009 (chat.py) ║ T010 (chat.html)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Migration (T001-T002)
2. Complete Phase 2: User Story 1 (T003-T006)
3. **STOP and VALIDATE**: Run truncation tests, send a test message to verify full storage
4. Deploy if ready — assistant responses now stored in full

### Incremental Delivery

1. Migration → DB constraint removed → Deploy
2. Add User Story 1 → Truncation limit increased → Deploy (MVP!)
3. Add User Story 2 → UI counter + schema aligned → Deploy
4. Each story adds consistency without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD approach per project constitution: write failing tests → implement → verify green
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `llm_max_tokens`, `sender.py` caption limit, `golden_queries.py` price — NOT changed (see research.md R-007)
