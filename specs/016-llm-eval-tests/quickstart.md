# Quickstart: LLM Eval Tests

**Branch**: `016-llm-eval-tests` | **Date**: 2026-02-10

## Prerequisites

1. **PostgreSQL 16 + pgvector** — dev-БД с seed-данными (50 вин с embeddings)
2. **OPENROUTER_API_KEY** — ключ для LLM API (в `.env` или env переменная)
3. **Python 3.12+** с установленными зависимостями (`pip install -r requirements.txt`)

## Quick Run

```bash
# Из директории backend/
cd backend

# Запустить все eval-тесты
python -m pytest tests/eval/ -v

# Запустить конкретную категорию
python -m pytest tests/eval/test_tool_selection.py -v
python -m pytest tests/eval/test_filter_accuracy.py -v
python -m pytest tests/eval/test_hallucination.py -v
python -m pytest tests/eval/test_semantic_quality.py -v

# Запустить по marker
python -m pytest -m eval -v
```

## Auto-Skip Behavior

Тесты автоматически пропускаются (skip) если:

| Condition | Skip Reason |
|-----------|-------------|
| `OPENROUTER_API_KEY` не задан | "OPENROUTER_API_KEY not set" |
| `DATABASE_URL` указывает на SQLite | "Real PostgreSQL required" |
| PostgreSQL host не достижим (DNS) | "PostgreSQL host 'db:5432' is not reachable" |

Проверка происходит при collection (до запуска тестов). Все 19 eval-тестов пропускаются одним сообщением.

## Test Structure

```
tests/eval/
├── conftest.py            # Fixtures + auto-skip logic
├── golden_queries.py      # 14 golden queries (data)
├── test_tool_selection.py # 8 tests — LLM picks correct tool
├── test_filter_accuracy.py # 3 tests — filter extraction accuracy
├── test_hallucination.py  # 3 tests — no invented wines
└── test_semantic_quality.py # 5 tests — semantic search quality
```

## Expected Output (when infra available)

```
tests/eval/test_tool_selection.py::test_tool_selection[red_dry_under_2000] PASSED
tests/eval/test_tool_selection.py::test_tool_selection[elegant_light] PASSED
tests/eval/test_tool_selection.py::test_tool_selection[pinot_noir] PASSED
...
tests/eval/test_hallucination.py::test_no_hallucinated_wines[...] PASSED
tests/eval/test_semantic_quality.py::test_semantic_search_relevance[semantic_romantic] PASSED
tests/eval/test_semantic_quality.py::test_semantic_search_ordering PASSED
tests/eval/test_semantic_quality.py::test_semantic_vs_structured_differentiation PASSED

19 passed in ~90s
```

## Expected Output (when infra NOT available)

```
19 skipped (PostgreSQL host 'db:5432' is not reachable)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| All tests skipped | Убедитесь, что PostgreSQL доступен и `OPENROUTER_API_KEY` задан в `.env` |
| Connection refused | PostgreSQL запущен? Проверьте `DATABASE_URL` в `.env` |
| DNS resolution failed | Если `DATABASE_URL` содержит Docker hostname (`db`), запускайте из Docker или измените на `localhost` |
| Flaky tool selection | LLM non-determinism. Перезапустите тест. При систематических fails — проверьте prompt в `sommelier_prompts.py` |
| Low similarity scores | Проверьте, что embeddings сгенерированы: `python -m app.scripts.generate_embeddings` |
