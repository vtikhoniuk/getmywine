# Research: Sessions History

**Date**: 2026-02-03
**Feature**: 010-sessions
**Status**: Complete

## Research Questions

1. Как лучше структурировать модель данных для множественных сессий?
2. Как эффективно генерировать названия сессий через LLM?
3. Как извлекать и хранить cross-session контекст?
4. Какой UX паттерн использовать для сайдбара?

---

## 1. Data Model Decision

### Decision: Модифицировать существующую модель Conversation

**Rationale:**
- Conversation уже связана с messages через FK
- Минимизирует изменения в существующем коде
- Messages остаются привязанными к conversation_id

**Alternatives Considered:**

| Вариант | Pros | Cons |
|---------|------|------|
| Modify Conversation | Минимум изменений, переиспользует логику | Миграция данных |
| New Session model | Чистая абстракция | Дублирование, много изменений |
| Conversation + Session (1:1) | Разделение concerns | Избыточная сложность |

**Changes Required:**

```python
# Current
class Conversation:
    user_id: UUID  # unique=True
    created_at: datetime
    updated_at: datetime

# New
class Conversation:
    user_id: UUID  # unique=False (CHANGE)
    title: Optional[str]  # NEW: max 30 chars
    closed_at: Optional[datetime]  # NEW: when session ended
    created_at: datetime
    updated_at: datetime
```

**Migration Strategy:**
1. Remove unique constraint on user_id
2. Add nullable title column
3. Add nullable closed_at column
4. Existing conversations: set title = formatted date

---

## 2. Session Naming Strategy

### Decision: LLM-based naming with fallback

**Prompt Design:**
```
Сгенерируй короткое название (1-3 слова, максимум 30 символов) для диалога на основе первых сообщений.
Название должно отражать тему: тип вина, событие или блюдо.

Примеры хороших названий:
- "Вино к стейку"
- "Бордо на ДР"
- "Розовое для пикника"
- "Новое шардоне"

Первое сообщение пользователя: {user_message}
Ответ AI: {ai_response}

Верни ТОЛЬКО название, без кавычек и пояснений.
```

**Implementation:**
- Trigger: После первого ответа AI (не welcome message)
- Async: Не блокирует основной response
- Fallback: Дата в формате "D месяца" ("3 февраля")
- Cache: Не пересчитывается после генерации

**Model**: Claude haiku для скорости и cost efficiency

---

## 3. Cross-Session Context Strategy

### Decision: Lazy extraction + summary storage

**Approach:**
1. При генерации welcome message извлекаем факты из последних 5 сессий
2. Храним summary в taste_profiles.session_insights (JSONB)
3. Обновляем при закрытии сессии

**Extracted Facts:**
```json
{
  "liked_wines": ["Бордо 2019", "Пино Нуар"],
  "disliked_wines": ["Сладкие"],
  "events_discussed": ["день рождения", "ужин"],
  "foods_paired": ["стейк", "рыба"],
  "last_updated": "2026-02-03T12:00:00Z"
}
```

**LLM Extraction Prompt:**
```
Извлеки ключевые факты из истории диалога для профиля пользователя.
Верни JSON с полями:
- liked_wines: список понравившихся вин
- disliked_wines: список не понравившихся
- events_discussed: упомянутые события
- foods_paired: блюда для сочетания

История: {messages}
```

**Alternatives Considered:**

| Вариант | Pros | Cons |
|---------|------|------|
| On-demand extraction | Всегда свежие данные | Медленно, дорого |
| Pre-computed summary | Быстро | Может устареть |
| Hybrid (выбран) | Баланс | Сложнее реализовать |

---

## 4. UI/UX Patterns

### Decision: ChatGPT-style sidebar with HTMX

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ [≡] GetMyWine                              [User ▾]     │
├──────────────────┬─────────────────────────────────────────┤
│                  │                                         │
│  [+ Новый диалог]│  Welcome message...                     │
│                  │                                         │
│  Сегодня         │  > User: Посоветуй вино к стейку       │
│  ├─ Вино к стейку│  < AI: Отличный выбор! Для стейка...   │
│  └─ Розовое...   │                                         │
│                  │                                         │
│  Вчера           │                                         │
│  ├─ Бордо на ДР  │                                         │
│  └─ Игристое     │                                         │
│                  │                                         │
│  [Показать ещё]  │  ┌──────────────────────────────────┐   │
│                  │  │ Напишите сообщение...     [Send] │   │
└──────────────────┴──┴──────────────────────────────────┴───┘
```

**HTMX Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/sessions` | GET | Список сессий (partial) |
| `/chat/sessions/{id}` | GET | История сессии (read-only) |
| `/chat/sessions` | POST | Создать новую сессию |
| `/chat/sessions/{id}` | DELETE | Удалить сессию |
| `/chat/sessions/{id}/title` | GET | Получить/обновить название |

**HTMX Attributes:**
```html
<!-- Sidebar list -->
<div hx-get="/chat/sessions"
     hx-trigger="load"
     hx-swap="innerHTML">
</div>

<!-- Session item -->
<a hx-get="/chat/sessions/{{ session.id }}"
   hx-target="#chat-messages"
   hx-swap="innerHTML"
   hx-push-url="true">
  {{ session.title }}
</a>

<!-- New session button -->
<button hx-post="/chat/sessions"
        hx-target="#chat-messages"
        hx-swap="innerHTML">
  + Новый диалог
</button>
```

---

## 5. Lifecycle Management

### Decision: Background task for cleanup

**Auto-close Logic:**
- Check `updated_at` vs current time
- If > 30 min → set `closed_at = updated_at + 30 min`
- Triggered on: next user request OR background job

**Retention:**
- Soft delete: set `deleted_at` timestamp
- Hard delete: background job after 90 days
- Cascade: ON DELETE CASCADE from users

**Implementation Options:**

| Approach | Pros | Cons |
|----------|------|------|
| On-request check | Simple, no infra | Latency on first request |
| Background cron | Clean separation | Extra infra |
| PostgreSQL triggers | DB-native | Harder to debug |

**Chosen**: On-request check for MVP, background job later if needed.

---

## Summary of Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Data model | Modify Conversation | Minimal changes, reuse messages |
| Session naming | LLM haiku + fallback | Fast, cheap, good quality |
| Cross-session context | Lazy extraction → JSONB | Balance speed and freshness |
| UI pattern | HTMX sidebar | Matches existing stack |
| Lifecycle | On-request check | Simple MVP |

---

## Open Questions (Resolved)

- ~~Как обрабатывать конкурентные запросы?~~ → Optimistic locking через updated_at
- ~~Нужен ли поиск по сессиям?~~ → Out of scope для v1
- ~~Как группировать сессии в sidebar?~~ → По дате (сегодня/вчера/старее)
