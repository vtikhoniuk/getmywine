# Implementation Plan: LLM Eval Tests

**Branch**: `016-llm-eval-tests` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-llm-eval-tests/spec.md`

## Summary

Набор golden query eval-тестов для проверки качества ответов LLM сомелье-бота: выбор инструмента (search_wines vs semantic_search), точность извлечения фильтров, обнаружение галлюцинаций, качество семантического поиска. Тесты используют реальную PostgreSQL + реальный LLM через OpenRouter API, автоматически пропускаются при отсутствии инфраструктуры.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: pytest 8.x, pytest-asyncio, SQLAlchemy 2.0, asyncpg, openai (OpenRouter-compatible), pgvector
**Storage**: PostgreSQL 16 + pgvector (существующая dev-БД с 50 винами и embeddings)
**Testing**: pytest с custom markers (`eval`), pytest-asyncio для async тестов
**Target Platform**: Linux (WSL2 / Docker), ручной запуск или nightly CI
**Project Type**: web (backend — Python/FastAPI, существующий проект)
**Performance Goals**: Полный прогон eval-тестов < 2 минут (SC-007)
**Constraints**: Требуется реальная PostgreSQL + OPENROUTER_API_KEY; LLM non-determinism учтён через однозначные запросы и 20% толерантность на числовые значения
**Scale/Scope**: 14+ golden queries в 4 категориях, 19 тестов

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **Clean Architecture** (Routers → Services → Repositories → Models) | PASS | Eval-тесты тестируют через публичный API SommelierService, не нарушая слоёв. ToolCallSpy — monkey-patch на уровне тестов, не затрагивает production-код |
| **Database First** (миграции → код) | PASS | Тесты используют существующую БД с seed-данными, новых миграций не требуется |
| **TDD** (Red → Green → Refactor) | PASS | Тесты пишутся как golden queries с ожидаемым поведением; фиксируют текущее качество и регрессии |
| **RAG-First** (рекомендации только из каталога) | PASS | test_hallucination.py напрямую проверяет этот принцип — все упомянутые вина должны существовать в каталоге |
| **18+ и никаких продаж** | N/A | Eval-тесты не затрагивают пользовательский интерфейс |
| **Образование > конверсия** | N/A | Eval-тесты не затрагивают контент рекомендаций |
| **Приватность данных** | PASS | Тесты не создают и не хранят пользовательские данные |
| **Ruff** (линтинг) | PASS | Код тестов соответствует Ruff-стандартам проекта |
| **100% покрытие критичных путей** | PASS | Eval-тесты расширяют покрытие RAG-пайплайна — критичного пути бота |

Все gates пройдены. Нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/016-llm-eval-tests/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: data model (golden queries)
├── quickstart.md        # Phase 1: how to run eval tests
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   ├── sommelier.py            # SommelierService (tested subject)
│   │   ├── sommelier_prompts.py    # WINE_TOOLS, SYSTEM_PROMPT_AGENTIC
│   │   └── llm.py                  # LLMService (OpenRouter provider)
│   ├── repositories/
│   │   └── wine.py                 # WineRepository (semantic_search)
│   └── models/
│       └── wine.py                 # Wine SQLAlchemy model
└── tests/
    ├── conftest.py                 # pytest_configure: registers 'eval' marker
    └── eval/                       # NEW: eval test suite
        ├── __init__.py
        ├── conftest.py             # Fixtures: eval_db, sommelier_service, catalog_wines, ToolCallSpy
        ├── golden_queries.py       # GoldenQuery dataclass + 14 golden queries
        ├── test_tool_selection.py  # 8 parametrized tests (tool choice)
        ├── test_filter_accuracy.py # 3 parametrized tests (filter extraction)
        ├── test_hallucination.py   # 3 parametrized tests (no invented wines)
        └── test_semantic_quality.py # 5 tests (relevance, ordering, differentiation)
```

**Structure Decision**: Eval-тесты размещены в `backend/tests/eval/` — отдельный пакет внутри существующей тестовой структуры. Не смешиваются с unit/integration/contract тестами. Имеют собственный conftest.py с fixtures для реальной БД и LLM.

## Design Decisions

### 1. Spy Pattern vs Mock Pattern

**Decision**: ToolCallSpy (monkey-patch) вместо mock/patch

**Rationale**: Spy перехватывает вызовы `execute_search_wines` / `execute_semantic_search` и записывает аргументы, но выполняет реальную логику. Это позволяет одновременно проверять:
- Какой инструмент выбрала LLM (spy data)
- Что инструмент вернул корректные результаты (real execution)

**Alternatives rejected**:
- `unittest.mock.patch` — подменяет возвращаемое значение, не позволяет проверить реальные результаты
- Логирование tool calls в SommelierService — потребовало бы изменения production-кода

### 2. Auto-skip Mechanism

**Decision**: `pytest_collection_modifyitems` hook + `socket.getaddrinfo` DNS check

**Rationale**: Тесты должны gracefully пропускаться на машинах без реальной PostgreSQL или API-ключа. DNS-проверка через `socket.getaddrinfo` быстрее, чем попытка подключения к БД, и ловит самый частый случай — Docker hostname `db` недоступен с хоста.

**Alternatives rejected**:
- `pytestmark = [pytest.mark.skipif(...)]` в conftest.py — не работает надёжно для всех тестов в пакете
- `pytest.importorskip` — не подходит, зависимость не в импорте, а в runtime connectivity

### 3. Golden Query Structure

**Decision**: Dataclass `GoldenQuery` с `id`, `query_ru`, `expected_tool`, `expected_filters`, `min_results`

**Rationale**: Единый формат для всех категорий тестов. Parametrize по `ids=lambda g: g.id` даёт читаемые имена тестов в pytest output.

### 4. Numeric Tolerance

**Decision**: 20% tolerance для числовых фильтров (цена)

**Rationale**: LLM non-determinism — при запросе "до 2000 рублей" LLM может передать `price_max=2000` или `price_max=1999` или `price_max=2100`. 20% покрывает разумный разброс без ложных срабатываний.

### 5. Hallucination Detection Strategy

**Decision**: Парсинг `[WINE:N]` секций → извлечение первой строки → fuzzy match с каталогом

**Rationale**: Используем существующий `parse_structured_response()` для парсинга. Fuzzy match (catalog_name in first_line.lower()) учитывает, что LLM может добавить markdown-форматирование или слегка изменить порядок слов в названии вина.

## Complexity Tracking

> Нет нарушений Constitution Check — таблица не требуется.
