# Research: Structured Output for Wine Recommendations

**Branch**: `018-structured-output` | **Date**: 2026-02-11

## R-001: OpenRouter + response_format для Claude

### Decision
Использовать стандартный параметр `response_format: { type: "json_schema", json_schema: {...} }` через OpenAI SDK. OpenRouter автоматически транслирует в Claude-нативный `output_config.format`.

### Rationale
- OpenRouter поддерживает `response_format: json_schema` для Claude Sonnet 4.5 и Opus 4.1+
- Трансляция прозрачна — не нужно менять SDK или формат вызовов
- Флаг `provider.require_parameters: true` (через `extra_body`) опционален — используется для гарантии маршрутизации на провайдера с поддержкой structured output
- Заголовок `structured-outputs-2025-11-13` нужен только для `strict: true` на tools, НЕ для `response_format`

### Alternatives Considered
| Альтернатива | Плюсы | Минусы |
|---|---|---|
| `type: "json_object"` (базовый JSON mode) | Проще, шире поддержка моделей | Нет гарантии схемы, парсинг может сломаться |
| Прямой Anthropic SDK с `output_config.format` | Нативный, без трансляции | Потеря OpenRouter маршрутизации, другой SDK |
| Библиотека `instructor` | Авто-Pydantic-to-schema, retry | Лишняя зависимость, конфликт с Langfuse wrapper |

---

## R-002: Tool Calling + Structured Output одновременно

### Decision
Передавать `tools` и `response_format` в ОДНОМ вызове API. Схема применяется ТОЛЬКО к финальному текстовому ответу (когда модель не возвращает tool_calls), а не к промежуточным шагам.

### Rationale
Из документации Claude:
> Grammars apply **only to Claude's direct output**, not to tool use calls, tool results, or thinking tags. Grammar state **resets between sections**.

Поведение в agentic loop:
1. **Шаг с tool_calls**: Модель возвращает `tool_calls` → schema НЕ применяется → `message.content` может быть null или reasoning text
2. **Финальный шаг (без tool_calls)**: `message.content` — JSON, соответствующий схеме

`response_format` передаётся на КАЖДОМ вызове в цикле — API сам определяет, когда применить.

### Alternatives Considered
| Альтернатива | Плюсы | Минусы |
|---|---|---|
| Передавать `response_format` только на последнем вызове | Меньше нагрузки на grammar compilation | Нужно определять "последний" вызов; grammar кэшируется после первого |
| Post-process с Pydantic validation | Без зависимости от API | Нет гарантий, нужен retry |

---

## R-003: JSON Schema — поддерживаемые фичи

### Decision
Использовать flat-ish схему с `anyOf` для двух типов ответа (recommendation/informational). Все объекты — с `additionalProperties: false`. Без рекурсии и числовых ограничений.

### Supported
- Базовые типы: object, array, string, integer, number, boolean, null
- `enum` (строки, числа)
- `const`
- `anyOf` — для discriminated unions
- `required`
- `additionalProperties: false` (обязательно для всех объектов)
- `default`

### NOT Supported (вызовет 400)
- Рекурсивные схемы
- `minimum`, `maximum`, `minLength`, `maxLength`
- `additionalProperties` не равный `false`
- Внешний `$ref`
- `minItems` > 1

### Design Decision
Вместо discriminated union через `anyOf` (сложнее, больше вероятность ошибок grammar) — использовать единую плоскую схему, где `wines` может быть пустым массивом для информационных ответов.

---

## R-004: Langfuse совместимость

### Decision
`langfuse.openai.AsyncOpenAI` прозрачно пробрасывает `response_format`. Изменений в Langfuse-интеграции не требуется.

### Rationale
- Langfuse wrapper — drop-in replacement для `openai.AsyncOpenAI`
- Уже работает с `extra_headers`, `extra_body`, `tools`
- `response_format` проходит как обычный параметр `chat.completions.create()`
- Langfuse автоматически логирует schema в metadata trace

### Limitation
`client.beta.chat.completions.parse()` (авто-парсинг Pydantic) НЕ поддерживает Langfuse-атрибуты (`name`, `metadata`). Использовать `chat.completions.create()` + ручной `json.loads()`.

---

## R-005: Формат ответа и парсинг

### Decision
`response.choices[0].message.content` — это JSON-строка. Парсить через `json.loads()` + `Pydantic.model_validate_json()`.

### Rationale
При использовании `chat.completions.create()` (не beta `.parse()`):
```python
raw_json: str = response.choices[0].message.content
parsed = SommelierResponse.model_validate_json(raw_json)
```

SDK НЕ авто-парсит — `message.content` всегда строка. `client.beta.chat.completions.parse()` не рекомендуется с OpenRouter + Langfuse.

---

## R-006: Обработка ошибок и fallback

### Decision
Обрабатывать 3 типа ошибок: refusal, truncation, schema validation. Fallback — существующий heuristic parser.

### Error Types
| Ошибка | `finish_reason` | Обработка |
|---|---|---|
| **Refusal** (safety policy) | `"refusal"` | Вернуть как informational response |
| **Truncation** (max_tokens) | `"length"` | Увеличить max_tokens или fallback |
| **Schema error** (невалидная схема) | 400 HTTP | Ошибка конфигурации, не runtime |
| **JSON parse error** | N/A | Fallback на heuristic parser |

### Fallback Chain
1. Попытка `json.loads()` + Pydantic validation
2. При неудаче — `_parse_heuristic()` (существующий regex-парсер)
3. При неудаче — `send_fallback_response()` (единый текст)

---

## R-007: Текущая архитектура — точки изменений

### Current Data Flow
```
User Message → TelegramBotService.process_message()
  → SommelierService.generate_response()
    → generate_agentic_response()
      → llm_service.generate_with_tools() [в цикле, max 2 итерации]
      ← response.content (str)
    ← response_text (str)
  → _extract_wines_from_response(response_text) [name matching через .find()]
  ← (response_text: str, wines: list[Wine])
→ send_wine_recommendations(response_text, wines)
  → parse_structured_response(response_text) [regex]
  ← ParsedResponse
→ Send intro/wine photos/closing → Telegram
```

### Critical Changes Required

1. **`llm.py` → `generate_with_tools()`**: Добавить параметр `response_format`
2. **`sommelier.py` → `generate_agentic_response()`**: Передать `response_format`, парсить JSON на финальном ответе, рендерить текст для истории
3. **`sommelier_prompts.py`**: Новые Pydantic-модели ответа, обновить промпты (убрать маркеры, добавить инструкции для JSON), обновить `parse_structured_response()`
4. **`telegram_bot.py` → `_extract_wines_from_response()`**: Заменить name matching на extraction из JSON-поля `wines[].wine_name`
5. **`sender.py` → `send_wine_recommendations()`**: Принимать structured object вместо text parsing
6. **`config.py`**: Обновить дефолтную модель
7. **`.env`**: Сменить `LLM_MODEL`

### Key Insight: Wine Matching
Текущая `_extract_wines_from_response()` ищет `wine.name` в тексте через `.find()`. Со structured output имя вина будет в JSON-поле — прямой lookup по имени, 100% надёжность.
