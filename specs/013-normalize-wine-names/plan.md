# Implementation Plan: Нормализация названий вин и отображение изображений

**Branch**: `013-normalize-wine-names` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-normalize-wine-names/spec.md`

## Summary

Алгоритмическая нормализация поля `name` в wines_seed.json и БД: функция `normalize_wine_name(name, producer, vintage_year)` удаляет категорийный префикс, `, {year}` и `, {producer}` с конца строки. Работает для всех 4 паттернов (проверено на 50 винах). Упрощение matching до прямого поиска по нормализованному name. Двухфазная миграция: обновление names в Alembic (алгоритмом), пересчёт эмбеддингов — отдельным скриптом. FR-007/FR-008/FR-009 уже реализованы.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Alembic, python-telegram-bot 21.x, Pillow, openai (embeddings)
**Storage**: PostgreSQL 16 + pgvector (HNSW index, cosine distance)
**Testing**: pytest + pytest-asyncio (unit/integration/contract)
**Target Platform**: Linux server (Docker Compose)
**Project Type**: web (backend-only for this feature)
**Performance Goals**: N/A (50 wines, batch migration)
**Constraints**: Embedding API может быть недоступен — миграция names не должна блокироваться
**Scale/Scope**: 50 вин в каталоге, 4 структурных паттерна name, 3 категорийных префикса

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture (Routers → Services → Repos → Models) | PASS | Изменения затрагивают seed-данные, миграцию, сервис telegram_bot и sender — каждый на своём слое |
| Database First (сначала миграция, потом код) | PASS | Alembic-миграция обновляет names в БД; код matching упрощается после |
| TDD | PASS | Тесты для нормализации seed, matching, и caption уже частично есть; новые тесты создаются до кода |
| RAG-First (рекомендации из каталога) | PASS | Нормализация улучшает точность RAG — LLM использует name «ТОЧНО как в каталоге», matching становится надёжнее |
| 18+ / нет продаж | N/A | Не затрагивается |
| Образование > конверсия | N/A | Не затрагивается |
| Приватность данных | N/A | Не затрагивается |
| Ruff / Commitizen | PASS | Соблюдается |
| 100% покрытие критичных путей | PASS | RAG-matching — критичный путь, тесты обязательны |

**Результат GATE**: Все применимые принципы соблюдены. Нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/013-normalize-wine-names/
├── spec.md              # Feature specification (clarified)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── data/
│   │   └── wines_seed.json          # MODIFY: нормализовать name для 50 вин
│   ├── models/
│   │   └── wine.py                  # READ ONLY: модель не меняется
│   ├── services/
│   │   ├── telegram_bot.py          # MODIFY: упростить _extract_wines_from_response()
│   │   └── sommelier_prompts.py     # READ ONLY: format_wine_catalog_for_prompt() уже использует wine.name
│   ├── bot/
│   │   ├── sender.py                # DONE: prepare_wine_photo() уже реализован
│   │   └── formatters.py            # DONE: format_wine_photo_caption() уже реализован
│   ├── repositories/
│   │   └── wine.py                  # READ ONLY: update_embedding() уже есть
│   ├── scripts/
│   │   └── generate_embeddings.py   # READ ONLY: скрипт пересчёта эмбеддингов уже есть
│   └── config.py                    # DONE: telegram_wine_photo_height уже добавлен
├── migrations/
│   └── versions/
│       └── 013_normalize_wine_names.py  # NEW: Alembic-миграция обновления names
└── tests/
    └── unit/
        ├── test_bot_sender.py       # DONE: тесты sender уже обновлены
        ├── test_wine_name_normalization.py  # NEW: тесты нормализации seed-данных
        └── test_extract_wines.py    # NEW: тесты упрощённого matching
```

**Structure Decision**: Существующая структура backend/ полностью подходит. Новых модулей не требуется — только изменения в существующих файлах и одна новая миграция.

## Complexity Tracking

Нет нарушений конституции — таблица не требуется.

## Constitution Re-check (Post Phase 1 Design)

| Принцип | Статус | Обоснование |
|---------|--------|-------------|
| Clean Architecture | PASS | Миграция (data layer) → seed (data) → service (matching) — каждое изменение на своём слое |
| Database First | PASS | Alembic-миграция 013 обновляет names до изменения кода matching |
| TDD | PASS | Тесты для нормализации и matching создаются до реализации |
| RAG-First | PASS | Короткие нормализованные names → лучший matching → LLM возвращает точные имена |
| 100% покрытие критичных путей | PASS | Matching — критичный путь, покрывается unit-тестами |

**Результат**: Дизайн не вводит новых нарушений. Все GATE пройдены.

## Generated Artifacts

| Артефакт | Путь | Описание |
|----------|------|----------|
| research.md | [research.md](research.md) | 8 решений: стратегия нормализации, миграция, эмбеддинги, matching, анализ паттернов |
| data-model.md | [data-model.md](data-model.md) | Нормализационная карта 50 вин, validation rules |
| quickstart.md | [quickstart.md](quickstart.md) | Порядок внедрения, проверки, конфигурация |

**Примечание**: contracts/ не создаётся — фича не добавляет новых API endpoints.
