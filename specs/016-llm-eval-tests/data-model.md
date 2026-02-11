# Data Model: LLM Eval Tests

**Branch**: `016-llm-eval-tests` | **Date**: 2026-02-10

## Entities

### GoldenQuery

Эталонный запрос с ожидаемым поведением LLM. Определён как Python dataclass в `tests/eval/golden_queries.py`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Yes | Уникальный идентификатор (snake_case, e.g. `red_dry_under_2000`) |
| `query_ru` | str | Yes | Текст запроса на русском языке |
| `expected_tool` | str | Yes | Ожидаемый инструмент: `"search_wines"` \| `"semantic_search"` \| `"any"` |
| `expected_filters` | dict | No | Ожидаемые фильтры (e.g. `{"wine_type": "red", "price_max": 2000}`) |
| `min_results` | int | No | Минимальное количество ожидаемых результатов (default: 1) |
| `description` | str | No | Человекочитаемое описание теста |

**Uniqueness**: По полю `id` — каждый golden query имеет уникальный идентификатор.

### Query Sets

Golden queries сгруппированы в 3 набора:

| Set | Variable | Count | Purpose |
|-----|----------|-------|---------|
| Tool Selection | `TOOL_SELECTION_QUERIES` | 8 | Проверка выбора инструмента |
| Filter Accuracy | `FILTER_ACCURACY_QUERIES` | 3 | Проверка извлечения фильтров |
| Semantic Quality | `SEMANTIC_QUERIES` | 3 | Проверка семантического поиска |

Дополнительно 3 inline-запроса в `test_hallucination.py` для проверки галлюцинаций.

**Total**: 14 golden queries (8 + 3 + 3) + 3 hallucination queries = 17 test cases.

### ToolCallSpy

Spy-объект для перехвата вызовов инструментов. Определён как класс в `tests/eval/conftest.py`.

| Field/Method | Type | Description |
|-------------|------|-------------|
| `calls` | list[tuple[str, dict]] | Лог всех вызовов: (tool_name, arguments) |
| `tool_names` | property → list[str] | Имена вызванных инструментов в порядке вызова |
| `first_tool` | property → str \| None | Имя первого вызванного инструмента |
| `first_args` | property → dict \| None | Аргументы первого вызова |
| `search_calls()` | method → list[dict] | Только аргументы search_wines вызовов |
| `semantic_calls()` | method → list[dict] | Только аргументы semantic_search вызовов |

**Lifecycle**: Создаётся через fixture `tool_spy` перед каждым тестом. Monkey-patches `sommelier_service.execute_search_wines` и `execute_semantic_search`. Не требует cleanup — fixture scope per-test.

## Referenced Entities (existing, not modified)

### Wine (из `app/models/wine.py`)

Используется в тестах галлюцинаций для сверки с каталогом.

| Key Fields | Type | Used In |
|-----------|------|---------|
| `name` | String(255) | `test_hallucination.py` — сверка с ответом LLM |
| `embedding` | Vector(1536) | `test_semantic_quality.py` — pgvector cosine search |

### SommelierService (из `app/services/sommelier.py`)

Тестируемый субъект. Используется через fixture `sommelier_service`.

| Key Methods | Used In |
|------------|---------|
| `generate_agentic_response()` | tool_selection, filter_accuracy, hallucination |
| `execute_search_wines()` | ToolCallSpy target |
| `execute_semantic_search()` | ToolCallSpy target |

### WineRepository (из `app/repositories/wine.py`)

Используется напрямую в semantic quality тестах.

| Key Methods | Used In |
|------------|---------|
| `semantic_search(embedding, limit)` | `test_semantic_quality.py` |

## Relationships

```
GoldenQuery ──parametrize──→ test functions
                               │
                               ├── test_tool_selection ──uses──→ ToolCallSpy ──wraps──→ SommelierService
                               ├── test_filter_accuracy ──uses──→ ToolCallSpy ──wraps──→ SommelierService
                               ├── test_hallucination ──uses──→ SommelierService + catalog_wines (Wine)
                               └── test_semantic_quality ──uses──→ WineRepository + LLMService
```

## No New Database Migrations

Эта фича не создаёт и не изменяет таблицы в БД. Все данные — seed wines, уже загруженные в dev-БД.
