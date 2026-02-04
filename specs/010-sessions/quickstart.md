# Quickstart: Sessions History

**Feature**: 010-sessions
**Date**: 2026-02-03

## Prerequisites

- Python 3.12+
- PostgreSQL 16 running
- Backend service from previous features
- Claude API key (for session naming)

## Quick Setup

### 1. Apply Migration

```bash
cd backend
uv run alembic upgrade head
```

### 2. Verify Migration

```bash
uv run alembic current
# Should show: 010_sessions (head)

# Check schema
docker exec -it aiwine-db psql -U postgres -d aiwine -c "\d conversations"
# Should show: title, closed_at columns
```

### 3. Run Tests

```bash
# Unit tests
uv run pytest tests/unit/test_session_naming.py -v
uv run pytest tests/unit/test_session_lifecycle.py -v

# Integration tests
uv run pytest tests/integration/test_sessions_api.py -v

# All session tests
uv run pytest -k sessions -v
```

### 4. Start Development Server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## Manual Testing

### Create New Session

```bash
# Login first
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' \
  -c cookies.txt

# Create session
curl -X POST http://localhost:8000/chat/sessions \
  -b cookies.txt \
  -H "Accept: application/json"
```

### List Sessions

```bash
curl http://localhost:8000/chat/sessions \
  -b cookies.txt \
  -H "Accept: application/json"
```

### Get Session History

```bash
curl http://localhost:8000/chat/sessions/{session_id} \
  -b cookies.txt \
  -H "Accept: application/json"
```

### Delete Session

```bash
curl -X DELETE http://localhost:8000/chat/sessions/{session_id} \
  -b cookies.txt
```

## Browser Testing

1. Open http://localhost:8000/chat
2. Check sidebar appears with session list
3. Click "Новый диалог" button
4. Send a message, verify session title updates
5. Click on old session, verify read-only mode
6. Delete a session, verify it disappears

## Key Files to Check

| File | Purpose |
|------|---------|
| `app/models/conversation.py` | Model changes |
| `app/repositories/conversation.py` | Multi-session queries |
| `app/services/chat.py` | Session lifecycle |
| `app/services/session_naming.py` | LLM naming |
| `app/routers/chat.py` | API endpoints |
| `app/templates/chat/_sidebar.html` | Session list UI |

## Environment Variables

```bash
# .env additions (if any)
SESSION_INACTIVITY_MINUTES=30
SESSION_RETENTION_DAYS=90
```

## Common Issues

### "conversations_user_id_key" constraint error

Migration not applied. Run:
```bash
uv run alembic upgrade head
```

### Session naming fails

Check Claude API key in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Fallback to date-based naming should work even without API key.

### Sidebar not loading

Check HTMX is loaded in base template:
```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
```

## Performance Check

```bash
# Session list query should be < 200ms
curl -w "\nTime: %{time_total}s\n" \
  http://localhost:8000/chat/sessions \
  -b cookies.txt \
  -H "Accept: application/json"
```

## Next Steps

After implementation:
1. Run `/speckit.tasks` to generate tasks.md
2. Create feature branch `010-sessions`
3. Implement tasks in order
4. PR review and merge
