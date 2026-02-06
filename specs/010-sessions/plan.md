# Implementation Plan: Sessions History

**Branch**: `010-sessions` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from User Story Map EPIC-010 (US-018, US-019, SS-010, SS-011, SS-012)

## Summary

Реализация истории сессий для GetMyWine: поддержка множественных диалогов на пользователя, автоматическое именование сессий по теме, сайдбар с историей, персонализированные welcome-сообщения на основе прошлых сессий, и управление жизненным циклом сессий (30 мин inactivity, 90 дней хранения).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, HTMX, Jinja2, Claude API
**Storage**: PostgreSQL 16 + pgvector
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux server (Docker)
**Project Type**: web (backend with SSR frontend)
**Performance Goals**: список сессий <200ms p95, переключение сессии <300ms p95
**Constraints**: 30 мин auto-close, 90 дней retention, max 30 символов в названии
**Scale/Scope**: до 1000 сессий на пользователя

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture | PASS | Routers → Services → Repositories → Models |
| Database First | PASS | Alembic миграция для изменений в conversations |
| TDD | PASS | Тесты для CRUD сессий, именования, lifecycle |
| RAG-First | PASS | SS-011 использует существующий RAG для истории |
| 18+ и никаких продаж | N/A | Не влияет на возрастную верификацию |
| Образование > конверсия | PASS | Ссылки на прошлые сессии для обучения |
| Приватность данных | PASS | Пользователь может удалить сессии |

**Result**: All gates PASS

## Project Structure

### Documentation (this feature)

```text
specs/010-sessions/
├── plan.md              # This file
├── research.md          # Phase 0: session naming patterns, lifecycle management
├── data-model.md        # Phase 1: Conversation changes, Session entity
├── quickstart.md        # Phase 1: как запустить и протестировать
├── contracts/           # Phase 1: OpenAPI schemas
│   └── sessions-api.yaml
└── tasks.md             # Phase 2 (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── conversation.py         # MODIFY: remove unique constraint, add title, closed_at
│   ├── schemas/
│   │   └── conversation.py         # MODIFY: add session schemas
│   ├── repositories/
│   │   └── conversation.py         # MODIFY: multi-session queries
│   ├── services/
│   │   ├── chat.py                 # MODIFY: session lifecycle
│   │   └── session_naming.py       # NEW: LLM-based session naming
│   ├── routers/
│   │   └── chat.py                 # MODIFY: session endpoints
│   └── templates/
│       └── chat/
│           ├── _sidebar.html       # NEW: session list partial
│           └── index.html          # MODIFY: add sidebar
├── migrations/versions/
│   └── 010_sessions_support.py     # Conversation schema changes
└── tests/
    ├── unit/
    │   ├── test_session_naming.py  # NEW
    │   └── test_session_lifecycle.py # NEW
    └── integration/
        └── test_sessions_api.py    # NEW
```

**Structure Decision**: Модификация существующей модели Conversation вместо создания новой сущности Session. Это минимизирует изменения и переиспользует существующую логику messages.

## Complexity Tracking

> No violations — standard implementation within existing architecture.

---

## Requirements Summary

### US-018: Просмотр истории сессий
- Сайдбар отображает прошлые сессии (сортировка по дате, новые сверху)
- Название сессии: 1-3 слова, max 30 символов
- Клик открывает историю read-only
- Нельзя продолжить старую сессию

### US-019: Новая сессия при входе
- Автоматическое создание новой сессии при входе
- Персонализированное welcome на основе истории пользователя
- Кнопка "Новый диалог" всегда доступна
- Старые сессии сохраняются

### SS-010: Автогенерация названий сессий
- Генерация после первого ответа AI
- По теме: вино, событие, блюдо
- Примеры: "Вино к стейку", "Бордо на ДР", "Розовое для пикника"
- Fallback: дата ("3 февраля")
- Max 30 символов

### SS-011: Cross-session контекст
- Извлечение ключевых фактов из прошлых сессий
- Включение в LLM контекст
- Избежание повторения рекомендаций
- Ссылки на прошлый опыт ("В прошлый раз вам понравилось...")

### SS-012: Lifecycle сессий
- Auto-close через 30 мин неактивности
- Хранение 90 дней минимум
- Удаление отдельной сессии пользователем
- Каскадное удаление при удалении аккаунта

---

## Key Technical Decisions

### 1. Model Changes

**Current**: `Conversation.user_id` has `unique=True` — one conversation per user.

**New**: Remove unique constraint, add fields:
- `title: Optional[str]` — auto-generated or null
- `closed_at: Optional[datetime]` — when session was closed
- `is_active: bool` — computed from closed_at or inactivity

### 2. Session Naming Strategy

Use LLM to generate 1-3 word title in Russian after first AI response:
- Input: first user message + first AI response
- Output: concise topic (wine type, event, dish)
- Fallback: formatted date

### 3. History Extraction (SS-011)

Query last N sessions per user, extract:
- Wine recommendations and feedback
- Detected preferences
- Store as user-level summary (optional: in taste_profiles or separate table)

### 4. UI Architecture

HTMX partial updates:
- `GET /chat/sessions` → sidebar list
- `GET /chat/sessions/{id}` → load read-only history
- `POST /chat/sessions/new` → create and switch
- `DELETE /chat/sessions/{id}` → remove session
