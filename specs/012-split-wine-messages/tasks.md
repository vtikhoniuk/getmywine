# Tasks: Структурированный формат сообщений с винными рекомендациями

**Input**: Design documents from `/specs/012-split-wine-messages/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Включены — конституция требует TDD и 100% покрытие критичных путей.

**Organization**: Задачи сгруппированы по user story. Функционал уже реализован — основная работа: тесты и рефакторинг дублирования.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Подготовка инфраструктуры тестирования для bot-модуля

- [x] T001 Создать conftest.py с фикстурами для bot-тестов в backend/tests/unit/conftest.py — добавить фикстуру mock_wine (Wine с image_url и без), фикстуру mock_update (мок telegram.Update)

---

## Phase 2: Foundational Tests (Shared Utilities)

**Purpose**: Тесты для утилит, используемых всеми user stories. ДОЛЖНЫ быть написаны до рефакторинга.

**⚠️ CRITICAL**: Эти тесты фиксируют текущее поведение перед рефакторингом. Все должны ПРОЙТИ на текущем коде.

- [x] T002 [P] Написать тесты parse_structured_response() в backend/tests/unit/test_structured_response.py — кейсы: полный ответ с 3 винами (is_structured=True), ответ с 1 вином (is_structured=True, wines=[1 элемент]), ответ без маркеров (is_structured=False), intro без вин (is_structured=False), пустая строка (is_structured=False), пробелы внутри маркеров (strip)
- [x] T003 [P] Написать тесты strip_markdown() в backend/tests/unit/test_structured_response.py — кейсы: удаление **bold**, удаление *italic*, удаление _underline_, текст без markdown (без изменений), комбинированный текст
- [x] T004 [P] Написать тесты sanitize_telegram_markdown() в backend/tests/unit/test_bot_utils.py — кейсы: ### heading → *heading*, **bold** → *bold*, обычный текст (без изменений), несколько заголовков
- [x] T005 [P] Написать тесты get_wine_image_path() в backend/tests/unit/test_bot_utils.py — кейсы: wine.image_url = "/static/images/wines/abc.png" → Path (если файл существует), wine.image_url = None → None, wine.image_url указывает на несуществующий файл → None
- [x] T006 [P] Написать тесты format_wine_photo_caption() в backend/tests/unit/test_bot_formatters.py — кейсы: вино со всеми полями (name, region, country, grapes, sweetness, price_rub), вино без grape_varieties, корректный формат plain text (4 строки), русская и английская локализация sweetness
- [x] T007 [P] Написать тесты get_sweetness_label() в backend/tests/unit/test_bot_formatters.py — кейсы: dry→"сухое"/"dry", semi_dry→"полусухое"/"semi-dry", sweet→"сладкое"/"sweet"
- [x] T008 Запустить все тесты Phase 2 и убедиться, что они проходят на текущем коде — `cd backend && python -m pytest tests/unit/test_structured_response.py tests/unit/test_bot_utils.py tests/unit/test_bot_formatters.py -v`

**Checkpoint**: Все unit-тесты для утилит проходят. Текущее поведение зафиксировано.

---

## Phase 3: User Story 1 — Новый пользователь, 5 сообщений (Priority: P1) 🎯 MVP

**Goal**: Рефакторинг: вынести общую логику отправки 5 сообщений в sender.py. Обработчик /start использует общую функцию.

**Independent Test**: Отправить /start от нового аккаунта → бот присылает ровно 5 сообщений: intro (текст) → wine1 (фото+caption) → wine2 (фото+caption) → wine3 (фото+caption) → closing (текст)

### Tests for User Story 1

- [x] T009 [P] [US1] Написать тесты send_wine_recommendations() — structured path в backend/tests/unit/test_bot_sender.py — кейсы: парсинг успешен + 3 вина с изображениями → 5 вызовов (reply_text, reply_photo×3, reply_text), возвращает True; caption каждого фото ≤1024 символов; caption — plain text (без markdown)
- [x] T010 [P] [US1] Написать тесты send_wine_recommendations() — порядок отправки в backend/tests/unit/test_bot_sender.py — кейс: проверить, что вызовы идут строго последовательно: intro → wine1 → wine2 → wine3 → closing

### Implementation for User Story 1

- [x] T011 [US1] Создать backend/app/bot/sender.py — функция send_wine_recommendations(update, response_text, wines, language) → bool. Извлечь общую логику из handlers/message.py:_send_structured() и handlers/start.py. Логика: parse_structured_response → если is_structured: отправить intro (sanitize_telegram_markdown, Markdown), для каждого wine: get_wine_image_path → если есть: reply_photo(caption=strip_markdown[:1024]), иначе reply_text → отправить closing; вернуть True. Иначе вернуть False.
- [x] T012 [US1] Обновить backend/app/bot/handlers/start.py — заменить дублированную логику отправки на вызов send_wine_recommendations() из sender.py. Сохранить fallback-логику после вызова (если вернул False).
- [x] T013 [US1] Запустить тесты US1 и убедиться, что они проходят — `cd backend && python -m pytest tests/unit/test_bot_sender.py -v -k "structured or order"`

**Checkpoint**: sender.py создан, start.py использует общую функцию. Тесты US1 проходят.

---

## Phase 4: User Story 2 — Возвращающийся пользователь, 5 сообщений (Priority: P1)

**Goal**: Обработчик message.py использует общую функцию send_wine_recommendations(). Первое сообщение — контекст без приветствия.

**Independent Test**: Отправить текстовый запрос от существующего пользователя → бот присылает 5 сообщений без повторного приветствия.

### Tests for User Story 2

- [x] T014 [P] [US2] Написать тест send_wine_recommendations() — возвращающийся пользователь в backend/tests/unit/test_bot_sender.py — кейс: intro не содержит приветствия (проверка через содержимое parsed.intro, переданного в reply_text)

### Implementation for User Story 2

- [x] T015 [US2] Обновить backend/app/bot/handlers/message.py — заменить _send_structured() и дублированную логику на вызов send_wine_recommendations() из sender.py. Сохранить fallback-логику.
- [x] T016 [US2] Запустить тесты US2 и все предыдущие — `cd backend && python -m pytest tests/unit/test_bot_sender.py tests/unit/test_structured_response.py -v`

**Checkpoint**: message.py использует общую функцию. Дублирование устранено. Тесты US1+US2 проходят.

---

## Phase 5: User Story 3 — Фотография бутылки с подписью (Priority: P1)

**Goal**: Тесты для edge cases отображения фото: отсутствие изображения, обрезка caption, менее 3 вин.

**Independent Test**: Запросить рекомендации → каждое из 3 сообщений с вином содержит фото бутылки и подпись (название, регион, тип, цена).

### Tests for User Story 3

- [x] T017 [P] [US3] Написать тест send_wine_recommendations() — вино без изображения в backend/tests/unit/test_bot_sender.py — кейс: wine.image_url=None → reply_text вместо reply_photo для этого вина; остальные вина отправляются как фото
- [x] T018 [P] [US3] Написать тест send_wine_recommendations() — обрезка caption в backend/tests/unit/test_bot_sender.py — кейс: wine_text длиной >1024 символов → caption обрезается до ≤1024; обрезанный caption содержит название вина
- [x] T019 [P] [US3] Написать тест send_wine_recommendations() — менее 3 вин в backend/tests/unit/test_bot_sender.py — кейс: parsed.wines=[1 элемент], wines=[1 wine] → отправляется intro + 1 фото + closing (3 сообщения); parsed.wines=[2 элемента] → intro + 2 фото + closing (4 сообщения)
- [x] T020 [US3] Запустить тесты US3 и все предыдущие — `cd backend && python -m pytest tests/unit/ -v`

**Checkpoint**: Все edge cases фото-сообщений покрыты тестами. Тесты US1+US2+US3 проходят.

---

## Phase 6: User Story 4 — Fallback при ошибке парсинга (Priority: P2)

**Goal**: Тесты для fallback-пути: ответ без маркеров → единое текстовое сообщение + отдельные фото вин.

**Independent Test**: Симулировать ответ без [INTRO]/[WINE:N] маркеров → бот отправляет текст + фото найденных вин.

### Tests for User Story 4

- [x] T021 [P] [US4] Написать тест send_wine_recommendations() — fallback path в backend/tests/unit/test_bot_sender.py — кейс: parse_structured_response возвращает is_structured=False → функция возвращает False
- [x] T022 [P] [US4] Написать тест fallback-логики в хендлере в backend/tests/unit/test_bot_sender.py — кейс: send_wine_recommendations() вернул False → хендлер отправляет: 1 reply_text (полный текст) + reply_photo для каждого вина с format_wine_photo_caption()

### Implementation for User Story 4

- [x] T023 [US4] Вынести fallback-логику отправки из handlers в sender.py — добавить функцию send_fallback_response(update, response_text, wines, language) для отправки единого текста + отдельных фото. Обновить start.py и message.py для использования этой функции.
- [x] T024 [US4] Запустить все тесты — `cd backend && python -m pytest tests/unit/ -v`

**Checkpoint**: Fallback-путь покрыт тестами. Все unit-тесты проходят.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Финальная валидация, линтинг, очистка

- [x] T025 Запустить Ruff на всех изменённых файлах — `cd backend && ruff check app/bot/sender.py app/bot/handlers/start.py app/bot/handlers/message.py && ruff format --check app/bot/sender.py app/bot/handlers/start.py app/bot/handlers/message.py`
- [x] T026 Запустить полный тест-suite — `cd backend && python -m pytest tests/ -v --tb=short`
- [x] T027 Удалить неиспользуемый код из start.py и message.py — убрать дублированные функции, которые были вынесены в sender.py (если остались)
- [ ] T028 Проверить по quickstart.md — ручная верификация: /start → 5 сообщений, текстовый запрос → 5 сообщений, отсутствие фото → текст

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Нет зависимостей
- **Phase 2 (Foundational Tests)**: Зависит от Phase 1 (conftest)
- **Phase 3 (US1)**: Зависит от Phase 2 (тесты утилит должны пройти до рефакторинга)
- **Phase 4 (US2)**: Зависит от Phase 3 (sender.py должен существовать)
- **Phase 5 (US3)**: Зависит от Phase 3 (sender.py должен существовать), может выполняться параллельно с Phase 4
- **Phase 6 (US4)**: Зависит от Phase 3 (sender.py должен существовать), может выполняться параллельно с Phase 4/5
- **Phase 7 (Polish)**: Зависит от всех предыдущих фаз

### User Story Dependencies

- **US1 (P1)**: Создаёт sender.py — БЛОКИРУЕТ US2, US3, US4
- **US2 (P1)**: Зависит от US1 (нужен sender.py). Может выполняться параллельно с US3.
- **US3 (P1)**: Зависит от US1 (нужен sender.py). Может выполняться параллельно с US2.
- **US4 (P2)**: Зависит от US1 (нужен sender.py). Может выполняться параллельно с US2/US3.

### Within Each User Story

- Тесты ДОЛЖНЫ быть написаны ПЕРВЫМИ
- Тесты ДОЛЖНЫ ПРОВАЛИТЬСЯ до реализации (TDD Red)
- Реализация — минимальный код для прохождения тестов (TDD Green)
- После прохождения — checkpoint

### Parallel Opportunities

- Phase 2: T002, T003, T004, T005, T006, T007 — все параллельно (разные файлы)
- Phase 3: T009, T010 — параллельно (один файл, но разные тест-классы)
- Phase 5: T017, T018, T019 — параллельно (разные тест-кейсы)
- Phase 6: T021, T022 — параллельно
- После Phase 3: US2 (Phase 4), US3 (Phase 5), US4 (Phase 6) — параллельно

---

## Parallel Example: Foundational Tests (Phase 2)

```bash
# Все тесты утилит можно писать одновременно:
Task: "T002 — тесты parse_structured_response() в test_structured_response.py"
Task: "T003 — тесты strip_markdown() в test_structured_response.py"
Task: "T004 — тесты sanitize_telegram_markdown() в test_bot_utils.py"
Task: "T005 — тесты get_wine_image_path() в test_bot_utils.py"
Task: "T006 — тесты format_wine_photo_caption() в test_bot_formatters.py"
Task: "T007 — тесты get_sweetness_label() в test_bot_formatters.py"
```

## Parallel Example: After Phase 3

```bash
# US2, US3, US4 могут выполняться параллельно:
Task: "T014+T015 — US2: обновление message.py"
Task: "T017+T018+T019 — US3: edge case тесты фото"
Task: "T021+T022+T023 — US4: fallback тесты и рефакторинг"
```

---

## Implementation Strategy

### MVP First (Phase 1 → Phase 2 → Phase 3)

1. Phase 1: Создать conftest.py
2. Phase 2: Написать тесты для утилит → убедиться что проходят
3. Phase 3: Создать sender.py, обновить start.py → тесты sender проходят
4. **STOP and VALIDATE**: /start от нового пользователя → 5 сообщений

### Incremental Delivery

1. Phase 1+2: Foundational → Тесты утилит проходят
2. Phase 3 (US1): sender.py + start.py → MVP ✓
3. Phase 4 (US2): message.py → Дублирование устранено ✓
4. Phase 5 (US3): Edge case тесты → Все граничные случаи покрыты ✓
5. Phase 6 (US4): Fallback тесты → Полное покрытие ✓
6. Phase 7: Polish → Готово к merge ✓

---

## Notes

- Функционал уже реализован — задачи сосредоточены на тестах и рефакторинге
- Конституция требует TDD — тесты включены во все фазы
- sender.py — единственный новый production-файл
- 4 новых тестовых файла: test_structured_response.py, test_bot_utils.py, test_bot_formatters.py, test_bot_sender.py
- Схема БД не изменяется — миграции не нужны
