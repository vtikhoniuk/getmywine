# План реализации: Регистрация и авторизация

**Ветка**: `001-user-auth` | **Дата**: 2026-02-02 | **Спецификация**: [spec.md](spec.md)

## Резюме

Реализация системы регистрации и авторизации для GetMyWine: email + пароль, проверка возраста 18+, сессии 7 дней, rate limiting, восстановление пароля. Соответствие 152-ФЗ (данные в РФ).

## Технический контекст

**Язык/Версия**: Python 3.12+
**Основные зависимости**: FastAPI, SQLAlchemy 2.0, Alembic, Passlib (bcrypt), python-jose (JWT)
**Хранилище**: PostgreSQL 16
**Тестирование**: pytest, pytest-asyncio, httpx (TestClient)
**Целевая платформа**: Linux VPS (systemd + Nginx)
**Тип проекта**: Web-приложение (backend + frontend SSR)
**Цели производительности**: < 500ms на операции auth (из NFR)
**Ограничения**: Данные хранятся в РФ (152-ФЗ)
**Масштаб**: MVP 100 DAU, 30 одновременных сессий

## Проверка конституции

*GATE: Должен пройти перед Phase 0. Перепроверить после Phase 1.*

| Принцип | Статус | Как соблюдается |
|---------|--------|-----------------|
| **Clean Architecture** | ✅ | Routers → Services → Repositories → Models |
| **Database First** | ✅ | Миграции Alembic перед кодом |
| **TDD** | ✅ | Тесты пишутся до реализации |
| **RAG-First** | N/A | Не применимо к auth |
| **18+ и никаких продаж** | ✅ | Чекбокс возраста при регистрации |
| **Приватность данных** | ✅ | Удаление аккаунта, хеширование паролей |

**Результат**: ✅ Все применимые принципы соблюдены

## Структура проекта

### Документация (эта фича)

```text
specs/001-user-auth/
├── plan.md              # Этот файл
├── spec.md              # Спецификация
├── research.md          # Phase 0: исследование
├── data-model.md        # Phase 1: модель данных
├── quickstart.md        # Phase 1: быстрый старт
├── contracts/           # Phase 1: API контракты
│   └── auth-api.yaml    # OpenAPI 3.0
└── checklists/
    └── requirements.md  # Чеклист качества
```

### Исходный код (корень репозитория)

```text
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── routers/
│   │   └── auth.py          # Auth endpoints
│   ├── services/
│   │   ├── auth.py          # Auth business logic
│   │   └── email.py         # Email sending
│   ├── repositories/
│   │   └── user.py          # User DB operations
│   ├── models/
│   │   └── user.py          # SQLAlchemy models
│   ├── schemas/
│   │   └── auth.py          # Pydantic schemas
│   └── templates/
│       ├── auth/
│       │   ├── login.html
│       │   ├── register.html
│       │   └── reset-password.html
│       └── emails/
│           └── password-reset.html
├── migrations/
│   └── versions/            # Alembic migrations
└── tests/
    ├── conftest.py
    ├── unit/
    │   └── test_auth_service.py
    ├── integration/
    │   └── test_auth_api.py
    └── contract/
        └── test_auth_contract.py
```

**Решение по структуре**: Web-приложение с SSR (HTMX + Jinja2). Backend-only на первом этапе, фронтенд через Jinja2 шаблоны.

## Отслеживание сложности

> Нарушений конституции нет — секция пуста.
