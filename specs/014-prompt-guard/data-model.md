# Data Model: 014-prompt-guard

**Date**: 2026-02-10

## Summary

Эта фича **не требует изменений схемы БД**. Нет новых таблиц, нет новых полей, нет миграций.

## Changes

### Modified: `ParsedResponse` dataclass (`sommelier_prompts.py`)

Единственное изменение в модели данных — расширение in-memory dataclass:

| Поле | Тип | Описание | Изменение |
|------|-----|----------|-----------|
| `intro` | `str` | Текст вступления | Без изменений |
| `wines` | `list[str]` | Тексты винных секций | Без изменений |
| `closing` | `str` | Текст завершения | Без изменений |
| `is_structured` | `bool` | Успешность парсинга | Без изменений |
| **`guard_type`** | **`Optional[str]`** | **Тип guard-маркера** | **NEW** |

**Допустимые значения `guard_type`:**
- `None` — легитимный запрос, guard не сработал
- `"off_topic"` — запрос не по теме вина
- `"prompt_injection"` — попытка переопределить инструкции
- `"social_engineering"` — социальная инженерия (ложные полномочия, угрозы, вознаграждения)

### Logging Format (не БД)

Guard-события логируются через Python logging, не в БД:

```
WARNING GUARD_ALERT type=off_topic user_id=<uuid> message="<first 100 chars>"
```

Отдельная таблица для логирования может быть добавлена в будущем, если потребуется аналитика.
