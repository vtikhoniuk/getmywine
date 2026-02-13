# Research: Message Length Limit Adjustment

**Feature**: 021-message-length-limit
**Date**: 2026-02-13

## R-001: PostgreSQL CHECK Constraint Removal

**Decision**: Drop the `ck_messages_content_length` CHECK constraint via Alembic migration. Do not replace it with a higher limit.

**Rationale**: PostgreSQL `Text` type has no practical length limit (~1 GB). The CHECK constraint was an artificial cap introduced early in development. Removing it entirely means future changes to `max_tokens` or response format won't require DB migrations. The application layer already controls input (Pydantic validation for web, Telegram API limits for bot) and output (`max_tokens` for LLM, `_truncate_for_storage()` as safety net).

**Alternatives considered**:
- Increase to 8000 chars: Still arbitrary, would need another migration if `max_tokens` increases
- Increase to 16000 chars: Same problem
- Remove and add Application-level check: Unnecessary overhead since input is already validated

## R-002: Alembic Migration Strategy

**Decision**: Create migration `015_drop_message_content_length_constraint.py` with `op.drop_constraint("ck_messages_content_length", "messages", type_="check")` in upgrade and re-create the constraint in downgrade.

**Rationale**: Alembic's `drop_constraint` is the standard approach. The constraint name `ck_messages_content_length` is explicitly set in migration 004, making it reliable to reference. Downgrade restores the constraint for rollback safety.

**Alternatives considered**:
- Raw SQL `ALTER TABLE messages DROP CONSTRAINT`: Works but loses Alembic's dialect abstraction
- Modifying migration 004 directly: Violates Alembic's sequential migration principle

## R-003: `_truncate_for_storage()` New Default Limit

**Decision**: Increase `max_length` default from `2000` to `50000`.

**Rationale**: The function exists as a safety net against extreme edge cases (malformed LLM output, infinite loops producing megabytes of text). Normal LLM output at `max_tokens=2000` produces ~4000-6000 characters for Russian text. Even with future `max_tokens` increases (e.g., 8000 tokens → ~24000 chars), 50000 provides generous headroom. The exact value is a pragmatic choice — large enough to never truncate normal output, small enough to prevent DB bloat from pathological cases.

**Alternatives considered**:
- Remove `_truncate_for_storage()` entirely: Loses the safety net; spec FR-007 requires preserving it
- Set to 10000: Too close to realistic max output if `max_tokens` increases
- Set to 100000: Unnecessary; 50000 is already 8-10x normal output

## R-004: Web UI Character Counter — 4096 chars

**Decision**: Update the HTML `maxlength` attribute, JavaScript counter display, and warning threshold to 4096.

**Rationale**: User chose 4096 to match the Telegram text message limit, providing cross-channel parity. Users can type the same length message in both the web UI and Telegram. Warning threshold set to 3900 (4096 - ~5%) to maintain the proportional warning zone.

**Alternatives considered**:
- Remove counter entirely: User initially chose this but reversed to 4096 for Telegram parity
- Keep at 2000: No longer matches any real constraint (DB CHECK is removed)

## R-005: Pydantic Schema Update

**Decision**: Update `SendMessageRequest.content` in `backend/app/schemas/chat.py` from `max_length=2000` to `max_length=4096`.

**Rationale**: The Pydantic schema validates **user input** messages sent via the web API. This must match the web UI counter (4096) and the Telegram message limit (4096) for consistency. This was not in the original spec's constraint landscape but was discovered during codebase research.

**Note**: This is a server-side validation that complements the client-side `maxlength` attribute. Both must be aligned.

## R-006: Test Updates

**Decision**: Update existing tests that assert 2000-char message length limits to reflect the new 4096 limit.

**Rationale**: Two test files contain hardcoded `2000` references for message length validation:
- `backend/tests/unit/test_chat_models.py` (line 120): Tests `SendMessageRequest` rejection at 2001 chars
- `backend/tests/contract/test_chat_messages.py` (lines 79, 93): Tests API rejection at 2001 chars

These must be updated to test at 4097 chars (new boundary). The `golden_queries.py` reference to `2000` is about `price_max`, not message length — no change needed.

## R-007: Files NOT Changed

**Decision**: The following files contain `2000` but should NOT be changed:

| File | Value | Reason |
|------|-------|--------|
| `backend/app/config.py` | `llm_max_tokens: int = 2000` | Controls LLM generation cost, not storage. Per spec: no change. |
| `backend/app/services/llm.py` (line 513) | `max_tokens=2000` | Same — LLM generation parameter |
| `backend/app/bot/sender.py` (line 110) | `[:1024]` | Telegram photo caption limit — platform constraint (FR-005) |
| `backend/tests/eval/golden_queries.py` | `price_max: 2000` | Wine price filter, not message length |

## R-008: Migration Ordering

**Decision**: Migration number `015`, down_revision `"014"`.

**Rationale**: Current head migration is `014_fix_sparkling_wines_and_sweetness.py`. The new migration follows sequentially. Naming convention: `015_drop_message_content_length_constraint.py`.
