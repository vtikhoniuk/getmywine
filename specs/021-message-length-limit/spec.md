# Feature Specification: Message Length Limit Adjustment

**Feature Branch**: `021-message-length-limit`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "Сейчас ограничение на длину сообщения в БД — 2000. Кажется, что это мало для ответа модели. Нужно понять реальные ограничения, например, какой максимальный размер подписи под изображением и поменять размер в БД. Заодно проверить установленные ограничения в коде."

## Context

The system stores conversation messages (both user and assistant) in a `messages` table with a CHECK constraint limiting `content` to 2000 characters. The LLM is configured with `max_tokens=2000`, but tokens do not map 1:1 to characters — especially for Russian text, where one token may encode 1–3 characters. This means the model can produce responses of 4000–6000+ characters that are silently truncated before storage, causing loss of conversation context for follow-up messages.

### Current Constraint Landscape (from codebase audit)

| Constraint | Current Value | Source | Type |
|---|---|---|---|
| Message content in DB | 2000 chars | `messages` table CHECK constraint | Hard limit |
| Truncation for storage | 2000 chars | `_truncate_for_storage()` default param | Code default |
| Web UI character counter | 2000 chars | `chat.html` JS counter | UI display |
| Telegram photo caption | 1024 chars | Telegram Bot API limit | Platform limit |
| Telegram text message | 4096 chars | Telegram Bot API limit | Platform limit |
| LLM max_tokens | 2000 tokens | `config.py` setting | LLM config |
| Conversation title | 30 chars | `String(30)` in ORM model | Schema limit |

### Problem

1. **Data loss**: Assistant responses are truncated to 2000 chars before saving to history, losing valuable context for multi-turn conversations
2. **Misleading history**: When the truncated version is included in LLM context for the next turn, the model operates on incomplete information
3. **Mismatched limits**: The DB limit (2000 chars) is lower than the LLM output capacity (~6000+ chars) and lower than the Telegram message limit (4096 chars per message)

## Clarifications

### Session 2026-02-13

- Q: What should the new DB limit be? → A: Remove the CHECK constraint entirely — PostgreSQL `Text` type has no practical length limit, so the constraint is unnecessary overhead. Future `max_tokens` changes won't require another migration.
- Q: What should the web UI character counter show? → A: 4096 characters — matching the Telegram message limit for cross-channel parity.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Full Assistant Responses Stored in History (Priority: P1)

As a user having a multi-turn conversation with the sommelier, I want my assistant's full responses to be preserved in conversation history so that follow-up questions have complete context.

**Why this priority**: This is the core problem — truncated history degrades conversation quality. Without this fix, the model loses context on every long response, leading to repetitive or inconsistent follow-up answers.

**Independent Test**: Send a message that triggers a long sommelier response (e.g., "Порекомендуй 5 вин к итальянскому ужину с описанием каждого"). Verify the full response is stored in the database and included in context for the next message.

**Acceptance Scenarios**:

1. **Given** the model generates a response of 5000 characters, **When** the response is saved to conversation history, **Then** the full 5000-character response is stored without truncation
2. **Given** a conversation where the previous assistant message was 4500 characters, **When** the user sends a follow-up question, **Then** the LLM context includes the complete previous response
3. **Given** the model generates a response up to the maximum token limit, **When** the response is stored, **Then** no data loss occurs and no database errors are raised

---

### User Story 2 — Hardcoded Limits Removed or Aligned (Priority: P2)

As a developer maintaining the system, I want all artificial length-related constraints in the codebase to be removed or aligned with actual platform limits so that there are no silent failures or stale assumptions.

**Why this priority**: Inconsistent limits across code and DB cause subtle bugs — e.g., the web UI counter showing 2000 while the DB allows unlimited, or truncation logic using a stale default. This must be addressed alongside the DB migration.

**Independent Test**: Search all hardcoded "2000" references related to message length in the codebase. Verify each one is either removed, updated, or documented as intentionally different.

**Acceptance Scenarios**:

1. **Given** the CHECK constraint is removed, **When** a developer inspects `_truncate_for_storage()`, **Then** it no longer truncates responses that fit within normal LLM output range
2. **Given** the CHECK constraint is removed, **When** a user opens the web chat interface, **Then** the character counter shows a 4096-character limit
3. **Given** the codebase is audited, **When** all message-length-related constants are reviewed, **Then** each one is either removed, updated, or has a documented reason for its value (e.g., Telegram caption = 1024 is a platform constraint)

---

### Edge Cases

- What happens when the LLM produces a very long response? — It is stored as-is; no DB constraint to violate
- What happens when a user message in the web UI exceeds 4096 characters? — The UI should show a warning and prevent submission
- What happens to existing messages in the database that were truncated under the old 2000-char limit? — No backfill; existing data remains as-is. Only new messages benefit
- What happens if `_truncate_for_storage()` is still called? — It should remain as a safety net but with a generous limit that does not truncate normal LLM responses

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove the CHECK constraint on `messages.content` — PostgreSQL `Text` type has no practical length limit, making the constraint unnecessary
- **FR-002**: System MUST create a database migration that drops the `ck_messages_content_length` CHECK constraint
- **FR-003**: System MUST remove or increase the `_truncate_for_storage()` default `max_length` parameter so that normal LLM responses (up to `max_tokens` output) are never truncated
- **FR-004**: System MUST update the web UI character counter in `chat.html` to show a 4096-character limit, matching the Telegram message limit for cross-channel parity
- **FR-005**: System MUST NOT change the Telegram photo caption limit (1024 chars) — this is a platform-imposed constraint
- **FR-006**: System MUST NOT change the Telegram text message limit (4096 chars) — this is a platform-imposed constraint
- **FR-007**: System MUST preserve existing truncation logic as a safety net for extreme edge cases (e.g., malformed LLM output producing megabytes of text)
- **FR-008**: The migration MUST be backward-compatible — existing messages remain valid
- **FR-009**: The change MUST apply equally to both user and assistant messages

### Key Entities

- **Message**: The `messages` table stores conversation messages. Key attribute: `content` (Text column, currently constrained by a CHECK on `char_length`). The CHECK constraint is to be removed.

## Assumptions

- Removing the CHECK constraint is safe because PostgreSQL `Text` type has no practical length limit and the application already bounds output via `max_tokens`.
- User messages from Telegram are already bounded by the 4096-char Telegram API limit. Web UI input is bounded by a 4096-char client-side counter, matching the Telegram limit for cross-channel parity.
- `_truncate_for_storage()` should remain as a safety net but with a limit high enough (e.g., 10000+ chars) to never truncate normal LLM output. The exact value is an implementation detail.
- No existing data migration or backfill is needed — truncated historical messages are acceptable as-is.
- Future increases to `max_tokens` will not require a DB migration since there is no longer a DB-level constraint.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of LLM responses within the configured `max_tokens` limit are stored in full without truncation
- **SC-002**: Zero database constraint violation errors when storing messages of any length
- **SC-003**: All hardcoded message-length references in the codebase are removed, updated, or explicitly documented as platform-specific exceptions
- **SC-004**: Existing messages in the database remain accessible and valid after the migration
