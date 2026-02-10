# Tasks: Agentic RAG для рекомендаций вин

**Input**: Design documents from `/specs/015-agentic-rag/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — конституция проекта требует TDD (Red → Green → Refactor).

**Organization**: Tasks grouped by user story. US1 — структурированный поиск (P1 MVP), US2 — семантический поиск (P2), US3 — контекстные запросы (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Конфигурация и определения инструментов

- [x] T001 [P] Add agent config settings to `backend/app/config.py` — add `agent_max_iterations: int = 2` and `embedding_model: str = "text-embedding-3-small"` to Settings class. See research.md R-004, R-006
- [x] T002 [P] Define tool JSON schemas as constants in `backend/app/services/sommelier_prompts.py` — add `TOOL_SEARCH_WINES` and `TOOL_SEMANTIC_SEARCH` dicts per data-model.md Tool Definitions section. Add `WINE_TOOLS = [TOOL_SEARCH_WINES, TOOL_SEMANTIC_SEARCH]` list

**Checkpoint**: Конфигурация и tool schemas определены как константы

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: LLM tool use support и новые фильтры в Repository — блокируют все user stories

**⚠️ CRITICAL**: Agent loop и tool execution зависят от этих компонентов

### Tests for Foundational

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] Write tests for `generate_with_tools()` in `backend/tests/unit/test_llm_tool_use.py` — test that method accepts `tools` parameter and returns full message object (content + tool_calls), test handling when response has tool_calls, test handling when response has only content (no tool_calls), test that existing `generate()` method is not affected. Mock OpenAI API responses. See research.md R-002
- [x] T004 [P] Write tests for new repository filters in `backend/tests/unit/test_wine_tools.py` — test `grape_variety` filter (exact ARRAY contains), test `food_pairing` filter (ARRAY overlap), test `region` filter (ilike), test combination of new + existing filters, test no results with impossible filter combo. See research.md R-003, data-model.md

### Implementation for Foundational

- [x] T005 Add `generate_with_tools()` method to `backend/app/services/llm.py` — add abstract method to `BaseLLMService`, implement in `OpenRouterService` (primary provider). Add pass-through in `LLMService` wrapper. `AnthropicService` and `OpenAIService`: raise `NotImplementedError` (not used in production, OpenRouter is the unified gateway). Method signature: `async def generate_with_tools(self, system_prompt, user_prompt, tools, messages=None, temperature=None, max_tokens=None) -> ChatCompletionMessage`. Return full message object (not just content). See research.md R-001, R-002
- [x] T006 Add `grape_variety`, `food_pairing`, `region` filters to `WineRepository.get_list()` in `backend/app/repositories/wine.py` — grape_variety: `Wine.grape_varieties.contains([value])`, food_pairing: `Wine.food_pairings.overlap([value])`, region: `Wine.region.ilike(f'%{value}%')`. All Optional[str]. See research.md R-003, data-model.md
- [x] T007 Add `get_query_embedding()` method to `backend/app/services/llm.py` — `async def get_query_embedding(self, query: str) -> list[float]`. Uses OpenAI embeddings API with model from config (`embedding_model`). See research.md R-006
- [x] T008 Run foundational tests: `pytest backend/tests/unit/test_llm_tool_use.py backend/tests/unit/test_wine_tools.py -v`

**Checkpoint**: LLM service поддерживает tool use, Repository поддерживает grape/food/region фильтры, эмбеддинг запросов работает

---

## Phase 3: User Story 1 — Точный поиск по структурированным критериям (Priority: P1) 🎯 MVP

**Goal**: LLM вызывает search_wines для структурированного поиска. Agent loop обрабатывает tool calls. Единый промпт заменяет 4-path маршрутизацию.

**Independent Test**: Отправить боту "посоветуй красное вино из Мальбека до 2000 рублей" → получить только красные вина с Мальбеком в ценовом диапазоне.

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Write tests for `search_wines` tool execution in `backend/tests/unit/test_wine_tools.py` — test execute_search_wines() calls WineRepository.get_list() with correct mapped parameters, test parameter validation (invalid enum → ignored, price_min > price_max → price_min ignored), test format_tool_response() returns correct JSON structure, test empty results return `{"found": 0, "wines": []}`, test that tool call is logged (name, parameters, result count) per FR-011. See data-model.md Tool Response Format
- [x] T010 [P] [US1] Write tests for agent loop in `backend/tests/unit/test_agent_loop.py` — test single iteration (LLM → tool_calls → execute → LLM → content), test max_iterations=2 limit, test no tool_calls (LLM responds directly), test fallback on error, test tool results are appended to messages correctly, test iteration counter increments. Mock LLM generate_with_tools(). See data-model.md State Transitions
- [x] T011 [P] [US1] Write tests for unified prompt in `backend/tests/unit/test_sommelier_unified.py` — test SYSTEM_PROMPT_AGENTIC contains tool usage instructions, test build_unified_user_prompt() includes user profile when present, test build_unified_user_prompt() includes events context, test build_unified_user_prompt() works without profile (cold start)

### Implementation for User Story 1

- [x] T012 [US1] Create unified system prompt `SYSTEM_PROMPT_AGENTIC` in `backend/app/services/sommelier_prompts.py` — extends SYSTEM_PROMPT_BASE with tool usage instructions, workflow, fallback behavior. Add `build_unified_user_prompt(user_message, user_profile=None, events_context=None)` function. See research.md R-005
- [x] T013 [US1] Implement `execute_search_wines()` in `backend/app/services/sommelier.py` — parse tool call arguments, validate enum values (wine_type, sweetness), map to WineRepository.get_list() parameters, call repository, format response as JSON with `format_tool_response()`. Log tool call. See data-model.md Tool 1: search_wines
- [x] T014 [US1] Implement `generate_agentic_response()` in `backend/app/services/sommelier.py` — agent loop: build messages (system + user + history), call LLM with tools, if tool_calls → execute → append results → repeat (max 2 iterations), if content → return. Include fallback to standard flow on error. See research.md R-004, data-model.md State Transitions
- [x] T015 [US1] Refactor `generate_response()` in `backend/app/services/sommelier.py` — replace 4-path routing (detect_event/detect_food → get_llm_prompt_for_*) with: build_unified_user_prompt() → generate_agentic_response(). Keep welcome flow (`generate_welcome_with_suggestions()`) unchanged. Preserve fallback to mock AI on LLM error. See spec.md Scope, research.md R-007
- [x] T016 [US1] Run all US1 tests: `pytest backend/tests/unit/test_wine_tools.py backend/tests/unit/test_agent_loop.py backend/tests/unit/test_sommelier_unified.py -v`

**Checkpoint**: Agent loop работает с search_wines инструментом; единый промпт заменяет 4-path; структурированные запросы возвращают релевантные вина

---

## Phase 4: User Story 2 — Семантический поиск по описаниям и настроению (Priority: P2)

**Goal**: LLM вызывает semantic_search для абстрактных запросов. Комбинация с search_wines для гибридных запросов.

**Independent Test**: Отправить боту "хочу что-нибудь лёгкое и освежающее на лето" → получить вина с лёгким телом и высокой кислотностью.

### Tests for User Story 2

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T017 [P] [US2] Write tests for `semantic_search` tool execution in `backend/tests/unit/test_wine_tools.py` — test execute_semantic_search() generates embedding via get_query_embedding(), test it calls WineRepository.semantic_search() with embedding + optional filters, test response includes similarity_score, test combined use: LLM calls both search_wines and semantic_search in one iteration. Mock embedding API and repository
- [x] T018 [P] [US2] Write tests for combined structured + semantic search in `backend/tests/unit/test_agent_loop.py` — test agent loop handles both tool calls in single iteration, test deduplication when same wine found by both tools, test results ordering (semantic scores used for ranking)

### Implementation for User Story 2

- [x] T019 [US2] Implement `execute_semantic_search()` in `backend/app/services/sommelier.py` — parse tool call arguments (query required, wine_type and price_max optional), call get_query_embedding(query), call WineRepository.semantic_search() with embedding + filters, format response with similarity_score. Log tool call. See data-model.md Tool 2: semantic_search, research.md R-006
- [x] T020 [US2] Add deduplication logic to agent loop in `backend/app/services/sommelier.py` — when multiple tools return overlapping wines, deduplicate by wine.id, merge results preserving order (semantic_score for ranking when available). Update generate_agentic_response()
- [x] T021 [US2] Run all US2 tests: `pytest backend/tests/unit/test_wine_tools.py backend/tests/unit/test_agent_loop.py -v`

**Checkpoint**: Семантический поиск работает; комбинированные запросы ("элегантное красное до 3000") используют оба инструмента

---

## Phase 5: User Story 3 — Комбинированные и контекстные запросы (Priority: P3)

**Goal**: История переписки учитывается при формировании tool calls. LLM использует контекст предыдущих сообщений для уточнения поиска.

**Independent Test**: "посоветуй красное" → красные вина. "а подешевле?" → красные вина дешевле предыдущих.

### Tests for User Story 3

- [x] T022 [P] [US3] Write tests for contextual queries in `backend/tests/unit/test_agent_loop.py` — test conversation history is included in messages sent to LLM, test that LLM receives previous tool calls and results in history, test follow-up query ("а подешевле?") scenario with mock LLM responses showing context-aware tool calls

### Implementation for User Story 3

- [x] T023 [US3] Verify conversation history integration in `backend/app/services/sommelier.py` — ensure `generate_agentic_response()` correctly includes conversation_history in messages list before the current user message, ensure history trimming (llm_max_history_messages config) is applied. This should already work from US1 implementation but needs explicit verification and possible adjustments
- [x] T024 [US3] Run all US3 tests: `pytest backend/tests/unit/test_agent_loop.py -v`

**Checkpoint**: Контекстные запросы работают; LLM учитывает историю при выборе инструментов и параметров

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Финальная верификация, logging, полный тест-сюит

- [x] T025 Run full test suite: `pytest backend/tests/ -v` — all 77 new tests pass, 0 new failures. 34 pre-existing failures (integration/DB tests, wine_repository fixtures, Russian morphology keyword matching) documented as unrelated
- [ ] T026 End-to-end verification via Telegram bot: send 4 test scenarios from quickstart.md (structured, semantic, combined, fallback) → verify correct wine recommendations with photos. Requires running bot instance with API key

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 can run in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 (config + tool schemas)
- **US1 (Phase 3)**: Depends on Phase 2 (LLM tool use + repository filters)
- **US2 (Phase 4)**: Depends on Phase 2 (embeddings) + Phase 3 (agent loop exists)
- **US3 (Phase 5)**: Depends on Phase 3 (agent loop with history support)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational — core deliverable, creates agent loop
- **US2 (P2)**: Depends on US1 — adds semantic_search tool to existing agent loop
- **US3 (P3)**: Depends on US1 — verifies history works with agent loop

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per constitution)
- Tool execution before agent loop integration
- Agent loop before generate_response() refactoring
- All tests pass before moving to next phase

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T003 and T004 can run in parallel (different test files)
- T009, T010, T011 can run in parallel (different test files)
- T017 and T018 can run in parallel (different test files)

---

## Parallel Example: User Story 1

```bash
# Tests in parallel (TDD Red phase):
Task: "Write search_wines tool tests in backend/tests/unit/test_wine_tools.py"
Task: "Write agent loop tests in backend/tests/unit/test_agent_loop.py"
Task: "Write unified prompt tests in backend/tests/unit/test_sommelier_unified.py"

