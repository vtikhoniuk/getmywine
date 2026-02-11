# Research: Мониторинг LLM через Langfuse

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-10

## Phase 0: Research Decisions

### RD-001: Langfuse Version — v3 Self-Hosted

**Decision**: Langfuse v3 (latest stable, self-hosted)

**Rationale**: v3 — текущая стабильная версия с поддержкой ClickHouse для аналитики, Worker для асинхронной обработки, и MinIO для blob storage. Обратная совместимость с Python SDK. Self-hosted вариант полностью бесплатный.

**Alternatives considered**:
- Langfuse v2 — проще (только PostgreSQL), но deprecated, нет ClickHouse-аналитики
- Langfuse Cloud — не self-hosted, данные уходят на внешний сервер

### RD-002: Docker Compose Architecture — 6 контейнеров

**Decision**: 6 контейнеров Langfuse: `langfuse-web`, `langfuse-worker`, `langfuse-postgres`, `langfuse-clickhouse`, `langfuse-redis`, `langfuse-minio`

**Rationale**: Официальная архитектура Langfuse v3. Все контейнеры обязательны:
- `langfuse-web` (image: `langfuse/langfuse:3`, порт 3000) — UI + API
- `langfuse-worker` (image: `langfuse/langfuse-worker:3`) — фоновая обработка трейсов
- `langfuse-postgres` (image: `postgres:17`, порт 5433) — метаданные, проекты, пользователи
- `langfuse-clickhouse` (image: `clickhouse/clickhouse-server`) — хранение и аналитика трейсов
- `langfuse-redis` (image: `redis:7`) — очередь и кэш
- `langfuse-minio` (image: `cgr.dev/chainguard/minio`) — S3-совместимое blob storage

**Alternatives considered**:
- Использовать существующий PostgreSQL проекта — конфликт миграций, риск порчи основной БД
- Убрать MinIO/ClickHouse — невозможно, Langfuse v3 требует все компоненты

### RD-003: SDK Integration Pattern — OpenAI Wrapper + @observe()

**Decision**: Комбинированный подход:
1. `langfuse.openai.AsyncOpenAI` вместо `openai.AsyncOpenAI` в `OpenRouterService.client`
2. `@observe()` декораторы на `generate_agentic_response`, `execute_search_wines`, `execute_semantic_search`

**Rationale**:
- OpenAI wrapper — 1 строка изменения, автоматически трекирует все LLM-вызовы (FR-001, FR-002)
- `@observe()` — создаёт span hierarchy для agentic loop (FR-003, FR-008)
- Комбинация даёт полный трейс: root span → LLM generation → tool call spans

**Alternatives considered**:
- Только OpenAI wrapper — нет spans для tool calls
- Manual SDK (langfuse.Langfuse()) — слишком много boilerplate кода
- OpenRouter Broadcast — нет контроля над вложенной hierarchy

### RD-004: OpenRouter Compatibility

**Decision**: Langfuse OpenAI wrapper полностью совместим с OpenRouter

**Rationale**: OpenRouter использует OpenAI-совместимый API. Langfuse обёртка работает с любым `base_url`. Для корректного трекинга стоимости рекомендуется `extra_body={"usage": {"include": True}}` (OpenRouter тогда возвращает usage data).

**Source**: [Langfuse OpenRouter Integration](https://langfuse.com/integrations/gateways/openrouter)

### RD-005: Auto-Provisioning Strategy

**Decision**: `LANGFUSE_INIT_*` env vars для zero-config первого запуска

**Rationale**: Langfuse v3 поддерживает auto-provisioning через переменные окружения:
- `LANGFUSE_INIT_ORG_ID`, `LANGFUSE_INIT_ORG_NAME` — организация
- `LANGFUSE_INIT_PROJECT_ID`, `LANGFUSE_INIT_PROJECT_NAME` — проект
- `LANGFUSE_INIT_PROJECT_PUBLIC_KEY`, `LANGFUSE_INIT_PROJECT_SECRET_KEY` — API-ключи
- `LANGFUSE_INIT_USER_EMAIL`, `LANGFUSE_INIT_USER_PASSWORD` — учётная запись

Для dev-окружения предзаданные ключи (`pk-lf-dev`, `sk-lf-dev`) позволяют backend'у подключаться к Langfuse без ручной настройки.

### RD-006: Graceful Degradation Mechanism

**Decision**: Langfuse SDK non-blocking по умолчанию + `LANGFUSE_TRACING_ENABLED` env var

**Rationale**: SDK буферизует события и отправляет асинхронными батчами. При недоступности Langfuse:
- SDK логирует ошибку, но не выбрасывает exception
- Бот продолжает работать без мониторинга
- `LANGFUSE_TRACING_ENABLED=false` полностью отключает трейсинг (нулевой overhead)

Дополнительно: backend в docker-compose НЕ зависит от Langfuse через `depends_on` — стартует независимо.
