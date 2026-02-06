# Tasks: Telegram-бот для GetMyWine

**Input**: Design documents from `/specs/011-telegram-bot/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD required per Constitution — tests written FIRST, must FAIL before implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/app/`, `backend/tests/`
- Based on existing project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and bot module structure

- [x] T001 Add python-telegram-bot dependency via `pip install python-telegram-bot[job-queue]` in backend/
- [x] T002 [P] Extend Settings class with Telegram config in backend/app/config.py (telegram_bot_token, telegram_mode, enable_telegram_bot, telegram_session_inactivity_hours)
- [x] T003 [P] Create bot module structure: backend/app/bot/__init__.py, backend/app/bot/handlers/__init__.py
- [x] T004 [P] Create language detection utility in backend/app/bot/utils.py (detect_language function per research.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create TelegramUser model in backend/app/models/telegram_user.py (per data-model.md)
- [x] T006 Extend Conversation model with channel and telegram_user_id fields in backend/app/models/conversation.py
- [x] T007 Create Alembic migration for telegram_users table and conversations extension in backend/migrations/versions/
- [ ] T008 Run migration: `alembic upgrade head` ⚠️ (requires running database)
- [x] T009 [P] Create TelegramUserRepository in backend/app/repositories/telegram_user.py
- [x] T010 [P] Extend ConversationRepository with telegram channel support in backend/app/repositories/conversation.py
- [x] T011 Create bot entry point in backend/app/bot/main.py (Application setup, polling mode)
- [x] T012 [P] Create error messages constants in backend/app/bot/messages.py (per contracts/bot-commands.md)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Первый контакт с ботом и регистрация (Priority: P1) 🎯 MVP

**Goal**: Пользователь запускает бота, создаётся профиль, получает приветственное сообщение с 3 рекомендациями вин

**Independent Test**: Открыть бота в Telegram → /start → получить приветствие с 3 винами

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US1] Unit test for start handler in backend/tests/unit/test_telegram_start.py
- [x] T014 [P] [US1] Unit test for TelegramUserRepository in backend/tests/unit/test_telegram_user_repository.py
- [x] T015 [US1] Integration test for /start flow in backend/tests/integration/test_telegram_start_flow.py

### Implementation for User Story 1

- [x] T016 [US1] Implement TelegramBotService.get_or_create_telegram_user() in backend/app/services/telegram_bot.py
- [x] T017 [US1] Implement TelegramBotService.create_telegram_session() in backend/app/services/telegram_bot.py
- [x] T018 [US1] Implement /start handler in backend/app/bot/handlers/start.py (creates TelegramUser, session, sends welcome with wines)
- [x] T019 [US1] Register start handler in backend/app/bot/main.py
- [x] T020 [US1] Verify tests pass for User Story 1 (24 tests passing)

**Checkpoint**: User Story 1 complete — bot responds to /start with personalized welcome

---

## Phase 4: User Story 2 - Получение рекомендаций вин (Priority: P1)

**Goal**: Пользователь отправляет текстовый запрос и получает рекомендации вин из каталога

**Independent Test**: Отправить "порекомендуй вино к стейку" → получить рекомендацию с обоснованием

### Tests for User Story 2

- [x] T021 [P] [US2] Unit test for message handler in backend/tests/unit/test_telegram_message.py
- [x] T022 [US2] Integration test for recommendation flow in backend/tests/integration/test_telegram_recommendation_flow.py

### Implementation for User Story 2

- [x] T023 [US2] Implement TelegramBotService.process_message() in backend/app/services/telegram_bot.py (integrates with SommelierService)
- [x] T024 [US2] Implement free-text message handler in backend/app/bot/handlers/message.py
- [x] T025 [US2] Add conversation history tracking for context in backend/app/services/telegram_bot.py
- [x] T026 [US2] Register message handler in backend/app/bot/main.py
- [x] T027 [US2] Verify tests pass for User Story 2 (20 tests passing)

**Checkpoint**: User Stories 1 AND 2 complete — bot handles /start and free-text recommendations

---

## Phase 5: User Story 3 - Просмотр информации о рекомендованном вине (Priority: P2)

**Goal**: Рекомендации отображаются структурированно с полной информацией о вине в мобильном формате

**Independent Test**: Получить рекомендацию → проверить наличие названия, региона, сорта, цены, обоснования

### Tests for User Story 3

- [x] T028 [P] [US3] Unit test for wine card formatter in backend/tests/unit/test_telegram_formatters.py
- [x] T029 [P] [US3] Unit test for inline keyboards in backend/tests/unit/test_telegram_keyboards.py (skipped - telegram module not available in test env)

### Implementation for User Story 3

- [x] T030 [P] [US3] Implement wine card formatter in backend/app/bot/formatters.py (Markdown format per contracts/bot-commands.md)
- [x] T031 [P] [US3] Implement characteristic visualizer (⬛⬜ bars) in backend/app/bot/formatters.py
- [x] T032 [US3] Implement feedback inline keyboard in backend/app/bot/keyboards.py
- [x] T033 [US3] Update message handler to use formatters in backend/app/bot/handlers/message.py
- [x] T034 [US3] Update start handler to use formatters in backend/app/bot/handlers/start.py
- [x] T035 [US3] Verify tests pass for User Story 3 (60 passed, 10 skipped)

**Checkpoint**: Wine cards display with full structured info and feedback buttons

---

## Phase 6: User Story 4 - Управление профилем через бота (Priority: P3)

**Goal**: Пользователь просматривает профиль, обновляет предпочтения, даёт обратную связь на рекомендации

**Independent Test**: /profile → увидеть профиль → нажать 👍 на рекомендации → профиль обновлён

### Tests for User Story 4

