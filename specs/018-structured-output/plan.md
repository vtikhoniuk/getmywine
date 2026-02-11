# Implementation Plan: Structured Output for Wine Recommendations

**Branch**: `018-structured-output` | **Date**: 2026-02-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-structured-output/spec.md`

## Summary

Перевести LLM-ответы с текстовых маркеров `[INTRO]/[WINE:N]/[CLOSING]` на JSON Structured Output. Модель: Claude Sonnet 4.5 через OpenRouter (`anthropic/claude-sonnet-4`). Structured output гарантирует парсинг ответа, устраняет regex-зависимость и обеспечивает 100% отображение фотографий вин в Telegram.

Ключевые изменения:
- Добавить `response_format: { type: "json_schema", json_schema: {...} }` в вызовы LLM
- Определить Pydantic-модели для двух типов ответов: рекомендация (с вином) и информационный (без вина)
- Заменить regex-парсинг на JSON-десериализацию
- Обновить sender для работы со структурированными объектами
- Сохранить heuristic-fallback для переходного периода
- Сменить модель с `openai/gpt-4.1` на `anthropic/claude-sonnet-4`

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, OpenAI SDK (для OpenRouter), Langfuse SDK, Pydantic v2
**Storage**: PostgreSQL 16 + pgvector (без изменений схемы)
**Testing**: pytest 8.x, pytest-asyncio; eval-тесты в `backend/tests/eval/`
**Target Platform**: Linux server (Docker, VPS)
**Project Type**: Web application (backend + telegram bot)
**Performance Goals**: Время ответа не увеличивается более чем на 500мс (SC-002)
**Constraints**: OpenRouter API совместимость; Langfuse wrapper прозрачность; сохранение tool calling в agentic loop
**Scale/Scope**: ~50 вин в каталоге, ~10 сообщений в истории диалога, 2 итерации agent loop

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| **Clean Architecture** (Routers → Services → Repositories → Models) | PASS | Изменения в слоях Services и Bot; модели данных (Pydantic) добавляются в services; репозитории не затрагиваются |
| **Database First** | PASS | Схема БД не меняется; новые Pydantic-модели — это модели ответа LLM, а не модели БД |
| **TDD** | PASS | Новые unit-тесты для JSON-парсинга; обновление eval-тестов для structured output |
| **RAG-First** | PASS | Tool calling сохраняется; вина по-прежнему из каталога через search_wines/semantic_search |
| **18+ и никаких продаж** | PASS | Без изменений в бизнес-логике |
| **Образование > конверсия** | PASS | Формат ответа меняется, не содержание |
| **Приватность данных** | PASS | Данные пользователей не затрагиваются |

**Gate result**: PASS — все принципы соблюдены, нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/018-structured-output/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: OpenRouter + structured output research
├── data-model.md        # Phase 1: Pydantic response models
├── quickstart.md        # Phase 1: Quick setup guide
├── contracts/           # Phase 1: JSON Schema contracts
│   └── llm-response-schema.json
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── llm.py                  # [MODIFY] Add response_format to generate/generate_with_tools
│   │   ├── sommelier.py            # [MODIFY] Use structured response, render text for history
│   │   ├── sommelier_prompts.py    # [MODIFY] New prompts for structured output, Pydantic models, update parse logic
│   │   └── telegram_bot.py         # [MODIFY] Replace _extract_wines_from_response with JSON wine names
│   ├── bot/
│   │   ├── sender.py               # [MODIFY] Accept structured objects instead of text parsing
│   │   └── handlers/
│   │       ├── start.py            # [MODIFY] Adapt to new structured response format
│   │       └── message.py          # [MODIFY] Adapt to new structured response format
│   └── config.py                   # [MODIFY] Update default model to anthropic/claude-sonnet-4
├── tests/
│   ├── eval/                       # [MODIFY] Update eval tests for structured output
│   └── unit/
│       └── test_structured_output.py  # [NEW] Unit tests for JSON parsing and Pydantic models
└── .env                            # [MODIFY] Change LLM_MODEL value
```

**Structure Decision**: Existing backend structure preserved. No new directories needed beyond the test file. All changes are modifications to existing files in the services and bot layers.
