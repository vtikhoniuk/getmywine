# Implementation Plan: Wine Catalog

**Branch**: `005-wine-catalog` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-wine-catalog/spec.md`

## Summary

Реализация каталога вин для AI-Sommelier: модель данных Wine с полным набором характеристик, API для CRUD и поиска (включая семантический через pgvector), и seed data из 50 реальных вин с изображениями.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, pgvector, Alembic
**Storage**: PostgreSQL 16 + pgvector extension
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux server (Docker)
**Project Type**: web (backend with SSR frontend)
**Performance Goals**: поиск по типу <100ms p95, семантический поиск <500ms p95
**Constraints**: RAG-first (только вина из каталога), 152-ФЗ (данные в РФ)
**Scale/Scope**: 50 вин на старте, масштабируется до 10K

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture | PASS | Routers → Services → Repositories → Models |
| Database First | PASS | Начинаем с миграции для таблицы wines |
| TDD | PASS | Тесты пишутся до реализации |
| RAG-First | PASS | pgvector для семантического поиска, все рекомендации из каталога |
| 18+ и никаких продаж | PASS | Только рекомендации, нет ссылок на покупку |
| Образование > конверсия | PASS | Описания и tasting notes для обучения |
| Приватность данных | N/A | Каталог публичный, не содержит личных данных |

**Result**: All gates PASS

## Project Structure

### Documentation (this feature)

```text
specs/005-wine-catalog/
├── plan.md              # This file
├── research.md          # Phase 0: источники данных, pgvector setup
├── data-model.md        # Phase 1: Wine entity, enums
├── quickstart.md        # Phase 1: как запустить и протестировать
├── contracts/           # Phase 1: OpenAPI schemas
│   └── wine-api.yaml
└── tasks.md             # Phase 2 (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── wine.py              # Wine model + enums
│   ├── schemas/
│   │   └── wine.py              # Pydantic schemas
│   ├── repositories/
│   │   └── wine.py              # Wine repository (CRUD + search)
│   ├── services/
│   │   └── wine.py              # Wine service (business logic)
│   ├── routers/
│   │   └── wine.py              # Wine API endpoints
│   └── core/
│       └── embeddings.py        # pgvector utilities
├── migrations/versions/
│   ├── 005_create_wines_table.py
│   └── 006_seed_wines.py
└── tests/
    ├── unit/
    │   └── test_wine_service.py
    ├── integration/
    │   └── test_wine_api.py
    └── fixtures/
        └── wines.py             # Test wine data
```

**Structure Decision**: Следуем существующей структуре backend/ с Clean Architecture layers.

## Complexity Tracking

> No violations — standard implementation within existing architecture.
