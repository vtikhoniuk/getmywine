# Research: Telegram-бот для GetMyWine

**Feature**: 011-telegram-bot
**Date**: 2026-02-05

## Research Tasks

### 1. Telegram Bot Framework Selection

**Decision**: python-telegram-bot 21.x

**Rationale**:
- Mature, well-documented library with async support
- Active development (v21 released 2024)
- Native Python asyncio integration — works with existing FastAPI async code
- Built-in conversation handlers for multi-step dialogs
- Good testing support with pytest-telegram-bot

**Alternatives Considered**:
- **aiogram 3.x**: Also async, slightly newer API, but less documentation in Russian community
- **Telethon**: More for user accounts, overkill for bots
- **pyrogram**: Similar to Telethon, not bot-focused

### 2. Bot Deployment Pattern (Polling vs Webhooks)

**Decision**: Long Polling for MVP, migration path to Webhooks for production

**Rationale**:
- **Polling advantages for MVP**:
  - No need for public HTTPS endpoint
  - Simpler local development and testing
  - Works behind firewalls/NAT
  - Easier debugging (logs are local)
- **Webhook advantages** (future):
  - Lower latency
  - Better for high load (no constant connection)
  - Required for serverless deployment

**Implementation**:
```python
# MVP: Polling mode
application.run_polling()

# Future: Webhook mode (when TELEGRAM_WEBHOOK_URL is set)
application.run_webhook(
    listen="0.0.0.0",
    port=8443,
    webhook_url=settings.telegram_webhook_url,
)
```

**Migration Path**:
- Add `TELEGRAM_MODE` env var: `polling` (default) | `webhook`
- When webhook URL configured, auto-switch to webhook mode

### 3. FastAPI + Telegram Bot Integration

**Decision**: Separate process with shared database

**Rationale**:
- FR-019 requires independent startup of web and bot
- Shared PostgreSQL database for user profiles and sessions
- Both use same SQLAlchemy models and repositories

**Implementation Options**:

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Same process, lifespan events | Single deploy | Coupling, complex shutdown | ❌ |
| Separate process, shared DB | Independent scaling, isolation | Two processes to manage | ✅ MVP |
| Webhook in FastAPI router | One process, webhook benefits | Requires HTTPS, more complex | Future |

**Chosen Architecture**:
```
┌─────────────────┐     ┌─────────────────┐
│   FastAPI Web   │     │  Telegram Bot   │
│   (port 8000)   │     │   (polling)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────┴──────┐
              │ PostgreSQL  │
              │   + pgvector│
              └─────────────┘
```

**Startup Commands**:
```bash
# Web only
ENABLE_BOT=false uvicorn app.main:app

# Bot only
ENABLE_WEB=false python -m app.bot.main

# Both (development)
ENABLE_BOT=true ENABLE_WEB=true python -m app.main
```

### 4. Telegram User ↔ Web User Linking

**Decision**: Optional linking via email verification code

**Rationale**:
- FR-005: Бот ДОЛЖЕН предоставлять возможность связать Telegram ID с существующим email-аккаунтом
- New Telegram users get standalone profile (TelegramUser with null user_id)
- Existing web users can link via `/link <email>` → verification code sent to email

**Flow**:
```
TelegramUser (telegram_id: 123456)
     │
     │ optional FK
     ▼
User (id: uuid, email: "user@example.com")
```

**Linking Process**:
1. User sends `/link user@example.com`
2. Bot checks if email exists in users table
3. If yes, sends 6-digit code to email
4. User sends code to bot
5. Bot links telegram_id to user_id
6. Profile merged (Telegram profile takes precedence for new data)

### 5. Session Management for Telegram

**Decision**: 24-hour session expiry (per clarification), reuse ChatSession model

**Rationale**:
- Clarification: "Session expires after 24 hours of inactivity"
- Reuse existing Conversation model with new `channel` field
- Same message history format, same LLM context

**Changes to Conversation model**:
```python
class Conversation(Base):
    # Existing fields...
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="web",  # "web" | "telegram"
    )
```

**Session Logic**:
- Web: 30 min inactivity (existing)
- Telegram: 24 hour inactivity (new)
- Configurable via `session_inactivity_minutes` per channel

### 6. Language Detection & Response

**Decision**: Telegram locale → message language detection → respond in same language

