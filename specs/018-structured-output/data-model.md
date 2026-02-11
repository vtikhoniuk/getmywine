# Data Model: Structured Output for Wine Recommendations

**Branch**: `018-structured-output` | **Date**: 2026-02-11

## Overview

Новые Pydantic-модели описывают структуру JSON-ответа LLM. Не затрагивают схему БД — это in-memory модели для парсинга и передачи между слоями.

## Entities

### WineRecommendation

Описание одного рекомендованного вина в ответе LLM.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wine_name` | `str` | Yes | Имя вина, точно как в каталоге. LLM копирует из результатов поиска |
| `description` | `str` | Yes | Описание вина с объяснением почему подходит (2-3 предложения, markdown) |

**Validation Rules:**
- `wine_name` не может быть пустым
- `description` не может быть пустым

**Relationships:**
- Маппится на `Wine` модель из БД через lookup по `wine_name`

---

### SommelierResponse

Единая модель ответа LLM. Плоская структура (без discriminated union) — тип определяется полем `response_type`, а `wines` может быть пустым.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `response_type` | `str` (enum) | Yes | Тип ответа: `"recommendation"`, `"informational"`, `"off_topic"` |
| `intro` | `str` | Yes | Вступительный текст (1-2 предложения) |
| `wines` | `list[WineRecommendation]` | Yes | Список рекомендованных вин (0-3 штуки). Пустой для informational/off_topic |
| `closing` | `str` | Yes | Завершающий вопрос или фраза для продолжения диалога |
| `guard_type` | `str` или `null` | No | Тип защиты: `"off_topic"`, `"prompt_injection"`, `"social_engineering"`, или null |

**Validation Rules:**
- `response_type` — одно из: `recommendation`, `informational`, `off_topic`
- `wines` — массив длиной 0-3
- Для `response_type: "recommendation"` — `wines` должен содержать >= 1 элемент (enforced в коде, не в schema)
- Для `response_type: "informational"` или `"off_topic"` — `wines` должен быть пустым
- `guard_type` обязателен для `response_type: "off_topic"`

**State Transitions:** N/A (immutable response object)

---

### ParsedResponse (existing, updated)

Существующий dataclass обновляется для совместимости с новым structured output, сохраняя обратную совместимость с heuristic parser.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `intro` | `str` | No | Вступительный текст |
| `wines` | `list[str]` | No | Текстовые блоки описания вин (для legacy) |
| `wine_names` | `list[str]` | No | **NEW**: Имена вин из каталога (для structured output) |
| `closing` | `str` | No | Завершающий текст |
| `is_structured` | `bool` | No | Удалось ли распарсить структуру |
| `guard_type` | `str` or `None` | No | Тип защиты |

**Migration Note:** `wine_names` добавляется как новое поле; `wines` (текстовые блоки) сохраняется для heuristic fallback.

---

## Mapping: SommelierResponse → ParsedResponse

```
SommelierResponse.intro       → ParsedResponse.intro
SommelierResponse.wines[].description → ParsedResponse.wines[]
SommelierResponse.wines[].wine_name   → ParsedResponse.wine_names[]
SommelierResponse.closing     → ParsedResponse.closing
SommelierResponse.guard_type  → ParsedResponse.guard_type
is_structured = True (always for valid JSON parse)
```

## Mapping: SommelierResponse → Conversation History

Для сохранения в историю диалога JSON-ответ рендерится в текст:

```
{intro}

{wines[0].description}

{wines[1].description}

{wines[2].description}

{closing}
```

Это обеспечивает естественный контекст для продолжения диалога и экономит токены (без JSON-обёртки).

## Mapping: SommelierResponse → Telegram Messages

| SommelierResponse field | Telegram action |
|---|---|
| `intro` | `reply_text(intro)` — первое сообщение |
| `wines[i].wine_name` | Lookup `Wine` by name → `get_wine_image_path(wine)` → `reply_photo()` |
| `wines[i].description` | Caption к фото (или текстовое сообщение если нет фото) |
| `closing` | `reply_text(closing)` — последнее сообщение |

## Database Impact

**Нет изменений схемы БД.** Все новые модели — in-memory Pydantic для парсинга ответов LLM. Существующая таблица `messages` продолжает хранить `content: Text` (рендеренный текст).
