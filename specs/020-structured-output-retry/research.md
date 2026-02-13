# Research: Structured Output Retry with Error Feedback

**Feature**: 020-structured-output-retry
**Date**: 2026-02-13

## R-001: Retry Strategy — Where in the Call Stack

**Decision**: Retry at the agent loop level (`generate_agentic_response`), wrapping `_parse_final_response` calls.

**Rationale**: The retry needs access to the `messages` list to append error feedback before re-calling the LLM. Only `generate_agentic_response` has both the messages context and the LLM service reference. Retrying inside `_parse_final_response` is impossible because it's a static method with no LLM access.

**Alternatives considered**:
- *Retry in `_parse_final_response`*: Rejected — static method, no LLM access, would require major refactor.
- *Retry in `generate_with_tools` (LLM layer)*: Rejected — LLM layer shouldn't know about application-level validation; violates Clean Architecture.
- *Retry in `telegram_bot.py` (caller)*: Rejected — would retry the entire flow including tool calls, wasting latency and tokens.

## R-002: Error Feedback Message Format

**Decision**: Append the invalid response as an `assistant` message, followed by a `user` message containing the validation error and instruction to fix it.

**Rationale**: This mirrors the Instructor library pattern. The LLM sees its own broken output and receives a concrete error message explaining what went wrong. This maximizes the chance of self-correction because the model can see exactly what it produced and what was invalid.

**Format**:
```
assistant: {raw invalid response}
user: "Your previous response failed validation: {error_description}. Please respond again with valid JSON matching the required schema. Do not include any text outside the JSON object."
```

**Alternatives considered**:
- *System message with error*: Rejected — system messages may be deprioritized by some models; user messages have stronger steering effect.
- *Only error, no raw response*: Rejected — without seeing its own output, the model may repeat the same mistake.
- *Retry without feedback (same request)*: Rejected — without error context, the model has no signal to change behavior; lower success rate.

## R-003: Test Strategy

**Decision**: Add test cases to existing `test_agent_loop.py` using the same mock patterns already established.

**Rationale**: The existing test file has 8 test classes covering agent loop mechanics with well-structured mocks for `generate_with_tools`. Adding retry tests follows the same pattern: mock the LLM to return invalid output on first call, valid on second.

**Test cases needed**:
1. First attempt fails parsing → retry succeeds → user gets valid response
2. All retry attempts fail → returns empty (graceful degradation)
3. Successful first attempt → no retry, no overhead
4. Refusal (`finish_reason=refusal`) → no retry
5. Truncation (`finish_reason=length`) → retry with truncation feedback
6. Semantically empty response → retry
7. Langfuse metadata includes retry count and error types

## R-004: _parse_final_response Return Type Refactor

**Decision**: Change `_parse_final_response` to return a dataclass/NamedTuple with `(text, wine_ids, error)` instead of a plain tuple `(str, list[str])`.

**Rationale**: The retry logic needs to know WHY parsing failed (to include in error feedback). Currently `_parse_final_response` returns `("", [])` on failure with no error details. A structured return type avoids breaking the existing tuple unpacking pattern while adding error information.

**Design**:
```python
@dataclass
class ParseResult:
    text: str
    wine_ids: list[str]
    error: str | None = None  # None = success, str = validation error description

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text.strip())
```

**Alternatives considered**:
- *Raise exception on failure*: Rejected — would require try/except in every call site; less clean than checking `.ok`.
- *Return tuple with 3 elements*: Rejected — less readable than named fields; easy to confuse positional args.
- *Keep returning `("", [])` and detect failure by empty string*: Rejected — loses error details needed for feedback message.

## R-005: Semantic Validation for Empty Responses

**Decision**: Add a `validate_semantic_content` function in `sommelier_prompts.py` that checks if a structurally valid `SommelierResponse` has meaningful content.

**Rationale**: FR-010 requires treating empty-but-valid responses as failures. This check belongs in `sommelier_prompts.py` alongside the Pydantic model since it's a domain-level validation rule.

**Rules**:
- If `response_type == "recommendation"` and `wines` list is empty → semantically invalid
- If `intro` is empty and `closing` is empty and no wine descriptions → semantically invalid
- If `response_type == "off_topic"` with empty intro → semantically invalid
- Allow `response_type == "informational"` with empty wines (valid: general wine knowledge answer)

**Alternatives considered**:
- *Pydantic model_validator*: Rejected — would make the Pydantic model reject what the JSON schema allows, causing confusing errors.
- *Check in `_parse_final_response`*: Possible but less reusable; better as a standalone function for testability.

## R-006: Content Truncation for History (FR-011)

**Decision**: Truncate at the last complete sentence/paragraph boundary within the 2000-char limit before saving to DB.

**Rationale**: Cutting mid-word would confuse the LLM in future context. Truncating at a paragraph break preserves readability. The full response is already sent to the user — truncation only affects stored history.

**Implementation**: In `telegram_bot.py`, before `message_repo.create()`, if `len(response_text) > max_content_length`, find the last `\n\n` within limit, or last `. ` within limit, and truncate there.

**Alternatives considered**:
- *Skip saving entirely (current fix)*: Works but loses context for future turns.
- *Truncate at exact char limit*: Simple but may break mid-word/mid-sentence.
- *Summarize with LLM*: Over-engineered for a storage-level concern.

## R-007: Configuration

**Decision**: Add a single setting `structured_output_max_retries: int = 2` in `config.py`.

**Rationale**: Only the retry count needs to be configurable. Temperature escalation (slightly increasing temp on retry) was considered but rejected — it adds complexity without proven benefit for structured output errors. The error feedback message is more effective than random sampling changes.

**Alternatives considered**:
- *Temperature increase per retry*: Rejected — structured output failures are usually due to model confusion, not low randomness. Error feedback is the better fix signal.
- *Configurable feedback message template*: Rejected — over-engineering; the message is implementation detail.
- *Per-error-type retry policy*: Rejected — all structured output errors benefit equally from retry with feedback.
