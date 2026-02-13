# Feature Specification: Structured Output Retry with Error Feedback

**Feature Branch**: `020-structured-output-retry`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "Retry with error feedback in agent loop when model returns invalid structured output"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Recovery from Invalid LLM Response (Priority: P1)

When a user asks the sommelier for a wine recommendation and the language model returns a malformed or unparseable response, the system automatically retries the request by sending the validation error back to the model. The user receives a valid recommendation without noticing the initial failure.

**Why this priority**: This is the core value of the feature. Today, an invalid structured output causes the user to see a generic error message ("service unavailable"), even though the model likely can produce a correct response on a second attempt. Automatic retry directly improves user experience and reduces visible failures.

**Independent Test**: Can be tested by simulating a malformed LLM response on the first attempt and verifying the system retries and returns a valid recommendation to the user.

**Acceptance Scenarios**:

1. **Given** a user sends a wine recommendation request, **When** the model returns an unparseable JSON response, **Then** the system retries the request with error feedback included in the conversation context, and the user receives a valid recommendation.
2. **Given** a user sends a request, **When** the model returns a JSON response that does not match the expected schema (e.g., missing required fields), **Then** the system retries with the validation error message, and the user receives a valid recommendation.
3. **Given** a user sends a request, **When** the model returns a truncated response (cut off mid-JSON), **Then** the system retries with feedback about the truncation, and the user receives a complete response.

---

### User Story 2 - Graceful Degradation After Retry Exhaustion (Priority: P2)

When the system has exhausted all retry attempts and still cannot get a valid response, the user receives a clear, friendly error message. The conversation history is not polluted with invalid data, allowing the next user message to succeed normally.

**Why this priority**: Even with retries, failures can still occur (e.g., model outage, persistent schema violations). The system must degrade gracefully and not leave the conversation in a broken state.

**Independent Test**: Can be tested by simulating persistent invalid responses across all retry attempts and verifying the user receives an error message and the conversation remains functional.

**Acceptance Scenarios**:

1. **Given** a user sends a request, **When** the model returns invalid responses on all retry attempts, **Then** the user receives a user-friendly error message indicating temporary unavailability.
2. **Given** the system has exhausted retries for a request, **When** the user sends a new message afterward, **Then** the new request is processed normally without being affected by the previous failure.
3. **Given** all retry attempts fail, **Then** no invalid content is saved to the conversation history.

---

### User Story 3 - Operational Visibility of Retry Events (Priority: P3)

System operators can monitor retry events to understand how often models fail to produce valid structured output, which models fail most frequently, and what types of validation errors occur. This enables data-driven decisions about model selection and prompt improvements.

**Why this priority**: Retries happen silently from the user's perspective. Without observability, the team cannot detect degradation trends, measure the retry success rate, or optimize prompts to reduce failures.

**Independent Test**: Can be tested by triggering retry scenarios and verifying that each retry attempt, its reason, and its outcome are recorded in the observability system.

**Acceptance Scenarios**:

1. **Given** a retry occurs, **When** the retry succeeds, **Then** the system logs the attempt number, the validation error that triggered the retry, and the successful outcome.
2. **Given** a retry occurs, **When** all retries are exhausted, **Then** the system logs each attempt, the validation errors, and the final failure outcome.

---

### Edge Cases

- When the model returns an empty response (no content at all), the system treats it as a validation failure and retries.
- When the model returns valid JSON with empty/meaningless content (empty intro, no wines, empty closing), the system treats it as a validation failure and retries.
- When a retry itself is interrupted by a network timeout or provider error, existing error handling applies (out of scope for this feature — see Assumptions).
- When the model returns a refusal (`finish_reason: "refusal"`), it is treated as a final response and NOT retried (see FR-004).
- When the response exceeds the maximum content length allowed for storage but is otherwise valid, the system shows the full response to the user and truncates it before saving to conversation history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically retry the request when the model's response fails structured output validation (unparseable JSON, schema mismatch, or truncated response).
- **FR-002**: System MUST include the validation error description in the retry request context so the model can correct its output.
- **FR-003**: System MUST limit retries to a configurable maximum number of attempts (default: 2 retry attempts after the initial request, for a total of 3 attempts).
- **FR-004**: System MUST NOT retry on model refusals (`finish_reason: "refusal"`), as these are intentional and unlikely to change on retry.
- **FR-005**: System MUST NOT save any invalid or intermediate responses to the conversation history.
- **FR-006**: System MUST return a user-friendly error message when all retry attempts are exhausted.
- **FR-007**: System MUST log each retry attempt with the validation error reason and attempt number.
- **FR-008**: System MUST not significantly increase the overall response time for successful first attempts (zero overhead when no retry is needed).
- **FR-009**: System MUST count the retry attempts independently from the existing tool-use iteration loop (retries are for output format correction, not for tool execution).
- **FR-010**: System MUST treat a structurally valid response with empty/meaningless content (e.g., empty intro, no wines, empty closing) as a validation failure and trigger a retry.
- **FR-011**: System MUST accept a valid structured output response that exceeds the storage length limit, show the full response to the user, and truncate it before saving to conversation history.

### Key Entities

- **Retry Attempt**: Represents a single retry of a failed structured output response. Attributes: attempt number, validation error message, outcome (success/failure), model response.
- **Validation Error**: The reason why a structured output response was rejected. Types: unparseable JSON, schema validation failure, truncated response, empty response, semantically empty response (valid structure but no meaningful content).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 80% of responses that fail on the first attempt succeed on retry, reducing user-visible errors.
- **SC-002**: Users experience no more than 5 seconds of additional delay per retry attempt beyond the normal response time.
- **SC-003**: Zero invalid or garbage content is saved to the conversation history (no data integrity violations).
- **SC-004**: 100% of retry events are logged with sufficient detail for post-incident analysis (attempt number, error type, outcome).
- **SC-005**: The retry mechanism adds zero overhead to requests where the first attempt succeeds.

## Clarifications

### Session 2026-02-13

- Q: Should a structurally valid JSON response with empty/meaningless content (empty intro, no wines, empty closing) be treated as a validation failure? → A: Yes — treat as validation failure and retry. A response with no wines and empty text is functionally useless.
- Q: When a valid structured output response exceeds the maximum storage length, what should the system do? → A: Accept and show to user in full, but truncate before saving to conversation history.

## Assumptions

- The current language model supports receiving error feedback as part of the conversation context (system/assistant/user messages) and can correct its output based on that feedback.
- Structured output validation failures are intermittent rather than systematic. If a model consistently fails, the issue is in the prompt or schema, not solvable by retries.
- The default of 2 retry attempts (3 total) balances recovery probability against response latency and cost. Industry practice (Instructor, LangChain) uses 1-3 retries.
- Network/provider errors (timeouts, 5xx) are handled separately from structured output validation failures and are out of scope for this feature.
- The existing observability system (Langfuse) is available for logging retry metadata.

## Dependencies

- Existing structured output parsing logic (`_parse_final_response`, `_extract_json_str` in `sommelier.py`)
- Existing agent loop with tool-use iterations (`generate_response` in `sommelier.py`)
- Existing observability integration (Langfuse tracing)
- Configurable settings infrastructure (`config.py` with `pydantic-settings`)
