# Implementation Plan: Taste Profile Discovery

**Branch**: `003-taste-profile` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-taste-profile/spec.md`

## Summary

Реализация системы изучения вкусового профиля пользователя. Включает: возможность пропустить онбординг-опрос, диалоговый сбор предпочтений через AI, описание запомнившихся вин свободным текстом, установку бюджета, автоматическое обновление профиля из диалогов. Профиль хранит параметры: сладость, кислотность, танины, тело, ароматы — каждый с оценкой уверенности.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Jinja2, HTMX
**Storage**: PostgreSQL 16 (существующая БД)
**Testing**: pytest, pytest-asyncio, httpx
**Target Platform**: Linux server (Docker)
**Project Type**: Web application (backend + SSR frontend)
**Performance Goals**: Обновление профиля < 500ms, извлечение характеристик < 2s
**Constraints**: Профиль хранится бессрочно, mock AI на этом этапе
**Scale/Scope**: MVP — один профиль на пользователя

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Clean Architecture | ✅ Pass | Routers → Services → Repositories → Models |
| Database First | ✅ Pass | Миграции для TasteProfile, WineMemory перед кодом |
| TDD | ✅ Pass | Contract tests перед реализацией |
| RAG-First | ⚪ N/A | Не применяется — сбор данных, не рекомендации |
| 18+ и никаких продаж | ✅ Pass | Сбор предпочтений, не продажи |
| Образование > конверсия | ✅ Pass | AI объясняет связь продуктов с вином |
| Приватность данных | ✅ Pass | Профиль принадлежит пользователю |

**Gate Status**: ✅ PASS — можно переходить к Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/003-taste-profile/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── profile-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── models/
│   │   ├── user.py              # Existing (US-001)
│   │   ├── message.py           # From US-002
│   │   ├── conversation.py      # From US-002
│   │   ├── taste_profile.py     # NEW
│   │   └── wine_memory.py       # NEW
│   ├── repositories/
│   │   ├── user.py              # Existing
│   │   ├── taste_profile.py     # NEW
│   │   └── wine_memory.py       # NEW
│   ├── services/
│   │   ├── auth.py              # Existing
│   │   ├── chat.py              # From US-002
│   │   ├── profile.py           # NEW (profile management)
│   │   └── profile_extractor.py # NEW (extract preferences from text)
│   ├── routers/
│   │   ├── auth.py              # Existing
│   │   ├── chat.py              # From US-002
│   │   └── profile.py           # NEW
│   ├── schemas/
│   │   ├── auth.py              # Existing
│   │   ├── chat.py              # From US-002
│   │   └── profile.py           # NEW
│   └── templates/
│       ├── chat.html            # From US-002 (modify for onboarding)
│       └── components/
│           └── onboarding.html  # NEW (skip/start survey UI)
├── migrations/
│   └── versions/
│       └── 005_create_taste_profile_tables.py  # NEW
└── tests/
    ├── contract/
    │   └── test_profile.py      # NEW
    ├── integration/
    │   └── test_onboarding_flow.py  # NEW
    └── unit/
        └── test_profile_extractor.py  # NEW
```

**Structure Decision**: Используем существующую структуру backend/ из US-001/US-002. Добавляем модели профиля, сервис извлечения предпочтений и API для управления профилем.

## Complexity Tracking

> Нет нарушений Constitution — таблица не требуется.
