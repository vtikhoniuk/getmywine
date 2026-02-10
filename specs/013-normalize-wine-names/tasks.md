# Tasks: Нормализация названий вин и отображение изображений

**Input**: Design documents from `/specs/013-normalize-wine-names/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — конституция проекта требует TDD (Red → Green → Refactor).

**Organization**: Tasks grouped by user story. US2 (фото) и FR-007/008/009 уже реализованы — включены только как верификация.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Создание утилиты нормализации и инфраструктуры тестов

- [X] T001 [P] Create `normalize_wine_name()` function in `backend/app/utils/wine_normalization.py` — алгоритм: strip prefix (Игристое вино/Шампанское/Вино), strip trailing `, {vintage_year}`, strip trailing `, {producer}`, trim. See research.md R-001
- [X] T002 [P] Write unit tests for `normalize_wine_name()` in `backend/tests/unit/test_wine_name_normalization.py` — cover all 4 patterns (A: standard 36 wines, B: producer embedded 8 wines, C: no year 4 wines, D: no year+no comma 2 wines), edge cases (trailing space wine #39, trailing period wine #26, «в подарочной упаковке» wine #45), verify all 50 names unique after normalization

**Checkpoint**: `normalize_wine_name()` passes all unit tests on 4 patterns + edge cases

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Обновление seed-данных — блокирует миграцию и тесты matching

**⚠️ CRITICAL**: Миграция и matching зависят от нормализованного seed

- [X] T003 Apply `normalize_wine_name()` to all 50 wines in `backend/app/data/wines_seed.json` — update `name` field for each wine using the function with that wine's `producer` and `vintage_year` values. Verify: no name starts with «Вино»/«Игристое вино»/«Шампанское», all 50 names unique

**Checkpoint**: wines_seed.json содержит нормализованные name для всех 50 вин

---

## Phase 3: User Story 1 — Чистые названия вин в каталоге (Priority: P1) 🎯 MVP

**Goal**: Поле name в БД содержит только собственное название вина. LLM-matching работает по прямому поиску нормализованного name.

**Independent Test**: Запустить миграцию → проверить SELECT name FROM wines: ни одно name не начинается с «Вино»/«Игристое вино»/«Шампанское»; отправить запрос боту → 3 вина с фотографиями.

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] [US1] Write test for Alembic migration in `backend/tests/unit/test_migration_normalize_names.py` — test that `normalize_wine_name()` is applied to all wines in DB, verify no prefixes remain, all names unique. Mock DB data with sample wines from each pattern (A, B, C, D)
- [X] T005 [P] [US1] Write tests for simplified `_extract_wines_from_response()` in `backend/tests/unit/test_extract_wines.py` — test direct name matching (wine.name found in LLM text → matched), test no match when name absent, test ordering by position in text, test max_wines=3 limit. Verify old workaround regex code is removed

### Implementation for User Story 1

- [X] T006 [US1] Create Alembic migration `backend/migrations/versions/013_normalize_wine_names.py` — SELECT id, name, producer, vintage_year FROM wines → apply `normalize_wine_name()` → UPDATE name WHERE id. Import function from `app.utils.wine_normalization`. Downgrade: pass (irreversible data migration)
- [X] T007 [US1] Simplify `_extract_wines_from_response()` in `backend/app/services/telegram_bot.py` (lines 293-347) — remove 3-level matching workaround (regex strip «Вино» prefix, regex strip vintage year). Replace with single-level: `candidates = [wine.name]`, direct `response_text.find(wine.name)`. Remove `import re` if no longer needed in method
- [X] T008 [US1] Run all existing tests to verify no regressions: `pytest backend/tests/unit/test_bot_sender.py backend/tests/unit/test_wine_name_normalization.py backend/tests/unit/test_extract_wines.py -v`

**Checkpoint**: Миграция нормализует names в БД; matching упрощён до прямого поиска; все тесты проходят

---

## Phase 4: User Story 2 — Корректное отображение фото бутылок (Priority: P1) ✅ DONE

**Goal**: Фото бутылки масштабировано, отцентрировано на белом фоне, высота настраивается.

**Independent Test**: Отправить запрос боту → фото с белым фоном, бутылка по центру, высота = TELEGRAM_WINE_PHOTO_HEIGHT.

**Status**: FR-007, FR-008, FR-009 уже реализованы:
- `prepare_wine_photo()` в `backend/app/bot/sender.py` — ресайз + белый фон ✅
- `telegram_wine_photo_height` в `backend/app/config.py` — настраиваемая высота ✅
- `format_wine_photo_caption()` в `backend/app/bot/formatters.py` — caption из полей ✅
- Тесты в `backend/tests/unit/test_bot_sender.py` — обновлены ✅
- `TELEGRAM_WINE_PHOTO_HEIGHT` в `docker-compose.yml` — добавлено ✅
- `Pillow>=10.0.0` в `backend/requirements.txt` — добавлено ✅

- [X] T009 [US2] Verify US2 implementation: run `pytest backend/tests/unit/test_bot_sender.py -v` and confirm all 12 tests pass (T009-T022). No new code required

**Checkpoint**: US2 полностью реализована и протестирована

---

## Phase 5: User Story 3 — Полнота структурированных данных (Priority: P2)

**Goal**: Все характеристики вин заполнены в отдельных полях, name не дублирует данные из других полей.

**Independent Test**: Проверить wines_seed.json: у каждого из 50 вин заполнены name, producer, vintage_year (или null для NV), country, region, grape_varieties, wine_type, sweetness, price_rub.

- [X] T010 [P] [US3] Write validation test in `backend/tests/unit/test_wine_seed_completeness.py` — load wines_seed.json, for each of 50 wines verify: name is non-empty and normalized (no prefix/producer/year), producer is non-empty, country is non-empty, region is non-empty, grape_varieties is non-empty list, wine_type is valid enum, sweetness is valid enum, price_rub > 0. vintage_year is int or null (6 NV wines)
- [X] T011 [US3] Run seed completeness test: `pytest backend/tests/unit/test_wine_seed_completeness.py -v`

**Checkpoint**: Все 50 вин имеют полные структурированные данные, name нормализовано

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Эмбеддинги, финальная верификация

- [ ] T012 Пересчитать эмбеддинги после миграции: run `docker compose exec backend python -m app.scripts.generate_embeddings` — verify embeddings updated for all 50 wines (requires API key). This is a separate phase per FR-005 (two-phase migration)
- [ ] T013 End-to-end verification: send a wine recommendation request via Telegram bot → verify 3 wines matched with photos, names displayed correctly in captions
- [X] T014 Run full test suite: `pytest backend/tests/ -v` — 239 unit tests pass, 0 new failures (29 pre-existing infrastructure failures in test_wine_repository, test_wine_api, test_wine_search, test_chat_service, test_proactive_suggestions unrelated to this feature)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 can run in parallel
- **Foundational (Phase 2)**: Depends on T001 (normalize function)
- **US1 (Phase 3)**: Depends on Phase 2 (normalized seed); T004/T005 parallel, then T006/T007 sequential
- **US2 (Phase 4)**: No dependencies — already implemented, verification only
- **US3 (Phase 5)**: Depends on Phase 2 (normalized seed)
- **Polish (Phase 6)**: Depends on US1 completion (migration applied)

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational — core deliverable, enables photo matching
- **US2 (P1)**: Independent — already done, verification only
- **US3 (P2)**: Depends on Foundational — can run parallel with US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per constitution)
- Migration before matching simplification (Database First per constitution)
- All tests pass before moving to next phase

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T004 and T005 can run in parallel (different test files)
- T009 and T010 can run in parallel (independent stories)
- US1 and US3 implementation can proceed in parallel after Phase 2

---

## Parallel Example: User Story 1

```bash
# Tests in parallel (TDD Red phase):
Task: "Write migration test in backend/tests/unit/test_migration_normalize_names.py"
Task: "Write matching test in backend/tests/unit/test_extract_wines.py"

# Then implementation sequentially (TDD Green phase):
Task: "Create Alembic migration 013_normalize_wine_names.py"
Task: "Simplify _extract_wines_from_response() in telegram_bot.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Create `normalize_wine_name()` + tests
2. Complete Phase 2: Update wines_seed.json
3. Complete Phase 3: Migration + simplified matching
4. **STOP and VALIDATE**: Run migration, test bot in Telegram
5. Deploy if matching works

### Incremental Delivery

1. Setup + Foundational → normalize function ready, seed updated
2. US1 → Migration + matching simplified → **MVP deployed** 🎯
3. US2 → Verify (already done) → Confirm photos working
4. US3 → Seed completeness validated → Data quality confirmed
5. Polish → Embeddings recomputed → Semantic search restored

---

## Notes

- [P] tasks = different files, no dependencies
- US2 is fully implemented — T009 is verification only
- T012 (embeddings) requires API key and is intentionally separate from migration (FR-005)
- Constitution mandates TDD: tests T002, T004, T005, T010 must fail before corresponding implementation
- Total: 14 tasks (4 test tasks, 6 implementation tasks, 1 seed update, 3 verification/polish)
