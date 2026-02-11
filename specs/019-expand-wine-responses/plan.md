# Implementation Plan: Расширенные ответы на околовинные темы

**Branch**: `019-expand-wine-responses` | **Date**: 2026-02-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-expand-wine-responses/spec.md`

## Summary

Бот отвечает слишком кратко на околовинные вопросы (регионы, технологии, история) — обычно 1-2 предложения. Нужно расширить до 5-10 предложений с тематической подводкой к обсуждению конкретных вин. Реализация: модификация системного промпта (`SYSTEM_PROMPT_BASE`) с добавлением инструкций для `response_type: "informational"` + Langfuse-тегирование для аналитики.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, OpenAI SDK (OpenRouter), Langfuse SDK, Pydantic v2
**Storage**: PostgreSQL 16 + pgvector (без изменений схемы)
**Testing**: pytest 8.x, pytest-asyncio (unit + eval тесты)
**Target Platform**: Linux server (VPS, systemd + Nginx)
**Project Type**: Web application (backend)
**Performance Goals**: N/A — изменение промпта, без влияния на производительность
**Constraints**: Увеличение длины ответа увеличивает потребление токенов (~2-3x для informational ответов)
**Scale/Scope**: Изменение 2 файлов (промпт + сомелье-сервис), добавление eval-тестов

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Обоснование |
|---------|--------|-------------|
| Clean Architecture | PASS | Изменения в слое сервисов (промпт + метаданные). Слои не нарушаются. |
| Database First | PASS | Изменений схемы БД нет. |
| TDD | PASS | Eval-тесты для informational ответов будут написаны до/параллельно с изменениями промпта. |
| RAG-First | PASS | Informational ответы уже используют знания LLM (не каталог). Промпт явно говорит: «отвечай из своих знаний с response_type "informational"». Подводка предлагает перейти к каталогу — усиливает RAG-путь. |
| Образование > конверсия | PASS | Фича напрямую усиливает образовательную миссию — более подробные ответы о вине. |
| 18+ и никаких продаж | PASS | Не затрагивается. |
| Приватность данных | PASS | Не затрагивается. |

**Результат**: Все гейты пройдены. Нарушений нет.

## Project Structure

### Documentation (this feature)

```text
specs/019-expand-wine-responses/
├── spec.md              # Спецификация (готова)
├── plan.md              # Этот файл
├── research.md          # Phase 0: анализ промпта и подходов
├── quickstart.md        # Phase 1: инструкции для разработчика
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (изменяемые файлы)

```text
backend/app/services/
├── sommelier_prompts.py    # Модификация SYSTEM_PROMPT_BASE (инструкции для informational)
└── sommelier.py            # Добавление Langfuse-тега для response_type="informational"

backend/tests/eval/
└── test_informational_eval.py  # Новый: eval-тесты для околовинных ответов
```

**Structure Decision**: Изменения минимальны — затрагивают только существующие файлы в `backend/app/services/` плюс один новый eval-тест. Архитектура не меняется.

## Complexity Tracking

> Нарушений конституции нет. Таблица не заполняется.
