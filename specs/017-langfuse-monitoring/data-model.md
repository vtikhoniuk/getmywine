# Data Model: Мониторинг LLM через Langfuse

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-10

## Entities

> Langfuse управляет собственными данными в отдельной БД. Эта модель описывает **концептуальные сущности** для интеграции SDK, а не таблицы в основной БД приложения.

### Trace

Полный путь обработки одного запроса пользователя.

| Attribute | Type | Description |
|-----------|------|-------------|
| id | string (auto) | Уникальный ID трейса (генерируется Langfuse) |
| name | string | Имя трейса — первые 50 символов запроса пользователя |
| session_id | string | ID Telegram-сессии пользователя |
| user_id | string | Telegram user ID |
| input | string | Полный текст запроса пользователя |
| output | string | Финальный ответ бота |
| metadata | dict | `{"tool_used": "search_wines", "iterations": 1}` |
| tags | list[str] | `["telegram", "agentic"]` |

### Span (Generation)

Отдельный LLM-вызов внутри трейса.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | Имя generation (автоматически из OpenAI wrapper) |
| model | string | `anthropic/claude-sonnet-4` |
| input_tokens | int | Количество input-токенов |
| output_tokens | int | Количество output-токенов |
| total_cost | float | Стоимость в USD (из OpenRouter usage) |
| latency_ms | int | Время выполнения в мс |
| prompt | list[dict] | Messages массив, отправленный в LLM |
| completion | string | Ответ LLM (content + tool_calls) |

### Span (Tool Call)

Выполнение инструмента внутри agentic loop.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | `execute_search_wines` или `execute_semantic_search` |
| input | dict | Аргументы инструмента (фильтры или query) |
| output | string | JSON-результат (список вин) |
| latency_ms | int | Время выполнения SQL/pgvector запроса |

### Score

Ручная или автоматическая оценка качества.

| Attribute | Type | Description |
|-----------|------|-------------|
| trace_id | string | Ссылка на трейс |
| name | string | Имя метрики (e.g., `quality`, `relevance`) |
| value | float | Числовое значение (0.0–1.0) |
| comment | string | Комментарий разработчика |

## Relationships

```text
Trace (1 per user request)
├── Span: generate_agentic_response (@observe)
│   ├── Generation: LLM call #1 (OpenAI wrapper, auto)
│   ├── Span: execute_search_wines (@observe)
│   ├── Generation: LLM call #2 (after tool result, auto)
│   └── Span: execute_semantic_search (@observe, if used)
└── Score (0..N, manual via UI)
```

## Configuration Model

Новые env vars в `Settings` (config.py):

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LANGFUSE_SECRET_KEY` | str | `""` | Langfuse project secret key |
| `LANGFUSE_PUBLIC_KEY` | str | `""` | Langfuse project public key |
| `LANGFUSE_HOST` | str | `"http://langfuse-web:3000"` | Langfuse server URL |
| `LANGFUSE_TRACING_ENABLED` | bool | `true` | Enable/disable tracing |

## No Migrations Required

Langfuse хранит все данные в собственной БД (`langfuse-postgres`). Основная БД приложения (`db`) не затрагивается. Никаких Alembic-миграций не требуется.
