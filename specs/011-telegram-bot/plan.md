# Implementation Plan: Telegram-бот для GetMyWine

**Branch**: `011-telegram-bot` | **Date**: 2026-02-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-telegram-bot/spec.md`

## Summary

Добавление Telegram-бота как альтернативного интерфейса к существующему GetMyWine. Бот использует ту же логику рекомендаций (SommelierService + LLM + RAG), что и веб-версия, обеспечивая единый пользовательский опыт через мессенджер. Техническая реализация через python-telegram-bot с polling (для MVP), интеграция с существующими сервисами через общий API-слой.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, существующие сервисы (SommelierService, ChatService, LLMService)
**Storage**: PostgreSQL 16 + pgvector (существующая БД)
**Testing**: pytest, pytest-asyncio, тестовые фикстуры из существующего backend
**Target Platform**: Linux server (VPS с systemd)
**Project Type**: web (расширение существующего backend)
**Performance Goals**: <10 сек на рекомендацию, 1000 concurrent users (снижено для MVP)
**Constraints**: Минимальный observability (только critical errors), без rate limiting для MVP
**Scale/Scope**: MVP — 5 user stories, интеграция с существующей БД и сервисами

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Clean Architecture | ✅ PASS | Routers → Services → Repositories → Models сохраняется |
| Database First | ✅ PASS | Новые таблицы через Alembic миграции |
| TDD | ✅ PASS | Тесты для bot handlers и интеграции |
| RAG-First | ✅ PASS | Используется существующий SommelierService с pgvector |
| 18+ и никаких продаж | ✅ PASS | /start = согласие с 18+, нет покупок в боте |
| Образование > конверсия | ✅ PASS | Объясняем рекомендации, без манипуляций |
| Приватность данных | ✅ PASS | Профиль управляется через /profile |
| Tech Stack | ✅ PASS | Python 3.12+, FastAPI, SQLAlchemy, PostgreSQL |
| Coding Standards | ✅ PASS | Ruff, conventional commits |

## Project Structure

### Documentation (this feature)

```text
specs/011-telegram-bot/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (bot commands spec)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   ├── telegram_user.py        # NEW: TelegramUser model
│   │   └── ... (existing)
│   ├── repositories/
│   │   ├── telegram_user.py        # NEW: TelegramUserRepository
│   │   └── ... (existing)
│   ├── services/
│   │   ├── telegram_bot.py         # NEW: TelegramBotService
│   │   └── ... (existing: chat.py, sommelier.py)
│   ├── bot/                        # NEW: Telegram bot module
│   │   ├── __init__.py
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── start.py            # /start command
│   │   │   ├── help.py             # /help command
│   │   │   ├── profile.py          # /profile command
│   │   │   └── message.py          # Free-text message handler
│   │   ├── keyboards.py            # Inline keyboards for feedback
│   │   ├── formatters.py           # Wine card formatting for Telegram
│   │   └── main.py                 # Bot entry point
│   ├── config.py                   # Extended with Telegram settings
│   └── main.py                     # Updated: optional bot startup
├── migrations/
│   └── versions/
│       └── xxx_add_telegram_user.py  # NEW: Alembic migration
└── tests/
    ├── unit/
    │   ├── test_telegram_handlers.py   # NEW
    │   └── test_telegram_formatters.py # NEW
    └── integration/
        └── test_telegram_flow.py       # NEW
```

**Structure Decision**: Telegram bot добавляется как отдельный модуль `backend/app/bot/` внутри существующего backend. Это позволяет:
- Переиспользовать существующие сервисы (ChatService, SommelierService)
- Единая конфигурация через app/config.py
- Раздельный запуск через переменные окружения (FR-019, FR-020)

## Complexity Tracking

> No constitution violations requiring justification.

| Decision | Rationale |
|----------|-----------|
| Polling вместо Webhooks | Для MVP проще настроить, не требует публичного HTTPS endpoint |
| Отдельный модуль bot/ | Изоляция Telegram-специфичного кода, легче тестировать |
| Переиспользование ChatService | Единая логика сессий, не дублируем код |

## Constitution Re-Check (Post Phase 1)

| Principle | Status | Verification |
|-----------|--------|--------------|
| Clean Architecture | ✅ PASS | bot/handlers → services → repositories → models |
| Database First | ✅ PASS | TelegramUser + Conversation extension через Alembic |
| TDD | ✅ PASS | Тесты запланированы в tests/unit/, tests/integration/ |
| RAG-First | ✅ PASS | Используем SommelierService без изменений |
| 18+ | ✅ PASS | Описание бота + /start = is_age_verified |
| Образование > конверсия | ✅ PASS | Объясняем рекомендации через recommendation_reason |
| Приватность | ✅ PASS | /profile для просмотра данных |
| Tech Stack | ✅ PASS | python-telegram-bot совместим с asyncio/FastAPI |
| Coding Standards | ✅ PASS | Ruff, conventional commits сохраняются |
