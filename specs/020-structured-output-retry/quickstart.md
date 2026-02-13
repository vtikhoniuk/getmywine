# Quickstart: Structured Output Retry

**Feature**: 020-structured-output-retry
**Date**: 2026-02-13

## Prerequisites

- Running GetMyWine backend (Docker or local)
- Telegram bot configured and running
- OpenRouter API key set in `.env`

## Configuration

New setting in `.env` (optional, has default):

```env
# Structured output retry (default: 2 retries after initial attempt = 3 total)
STRUCTURED_OUTPUT_MAX_RETRIES=2
```

## How to Verify

### Scenario 1: Automatic Retry (Normal Operation)

Retry is invisible to the user. To verify it works, check logs after a period of normal usage:

```bash
docker compose logs backend | grep "Structured output retry"
```

**Expected**: Log entries showing retry attempts when they occur, e.g.:
```
INFO: Structured output retry 1/2: Pydantic validation failed — response_type must be one of {'recommendation', 'informational', 'off_topic'}
INFO: Structured output retry 1/2 succeeded
```

### Scenario 2: Graceful Degradation

If the model consistently returns invalid output (e.g., provider issues), after 3 total attempts the user sees the standard error message:

```
Телеграм-бот: "Извините, сервис рекомендаций временно недоступен. Попробуйте позже."
```

**Expected**: No garbage text, no DB constraint errors, conversation continues normally on next message.

### Scenario 3: Langfuse Observability

1. Open Langfuse dashboard
2. Find a trace for `generate_agentic_response`
3. Check metadata

**Expected** (when retry occurred):
```json
{
  "tools_used": ["search_wines"],
  "iterations": 1,
  "response_type": "recommendation",
  "structured_output_retries": 1,
  "structured_output_errors": ["Pydantic validation failed: response_type must be one of ..."]
}
```

**Expected** (normal, no retry):
```json
{
  "structured_output_retries": 0,
  "structured_output_errors": []
}
```

### Scenario 4: Content Truncation (Long Valid Response)

Send a request that generates a long response (e.g., ask for many wines):

```
Пользователь: посоветуй 5 красных вин из разных регионов, с подробным описанием каждого
```

**Expected**: User sees full response in Telegram. In DB, the saved message is truncated to ≤2000 chars at a paragraph boundary. Next message works normally with conversation context.

## Running Tests

```bash
cd backend
python -m pytest tests/unit/test_agent_loop.py -v -k "retry"
```

**Expected**: All retry-related tests pass:
- `test_retry_on_parse_failure_succeeds`
- `test_retry_exhaustion_returns_empty`
- `test_no_retry_on_success`
- `test_no_retry_on_refusal`
- `test_retry_on_truncated_response`
- `test_retry_on_semantically_empty_response`
- `test_retry_metadata_in_langfuse`