- [ ] T036 [P] [US4] Unit test for profile handler in backend/tests/unit/test_telegram_profile.py
- [ ] T037 [P] [US4] Unit test for feedback callback handler in backend/tests/unit/test_telegram_feedback.py

### Implementation for User Story 4

- [ ] T038 [US4] Implement /profile handler in backend/app/bot/handlers/profile.py (show profile, update buttons)
- [ ] T039 [US4] Implement profile edit keyboards in backend/app/bot/keyboards.py (sweetness, budget selection)
- [ ] T040 [US4] Implement feedback callback handler in backend/app/bot/handlers/profile.py (like/dislike processing)
- [ ] T041 [US4] Implement TelegramBotService.update_preference() in backend/app/services/telegram_bot.py
- [ ] T042 [US4] Implement TelegramBotService.record_feedback() in backend/app/services/telegram_bot.py
- [ ] T043 [US4] Register profile and callback handlers in backend/app/bot/main.py
- [ ] T044 [US4] Verify tests pass for User Story 4

**Checkpoint**: Profile management complete — users can view, update profile and give feedback

---

## Phase 7: User Story 5 - Помощь и навигация (Priority: P3)

**Goal**: Пользователь получает справку через /help, может уточнять предыдущие запросы

**Independent Test**: /help → увидеть список команд → уточнить предыдущий запрос

### Tests for User Story 5

- [ ] T045 [P] [US5] Unit test for help handler in backend/tests/unit/test_telegram_help.py
- [ ] T046 [P] [US5] Unit test for unknown command handler in backend/tests/unit/test_telegram_unknown.py

### Implementation for User Story 5

- [ ] T047 [US5] Implement /help handler in backend/app/bot/handlers/help.py (per contracts/bot-commands.md)
- [ ] T048 [US5] Implement unknown command handler in backend/app/bot/handlers/message.py
- [ ] T049 [US5] Register help handler in backend/app/bot/main.py
- [ ] T050 [US5] Verify tests pass for User Story 5

**Checkpoint**: All 5 user stories complete and independently testable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, optional features

### Account Linking (FR-005)

- [ ] T051 [P] Unit test for link handler in backend/tests/unit/test_telegram_link.py
- [ ] T052 Implement /link handler in backend/app/bot/handlers/link.py (email verification flow)
- [ ] T053 Register link handler in backend/app/bot/main.py

### Error Handling & Edge Cases

- [ ] T054 Add LLM unavailable error handling in all handlers
- [ ] T055 Add session expiry handling (24h inactivity)
- [ ] T056 Add graceful shutdown handling in backend/app/bot/main.py

### Final Validation

- [ ] T057 Run full test suite: `pytest backend/tests/`
- [ ] T058 Manual testing per quickstart.md
- [ ] T059 Verify all acceptance scenarios from spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 — can proceed in parallel after Foundational
  - US3 depends on US2 (uses formatters in message handler)
  - US4 and US5 are P3 — can proceed after US1+US2+US3
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 2 (Foundational)
    │
    ├── Phase 3 (US1: /start) ──┐
    │                           │
    └── Phase 4 (US2: recs) ────┼── Phase 5 (US3: formatting)
                                │         │
                                │         ├── Phase 6 (US4: profile)
                                │         │
                                │         └── Phase 7 (US5: help)
                                │
                                └── Phase 8 (Polish)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Service methods before handlers
- Handlers before registration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002, T003, T004 can run in parallel
```

**Phase 2 (Foundational)**:
```
After T005-T008 (model + migration):
  T009, T010, T012 can run in parallel
```

**Phase 3 (US1)**:
```
T013, T014 can run in parallel (tests)
```

**Phase 5 (US3)**:
```
T028, T029 can run in parallel (tests)
T030, T031 can run in parallel (formatters)
```

**Phase 6-7 (US4, US5)**:
```
Can run in parallel if team has capacity
T036, T037, T045, T046 can all run in parallel (tests)
```

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Unit test for wine card formatter in backend/tests/unit/test_telegram_formatters.py"
Task: "Unit test for inline keyboards in backend/tests/unit/test_telegram_keyboards.py"

# Launch formatters in parallel:
Task: "Implement wine card formatter in backend/app/bot/formatters.py"
Task: "Implement characteristic visualizer in backend/app/bot/formatters.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (/start)
4. **STOP and VALIDATE**: Test /start independently
5. Complete Phase 4: User Story 2 (recommendations)
6. **STOP and VALIDATE**: Test recommendations independently
7. Deploy/demo if ready — **This is MVP!**

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (/start) → Test → Deploy (minimal bot)
3. Add US2 (recommendations) → Test → Deploy (**MVP!**)
4. Add US3 (formatting) → Test → Deploy (better UX)
5. Add US4 (profile) → Test → Deploy (personalization)
6. Add US5 (help) → Test → Deploy (complete feature)
7. Add Polish → Test → Deploy (production-ready)

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 + Phase 4**

- User can /start bot and get welcome with wines
- User can ask for recommendations and get responses
- Total: ~27 tasks (T001-T027)

---

## Summary

| Phase | User Story | Priority | Tasks | Test Tasks |
|-------|------------|----------|-------|------------|
| 1 | Setup | - | 4 | 0 |
| 2 | Foundational | - | 8 | 0 |
| 3 | US1: /start | P1 | 8 | 3 |
| 4 | US2: Recommendations | P1 | 7 | 2 |
| 5 | US3: Wine formatting | P2 | 8 | 2 |
| 6 | US4: Profile | P3 | 9 | 2 |
| 7 | US5: Help | P3 | 6 | 2 |
| 8 | Polish | - | 9 | 1 |
| **Total** | | | **59** | **12** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution requires TDD — tests are mandatory
