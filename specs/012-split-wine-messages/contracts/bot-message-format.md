# Contract: Bot Message Format

**Date**: 2026-02-10

## Описание

Контракт формата сообщений Telegram-бота при отправке винных рекомендаций.

## Structured Response Format (LLM → Parser)

Ответ LLM должен содержать маркеры секций:

```
[INTRO]
Краткое вступление (1-2 предложения)
[/INTRO]

[WINE:1]
Название вина, регион, описание, почему подходит
[/WINE:1]

[WINE:2]
Название вина, регион, описание, почему подходит
[/WINE:2]

[WINE:3]
Название вина, регион, описание, почему подходит
[/WINE:3]

[CLOSING]
Вопрос для продолжения диалога
[/CLOSING]
```

### Правила парсинга

- `is_structured = True` если найдены `[INTRO]` И хотя бы один `[WINE:N]`
- `[CLOSING]` опционален
- Маркеры нечувствительны к пробелам внутри (`.strip()`)
- Regex: `\[INTRO\](.*?)\[/INTRO\]` с флагом `re.DOTALL`

## Telegram Message Sequence (Bot → User)

### Structured Path (is_structured=True)

| # | Тип | Содержимое | Parse Mode | Лимит |
|---|-----|-----------|------------|-------|
| 1 | `reply_text` | `sanitize_telegram_markdown(intro)` | Markdown | 4096 chars |
| 2 | `reply_photo` | Wine 1: photo + `strip_markdown(wine_text)` | None (plain text) | Caption: 1024 chars |
| 3 | `reply_photo` | Wine 2: photo + `strip_markdown(wine_text)` | None (plain text) | Caption: 1024 chars |
| 4 | `reply_photo` | Wine 3: photo + `strip_markdown(wine_text)` | None (plain text) | Caption: 1024 chars |
| 5 | `reply_text` | `sanitize_telegram_markdown(closing)` | Markdown | 4096 chars |

### Fallback Path (is_structured=False)

| # | Тип | Содержимое | Parse Mode |
|---|-----|-----------|------------|
| 1 | `reply_text` | `sanitize_telegram_markdown(full_response)` | Markdown |
| 2-4 | `reply_photo` | Extracted wines: photo + `format_wine_photo_caption(wine)` | None |

### No-Image Fallback (per wine)

Если `get_wine_image_path(wine)` возвращает `None`:

| # | Тип | Содержимое | Parse Mode |
|---|-----|-----------|------------|
| N | `reply_text` | `sanitize_telegram_markdown(wine_text)` | Markdown |

## Photo Caption Format (format_wine_photo_caption)

Используется в fallback path. Формат plain text:

```
{wine.name}
{wine.region}, {wine.country}
{grape_varieties}  (if available, first 3 joined)
{sweetness_label}, ~{price_rub}₽
```

Пример:
```
Вино Malbec, Luigi Bosca, 2024
Мендоза, Аргентина
мальбек 100%
сухое, ~2500₽
```

## Markdown Transformations

### sanitize_telegram_markdown (text messages)

| Input | Output |
|-------|--------|
| `### Heading` | `*Heading*` |
| `**bold**` | `*bold*` |
| Всё остальное | Без изменений |

### strip_markdown (photo captions)

| Input | Output |
|-------|--------|
| `**bold**` | `bold` |
| `*italic*` | `italic` |
| `_underline_` | `underline` |
