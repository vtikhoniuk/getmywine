# C4 Архитектура: GetMyWine

> **Дата:** 2026-02-01
> **Версия:** 1.0

---

## Level 1: System Context

```mermaid
flowchart TB
    User[("👤 Пользователь")]

    subgraph System["GetMyWine"]
        App["🍷 Веб-приложение"]
    end

    LLM["🤖 LLM API\n(Claude/GPT)"]

    User -->|"Использует"| App
    App -->|"Генерация ответов"| LLM
```

**Описание:**
- Пользователь взаимодействует через веб-браузер
- Система использует внешний LLM API для генерации рекомендаций

---

## Level 2: Container Diagram

```mermaid
flowchart TB
    User[("👤 Пользователь")]

    subgraph System["GetMyWine"]
        Frontend["📄 Frontend\n(HTMX + JS)"]
        Backend["⚙️ Backend API\n(FastAPI)"]
        DB[("🗄️ Database\n(PostgreSQL + pgvector)")]
    end

    LLM["🤖 LLM API"]

    User -->|"HTTPS"| Frontend
    Frontend -->|"HTMX requests"| Backend
    Backend -->|"SQL + Vector search"| DB
    Backend -->|"Chat completion"| LLM
```

**Контейнеры:**

| Контейнер | Технология | Назначение |
|-----------|------------|------------|
| Frontend | HTMX + JavaScript | UI, чат-интерфейс, реактивность |
| Backend | FastAPI (Python) | Бизнес-логика, API, SSR шаблонов |
| Database | PostgreSQL + pgvector | Пользователи, профили, история, embeddings |
| LLM API | Claude / GPT | Генерация ответов |

---

## Level 3: Component Diagram (Backend)

```mermaid
flowchart TB
    subgraph Backend["FastAPI Backend"]
        Auth["🔐 Auth"]
        Chat["💬 Chat"]
        Profile["👤 Profile"]
        Catalog["🍷 Catalog"]
        RAG["🔍 RAG"]
        Templates["📄 Jinja2 Templates"]
    end

    DB[("PostgreSQL\n+ pgvector")]
    LLM["LLM API"]

    Auth --> DB
    Profile --> DB
    Chat --> RAG
    Chat --> LLM
    RAG --> DB
    Catalog --> DB
    Templates --> Chat
    Templates --> Profile
```

**Компоненты:**

| Компонент | Ответственность |
|-----------|-----------------|
| Auth | Регистрация, вход, сессии (JWT) |
| Chat | Обработка сообщений, история |
| Profile | Вкусовой профиль, настройки |
| Catalog | CRUD вин, поиск |
| RAG | Поиск релевантных вин через pgvector |
| Templates | Jinja2 шаблоны для HTMX |

---

## Технологический стек

### MVP Stack:

| Слой | Технология | Почему |
|------|------------|--------|
| **Frontend** | HTMX + Vanilla JS | Простота, минимум JS, быстрая разработка |
| **Backend** | FastAPI | Async, типизация, хорошая документация |
| **Templates** | Jinja2 | SSR, интеграция с HTMX |
| **Database** | PostgreSQL | Надёжность, pgvector встроен |
| **Vector** | pgvector | Embeddings в той же БД |
| **LLM** | Claude API | Качество, русский язык |
| **Hosting** | VPS | Полный контроль, фиксированная стоимость |

### Python зависимости:

```
fastapi
uvicorn
sqlalchemy
asyncpg
pgvector
jinja2
python-jose[cryptography]  # JWT
passlib[bcrypt]            # passwords
anthropic                  # Claude API
```

---

## Деплоймент

```mermaid
flowchart LR
    Git["GitHub"] -->|"git pull"| VPS["VPS"]
    VPS -->|"systemd"| Uvicorn["Uvicorn"]
    Uvicorn --> Nginx["Nginx"]
    Nginx -->|"HTTPS"| Users["Пользователи"]
    VPS --> PostgreSQL["PostgreSQL"]
```

**Процесс:**
1. Push в main
2. SSH на VPS, git pull
3. Перезапуск сервиса через systemd
4. Nginx как reverse proxy + SSL (Let's Encrypt)

**Структура на VPS:**
```
/opt/getmywine/
├── app/
│   ├── main.py
│   ├── routers/
│   ├── models/
│   ├── templates/
│   └── static/
├── .env
└── venv/
```