# Then implementation sequentially (TDD Green phase):
Task: "Create unified prompt in sommelier_prompts.py"
Task: "Implement search_wines tool in sommelier.py"
Task: "Implement agent loop in sommelier.py"
Task: "Refactor generate_response() in sommelier.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Config + tool schemas
2. Complete Phase 2: LLM tool use + repository filters
3. Complete Phase 3: Agent loop + search_wines + unified prompt
4. **STOP and VALIDATE**: Test bot in Telegram — structured search works
5. Deploy if search_wines works correctly

### Incremental Delivery

1. Setup + Foundational → LLM tool use ready, repository extended
2. US1 → Agent loop + search_wines → **MVP deployed** 🎯
3. US2 → Semantic search added → Hybrid queries work
4. US3 → Contextual queries verified → Full feature complete
5. Polish → Full test suite + E2E → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- US2 depends on US1 because semantic_search tool is added to the existing agent loop
- US3 is primarily verification — conversation history is passed through in US1, US3 confirms it works correctly
- No new dependencies — OpenAI SDK already in requirements.txt
- No DB migrations — schema unchanged, only new Repository filters
- Welcome flow (`generate_welcome_with_suggestions()`) is explicitly out of scope
- Total: 26 tasks (8 test tasks, 12 implementation tasks, 2 setup, 1 config, 3 verification)
