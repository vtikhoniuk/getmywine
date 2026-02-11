# Implementation Plan: Мониторинг LLM через Langfuse

**Branch**: `017-langfuse-monitoring` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-langfuse-monitoring/spec.md`

## Summary

Self-hosted Langfuse v3 как Docker Compose-сервис для мониторинга LLM-запросов сомелье-бота. Langfuse SDK интегрируется в `LLMService` (OpenAI wrapper) и `SommelierService` (`@observe()` декоратор), обеспечивая автоматический трейсинг вызовов LLM, tool calls, стоимости и токенов. 6 дополнительных контейнеров (langfuse-web, langfuse-worker, PostgreSQL для Langfuse, ClickHouse, Redis, MinIO) добавляются в docker-compose.yml. Трейсинг non-blocking — отказ Langfuse не влияет на работу бота.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: langfuse (Python SDK), openai (уже установлен — Langfuse обёртка совместима), Docker Compose
**Storage**: PostgreSQL 17 (отдельный для Langfuse), ClickHouse (аналитика трейсов), MinIO (blob storage), Redis 7 (очередь)
**Testing**: Ручная проверка — отправить запрос боту, проверить трейс в Langfuse UI
**Target Platform**: Linux (WSL2 / Docker)
**Project Type**: web (backend — Python/FastAPI, существующий проект)
**Performance Goals**: Латентность ответа бота увеличивается не более чем на 5% (SC-005)
**Constraints**: Self-hosted only (dev-окружение); Langfuse SDK non-blocking по умолчанию; порт PostgreSQL Langfuse не должен конфликтовать с основной БД (5432 → 5433)
**Scale/Scope**: ~50 запросов/день (dev), 6 новых Docker-контейнеров, 4 файла бэкенда модифицируются (llm.py, sommelier.py, config.py, requirements.txt)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **Clean Architecture** (Routers → Services → Repositories → Models) | PASS | Langfuse SDK интегрируется на уровне Services (LLMService, SommelierService). Не затрагивает Routers, Repositories, Models. `@observe()` декоратор — cross-cutting concern, не нарушает слоёв |
| **Database First** (миграции → код) | PASS | Langfuse использует собственную БД (отдельный PostgreSQL). Никаких миграций в основной БД приложения не требуется |
| **TDD** (Red → Green → Refactor) | N/A | Мониторинг не добавляет бизнес-логику — это observability layer. Проверяется ручным smoke-тестом (отправить запрос → проверить трейс в UI) |
| **RAG-First** (рекомендации только из каталога) | PASS | Langfuse только наблюдает за RAG-pipeline, не модифицирует его |
| **18+ и никаких продаж** | N/A | Мониторинг не затрагивает пользовательский интерфейс |
| **Образование > конверсия** | N/A | Мониторинг не затрагивает контент рекомендаций |
| **Приватность данных** | PASS | Self-hosted Langfuse — данные хранятся локально. В dev-окружении нет реальных пользовательских данных |
| **Ruff** (линтинг) | PASS | Новый код (минимальные изменения) соответствует Ruff-стандартам |
| **100% покрытие критичных путей** | PASS | Langfuse observability не является критичным путём — это non-blocking monitoring |

Все gates пройдены. Нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/017-langfuse-monitoring/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: data model (Langfuse entities)
├── quickstart.md        # Phase 1: how to run Langfuse
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                      # MODIFIED: add Langfuse env vars
│   ├── services/
│   │   ├── llm.py                     # MODIFIED: replace AsyncOpenAI with langfuse wrapper
│   │   └── sommelier.py              # MODIFIED: add @observe() decorators
│   └── ...
├── requirements.txt                   # MODIFIED: add langfuse dependency
└── ...

docker-compose.yml                     # MODIFIED: add 6 Langfuse containers
.env.example                           # MODIFIED: add Langfuse env vars
```

**Structure Decision**: Минимальные изменения в существующем коде. Langfuse SDK интегрируется через: 1) замену `openai.AsyncOpenAI` на `langfuse.openai.AsyncOpenAI` в LLMService, 2) `@observe()` декораторы на ключевых методах SommelierService. Docker-инфраструктура добавляется в существующий docker-compose.yml.

## Design Decisions

### 1. SDK Integration: OpenAI Wrapper + @observe() Decorator

**Decision**: Комбинированный подход — OpenAI SDK wrapper для автоматического трейсинга LLM-вызовов + `@observe()` для agentic loop hierarchy.

**Rationale**: OpenAI wrapper (`langfuse.openai.AsyncOpenAI`) — замена одного импорта в `OpenRouterService.client`, автоматически захватывает все `chat.completions.create()` и `embeddings.create()` вызовы с токенами, стоимостью, латентностью. `@observe()` на `generate_agentic_response`, `execute_search_wines`, `execute_semantic_search` создаёт иерархию spans в трейсе.

**Alternatives rejected**:
- Только OpenAI wrapper — не создаёт spans для tool execution (FR-003)
- Только manual SDK (`langfuse.Langfuse()`) — избыточный boilerplate для автоматически трекируемых LLM-вызовов
- OpenRouter Broadcast — нет контроля над метаданными и hierarchy

### 2. Separate PostgreSQL for Langfuse

**Decision**: Отдельный PostgreSQL 17 для Langfuse (порт 5433), не трогая основную БД приложения (pgvector на порту 5432).

**Rationale**: Langfuse использует собственные миграции и схему. Смешивание с основной БД создаёт риск конфликтов миграций и усложняет бэкап/восстановление. Langfuse-PostgreSQL — обычный Postgres 17, без pgvector.

**Alternatives rejected**:
- Общая БД — конфликт миграций, усложнение бэкапов
- SQLite — Langfuse v3 не поддерживает SQLite

### 3. Port Mapping Strategy

**Decision**: Langfuse web на порту 3000, Langfuse PostgreSQL на 5433, остальные Langfuse-сервисы на localhost-only портах.

**Rationale**: Порт 5432 занят основной БД. ClickHouse (8123/9000), Redis (6379), MinIO (9090) не конфликтуют с существующими сервисами. Только langfuse-web и MinIO API доступны снаружи.

### 4. Graceful Degradation

**Decision**: Langfuse SDK non-blocking по умолчанию. Дополнительно: `LANGFUSE_TRACING_ENABLED` env var для полного отключения.

**Rationale**: SDK буферизует трейсы и отправляет асинхронно. При недоступности Langfuse — SDK логирует ошибку, но не блокирует ответ бота. `depends_on` в docker-compose БЕЗ `condition: service_healthy` для langfuse — backend стартует независимо.

### 5. Auto-provisioning via LANGFUSE_INIT_* Variables

**Decision**: Использовать `LANGFUSE_INIT_*` env vars для автоматического создания организации, проекта и пользователя при первом запуске.

**Rationale**: Zero-config requirement (FR-004, US3). Разработчик выполняет `docker compose up` и сразу получает готовый проект с ключами API. Без auto-provisioning потребуется ручная настройка через UI.

## Complexity Tracking

> Нет нарушений Constitution Check — таблица не требуется.
