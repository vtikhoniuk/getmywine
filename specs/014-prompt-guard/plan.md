# Implementation Plan: Prompt Guard

**Branch**: `014-prompt-guard` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-prompt-guard/spec.md`

## Summary

Добавить многоуровневую защиту AI-сомелье от нецелевого использования: ограничение тематики диалога только вином, защита от prompt injection и социальной инженерии, рекомендации только из каталога. Реализация через обновление системного промпта, расширение парсера ответов для маркера `[GUARD]`, и логирование попыток манипуляций.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x
**Storage**: PostgreSQL 16 + pgvector (без изменений схемы)
**Testing**: pytest (unit + integration)
**Target Platform**: Linux server (VPS, systemd + Nginx)
**Project Type**: web (backend + frontend + telegram bot)
**Performance Goals**: Нет дополнительных требований — парсинг `[GUARD]` маркера добавляет ~0 задержки
**Constraints**: Защита на уровне системного промпта — без дополнительных API-вызовов
**Scale/Scope**: 3 файла для изменения, 2 новых тестовых файла, 0 новых таблиц БД

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture (Routers → Services → Repositories → Models) | PASS | Изменения в Services layer (sommelier_prompts, chat). Без нарушений слоёв |
| Database First | PASS | Нет изменений схемы БД |
| TDD | PASS | Тесты парсера пишутся до кода. Тестовые наборы промптов — для ручной валидации |
| RAG-First | PASS | Укрепляется: явные инструкции «только из каталога» + поведение при запросе вин не из каталога |
| 18+ и никаких продаж | PASS | Без изменений |
| Образование > конверсия | PASS | Guard redirect всегда предлагает винный контент |
| Приватность данных | PASS | Логирование содержит user_id и текст запроса, но не PII |

**Post-Phase 1 re-check**: Все принципы соблюдены. Архитектура не усложнена — расширяется один dataclass, один regex в парсере, один блок в промпте.

## Project Structure

### Documentation (this feature)

```text
specs/014-prompt-guard/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research decisions
├── data-model.md        # Phase 1: data model changes
├── quickstart.md        # Phase 1: implementation quickstart
├── contracts/           # Phase 1: no new API contracts
│   └── README.md        # Explanation why no contracts
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── services/
│       ├── sommelier_prompts.py   # MODIFY: system prompt + ParsedResponse + parser
│       └── chat.py                # MODIFY: guard logging after response parsing
└── tests/
    └── unit/
        ├── test_structured_response.py  # MODIFY: add [GUARD] parser tests
        └── test_prompt_guard.py         # NEW: guard-specific test scenarios
```

**Structure Decision**: Минимальные изменения в существующих файлах. Единственный новый файл — `test_prompt_guard.py` для тестов конкретно guard-сценариев. Парсер остаётся в `sommelier_prompts.py` (единая точка парсинга).

## Complexity Tracking

Нет нарушений Constitution — таблица не требуется.

## Implementation Details

### 1. Обновление системного промпта (`sommelier_prompts.py`)

Добавить в `SYSTEM_PROMPT_BASE` после секции `ОГРАНИЧЕНИЯ:` новые секции:

**ТЕМАТИЧЕСКИЕ ОГРАНИЧЕНИЯ:**
- Список допустимых тем (вино, гастрономия, сочетания еды и вина, виноделие, гастротуризм)
- Инструкция по отклонению: вежливо + перенаправить к вину + стандартный формат ответа

**ЗАЩИТА ОТ МАНИПУЛЯЦИЙ:**
- Игнорирование заявлений о привилегированном доступе
- Устойчивость к угрозам и обещаниям вознаграждений
- Защита от переопределения инструкций
- Запрет раскрытия системного промпта
- Отклонение «новых правил» от пользователя

**РЕКОМЕНДАЦИИ ТОЛЬКО ИЗ КАТАЛОГА:**
- При запросе вина не из каталога — обсудить, предложить аналоги
- При настаивании — объяснить, что рекомендуем только проверенные вина

**МАРКЕР [GUARD]:**
- Инструкция: при отклонении добавлять `[GUARD:тип]` перед `[INTRO]`
- Типы: `off_topic`, `prompt_injection`, `social_engineering`
- При легитимном запросе — маркер НЕ добавляется

### 2. Расширение парсера (`sommelier_prompts.py`)

**ParsedResponse dataclass:**
- Добавить поле `guard_type: Optional[str] = None`

**parse_structured_response():**
- Перед поиском `[INTRO]` — поиск `[GUARD:тип]` через regex `\[GUARD:(\w+)\]`
- Если найден — записать тип в `guard_type`, стрипнуть маркер из текста
- Остальной парсинг ([INTRO], [WINE], [CLOSING]) без изменений

### 3. Логирование в ChatService (`chat.py`)

В `send_message()` после получения ответа от `self.sommelier.generate_response()`:
- Парсить ответ через `parse_structured_response()`
- Если `parsed.guard_type` не None — логировать:
  ```
  logger.warning("GUARD_ALERT type=%s user_id=%s message=\"%s\"", guard_type, user_id, content[:100])
  ```
- Перед сохранением в БД — стрипнуть `[GUARD:тип]` из текста ответа

### 4. Тесты

**test_structured_response.py** — расширение:
- Тест парсинга `[GUARD:off_topic]` перед стандартным ответом
- Тест парсинга `[GUARD:prompt_injection]`
- Тест отсутствия guard_type при обычном ответе
- Тест что guard_type не ломает парсинг [INTRO]/[WINE]/[CLOSING]

**test_prompt_guard.py** — новый файл:
- Тестовые наборы промптов по категориям (off_topic, injection, social_engineering)
- Тесты логирования (mock logger, проверка формата)
- Тесты стрипа [GUARD] из ответа перед сохранением
