# Quickstart: Structured Output for Wine Recommendations

**Branch**: `018-structured-output` | **Date**: 2026-02-11

## Prerequisites

- Python 3.12+
- Docker + Docker Compose (для PostgreSQL + Langfuse)
- OpenRouter API key с доступом к `anthropic/claude-sonnet-4`

## Setup

### 1. Переключение на ветку

```bash
git checkout 018-structured-output
```

### 2. Обновление .env

```bash
# Сменить модель с GPT-4.1 на Claude Sonnet 4.5
LLM_MODEL=anthropic/claude-sonnet-4
```

### 3. Запуск

```bash
docker compose up -d
```

## Проверка работоспособности

### Test 1: Recommendation (User Story 1)

Отправить боту в Telegram:
```
посоветуй красное вино к стейку
```

**Ожидание**: 5 отдельных сообщений — intro, 3 фото вин с подписями, closing вопрос.

### Test 2: Welcome (User Story 2)

Нажать `/start` в боте.

**Ожидание**: 5 отдельных сообщений — приветствие, 3 фото вин, закрывающий вопрос.

### Test 3: Informational (User Story 3)

Отправить:
```
что такое танины?
```

**Ожидание**: Одно текстовое сообщение без фото.

### Test 4: Off-topic (User Story 4)

Отправить:
```
реши уравнение x^2 = 4
```

**Ожидание**: Вежливое перенаправление к теме вина, возможно с предложением вин.

## Мониторинг

### Langfuse

Открыть http://localhost:3000 → Traces → проверить:
- `response_format` параметр в запросе
- JSON-ответ в response content
- Tool calls видны в trace

### Логи бота

```bash
docker compose logs -f telegram-bot
```

Искать:
- `Structured JSON parse: response_type=recommendation, wines=3` — успешный парсинг
- `Structured output parse failed` — fallback на heuristic

## Rollback

Для отката на текстовые маркеры:
```bash
# В .env вернуть:
LLM_MODEL=openai/gpt-4.1

docker compose restart telegram-bot
```

Heuristic fallback автоматически активируется для моделей без structured output.

## Key Files Changed

| Файл | Что изменено |
|------|-------------|
| `backend/app/services/sommelier_prompts.py` | Pydantic-модели ответа, JSON schema, обновлённые промпты |
| `backend/app/services/llm.py` | Параметр `response_format` в `generate_with_tools()` |
| `backend/app/services/sommelier.py` | JSON-парсинг ответа, рендер текста для истории |
| `backend/app/services/telegram_bot.py` | Wine extraction из JSON вместо `.find()` |
| `backend/app/bot/sender.py` | Приём structured objects, wine lookup по имени |
| `backend/app/config.py` | Дефолтная модель → `anthropic/claude-sonnet-4` |
| `backend/tests/unit/test_structured_output.py` | Тесты парсинга JSON-ответов |
