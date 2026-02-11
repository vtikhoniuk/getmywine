# Research: LLM Eval Tests

**Branch**: `016-llm-eval-tests` | **Date**: 2026-02-10

## R1: Подход к тестированию LLM-агента

**Decision**: Golden query eval-тесты с реальным LLM + реальной БД (интеграционные)

**Rationale**: Unit-тесты с mock LLM не проверяют качество принятия решений (tool selection, filter extraction). Eval-тесты с реальным LLM фиксируют текущий baseline и обнаруживают регрессии при изменении промптов или модели.

**Alternatives considered**:
- **Mock-based unit tests** — уже есть в `tests/unit/test_wine_tools.py`, проверяют только execution logic
- **LLM-as-judge** (второй LLM оценивает ответы первого) — overhead и дополнительный non-determinism; избыточно для 50-винного каталога
- **Snapshot tests** (записать ответы, сравнивать diff) — слишком хрупкие из-за LLM non-determinism
- **Deterministic mock tests** (Level 1 из исходного плана) — полезны, но не заменяют проверку реального LLM

## R2: Перехват tool calls

**Decision**: ToolCallSpy (monkey-patch на `execute_search_wines` / `execute_semantic_search`)

**Rationale**: Spy позволяет записать имя инструмента и аргументы, при этом выполнив реальный поиск. Это единственный подход, который одновременно даёт:
1. Данные для assertions по tool selection и filter accuracy
2. Реальные результаты поиска для hallucination detection

**Alternatives considered**:
- **Spy на уровне `llm_service.generate_with_tools()`** — ловит raw tool_calls от LLM, но не видит post-processing (enum mapping, price validation, broadening)
- **Middleware/logging в SommelierService** — требует изменения production-кода, нарушает принцип минимальных изменений
- **pytest-mock / `unittest.mock.patch`** — подменяет функцию целиком, не позволяет выполнить реальную логику

## R3: Механизм auto-skip

**Decision**: `pytest_collection_modifyitems` hook + DNS check (`socket.getaddrinfo`)

**Rationale**: Тесты должны корректно пропускаться в трёх сценариях:
1. Нет `OPENROUTER_API_KEY` → skip
2. `DATABASE_URL` указывает на SQLite → skip
3. PostgreSQL host не достижим (Docker hostname `db` вне Docker) → skip

DNS check через `socket.getaddrinfo` — быстрый (~1ms) и достаточный для определения доступности хоста.

**Alternatives considered**:
- **`pytestmark` в conftest.py** — не работает надёжно: skipif marker в conftest не применяется ко всем тестам пакета
- **`pytest.importorskip`** — не подходит, проблема не в отсутствующем модуле
- **TCP connect check** — надёжнее DNS, но медленнее (timeout) и избыточен для нашего случая
- **Попытка подключения к БД** — самый надёжный, но самый медленный (~5s timeout при недоступности)

## R4: Формат golden queries

**Decision**: Python dataclass `GoldenQuery` с полями `id`, `query_ru`, `expected_tool`, `expected_filters`, `min_results`, `description`

**Rationale**: Dataclass даёт type hints, IDE autocomplete, и natural pytest parametrize integration (`ids=lambda g: g.id`). Данные определены в отдельном файле `golden_queries.py` для переиспользования между test modules.

**Alternatives considered**:
- **YAML/JSON файлы** — дополнительный parsing, потеря type safety, сложнее для IDE навигации
- **pytest fixtures** — менее читаемо при 14+ queries, сложнее параметризовать
- **Inline dicts в каждом тесте** — дублирование, нет единого источника истины

## R5: Обнаружение галлюцинаций

**Decision**: Парсинг `[WINE:N]` секций через `parse_structured_response()` → извлечение имени вина из первой строки → case-insensitive substring match с каталогом

**Rationale**: Используем существующий парсер структурированных ответов. Substring match (`catalog_name in first_line.lower()`) вместо exact match учитывает:
- Markdown форматирование (`**Château Margaux**` → `château margaux`)
- Дополнительный текст (регион, винтаж в той же строке)
- Незначительные вариации в написании

**Alternatives considered**:
- **Exact match по имени** — слишком хрупкий, LLM часто добавляет контекст к имени
- **Fuzzy matching (Levenshtein)** — overhead, requires additional dependency
- **LLM-as-judge** — спрашивать второй LLM "это вино из каталога?" — медленно и circular

## R6: Качество семантического поиска

**Decision**: Три типа проверок:
1. **Relevance** — similarity score > 0.25 для каждого результата
2. **Ordering** — результаты отсортированы по убыванию similarity
3. **Differentiation** — разные по смыслу запросы возвращают разные топ-3

**Rationale**: Порог 0.25 выбран эмпирически на основе распределения cosine similarity для 50-винного каталога с 1536-dimensional embeddings. Differentiation test ("ягодные ноты" vs "минеральное белое") проверяет, что embeddings действительно различают семантику, а не возвращают один и тот же набор.

**Alternatives considered**:
- **Recall@K метрики** — требуют hand-labeled relevance judgments для каждого запроса, overhead для 50-винного каталога
- **NDCG** — то же, требует graded relevance
- **Порог 0.5** — слишком строгий, отсекает частично релевантные результаты