**Rationale**:
- Clarification: "Изначально определяется по локали Telegram, затем бот отвечает на языке сообщения пользователя"
- Telegram API provides `user.language_code` (e.g., "ru", "en")
- Simple heuristic for message language detection

**Implementation**:
```python
def detect_language(message_text: str, telegram_locale: str) -> str:
    """Detect language from message, fallback to Telegram locale."""
    # Simple Cyrillic detection
    cyrillic_ratio = sum(1 for c in message_text if '\u0400' <= c <= '\u04FF') / max(len(message_text), 1)
    if cyrillic_ratio > 0.3:
        return "ru"
    if telegram_locale and telegram_locale.startswith("ru"):
        return "ru"
    return "en"  # Default to English
```

**LLM Prompt Modification**:
- Add language instruction to system prompt based on detected language
- "Отвечай на русском языке" or "Respond in English"

### 7. Wine Card Formatting for Telegram

**Decision**: Markdown formatting with emoji indicators

**Rationale**:
- FR-009: Структурированная информация о вине
- FR-010: Адаптация для мобильного формата
- Telegram supports MarkdownV2 and HTML

**Format Example**:
```
🍷 *Château Margaux 2015*
📍 Бордо, Франция
🍇 Каберне Совиньон, Мерло

*Характеристики:*
• Сладость: сухое
• Кислотность: ⬛⬛⬛⬜⬜
• Танины: ⬛⬛⬛⬛⬜
• Тело: ⬛⬛⬛⬛⬜

💰 ~$350

*Почему вам понравится:*
Классическое бордо с элегантными танинами...

[👍 Понравилось] [👎 Не моё]
```

**Inline Keyboard for Feedback** (FR-014):
```python
InlineKeyboardMarkup([
    [
        InlineKeyboardButton("👍", callback_data=f"like:{wine_id}"),
        InlineKeyboardButton("👎", callback_data=f"dislike:{wine_id}"),
    ]
])
```

### 8. Error Handling & LLM Fallback

**Decision**: Graceful degradation with user-friendly messages

**Rationale**:
- Clarification: "Возвращать сообщение об ошибке и предлагать попробовать позже"
- NOTE-009: Minimal observability — log critical errors only

**Error Messages**:
| Error Type | User Message |
|------------|--------------|
| LLM unavailable | "К сожалению, сервис рекомендаций временно недоступен. Попробуйте через несколько минут." |
| Database error | "Произошла техническая ошибка. Мы уже работаем над решением." |
| Unknown command | "Я не понял запрос. Попробуйте переформулировать или отправьте /help" |
| No wines found | "К сожалению, не нашёл подходящих вин. Попробуйте уточнить критерии." |

### 9. Testing Strategy

**Decision**: Unit tests for handlers + integration tests with mocked Telegram API

**Rationale**:
- Constitution: TDD — тесты перед кодом
- python-telegram-bot provides test utilities

**Test Structure**:
```
tests/
├── unit/
│   ├── test_telegram_handlers.py    # Handler logic
│   ├── test_telegram_formatters.py  # Wine card formatting
│   └── test_language_detection.py   # Language detection
└── integration/
    └── test_telegram_flow.py        # Full flow with mocked bot
```

**Mocking Strategy**:
- Mock `telegram.Bot` for unit tests
- Use `pytest-asyncio` for async handlers
- Reuse existing database fixtures from `tests/conftest.py`

### 10. Configuration & Environment Variables

**Decision**: Extend existing Settings class

**New Environment Variables**:
```python
# Telegram Bot
telegram_bot_token: str = ""           # @BotFather token
telegram_webhook_url: str = ""         # Optional: for webhook mode
telegram_mode: str = "polling"         # "polling" | "webhook"

# Feature flags
enable_telegram_bot: bool = True       # Enable/disable bot
enable_web: bool = True                # Enable/disable web

# Telegram-specific session
telegram_session_inactivity_hours: int = 24  # Session timeout for Telegram
```

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Framework | python-telegram-bot 21.x | Mature, async, good docs |
| Deployment | Polling (MVP) → Webhooks (future) | Simplicity for MVP |
| Architecture | Separate process, shared DB | FR-019 independence |
| User linking | Optional via email code | FR-005 support |
| Sessions | 24h expiry, reuse Conversation | Per clarification |
| Language | Telegram locale + message detection | Per clarification |
| Formatting | Markdown with emoji | Mobile-friendly |
| Testing | Unit + integration, mocked API | TDD compliance |
