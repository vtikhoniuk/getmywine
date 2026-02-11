# CLAUDE.md

Инструкции для Claude Code при работе с Discovery Kit.

## Что это

**Discovery Kit** — набор агентов и скиллов для автоматизации discovery-фазы разработки. Превращает идею в набор документов, готовых для передачи разработчику.

**Философия:** Docs as Code — всё в Markdown, версионируется, модульно.

---

## Архитектура: Агенты vs Скиллы

| Компонент | Содержит | Аналогия |
|-----------|----------|----------|
| **Агент** | Личность, ценности, стиль общения | "Кто ты" |
| **Скилл** | Процесс, шаги, шаблоны вывода | "Что ты делаешь" |

Один агент может иметь несколько скиллов. Скиллы переиспользуются между агентами.

### Naming Convention

```
Первая цифра = номер агента (шаг 10)
Вторая цифра = номер скилла этого агента

00 — Lyra (метаагент)
10 — Business Analyst → скиллы 11, 12, 13
20 — System Analyst → скилл 21
30 — Idea Challenger → скиллы 31, 32, 33, 34
40 — Solution Architect → скиллы 41-47
50 — Product Designer → скиллы 51, 52
61 — Artifact Validator (standalone, без агента)
```

---

## Структура проекта

```
01-discovery-kit-1.1.7/
├── CLAUDE.md                          # Этот файл
├── 99-ideal-development-process.md    # Полный pipeline (справочник)
│
├── 00-temporaty-files/                # Временные файлы, заметки
│   ├── design-tokens-export-note.md
│   └── projects-ideas.md
│
├── 01-agents/
│   ├── 00-mother-of-all-agents.md     # Lyra — метаагент для создания промптов
│   ├── 99-Ben-tech-lead-friend.md     # Ben — техлид-друг
│   ├── 01-discovery-agents/
│   │   ├── 10-business-analyst.md     # Clarifier
│   │   ├── 20-system-analyst.md       # NFR Specialist
│   │   └── 30-idea-challenger.md      # Адвокат дьявола
│   └── 02-solution-design-agents/
│       ├── 40-solution-architect.md   # Архитектор
│       └── 50-product-designer.md     # Структуратор
│
├── 02-skills/
│   ├── 01-discovery-skills/
│   │   ├── 11-brief-writing.md        # Сбор требований, написание брифа
│   │   ├── 12-user-story-mapping.md   # User Story Map
│   │   ├── 13-user-journey-map.md     # User Journey (Mermaid)
│   │   ├── 21-nfr-collection.md       # NFR и атрибуты качества
│   │   ├── 31-lean-canvas.md          # Lean Canvas
│   │   ├── 32-market-research.md      # Deep Market Research (standalone)
│   │   ├── 33-persona-generation.md   # Генерация персон
│   │   └── 34-persona-interview.md    # Симуляция custdev-интервью
│   └── 02-solution-design-skills/
│       ├── 41-artifact-recommendation.md  # Рекомендации по артефактам (standalone)
│       ├── 42-c4-diagrams.md              # C4 Context + Container (Mermaid)
│       ├── 43-tech-research.md            # Deep Research технологий (standalone)
│       ├── 44-adr.md                      # Architecture Decision Records
│       ├── 45-er-diagram.md               # ER + Data Dictionary (Mermaid)
│       ├── 46-sequence-diagrams.md        # Sequence диаграммы (Mermaid)
│       ├── 47-api-inventory.md            # Список API endpoints
│       ├── 51-information-architecture.md # Информационная архитектура
│       ├── 52-wireframe-spec.md           # Unicode wireframes (standalone)
│       └── 61-artifact-validator.md       # Валидация артефактов (standalone)
│
├── 50-project-docs/                   # Сгенерированные артефакты проектов
│   ├── 01-project-01/
│   └── 02-project-02/
│
└── 98-adapters/
    └── 99-education-adapter.md        # Адаптер для образовательных проектов
```

---

## Ключевые паттерны

### Clarification Loop
Скиллы используют итеративный сбор требований с отслеживанием неопределённости:
- Критические разделы (70% веса) + Вспомогательные (30%)
- Цель: неопределённость ≤ 0.01

### Escape Hatch
Всегда давать пользователю выход:
- "Не знаю" → разбить на части или предложить варианты
- "Хватит вопросов" → зафиксировать как открытый вопрос и продолжить

