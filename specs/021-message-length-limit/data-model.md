# Data Model: Message Length Limit Adjustment

**Feature**: 021-message-length-limit
**Date**: 2026-02-13

## Entity: Message

**Table**: `messages`
**Model**: `backend/app/models/message.py`

### Current Schema

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| conversation_id | UUID | FK → conversations.id, NOT NULL, INDEX |
| role | Enum(MessageRole) | NOT NULL |
| content | Text | NOT NULL, **CHECK char_length(content) <= 2000** |
| created_at | DateTime(tz) | NOT NULL, default now(), INDEX |
| is_welcome | Boolean | NOT NULL, default false |

### Target Schema (after migration)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| conversation_id | UUID | FK → conversations.id, NOT NULL, INDEX |
| role | Enum(MessageRole) | NOT NULL |
| content | Text | NOT NULL *(CHECK constraint removed)* |
| created_at | DateTime(tz) | NOT NULL, default now(), INDEX |
| is_welcome | Boolean | NOT NULL, default false |

### Change Summary

| Change | Before | After |
|--------|--------|-------|
| CHECK constraint `ck_messages_content_length` | `char_length(content) <= 2000` | **Removed** |
| SQLAlchemy model | No change needed | No change needed |

**Note**: The SQLAlchemy model at `backend/app/models/message.py` already uses `Text` without any length parameter. The constraint was only defined at the database level in migration 004. No Python model changes are needed.

## Validation Layer Changes

### Pydantic Schema: `SendMessageRequest`

**File**: `backend/app/schemas/chat.py`

| Field | Before | After |
|-------|--------|-------|
| `content` | `Field(..., min_length=1, max_length=2000)` | `Field(..., min_length=1, max_length=4096)` |

**Rationale**: Server-side validation for **user input** messages via the web API. Matches the Telegram text message limit (4096) and the web UI counter (4096).

### Application Safety Net: `_truncate_for_storage()`

**File**: `backend/app/services/telegram_bot.py`

| Parameter | Before | After |
|-----------|--------|-------|
| `max_length` default | `2000` | `50000` |

**Rationale**: Safety net for extreme edge cases only. Normal LLM output (~4000-6000 chars) should never be truncated. See research.md R-003.

## Migration

**File**: `backend/migrations/versions/015_drop_message_content_length_constraint.py`
**Revision**: `"015"` | **Down revision**: `"014"`

### Upgrade

```python
op.drop_constraint("ck_messages_content_length", "messages", type_="check")
```

### Downgrade

```python
op.create_check_constraint(
    "ck_messages_content_length",
    "messages",
    "char_length(content) <= 2000",
)
```

**Backward compatibility**: Existing messages all have `char_length(content) <= 2000` (enforced by the old constraint), so downgrade is safe. New messages stored after upgrade may exceed 2000 chars, making downgrade lossy if such messages exist — acceptable tradeoff.
