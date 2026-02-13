# Data Model: Structured Output Retry

**Feature**: 020-structured-output-retry
**Date**: 2026-02-13

## Database Changes

**None.** This feature does not modify the database schema. All retry state is ephemeral (in-memory during a single request).

## In-Memory Data Structures

### ParseResult

Replaces the current `tuple[str, list[str]]` return type of `_parse_final_response`.

```
ParseResult
├── text: str              # Rendered response text (empty on failure)
├── wine_ids: list[str]    # Wine UUIDs from structured response
└── error: str | None      # Validation error description (None = success)
```

**State transitions**:

```
LLM Response
    │
    ▼
┌─────────────────────┐
│ _parse_final_response│
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     │             │
  ok=True      ok=False
     │             │
     ▼             ▼
  Return to    Retry?
  caller       ┌──┴──┐
               │     │
            attempt  attempt
            < max    >= max
               │       │
               ▼       ▼
           Append    Return
           error     empty
           to msgs   (graceful
           & retry    degradation)
```

### Retry Context (ephemeral, within agent loop)

```
retry_attempt: int = 0
retry_errors: list[str] = []
```

These are local variables in `generate_agentic_response()`, not persisted anywhere.

### Langfuse Metadata Extension

The existing `_update_langfuse_metadata` call is extended with:

```
metadata:
├── tools_used: list[str]          # Existing
├── iterations: int                # Existing
├── response_type: str | None      # Existing
├── structured_output_retries: int      # NEW — number of retries performed
└── structured_output_errors: list[str] # NEW — validation error messages
```

## Content Truncation (FR-011)

For valid responses exceeding 2000 characters, truncation is applied **before saving** to the `messages` table:

```
Original response (full, sent to user)
    │
    ▼
Truncation logic:
    1. Find last "\n\n" within 2000 chars → truncate there
    2. Else find last ". " within 2000 chars → truncate there
    3. Else hard-truncate at 2000 chars
    │
    ▼
Truncated text saved to messages.content (≤2000 chars)
```

This preserves the existing `ck_messages_content_length` constraint without DB migration.
