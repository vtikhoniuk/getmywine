# Quickstart: Agentic RAG для рекомендаций вин

**Feature**: 015-agentic-rag | **Date**: 2026-02-10

## Prerequisites

- Python 3.12+
- PostgreSQL 16 с pgvector extension
- OpenRouter API key (или OpenAI API key)
- Docker Compose (для запуска полного стека)
- Эмбеддинги сгенерированы для всех 50 вин (фича 013 — T012)

## Быстрый старт

### 1. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

Новые зависимости **не добавляются** — всё работает на существующем OpenAI SDK.

### 2. Конфигурация

В `.env` или `docker-compose.yml`:

```env
# Обязательно — LLM провайдер
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...

# Модель с поддержкой tool use
LLM_MODEL=anthropic/claude-sonnet-4

# Опционально — настройка agent loop
AGENT_MAX_ITERATIONS=2    # Максимум итераций tool calls (default: 2)
```

### 3. Запуск тестов

```bash
# Все тесты agentic RAG
cd backend
python3 -m pytest tests/unit/test_agent_loop.py tests/unit/test_wine_tools.py tests/unit/test_llm_tool_use.py -v

# Полный набор тестов
python3 -m pytest tests/ -v
```

### 4. Запуск бота

```bash
docker compose up -d
# Или локально:
cd backend
python3 -m app.main
```

## Ключевые файлы

| Файл | Роль | Изменение |
|------|------|-----------|
| `backend/app/services/llm.py` | LLM провайдер | MODIFY: добавить `generate_with_tools()` |
| `backend/app/services/sommelier.py` | Оркестратор | MODIFY: agent loop заменяет 4-path |
| `backend/app/services/sommelier_prompts.py` | Промпты | MODIFY: единый промпт + tool defs |
| `backend/app/repositories/wine.py` | Запросы к БД | MODIFY: новые фильтры |
| `backend/app/config.py` | Конфигурация | MODIFY: agent settings |

## Тестирование вручную

### Сценарий 1: Структурированный поиск

Отправить боту в Telegram:
```
Посоветуй красное вино из Мальбека до 2000 рублей
```
**Ожидание**: 3 красных вина с сортом Мальбек, цена ≤ 2000₽

### Сценарий 2: Семантический поиск

```
Хочу что-нибудь лёгкое и освежающее на лето
```
**Ожидание**: Белые/розовые вина с лёгким телом и высокой кислотностью

### Сценарий 3: Комбинированный запрос

```
Элегантное красное до 3000 к стейку
```
**Ожидание**: Красные вина с food_pairing "стейк", цена ≤ 3000₽, семантически "элегантное"

### Сценарий 4: Fallback (нет фильтров)

```
Привет! Что посоветуешь?
```
**Ожидание**: Разнообразные рекомендации (LLM решает без tool calls или вызывает search без фильтров)

## Диагностика

Логи tool calls записываются в стандартный logger:
```
INFO: Tool call: search_wines(wine_type=red, price_max=2000) → 5 wines found
INFO: Tool call: semantic_search(query="элегантное вино") → 7 wines found
INFO: Agent loop completed in 1 iteration(s)
```

При ошибке tool use:
```
WARNING: Tool use failed: {error}. Falling back to standard catalog.
```
