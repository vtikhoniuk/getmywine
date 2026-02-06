# Quickstart: Telegram-бот для GetMyWine

**Feature**: 011-telegram-bot
**Date**: 2026-02-05

## Prerequisites

- Python 3.12+
- PostgreSQL 16 with pgvector extension
- Existing GetMyWine backend running
- Telegram account

## 1. Create Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot`
3. Choose a name: `GetMyWine` (display name)
4. Choose a username: `getmywine_bot` (must end with `bot`)
5. Save the **HTTP API token** — you'll need it

### Configure Bot via BotFather

```
/setdescription
# Paste the description from contracts/bot-commands.md

/setabouttext
# Paste the about text from contracts/bot-commands.md

/setcommands
# Paste:
start - Начать работу с ботом
help - Показать справку
profile - Ваш вкусовой профиль
link - Связать с веб-аккаунтом
```

## 2. Install Dependencies

```bash
cd backend
pip install "python-telegram-bot[job-queue]"
```

This adds:
- `python-telegram-bot` — Telegram Bot API wrapper
- `APScheduler` — for job queue (session cleanup)

## 3. Configure Environment

Add to `.env`:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_MODE=polling  # or "webhook" for production

# Feature flags (optional, both enabled by default)
ENABLE_TELEGRAM_BOT=true
ENABLE_WEB=true

# Session timeout for Telegram (hours)
TELEGRAM_SESSION_INACTIVITY_HOURS=24
```

## 4. Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `telegram_users` table
- Adds `channel` and `telegram_user_id` columns to `conversations`

## 5. Run the Bot

### Option A: Bot Only

```bash
cd backend
ENABLE_WEB=false python -m app.bot.main
```

### Option B: Web Only (no bot)

```bash
cd backend
ENABLE_TELEGRAM_BOT=false uvicorn app.main:app --reload
```

### Option C: Both (development)

```bash
cd backend
uvicorn app.main:app --reload
# In another terminal:
python -m app.bot.main
```

## 6. Test the Bot

1. Open your bot in Telegram: `@your_bot_username`
2. Click **Start** or send `/start`
3. You should receive a welcome message with 3 wine recommendations
4. Try sending a message: "порекомендуй красное к стейку"

## Directory Structure (after implementation)

```
backend/
├── app/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── main.py              # Bot entry point
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── start.py         # /start command
│   │   │   ├── help.py          # /help command
│   │   │   ├── profile.py       # /profile command
│   │   │   ├── link.py          # /link command
│   │   │   └── message.py       # Free-text handler
│   │   ├── keyboards.py         # Inline keyboards
│   │   └── formatters.py        # Wine card formatting
│   ├── models/
│   │   └── telegram_user.py     # NEW
│   ├── repositories/
│   │   └── telegram_user.py     # NEW
│   └── services/
│       └── telegram_bot.py      # NEW
└── tests/
    ├── unit/
    │   ├── test_telegram_handlers.py
    │   └── test_telegram_formatters.py
    └── integration/
        └── test_telegram_flow.py
```

## Common Issues

### Bot not responding

1. Check `TELEGRAM_BOT_TOKEN` is correct
2. Ensure bot process is running
3. Check logs for errors

### Database connection errors

1. Ensure PostgreSQL is running
2. Check `DATABASE_URL` in `.env`
3. Verify migration was applied: `alembic current`

### LLM errors

Bot will show fallback message if LLM is unavailable:
```
"К сожалению, сервис рекомендаций временно недоступен..."
```

Check `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` configuration.

## Production Deployment

For production, consider:

1. **Webhook mode** instead of polling:
   ```bash
   TELEGRAM_MODE=webhook
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook
   ```

2. **Systemd service** for bot:
   ```ini
   # /etc/systemd/system/getmywine-bot.service
   [Unit]
   Description=GetMyWine Telegram Bot
   After=network.target postgresql.service

   [Service]
   User=www-data
   WorkingDirectory=/var/www/getmywine/backend
   Environment="PATH=/var/www/getmywine/backend/.venv/bin"
   EnvironmentFile=/var/www/getmywine/.env
   ExecStart=/var/www/getmywine/backend/.venv/bin/python -m app.bot.main
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Nginx** for webhook endpoint (if using webhook mode)

## Next Steps

After basic setup works:

1. Implement `/link` command for account linking
2. Add profile editing via inline keyboards
3. Set up session cleanup job
4. Add monitoring/logging for production
