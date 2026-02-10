# Implementation Plan: 012-split-wine-messages

**Branch**: `012-split-wine-messages` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-split-wine-messages/spec.md`

## Summary

Формализация существующего формата 5 сообщений в Telegram-боте (вступление → 3 вина с фото → завершение). Функционал уже реализован в коде. Основная работа: рефакторинг дублированной логики отправки между `start.py` и `message.py`, добавление unit-тестов для парсинга, утилит и форматирования.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: python-telegram-bot 21.x, FastAPI, SQLAlchemy 2.0
**Storage**: PostgreSQL 16 + pgvector (существующая БД, без изменений схемы)
**Testing**: pytest
**Target Platform**: Linux server (VPS, systemd + Nginx)
**Project Type**: web (backend-only для этой фичи)
**Performance Goals**: Все 5 сообщений доставлены за ≤15 секунд (включая LLM-генерацию)
**Constraints**: Telegram caption ≤1024 символов, Markdown v1, sequential sending
**Scale/Scope**: ~50 вин в каталоге, стандартная нагрузка (десятки пользователей)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture (Routers → Services → Repositories → Models) | PASS | Сохраняется: handlers → TelegramBotService → SommelierService → Wine model |
| Database First (сначала миграция) | PASS | Миграции не требуются — схема не изменяется |
| TDD (Red → Green → Refactor) | VIOLATION → WILL FIX | Тесты отсутствуют — будут добавлены |
| RAG-First (рекомендации из каталога) | PASS | Не затрагивается — алгоритм подбора вне scope |
| 18+ и никаких продаж | PASS | Не затрагивается |
| Образование > конверсия | PASS | Формат сообщений объясняет "почему" рекомендуем |
| Приватность данных | PASS | Не затрагивается |
| Ruff, Commitizen, OpenAPI | PASS | Будет соблюдено |

**Re-check after Phase 1**: TDD violation будет устранён добавлением тестов.

## Project Structure

### Documentation (this feature)

```text
specs/012-split-wine-messages/
├── plan.md              # Этот файл
├── research.md          # Анализ текущей реализации
├── data-model.md        # Модель данных (без изменений)
├── quickstart.md        # Инструкция по быстрому старту
├── contracts/
│   └── bot-message-format.md  # Контракт формата сообщений
└── tasks.md             # Задачи (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── start.py          # Обработчик /start (рефакторинг)
│   │   │   └── message.py        # Обработчик сообщений (рефакторинг)
│   │   ├── formatters.py         # Форматирование карточек вин
│   │   ├── utils.py              # Утилиты (markdown, images, language)
│   │   └── sender.py             # НОВЫЙ: общая логика отправки 5 сообщений
│   └── services/
│       └── sommelier_prompts.py  # Парсинг структурированного ответа
└── tests/
    └── unit/
        ├── test_structured_response.py  # НОВЫЙ: тесты парсинга
        ├── test_bot_utils.py            # НОВЫЙ: тесты утилит
        ├── test_bot_formatters.py       # НОВЫЙ: тесты форматирования
        └── test_bot_sender.py           # НОВЫЙ: тесты отправки
```

**Structure Decision**: Используется существующая структура `backend/`. Единственный новый production-файл — `sender.py` для устранения дублирования. 4 новых тестовых файла.

## Implementation Approach

### Шаг 1: Тесты для существующего кода (TDD — Red)

Написать тесты, которые фиксируют текущее поведение:

1. **test_structured_response.py** — парсинг `parse_structured_response()`:
   - Полный ответ с 3 винами → `is_structured=True`
   - Ответ с 1 вином → `is_structured=True`, `wines` содержит 1 элемент
   - Ответ без маркеров → `is_structured=False`
   - Ответ с intro но без вин → `is_structured=False`
   - Пустая строка → `is_structured=False`
   - `strip_markdown()` — удаление `**bold**`, `*italic*`, `_underline_`

2. **test_bot_utils.py** — утилиты:
   - `sanitize_telegram_markdown()` — конвертация заголовков и bold
   - `get_wine_image_path()` — резолв пути, None при отсутствии файла, None при пустом URL
   - `detect_language()` — русский/английский по порогу кириллицы

3. **test_bot_formatters.py** — форматирование:
   - `format_wine_photo_caption()` — корректный формат plain text
   - `get_sweetness_label()` — локализация типов вин

### Шаг 2: Рефакторинг — вынести общую логику (Refactor)

Создать `backend/app/bot/sender.py` с функцией:

```python
async def send_wine_recommendations(
    update: Update,
    response_text: str,
    wines: list[Wine],
    language: str = "ru",
) -> bool:
    """Send structured wine recommendations as 5 separate messages.

    Returns True if structured format was sent, False if fallback needed.
    """
```

Обновить `start.py` и `message.py` для использования `send_wine_recommendations()`.

### Шаг 3: Тесты для sender.py (TDD — Green)

4. **test_bot_sender.py** — интеграционные тесты с мокированным Telegram API:
   - Structured path: 5 вызовов (1 text + 3 photo + 1 text)
   - Fallback path: 1 text + N photos
   - Missing image fallback: text вместо photo
   - Caption truncation: ≤1024 символов

### Шаг 4: Валидация

- Все тесты проходят (`pytest`)
- Ruff без ошибок
- Ручная проверка в Telegram (если доступен токен)
