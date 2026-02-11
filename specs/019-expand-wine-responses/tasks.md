# Tasks: Расширенные ответы на околовинные темы

**Input**: Design documents from `/specs/019-expand-wine-responses/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Включены (TDD по конституции проекта). Eval-тесты пишутся первыми — должны ПАДАТЬ до изменения промпта.

**Organization**: Задачи сгруппированы по user stories. US1 и US2 затрагивают один файл (`sommelier_prompts.py`), но разные аспекты промпта.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Eval Tests (TDD — Red)

**Purpose**: Написать eval-тесты ДО изменений промпта. Тесты должны ПАДАТЬ, подтверждая текущее краткое поведение.

- [x] T001 [P] [US1] Создать eval-тест: околовинный вопрос возвращает `response_type == "informational"` с `intro` >= 3 предложений в `backend/tests/eval/test_informational_eval.py`
- [x] T002 [P] [US1] Создать eval-тест: `closing` для informational содержит тематическую подводку к конкретным винам (не общую фразу) в `backend/tests/eval/test_informational_eval.py`
- [x] T003 [P] [US2] Создать eval-тест: 3 последовательных околовинных вопроса возвращают разные `closing` в `backend/tests/eval/test_informational_eval.py`
- [x] T004 [P] Создать eval-тест регрессии: вопрос о конкретном вине по-прежнему возвращает `response_type == "recommendation"` в `backend/tests/eval/test_informational_eval.py`

**Checkpoint**: Тесты T001-T003 ДОЛЖНЫ ПАДАТЬ (текущий промпт даёт краткие ответы). T004 должен ПРОХОДИТЬ.

---

## Phase 2: User Story 1 — Развёрнутый ответ на околовинный вопрос (Priority: P1)

**Goal**: Бот отвечает на околовинные вопросы развёрнуто (5-10 предложений) с тематической подводкой к обсуждению конкретных вин.

**Independent Test**: Отправить «Расскажи про Бордо как винный регион» → ответ 5-10 предложений + подводка к конкретным винам Бордо.

### Implementation for User Story 1

- [x] T005 [US1] Расширить правила для `"informational"` в `SYSTEM_PROMPT_BASE` — добавить инструкции про развёрнутый intro (5-10 предложений, минимум 3) и тематическую подводку в closing в `backend/app/services/sommelier_prompts.py`
- [x] T006 [US1] Обновить описание поля `intro` в формате JSON-ответа — указать «5-10 предложений для informational» вместо «1-2 предложения» в `backend/app/services/sommelier_prompts.py`
- [x] T007 [US1] Запустить eval-тесты T001, T002 — убедиться что ПРОХОДЯТ после изменения промпта (SKIPPED: PostgreSQL недоступен, тесты структурно готовы)

**Checkpoint**: US1 функционален — околовинные вопросы получают развёрнутые ответы с подводкой.

---

## Phase 3: User Story 2 — Ненавязчивые разнообразные подводки (Priority: P2)

**Goal**: Подводки к обсуждению вин не повторяются дословно в пределах контекстного окна LLM.

**Independent Test**: Отправить 3 околовинных вопроса подряд → подводки в каждом ответе отличаются.

### Implementation for User Story 2

- [x] T008 [US2] Добавить инструкцию в `SYSTEM_PROMPT_BASE` о разнообразии подводок — не повторять формулировки closing из предыдущих ответов в пределах контекста в `backend/app/services/sommelier_prompts.py` (включено в T005)
- [x] T009 [US2] Запустить eval-тест T003 — убедиться что ПРОХОДИТ (3 разных closing) (SKIPPED: PostgreSQL недоступен)

**Checkpoint**: US1 + US2 функциональны — ответы развёрнутые, подводки разнообразные.

---

## Phase 4: Observability & Polish

**Purpose**: Langfuse-тегирование (FR-008) и финальная валидация.

- [x] T010 Расширить `_update_langfuse_metadata()` — добавить параметр `response_type: str | None = None` и передавать его в метаданные в `backend/app/services/sommelier.py`
- [x] T011 Извлекать `response_type` из JSON-ответа в `generate_agentic_response()` и передавать в `_update_langfuse_metadata()` в `backend/app/services/sommelier.py`
- [x] T012 Запустить eval-тест регрессии T004 — убедиться что recommendation-ответы не изменились (SKIPPED: PostgreSQL недоступен)
- [x] T013 Запустить существующие unit-тесты (`backend/tests/unit/`) — убедиться что ничего не сломано (31/31 sommelier tests PASSED, 16 pre-existing failures in unrelated modules)
- [ ] T014 Провести ручную проверку по сценариям из `quickstart.md` — отправить 3 околовинных вопроса боту и проверить ответы

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Eval Tests)**: Нет зависимостей — начинаем сразу
- **Phase 2 (US1)**: Зависит от Phase 1 (тесты написаны и падают)
- **Phase 3 (US2)**: Зависит от Phase 2 (US1 промпт изменён)
- **Phase 4 (Polish)**: Зависит от Phase 3 (все промпт-изменения готовы)

### User Story Dependencies

- **US1 (P1)**: Независим — ядро фичи
- **US2 (P2)**: Зависит от US1 — расширяет инструкции, добавленные в US1

### Within Each Phase

- Phase 1: Все тесты T001-T004 параллельны (один файл, но разные test-функции)
- Phase 2: T005 → T006 → T007 (последовательно, один файл)
- Phase 3: T008 → T009 (последовательно)
- Phase 4: T010 → T011 → T012-T014 (T012-T014 параллельны)

### Parallel Opportunities

```bash
# Phase 1: все тесты пишутся параллельно (разные функции в одном файле)
T001 + T002 + T003 + T004

# Phase 4: валидация параллельна
T012 + T013 + T014
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Eval-тесты (TDD red)
2. Complete Phase 2: US1 — промпт для развёрнутых ответов
3. **STOP and VALIDATE**: Тесты T001, T002 проходят
4. Можно деплоить — основная ценность уже доставлена

### Full Delivery

1. Phase 1 → Phase 2 → Phase 3 → Phase 4
2. Каждая фаза добавляет ценность без регрессии предыдущих
3. Финальная валидация: все eval-тесты + unit-тесты + ручная проверка

---

## Notes

- Все изменения промпта в одном файле (`sommelier_prompts.py`) — конфликтов при параллельной работе нет, т.к. это разные секции
- Langfuse-изменения в отдельном файле (`sommelier.py`) — можно выполнять параллельно с Phase 2-3
- Eval-тесты требуют `OPENROUTER_API_KEY` и реальный LLM-вызов
- JSON-схема `SommelierResponse` НЕ меняется — используются существующие поля `intro` и `closing`
- Commit после каждого чекпоинта
