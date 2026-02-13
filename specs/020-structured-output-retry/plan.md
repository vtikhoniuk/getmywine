# Implementation Plan: Structured Output Retry with Error Feedback

**Branch**: `020-structured-output-retry` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-structured-output-retry/spec.md`

## Summary

Add retry-with-error-feedback logic to the sommelier agent loop when the LLM returns an invalid structured output response. On parse failure, the system appends the validation error to the conversation context and re-calls the LLM (up to 2 retries). This follows the Instructor/LangChain pattern of feeding Pydantic validation errors back to the model for self-correction.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, OpenAI SDK (via OpenRouter), Langfuse SDK, Pydantic v2
**Storage**: PostgreSQL 16 + pgvector (existing, no schema changes)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker)
**Project Type**: web (backend-only changes)
**Performance Goals**: Zero overhead on successful first attempt; ≤5s additional delay per retry
**Constraints**: Max 2 retries (3 total attempts); retry counter independent of tool-use iterations
**Scale/Scope**: Single service change (sommelier.py) + config + tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Clean Architecture (Routers → Services → Repositories → Models) | PASS | Changes stay in Services layer (sommelier.py). No router/repository changes. |
| Database First | PASS | No schema changes required. |
| TDD | PASS | Tests will be written before implementation (see research.md R-003). |
| RAG-First | PASS | Retry does not affect RAG pipeline; tool results are preserved across retries. |
| 18+ / No Sales | PASS | No impact on product principles. |
| Coding Standards (Ruff, Commitizen, coverage) | PASS | All new code linted; critical paths tested. |

No violations. No Complexity Tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/020-structured-output-retry/
├── spec.md              # Feature specification (done)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — no DB changes)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                        # Add structured_output_max_retries setting
│   └── services/
│       ├── sommelier.py                 # Retry logic in generate_agentic_response()
│       │                                  Refactor _parse_final_response() to return error details
│       ├── sommelier_prompts.py         # Add semantic validation (empty content check)
│       └── telegram_bot.py              # Add content truncation for long valid responses (FR-011)
└── tests/
    └── unit/
        └── test_agent_loop.py           # Add retry-specific test cases
```

**Structure Decision**: Backend-only changes within existing service layer. No new modules or packages needed.
