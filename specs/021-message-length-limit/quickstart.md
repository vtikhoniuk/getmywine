# Quickstart: Message Length Limit Adjustment

**Feature**: 021-message-length-limit
**Date**: 2026-02-13

## Prerequisites

- PostgreSQL 16 running with the existing getmywine database
- Python 3.12+ virtual environment with dependencies installed
- Alembic migrations up to `014` applied

## Setup

```bash
# Apply the new migration
cd backend && alembic upgrade head
```

## Validation Scenarios

### Scenario 1: DB Constraint Removed (US1 — P1)

**Goal**: Verify the CHECK constraint no longer exists and long messages can be stored.

```bash
# Connect to PostgreSQL and verify constraint is gone
psql -d getmywine -c "
  SELECT conname FROM pg_constraint
  WHERE conrelid = 'messages'::regclass
  AND conname = 'ck_messages_content_length';
"
# Expected: 0 rows (constraint removed)

# Insert a message longer than 2000 chars (should succeed)
psql -d getmywine -c "
  INSERT INTO messages (id, conversation_id, role, content)
  VALUES (
    gen_random_uuid(),
    (SELECT id FROM conversations LIMIT 1),
    'assistant',
    repeat('А', 5000)
  );
"
# Expected: INSERT 0 1 (success, no constraint violation)

# Clean up test data
psql -d getmywine -c "
  DELETE FROM messages WHERE content = repeat('А', 5000);
"
```

### Scenario 2: Full LLM Response Stored (US1 — P1)

**Goal**: Send a message that triggers a long response and verify it's stored in full.

1. Open Telegram bot or web UI
2. Send: "Порекомендуй 5 вин к итальянскому ужину с подробным описанием каждого"
3. Wait for the response (likely 3000-5000 chars)
4. Check the database:

```bash
psql -d getmywine -c "
  SELECT char_length(content), left(content, 100)
  FROM messages
  WHERE role = 'assistant'
  ORDER BY created_at DESC
  LIMIT 1;
"
# Expected: char_length > 2000 (if model produced a long response)
# The content should NOT be truncated at 2000
```

### Scenario 3: Web UI Counter Shows 4096 (US2 — P2)

**Goal**: Verify the web UI character counter reflects the new limit.

1. Open the web chat at `https://your-domain/chat`
2. Observe the character counter below the input field: should show `0 / 4096`
3. Type a long message (e.g., paste 3000 characters of text)
4. Counter should show `3000 / 4096` without warning color
5. Type until 3900+ characters — counter should turn red (warning)
6. Try to type past 4096 characters — input should be blocked (`maxlength` attribute)

### Scenario 4: API Rejects Messages Over 4096 Chars (US2 — P2)

**Goal**: Verify server-side validation enforces the 4096 limit.

```bash
# Send a message that exceeds 4096 chars via API
curl -X POST https://your-domain/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(python3 -c 'print("x" * 4097)')\"}" \
  -w "\n%{http_code}"
# Expected: 422 Unprocessable Entity (Pydantic validation error)

# Send a message at exactly 4096 chars (should succeed if authenticated)
curl -X POST https://your-domain/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$(python3 -c 'print("x" * 4096)')\"}" \
  -w "\n%{http_code}"
# Expected: 200 OK (or 401 if not authenticated — validation passes either way)
```

### Scenario 5: Migration Downgrade (Rollback Safety)

**Goal**: Verify the migration can be rolled back.

```bash
cd backend && alembic downgrade -1
# Expected: Downgrades to 014, re-creates the CHECK constraint

# Verify constraint is back
psql -d getmywine -c "
  SELECT conname FROM pg_constraint
  WHERE conrelid = 'messages'::regclass
  AND conname = 'ck_messages_content_length';
"
# Expected: 1 row (constraint restored)

# Re-apply for continued development
cd backend && alembic upgrade head
```

### Scenario 6: Existing Tests Pass

**Goal**: Verify no regressions.

```bash
cd /home/vt/getmywine && python -m pytest backend/tests/ -v
# Expected: All tests pass (including updated boundary tests at 4097 chars)
```

## Automated Test Commands

```bash
# Run all tests
python -m pytest backend/tests/ -v

# Run only message-related tests
python -m pytest backend/tests/unit/test_chat_models.py -v
python -m pytest backend/tests/contract/test_chat_messages.py -v

# Run with Ruff linting
ruff check backend/app/schemas/chat.py backend/app/services/telegram_bot.py backend/app/templates/chat.html
```
