# Implementation Plan: Agentic RAG для рекомендаций вин

**Branch**: `015-agentic-rag` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-agentic-rag/spec.md`

## Summary

Замена случайной выборки 20 вин на интеллектуальный поиск через LLM tool use. Текущая система передаёт случайные вина в промпт LLM; новая — позволяет LLM самостоятельно вызывать инструменты поиска (структурированный SQL + семантический pgvector). Единый системный промпт заменяет 4-path маршрутизацию (cold_start/personalized/event/food). Реактивный ReAct loop с максимумом 2 итерациями tool calls.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, OpenAI SDK (для OpenRouter API), pgvector
**Storage**: PostgreSQL 16 + pgvector (существующая БД, 50 вин с эмбеддингами 1536 dims)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker Compose)
**Project Type**: Web application (backend only для данной фичи)
**Performance Goals**: Ответ бота ≤ +3 сек к текущему (1-2 доп. LLM вызова для tool use)
**Constraints**: Максимум 2 итерации tool calls на запрос; обратная совместимость с форматом [INTRO][WINE:1-3][CLOSING]
**Scale/Scope**: 50 вин, ~десятки пользователей, один Telegram бот

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| **Clean Architecture** (Routers → Services → Repositories → Models) | ✅ PASS | Agent loop в SommelierService → WineRepository → Wine model. Слои сохранены |
| **Database First** (сначала миграция, потом код) | ✅ PASS | Схема БД не меняется. Добавляются только новые фильтры в Repository (grape_varieties, food_pairings) |
| **TDD** (Red → Green → Refactor) | ✅ PASS | Тесты пишутся перед реализацией для каждого компонента |
| **RAG-First** (рекомендации только из каталога) | ✅ PASS | Инструменты ищут только в каталоге wines. Нет совпадений → явное сообщение. Галлюцинации контролируются tool use |

**Gate result**: ALL PASS — переходим к Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/015-agentic-rag/
├── plan.md              # This file
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: tool schemas, no DB changes
├── quickstart.md        # Phase 1: dev setup & testing guide
└── tasks.md             # Phase 2: implementation tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   └── wine.py              # Existing — no changes
│   ├── repositories/
│   │   └── wine.py              # MODIFY: add grape_varieties, food_pairings filters
│   ├── services/
│   │   ├── llm.py               # MODIFY: add generate_with_tools() and get_query_embedding()
│   │   ├── sommelier.py         # MODIFY: replace 4-path with agent loop
│   │   └── sommelier_prompts.py # MODIFY: unified system prompt with tool definitions
│   └── config.py                # MODIFY: add agent-related config (max_iterations)
└── tests/
    └── unit/
        ├── test_agent_loop.py           # NEW: agent loop tests
        ├── test_wine_tools.py           # NEW: tool execution tests
        ├── test_llm_tool_use.py         # NEW: LLM tool use integration
        └── test_sommelier_unified.py    # NEW: unified prompt tests
```

**Structure Decision**: Backend-only changes. Новые файлы не создаются — все изменения в существующих модулях. Тесты — новые файлы в `backend/tests/unit/`.
