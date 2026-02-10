# Quickstart: 014-prompt-guard

**Branch**: `014-prompt-guard`

## Что меняется

| Файл | Изменение |
|------|-----------|
| `backend/app/services/sommelier_prompts.py` | Добавить секции защиты в `SYSTEM_PROMPT_BASE`. Расширить `ParsedResponse` полем `guard_type`. Обновить `parse_structured_response()` для парсинга `[GUARD:type]` |
| `backend/app/services/chat.py` | Парсинг ответа после LLM-вызова, логирование guard-событий, стрип `[GUARD]` перед сохранением |
| `backend/tests/unit/test_structured_response.py` | Добавить тесты парсинга `[GUARD]` маркера |
| `backend/tests/unit/test_prompt_guard.py` | Новый файл: тесты guard-логирования и стрипа маркера |

## Порядок реализации (TDD)

### Шаг 1: Тесты парсера (Red)
```bash
# Написать тесты для [GUARD] парсинга в test_structured_response.py
cd backend && python -m pytest tests/unit/test_structured_response.py -v
```

### Шаг 2: Расширить ParsedResponse и парсер (Green)
```bash
# Добавить guard_type в ParsedResponse
# Обновить parse_structured_response()
cd backend && python -m pytest tests/unit/test_structured_response.py -v
```

### Шаг 3: Тесты логирования (Red)
```bash
# Написать test_prompt_guard.py — тесты логирования и стрипа
cd backend && python -m pytest tests/unit/test_prompt_guard.py -v
```

### Шаг 4: Логирование в ChatService (Green)
```bash
# Обновить chat.py — парсинг, логирование, стрип
cd backend && python -m pytest tests/unit/test_prompt_guard.py -v
```

### Шаг 5: Обновить системный промпт
```bash
# Добавить защитные секции в SYSTEM_PROMPT_BASE
# Ручное тестирование с LLM
```

### Шаг 6: Полный прогон тестов
```bash
cd backend && python -m pytest tests/ -v
```

## Ключевые решения

1. **Защита в BASE промпте** — все варианты (cold start, personalized, continuation) наследуют автоматически
2. **[GUARD:type] маркер** — перед [INTRO], парсится существующей функцией, стрипается до отправки клиенту
3. **Logging, не DB** — `logger.warning("GUARD_ALERT ...")` через Python logging
4. **Стандартный формат ответа при отклонении** — AI всегда возвращает вина, даже при guard-срабатывании
