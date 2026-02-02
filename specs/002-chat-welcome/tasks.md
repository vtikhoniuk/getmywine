# Tasks: Chat Welcome & AI Greeting

**Input**: Design documents from `/specs/002-chat-welcome/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/chat-api.yaml

**Tests**: Включены согласно принципу TDD из конституции.

**Organization**: Задачи сгруппированы по User Stories для независимой реализации и тестирования.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно запускать параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой User Story относится задача (US1, US2, US3, US4)

---

## Phase 1: Setup

**Purpose**: Подготовка структуры для новой фичи

- [ ] T001 Verify existing backend structure from US-001 is functional
- [ ] T002 [P] Create empty test files structure in backend/tests/

---

## Phase 2: Foundational (Database & Core Models)

**Purpose**: Базовая инфраструктура, которая ДОЛЖНА быть готова до начала User Stories

**⚠️ CRITICAL**: Работа над User Stories не может начаться до завершения этой фазы

- [ ] T003 Create Alembic migration 004_create_chat_tables.py in backend/migrations/versions/
- [ ] T004 Apply migration and verify tables created
- [ ] T005 [P] Create MessageRole enum in backend/app/models/message.py
- [ ] T006 [P] Create Conversation model in backend/app/models/conversation.py
- [ ] T007 [P] Create Message model in backend/app/models/message.py
- [ ] T008 [P] Create Pydantic schemas in backend/app/schemas/chat.py
- [ ] T009 [P] Create ConversationRepository in backend/app/repositories/conversation.py
- [ ] T010 [P] Create MessageRepository in backend/app/repositories/message.py
- [ ] T011 [P] Unit tests for models in backend/tests/unit/test_chat_models.py

**Checkpoint**: Foundation ready — можно начинать работу над User Stories

---

## Phase 3: User Story 1 - First Visit Welcome (Priority: P1) 🎯 MVP

**Goal**: Новый пользователь видит приветственное сообщение при первом входе в чат

**Independent Test**: Создать пользователя, открыть чат — должно появиться приветственное сообщение

### Tests for User Story 1

> **NOTE: Написать тесты ПЕРВЫМИ, убедиться что они ПАДАЮТ**

- [ ] T012 [P] [US1] Contract test for GET /chat/conversation (new user) in backend/tests/contract/test_chat_conversation.py
- [ ] T013 [P] [US1] Contract test for GET /chat/conversation (401 unauthorized) in backend/tests/contract/test_chat_conversation.py

### Implementation for User Story 1

- [ ] T014 [US1] Create ChatService with get_or_create_conversation() in backend/app/services/chat.py
- [ ] T015 [US1] Implement welcome message creation logic in ChatService
- [ ] T016 [US1] Create chat router with GET /api/v1/chat/conversation in backend/app/routers/chat.py
- [ ] T017 [US1] Register chat router in backend/app/main.py
- [ ] T018 [US1] Integration test: first visit shows welcome in backend/tests/integration/test_chat_welcome.py

**Checkpoint**: User Story 1 завершена — новые пользователи видят приветствие

---

## Phase 4: User Story 2 - Chat Interface (Priority: P1)

**Goal**: Пользователь может отправить сообщение и получить ответ от AI

**Independent Test**: Отправить сообщение в чат — AI отвечает

### Tests for User Story 2

- [ ] T019 [P] [US2] Contract test for POST /chat/messages (success) in backend/tests/contract/test_chat_messages.py
- [ ] T020 [P] [US2] Contract test for POST /chat/messages (validation error) in backend/tests/contract/test_chat_messages.py
- [ ] T021 [P] [US2] Contract test for POST /chat/messages (401 unauthorized) in backend/tests/contract/test_chat_messages.py
- [ ] T022 [P] [US2] Unit test for MockAIService in backend/tests/unit/test_ai_mock.py

### Implementation for User Story 2

- [ ] T023 [US2] Create MockAIService in backend/app/services/ai_mock.py
- [ ] T024 [US2] Implement send_message() in ChatService in backend/app/services/chat.py
- [ ] T025 [US2] Add POST /api/v1/chat/messages endpoint in backend/app/routers/chat.py
- [ ] T026 [US2] Create chat.html template with message input in backend/app/templates/chat.html
- [ ] T027 [US2] Add /chat page route in backend/app/routers/pages.py
- [ ] T028 [US2] Add JavaScript for sending messages and loading indicator in backend/app/templates/chat.html
- [ ] T029 [US2] Integration test: send message and receive AI response in backend/tests/integration/test_chat_flow.py

**Checkpoint**: User Stories 1 и 2 завершены — полноценный чат с приветствием и ответами AI

---

## Phase 5: User Story 3 - Age Restriction Display (Priority: P2)

**Goal**: На странице чата отображается предупреждение 18+

**Independent Test**: Открыть чат — видно предупреждение о возрастном ограничении

### Tests for User Story 3

- [ ] T030 [US3] Contract test: chat page contains 18+ warning in backend/tests/contract/test_chat_page.py

### Implementation for User Story 3

- [ ] T031 [US3] Add 18+ warning banner to chat.html header in backend/app/templates/chat.html
- [ ] T032 [US3] Style 18+ warning to be visible without scrolling in backend/app/templates/chat.html

**Checkpoint**: User Story 3 завершена — юридическое требование выполнено

---

## Phase 6: User Story 4 - Returning User (Priority: P2)

**Goal**: Вернувшийся пользователь видит историю предыдущих сообщений

**Independent Test**: Отправить сообщения, выйти, зайти снова — история сохранена

### Tests for User Story 4

- [ ] T033 [P] [US4] Contract test for GET /chat/messages/history in backend/tests/contract/test_chat_history.py
- [ ] T034 [P] [US4] Contract test for history pagination in backend/tests/contract/test_chat_history.py

### Implementation for User Story 4

- [ ] T035 [US4] Implement get_message_history() in ChatService in backend/app/services/chat.py
- [ ] T036 [US4] Add GET /api/v1/chat/messages/history endpoint in backend/app/routers/chat.py
- [ ] T037 [US4] Add infinite scroll or "load more" to chat.html in backend/app/templates/chat.html
- [ ] T038 [US4] Integration test: returning user sees history in backend/tests/integration/test_chat_history.py

**Checkpoint**: Все User Stories завершены

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Улучшения, затрагивающие несколько User Stories

- [ ] T039 Add error handling for AI timeout (30s) in backend/app/services/chat.py
- [ ] T040 Add network error handling in chat.html JavaScript
- [ ] T041 [P] Add message length validation (max 2000) to frontend in backend/app/templates/chat.html
- [ ] T042 [P] Add logging for chat operations in backend/app/services/chat.py
- [ ] T043 Run all tests and fix any failures
- [ ] T044 Rebuild Docker image and verify all endpoints work
- [ ] T045 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Нет зависимостей — можно начинать сразу
- **Phase 2 (Foundational)**: Зависит от Phase 1 — **БЛОКИРУЕТ** все User Stories
- **Phase 3-6 (User Stories)**: Все зависят от Phase 2
  - US1 и US2 — P1, критичны для MVP
  - US3 и US4 — P2, можно отложить
- **Phase 7 (Polish)**: Зависит от всех User Stories

### User Story Dependencies

- **User Story 1 (P1)**: Может начаться после Phase 2 — независима
- **User Story 2 (P1)**: Может начаться после Phase 2 — использует ChatService из US1
- **User Story 3 (P2)**: Может начаться после US2 (нужен chat.html)
- **User Story 4 (P2)**: Может начаться после Phase 2 — независима

### Within Each User Story

- Тесты ДОЛЖНЫ быть написаны и ПАДАТЬ до реализации
- Models → Repositories → Services → Routers → Frontend
- Story завершена → переход к следующей

### Parallel Opportunities

- T005-T011 (Phase 2) — все модели и схемы параллельно
- T012-T013, T019-T022 (Tests) — тесты параллельно внутри фазы
- T033-T034 (US4 tests) — параллельно

---

## Parallel Example: Phase 2

```bash
# Запустить все модели параллельно:
Task: "Create MessageRole enum in backend/app/models/message.py"
Task: "Create Conversation model in backend/app/models/conversation.py"
Task: "Create Message model in backend/app/models/message.py"
Task: "Create Pydantic schemas in backend/app/schemas/chat.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Завершить Phase 1: Setup
2. Завершить Phase 2: Foundational (CRITICAL)
3. Завершить Phase 3: User Story 1 (приветствие)
4. Завершить Phase 4: User Story 2 (отправка сообщений)
5. **СТОП и ВАЛИДАЦИЯ**: Протестировать чат независимо
6. Deploy/demo если готово

### Incremental Delivery

1. Setup + Foundational → База готова
2. + User Story 1 → Приветствие работает → Demo
3. + User Story 2 → Чат работает → Demo (MVP!)
4. + User Story 3 → 18+ предупреждение → Demo
5. + User Story 4 → История сохраняется → Demo

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Setup | 2 | Проверка структуры |
| Foundational | 9 | Миграции, модели, схемы |
| US1 (P1) | 7 | Приветствие |
| US2 (P1) | 11 | Чат-интерфейс |
| US3 (P2) | 3 | 18+ предупреждение |
| US4 (P2) | 6 | История сообщений |
| Polish | 7 | Ошибки, валидация |
| **Total** | **45** | |

---

## Notes

- [P] tasks = разные файлы, нет зависимостей
- [Story] label связывает задачу с User Story
- Каждая User Story независимо тестируема
- Проверять что тесты падают до реализации
- Коммит после каждой задачи или логической группы
- Остановка на чекпоинте для валидации
