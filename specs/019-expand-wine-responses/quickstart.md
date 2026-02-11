# Quickstart: 019-expand-wine-responses

## Обзор изменений

Эта фича расширяет ответы бота на околовинные вопросы (регионы, технологии, история) с 1-2 предложений до 5-10, добавляя тематическую подводку к обсуждению конкретных вин. Также добавляется Langfuse-тег для аналитики.

**Затрагиваемые файлы**:
- `backend/app/services/sommelier_prompts.py` — расширение инструкций для informational ответов
- `backend/app/services/sommelier.py` — Langfuse-тегирование response_type
- `backend/tests/eval/test_informational_eval.py` — новый eval-тест

**НЕ затрагивается**: схема БД, API контракты, JSON-схема ответа, парсинг, рендеринг, Telegram-отправка.

## Что менять

### 1. Системный промпт (`sommelier_prompts.py`)

В `SYSTEM_PROMPT_BASE`, в раздел «ПРАВИЛА ТИПОВ ОТВЕТА» (после строки 49), добавить развёрнутые инструкции для `"informational"`:

```
Текущее:
- "informational" — общий вопрос о вине без рекомендаций. wines пустой массив [].

Новое:
- "informational" — вопрос о винной культуре (регионы, сорта, технологии, история, терминология)
  без запроса конкретного вина. wines пустой массив [].
  ВАЖНО для informational:
  - intro: развёрнутый ответ на 5-10 предложений. Раскрой тему информативно и интересно.
    Если тема узкая — минимум 3 предложения, не лей воду.
  - closing: тематическая подводка к обсуждению конкретных вин, СВЯЗАННЫХ с темой вопроса.
    Например: вопрос о Тоскане → предложи обсудить тосканские вина.
    НЕ используй общие фразы типа «хотите подобрать вино?».
  - Подводки должны быть разнообразными — не повторяй формулировки из предыдущих ответов.
```

Также обновить описание поля `intro` (строка 35):
```
Текущее:
"intro": "Вступительный текст (1-2 предложения)"

Новое:
"intro": "Вступительный текст (1-2 предложения для recommendation/off_topic, 5-10 предложений для informational)"
```

### 2. Langfuse-метаданные (`sommelier.py`)

В методе `_update_langfuse_metadata()` добавить параметр `response_type` и передавать его:

```python
@staticmethod
def _update_langfuse_metadata(
    tools_used: list[str], iterations: int, response_type: str | None = None
) -> None:
    if langfuse_context is None:
        return
    try:
        metadata = {
            "tools_used": tools_used,
            "iterations": iterations,
        }
        if response_type:
            metadata["response_type"] = response_type
        langfuse_context.update_current_observation(metadata=metadata)
    except Exception:
        pass
```

В `generate_agentic_response()`, после парсинга JSON-ответа (где извлекаются `wine_names`), извлечь `response_type` и передать в `_update_langfuse_metadata()`.

### 3. Eval-тесты (`test_informational_eval.py`)

Новый файл с тестами:
- Околовинные вопросы возвращают `response_type == "informational"` с `intro` >= 3 предложений
- `closing` содержит тематическую подводку (не общую фразу)
- Регрессия: вопрос о конкретном вине → `response_type == "recommendation"`

## Как запустить

```bash
# Eval-тесты (требуют OPENROUTER_API_KEY)
cd backend && pytest tests/eval/test_informational_eval.py -v -m eval

# Все eval-тесты (включая существующие)
cd backend && pytest tests/eval/ -v -m eval

# Unit-тесты (проверить что ничего не сломали)
cd backend && pytest tests/unit/ -v
```

## Как проверить вручную

1. Запустить бота
2. Отправить: «Расскажи про Бордо как винный регион»
3. Ожидать: 5-10 предложений + подводка к тому, чтобы обсудить конкретные вина из Бордо
4. Отправить: «Что такое танины?»
5. Ожидать: 5-10 предложений + подводка к винам с выраженными танинами
6. Проверить: подводки в п.3 и п.5 отличаются формулировкой
7. Проверить Langfuse: трейсы содержат `response_type: "informational"`