### Gold / Silver / Bronze
Для NFR и технических решений — варианты с разным уровнем амбиций.

### Языковой протокол
- Внутренняя обработка: английский (терминология, поиск)
- Коммуникация с пользователем: только русский

---

## Важные ограничения

### В бизнес-скиллах (11, 12, 13) — НИКАКИХ технических решений

**НЕ делай:**
- Не предлагай технические реализации (веб, мобильное, API)
- Не упоминай фреймворки и языки
- Не принимай архитектурные решения

**Делай:**
- Фокус на ЧТО, ЗАЧЕМ, КТО, КОГДА, ГДЕ
- Технические решения оставляй агентам 40+

### Constraints vs Quality Attributes

| Что | Где | Почему |
|-----|-----|--------|
| **Constraints** (бюджет, сроки, команда) | Brief (11) | Влияют на scope сразу |
| **Quality Attributes** (performance, security) | NFR (21) | Нужен масштаб из USM |

---

## Рекомендуемый порядок

```
1. Brief (11) → USM (12) → NFR (21)     — основа
2. Lean Canvas (31) → Market Research (32) — валидация идеи
3. C4 (42) → ER (45) → API (47) → Sequences (46) — архитектура
4. IA (51) → Wireframes (52)             — UX
5. Artifact Validator (61)               — финальная проверка
```

---

## Выходные артефакты

- **Brief** — описание идеи и проблемы
- **User Story Map** — карта пользовательских сценариев
- **User Journey Map** — визуализация пути пользователя
- **NFR** — нефункциональные требования
- **Lean Canvas** — бизнес-модель на одной странице
- **Personas** — портреты пользователей
- **C4 Diagrams** — архитектурные диаграммы
- **ER Diagram** — модель данных
- **Sequence Diagrams** — диаграммы взаимодействий
- **API Inventory** — список endpoints
- **Information Architecture** — структура навигации
- **Wireframes** — схемы экранов (Unicode)
- **ADR** — записи архитектурных решений

## Active Technologies
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, Jinja2, HTMX (002-chat-welcome)
- PostgreSQL 16 (существующая БД из US-001) (002-chat-welcome)
- PostgreSQL 16 (существующая БД) (003-taste-profile)
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, pgvector, Alembic (005-wine-catalog)
- PostgreSQL 16 + pgvector extension (005-wine-catalog)
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, существующие сервисы (SommelierService, ChatService, LLMService) (011-telegram-bot)
- PostgreSQL 16 + pgvector (существующая БД) (011-telegram-bot)
- Python 3.12+ + python-telegram-bot 21.x, FastAPI, SQLAlchemy 2.0 (012-split-wine-messages)
- PostgreSQL 16 + pgvector (существующая БД, без изменений схемы) (012-split-wine-messages)
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, Alembic, python-telegram-bot 21.x, Pillow, openai (embeddings) (013-normalize-wine-names)
- PostgreSQL 16 + pgvector (HNSW index, cosine distance) (013-normalize-wine-names)
- PostgreSQL 16 + pgvector (без изменений схемы) (014-prompt-guard)
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, OpenAI SDK (для OpenRouter API), pgvector (015-agentic-rag)
- PostgreSQL 16 + pgvector (существующая БД, 50 вин с эмбеддингами 1536 dims) (015-agentic-rag)
- Python 3.12+ + pytest 8.x, pytest-asyncio, SQLAlchemy 2.0, asyncpg, openai (OpenRouter-compatible), pgvector (016-llm-eval-tests)
- PostgreSQL 16 + pgvector (существующая dev-БД с 50 винами и embeddings) (016-llm-eval-tests)
- Python 3.12+ + langfuse (Python SDK), openai (уже установлен — Langfuse обёртка совместима), Docker Compose (017-langfuse-monitoring)
- PostgreSQL 17 (отдельный для Langfuse), ClickHouse (аналитика трейсов), MinIO (blob storage), Redis 7 (очередь) (017-langfuse-monitoring)
- Python 3.12+ + FastAPI, SQLAlchemy 2.0, python-telegram-bot 21.x, OpenAI SDK (для OpenRouter), Langfuse SDK, Pydantic v2 (018-structured-output)

## Recent Changes
- 002-chat-welcome: Added Python 3.12+ + FastAPI, SQLAlchemy 2.0, Jinja2, HTMX
