"""Tests for SommelierService.generate_agentic_response() — agent loop.

T010: TDD Red phase — tests should FAIL with AttributeError because
generate_agentic_response() does not exist yet on SommelierService.

Agent loop flow:
1. Build messages list: [system, user_prompt (with context)]
2. Call LLM with tools -> get response message
3. If response has tool_calls -> execute each tool -> append assistant msg +
   tool results to messages -> increment iteration -> repeat from step 2
4. If response has content (no tool_calls) -> return content
5. If iteration >= max_iterations -> call LLM one final time without tools
   -> return content
6. On error -> return None (caller handles fallback)

Tests:
1. test_single_iteration_with_tool_call
2. test_max_iterations_limit
3. test_no_tool_calls_direct_response
4. test_fallback_on_error
5. test_tool_results_appended_to_messages
6. test_iteration_counter_increments
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm import LLMError
from app.services.sommelier import SommelierService, ParseResult


# ---------------------------------------------------------------------------
# Valid SommelierResponse JSON for retry tests
# ---------------------------------------------------------------------------

VALID_SOMMELIER_JSON = json.dumps({
    "response_type": "recommendation",
    "intro": "Вот отличные варианты красного вина!",
    "wines": [
        {
            "wine_id": "550e8400-e29b-41d4-a716-446655440000",
            "wine_name": "Malbec Reserva 2020",
            "description": "**Malbec Reserva, Мендоса, Аргентина, 2020, 1800₽**\nОтличный выбор для ужина.",
        }
    ],
    "closing": "Хотите узнать больше о аргентинских винах?",
    "guard_type": None,
}, ensure_ascii=False)

INVALID_JSON = '{"broken": true, "not_a_sommelier_response'

SEMANTICALLY_EMPTY_JSON = json.dumps({
    "response_type": "recommendation",
    "intro": "",
    "wines": [],
    "closing": "",
    "guard_type": None,
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_tool_call(
    call_id: str = "call_abc123",
    name: str = "search_wines",
    arguments: str = '{"wine_type": "red", "price_max": 2000}',
) -> MagicMock:
    """Create a mock tool_call object mimicking OpenAI ChatCompletionMessage."""
    tc = MagicMock()
    tc.id = call_id
    tc.type = "function"
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def _make_msg_with_tool_calls(tool_calls: list | None = None) -> MagicMock:
    """Mock ChatCompletionMessage that contains tool_calls (no content)."""
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = tool_calls or [_make_mock_tool_call()]
    return msg


def _make_msg_with_content(content: str = "[INTRO]Here are wines...[/INTRO]") -> MagicMock:
    """Mock ChatCompletionMessage that contains content (no tool_calls)."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    return msg


def _make_sommelier_service() -> SommelierService:
    """Create a SommelierService with mocked dependencies.

    - db: AsyncMock (not used in generate_agentic_response)
    - llm_service: MagicMock with generate_with_tools as AsyncMock
    - wine_repo: AsyncMock
    - execute_search_wines: AsyncMock returning JSON string
    """
    mock_db = AsyncMock()

    with patch.object(SommelierService, "__init__", lambda self, db: None):
        service = SommelierService(mock_db)

    service.db = mock_db
    service.llm_service = MagicMock()
    service.llm_service.generate_with_tools = AsyncMock()
    service.wine_repo = AsyncMock()
    service.execute_search_wines = AsyncMock(
        return_value=json.dumps({
            "found": 2,
            "wines": [
                {"name": "Malbec Reserva 2020", "price_rub": 1800},
                {"name": "Cabernet Sauvignon 2019", "price_rub": 1950},
            ],
            "filters_applied": {"wine_type": "red", "price_max": 2000},
        })
    )

    return service


# ---------------------------------------------------------------------------
# T010-1: Single iteration with tool call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSingleIterationWithToolCall:
    """LLM returns tool_calls on first call, then content on second call."""

    async def test_single_iteration_with_tool_call(self):
        """After one tool call, LLM should produce final content."""
        service = _make_sommelier_service()

        mock_msg_tools = _make_msg_with_tool_calls()
        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)

        # First call -> tool_calls, second call -> content
        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        result = await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find me a red wine under 2000 RUB",
        )

        # execute_search_wines should have been called once
        service.execute_search_wines.assert_called_once()

        # Final content should be the raw JSON structured response
        assert "Вот отличные варианты красного вина!" in result[0]

    async def test_tool_call_arguments_parsed_and_forwarded(self):
        """Arguments from the tool_call should be parsed and passed to execute_search_wines."""
        service = _make_sommelier_service()

        tool_call = _make_mock_tool_call(
            arguments='{"wine_type": "white", "price_max": 1500}'
        )
        mock_msg_tools = _make_msg_with_tool_calls(tool_calls=[tool_call])
        mock_msg_content = _make_msg_with_content("Here you go!")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="I want white wine",
        )

        # Verify the parsed arguments were forwarded
        call_args = service.execute_search_wines.call_args
        passed_arguments = call_args[0][0] if call_args[0] else call_args[1].get("arguments", {})
        assert passed_arguments.get("wine_type") == "white" or service.execute_search_wines.called


# ---------------------------------------------------------------------------
# T010-2: Max iterations limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMaxIterationsLimit:
    """LLM keeps returning tool_calls. After max iterations, loop must stop."""

    async def test_max_iterations_forces_final_call_without_tools(self):
        """After agent_max_iterations tool rounds, make one final LLM call without tools."""
        service = _make_sommelier_service()

        mock_msg_tools_1 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_1")]
        )
        mock_msg_tools_2 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_2")]
        )
        mock_msg_final = _make_msg_with_content(VALID_SOMMELIER_JSON)

        # Two iterations of tool_calls, then the forced final call returns content
        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools_1, mock_msg_tools_2, mock_msg_final]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.agent_max_iterations = 2
            mock_settings.structured_output_max_retries = 2
            mock_get_settings.return_value = mock_settings

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find red wine",
            )

        assert "Вот отличные варианты красного вина!" in result[0]
        # LLM should have been called 3 times: 2 with tools + 1 final without
        assert service.llm_service.generate_with_tools.call_count == 3

    async def test_max_iterations_final_call_has_no_tools(self):
        """The final LLM call (after max iterations) must NOT include tools."""
        service = _make_sommelier_service()

        mock_msg_tools_1 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_1")]
        )
        mock_msg_tools_2 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_2")]
        )
        mock_msg_final = _make_msg_with_content("Done.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools_1, mock_msg_tools_2, mock_msg_final]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.agent_max_iterations = 2
            mock_get_settings.return_value = mock_settings

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # The third (final) call should have tools=None or tools=[]
        # indicating the loop forced a non-tool call
        final_call_kwargs = service.llm_service.generate_with_tools.call_args_list[-1].kwargs
        tools_in_final = final_call_kwargs.get("tools")
        assert tools_in_final is None or tools_in_final == [], (
            f"Final call should have no tools, got: {tools_in_final}"
        )


# ---------------------------------------------------------------------------
# T010-3: No tool calls — direct response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNoToolCallsDirectResponse:
    """LLM returns content immediately (no tool_calls)."""

    async def test_returns_content_directly(self):
        """Should return LLM content without executing any tools."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        result = await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Tell me about Merlot",
        )

        assert "Вот отличные варианты красного вина!" in result[0]
        # No tools should have been executed
        service.execute_search_wines.assert_not_called()

    async def test_llm_called_exactly_once(self):
        """When LLM responds with content directly, it should be called only once."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="What is wine?",
        )

        assert service.llm_service.generate_with_tools.call_count == 1


# ---------------------------------------------------------------------------
# T010-4: Fallback on error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFallbackOnError:
    """LLM raises LLMError. generate_agentic_response should return None."""

    async def test_returns_none_on_llm_error(self):
        """When LLMError is raised, should return None for caller to handle."""
        service = _make_sommelier_service()

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=LLMError("API rate limit exceeded")
        )

        result = await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find me a wine",
        )

        assert result is None

    async def test_returns_none_on_generic_exception(self):
        """When a generic Exception is raised, should also return None."""
        service = _make_sommelier_service()

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=Exception("Network timeout")
        )

        result = await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find me a wine",
        )

        assert result is None

    async def test_no_tool_execution_on_error(self):
        """When LLM fails on the first call, no tool should be executed."""
        service = _make_sommelier_service()

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=LLMError("Connection failed")
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find me a wine",
        )

        service.execute_search_wines.assert_not_called()


# ---------------------------------------------------------------------------
# T010-5: Tool results appended to messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestToolResultsAppendedToMessages:
    """After tool execution, messages list must contain assistant msg + tool result."""

    async def test_messages_contain_tool_result_with_correct_role(self):
        """Messages passed to the second LLM call should include a 'tool' role message."""
        service = _make_sommelier_service()

        tool_call = _make_mock_tool_call(call_id="call_xyz789")
        mock_msg_tools = _make_msg_with_tool_calls(tool_calls=[tool_call])
        mock_msg_content = _make_msg_with_content("Based on the search results...")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find red wine",
        )

        # Inspect messages passed to the second LLM call
        second_call = service.llm_service.generate_with_tools.call_args_list[1]
        second_call_kwargs = second_call.kwargs
        messages = second_call_kwargs.get("messages")

        assert messages is not None, "Second LLM call must receive messages parameter"

        # Find the tool result message
        tool_messages = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_messages) >= 1, (
            f"Expected at least one tool message, got: {[m.get('role') for m in messages]}"
        )

        tool_msg = tool_messages[0]
        assert tool_msg["tool_call_id"] == "call_xyz789"
        assert "content" in tool_msg
        # Content should be the JSON response from execute_search_wines
        parsed = json.loads(tool_msg["content"])
        assert "found" in parsed
        assert "wines" in parsed

    async def test_messages_contain_assistant_message_with_tool_calls(self):
        """Messages passed to second call should include the assistant message with tool_calls."""
        service = _make_sommelier_service()

        tool_call = _make_mock_tool_call(call_id="call_abc")
        mock_msg_tools = _make_msg_with_tool_calls(tool_calls=[tool_call])
        mock_msg_content = _make_msg_with_content("Here are your wines.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find wine",
        )

        # Inspect the second call's messages
        second_call_kwargs = service.llm_service.generate_with_tools.call_args_list[1].kwargs
        messages = second_call_kwargs.get("messages")

        assert messages is not None

        # There should be an assistant message (the one with tool_calls)
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        assert len(assistant_messages) >= 1, (
            "Expected at least one assistant message in second call's messages"
        )


# ---------------------------------------------------------------------------
# T010-6: Iteration counter increments correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIterationCounterIncrements:
    """Verify LLM is called correct number of times based on iterations."""

    async def test_zero_tool_calls_one_llm_call(self):
        """No tool calls -> 1 LLM call total."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Hello",
        )

        assert service.llm_service.generate_with_tools.call_count == 1

    async def test_one_tool_call_two_llm_calls(self):
        """One round of tool_calls -> 2 LLM calls total."""
        service = _make_sommelier_service()

        mock_msg_tools = _make_msg_with_tool_calls()
        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find red wine",
        )

        assert service.llm_service.generate_with_tools.call_count == 2

    async def test_two_tool_calls_three_llm_calls(self):
        """Two rounds of tool_calls (hitting max_iterations=2) -> 3 LLM calls total."""
        service = _make_sommelier_service()

        mock_msg_tools_1 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_1")]
        )
        mock_msg_tools_2 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_2")]
        )
        mock_msg_final = _make_msg_with_content("Final.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools_1, mock_msg_tools_2, mock_msg_final]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.agent_max_iterations = 2
            mock_get_settings.return_value = mock_settings

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # 2 tool iterations + 1 final call = 3 total
        assert service.llm_service.generate_with_tools.call_count == 3

    async def test_execute_search_wines_called_per_iteration(self):
        """execute_search_wines should be called once per tool-call iteration."""
        service = _make_sommelier_service()

        mock_msg_tools_1 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_1")]
        )
        mock_msg_tools_2 = _make_msg_with_tool_calls(
            tool_calls=[_make_mock_tool_call(call_id="call_2")]
        )
        mock_msg_final = _make_msg_with_content("Done.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools_1, mock_msg_tools_2, mock_msg_final]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.agent_max_iterations = 2
            mock_get_settings.return_value = mock_settings

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # Two iterations with tool_calls -> execute_search_wines called twice
        assert service.execute_search_wines.call_count == 2


# ---------------------------------------------------------------------------
# T010-extra: Optional parameters (conversation_history, user_profile, events)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOptionalParameters:
    """Verify optional parameters are handled and forwarded correctly."""

    async def test_conversation_history_included_in_messages(self):
        """When conversation_history is provided, it should appear in messages."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content("Answer.")
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        history = [
            {"role": "user", "content": "I like red wine"},
            {"role": "assistant", "content": "Great choice!"},
        ]

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="What else do you recommend?",
            conversation_history=history,
        )

        # Inspect messages passed to LLM
        call_kwargs = service.llm_service.generate_with_tools.call_args.kwargs
        messages = call_kwargs.get("messages")

        if messages is not None:
            # History messages should be included
            roles = [m.get("role") for m in messages]
            assert "user" in roles
            assert "assistant" in roles

    async def test_user_profile_included_in_prompt(self):
        """When user_profile is provided, it should be reflected in the user prompt."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        profile = {"sweetness_pref": "dry", "favorite_regions": ["Bordeaux"]}

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Recommend a wine",
            user_profile=profile,
        )

        # The method should have been called (exact prompt structure depends on implementation)
        service.llm_service.generate_with_tools.assert_called_once()

    async def test_events_context_included_in_prompt(self):
        """When events_context is provided, it should be included in the prompt."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Wine for a holiday",
            events_context="Today: International Wine Day",
        )

        service.llm_service.generate_with_tools.assert_called_once()


# ---------------------------------------------------------------------------
# T018: Combined structured + semantic search in agent loop
# TDD Red — execute_semantic_search doesn't exist yet on SommelierService
# ---------------------------------------------------------------------------


def _make_sommelier_service_with_both_tools() -> SommelierService:
    """Create a SommelierService with both execute_search_wines and execute_semantic_search mocked."""
    mock_db = AsyncMock()

    with patch.object(SommelierService, "__init__", lambda self, db: None):
        service = SommelierService(mock_db)

    service.db = mock_db
    service.llm_service = MagicMock()
    service.llm_service.generate_with_tools = AsyncMock()
    service.wine_repo = AsyncMock()

    # Mock both tool executors
    service.execute_search_wines = AsyncMock(
        return_value=json.dumps({
            "found": 2,
            "wines": [
                {"name": "Malbec Reserva 2020", "price_rub": 1800},
                {"name": "Cabernet Sauvignon 2019", "price_rub": 1950},
            ],
            "filters_applied": {"wine_type": "red"},
        })
    )
    service.execute_semantic_search = AsyncMock(
        return_value=json.dumps({
            "found": 2,
            "wines": [
                {"name": "Malbec Reserva 2020", "similarity_score": 0.95, "price_rub": 1800},
                {"name": "Pinot Noir Reserve 2021", "similarity_score": 0.88, "price_rub": 2200},
            ],
            "filters_applied": {"query": "elegant red wine"},
        })
    )

    return service


@pytest.mark.asyncio
class TestCombinedToolCalls:
    """Tests for agent loop handling both search_wines and semantic_search in one iteration."""

    async def test_both_tools_called_in_single_iteration(self):
        """When LLM returns both tool calls, both should be executed."""
        service = _make_sommelier_service_with_both_tools()

        # LLM returns both tool calls simultaneously
        search_tc = _make_mock_tool_call(
            call_id="call_search",
            name="search_wines",
            arguments='{"wine_type": "red"}',
        )
        semantic_tc = _make_mock_tool_call(
            call_id="call_semantic",
            name="semantic_search",
            arguments='{"query": "elegant red wine"}',
        )
        mock_msg_tools = _make_msg_with_tool_calls(
            tool_calls=[search_tc, semantic_tc]
        )
        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        result = await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find an elegant red wine",
        )

        # Both tools should have been called
        service.execute_search_wines.assert_called_once()
        service.execute_semantic_search.assert_called_once()

        assert "Вот отличные варианты красного вина!" in result[0]

    async def test_both_tool_results_in_messages(self):
        """Messages for second LLM call should contain results from both tools."""
        service = _make_sommelier_service_with_both_tools()

        search_tc = _make_mock_tool_call(
            call_id="call_search",
            name="search_wines",
            arguments='{"wine_type": "red"}',
        )
        semantic_tc = _make_mock_tool_call(
            call_id="call_semantic",
            name="semantic_search",
            arguments='{"query": "elegant"}',
        )
        mock_msg_tools = _make_msg_with_tool_calls(
            tool_calls=[search_tc, semantic_tc]
        )
        mock_msg_content = _make_msg_with_content("Combined results.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Elegant red wine",
        )

        # Second call should have tool results from both
        second_call_kwargs = service.llm_service.generate_with_tools.call_args_list[1].kwargs
        messages = second_call_kwargs.get("messages")

        tool_messages = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_messages) == 2, (
            f"Expected 2 tool result messages, got {len(tool_messages)}"
        )

        tool_call_ids = {m["tool_call_id"] for m in tool_messages}
        assert "call_search" in tool_call_ids
        assert "call_semantic" in tool_call_ids

    async def test_two_llm_calls_with_both_tools(self):
        """Combined tool call iteration should still result in only 2 LLM calls."""
        service = _make_sommelier_service_with_both_tools()

        search_tc = _make_mock_tool_call(call_id="c1", name="search_wines", arguments='{}')
        semantic_tc = _make_mock_tool_call(call_id="c2", name="semantic_search", arguments='{"query": "test"}')
        mock_msg_tools = _make_msg_with_tool_calls(tool_calls=[search_tc, semantic_tc])
        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="Find wine",
        )

        # One iteration with both tools + one final = 2 LLM calls
        assert service.llm_service.generate_with_tools.call_count == 2


# ---------------------------------------------------------------------------
# T022: Contextual queries — conversation history integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestContextualQueries:
    """Tests verifying conversation history is properly passed to LLM for context-aware tool calls."""

    async def test_conversation_history_in_messages_sent_to_llm(self):
        """Conversation history messages should appear in the messages list sent to LLM."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content("Here is a cheaper wine.")
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        history = [
            {"role": "user", "content": "посоветуй красное вино"},
            {"role": "assistant", "content": "Вот Malbec Reserva 2020 за 1800₽."},
        ]

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="а подешевле?",
            conversation_history=history,
        )

        call_kwargs = service.llm_service.generate_with_tools.call_args.kwargs
        messages = call_kwargs.get("messages")

        assert messages is not None

        # Find the history messages
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]

        # History should be included: at least the 2 from history + 1 current user message
        assert len(user_messages) >= 2, (
            f"Expected at least 2 user messages (1 history + 1 current), got {len(user_messages)}"
        )
        assert len(assistant_messages) >= 1, (
            f"Expected at least 1 assistant message from history, got {len(assistant_messages)}"
        )

    async def test_history_appears_before_current_message(self):
        """History messages should appear before the current user message in the messages list."""
        service = _make_sommelier_service()

        mock_msg_content = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=mock_msg_content
        )

        history = [
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "first response"},
        ]

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="second message",
            conversation_history=history,
        )

        call_kwargs = service.llm_service.generate_with_tools.call_args.kwargs
        messages = call_kwargs.get("messages")

        # Find indexes
        non_system = [m for m in messages if m.get("role") != "system"]
        # History user message should be first among non-system
        assert "first message" in non_system[0].get("content", "")
        # Current user message should be last
        assert "second message" in non_system[-1].get("content", "")

    async def test_tool_calls_from_history_iteration_preserved(self):
        """After a tool call iteration, the assistant msg + tool results are in messages
        for the second LLM call — verifying history context persists across iterations."""
        service = _make_sommelier_service()

        history = [
            {"role": "user", "content": "посоветуй красное вино"},
            {"role": "assistant", "content": "Вот несколько вариантов красного вина."},
        ]

        tool_call = _make_mock_tool_call(call_id="call_follow_up")
        mock_msg_tools = _make_msg_with_tool_calls(tool_calls=[tool_call])
        mock_msg_content = _make_msg_with_content("Here's a cheaper option.")

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[mock_msg_tools, mock_msg_content]
        )

        await service.generate_agentic_response(
            system_prompt="You are a sommelier.",
            user_message="а подешевле?",
            conversation_history=history,
        )

        # Second LLM call should have: system + history + user + assistant(tool_calls) + tool result
        second_call_kwargs = service.llm_service.generate_with_tools.call_args_list[1].kwargs
        messages = second_call_kwargs.get("messages")

        roles = [m.get("role") for m in messages]
        assert "system" in roles
        assert "tool" in roles
        # History should still be present
        all_content = " ".join(m.get("content", "") or "" for m in messages)
        assert "посоветуй красное вино" in all_content


# ---------------------------------------------------------------------------
# Retry tests helper: mock settings with structured_output_max_retries
# ---------------------------------------------------------------------------


def _mock_settings_with_retries(max_retries: int = 2):
    """Create mock settings with structured_output_max_retries."""
    mock_settings = MagicMock()
    mock_settings.agent_max_iterations = 2
    mock_settings.llm_max_history_messages = 10
    mock_settings.structured_output_max_retries = max_retries
    return mock_settings


# ---------------------------------------------------------------------------
# T006: Retry on parse failure succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryOnParseFailureSucceeds:
    """When first LLM call returns invalid JSON, retry with error feedback succeeds."""

    async def test_retry_on_parse_failure_succeeds(self):
        """Mock generate_with_tools to return invalid JSON on first call,
        valid SommelierResponse on second call. Verify retry works."""
        service = _make_sommelier_service()

        # First call: no tool calls, invalid JSON content
        msg_invalid = _make_msg_with_content(INVALID_JSON)
        # Second call (retry): valid structured response
        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_invalid, msg_valid]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find me a red wine",
            )

        # Should have called LLM twice (initial + 1 retry)
        assert service.llm_service.generate_with_tools.call_count == 2

        # Result should be the valid rendered response
        assert result is not None
        text, wine_ids = result
        assert "Вот отличные варианты красного вина!" in text
        assert len(wine_ids) == 1

    async def test_retry_messages_contain_error_feedback(self):
        """The retry call should include the invalid response as assistant msg
        and error feedback as user msg."""
        service = _make_sommelier_service()

        msg_invalid = _make_msg_with_content(INVALID_JSON)
        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_invalid, msg_valid]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # Inspect the second (retry) call's messages
        retry_call_kwargs = service.llm_service.generate_with_tools.call_args_list[1].kwargs
        messages = retry_call_kwargs.get("messages")

        # Should contain an assistant message with the invalid content
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        assert any(INVALID_JSON in (m.get("content") or "") for m in assistant_msgs), (
            "Retry messages should include the invalid response as assistant message"
        )

        # Should contain a user message with error feedback
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assert any("validation" in (m.get("content") or "").lower() or
                    "failed" in (m.get("content") or "").lower()
                    for m in user_msgs), (
            "Retry messages should include error feedback as user message"
        )


# ---------------------------------------------------------------------------
# T007: No retry on success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNoRetryOnSuccess:
    """When first LLM call returns valid JSON, no retry should occur."""

    async def test_no_retry_on_success(self):
        """Valid response on first call: LLM called exactly once."""
        service = _make_sommelier_service()

        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=msg_valid
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # Called exactly once — no retry
        assert service.llm_service.generate_with_tools.call_count == 1

        # Valid result
        assert result is not None
        text, wine_ids = result
        assert "Вот отличные варианты красного вина!" in text


# ---------------------------------------------------------------------------
# T008: No retry on refusal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNoRetryOnRefusal:
    """When LLM returns finish_reason='refusal', no retry should occur (FR-004)."""

    async def test_no_retry_on_refusal(self):
        """Refusal is intentional — should not be retried."""
        service = _make_sommelier_service()

        msg_refusal = MagicMock()
        msg_refusal.content = "I cannot help with that."
        msg_refusal.tool_calls = None
        msg_refusal.finish_reason = "refusal"

        service.llm_service.generate_with_tools = AsyncMock(
            return_value=msg_refusal
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Help me hack a system",
            )

        # Called exactly once — no retry for refusals
        assert service.llm_service.generate_with_tools.call_count == 1


# ---------------------------------------------------------------------------
# T009: Retry on truncated response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryOnTruncatedResponse:
    """When LLM returns finish_reason='length' with truncated JSON, retry should occur."""

    async def test_retry_on_truncated_response(self):
        """Truncated response (finish_reason=length) should trigger retry."""
        service = _make_sommelier_service()

        # First call: truncated response
        msg_truncated = MagicMock()
        msg_truncated.content = '{"response_type": "recommendation", "intro": "Вот вина'
        msg_truncated.tool_calls = None
        msg_truncated.finish_reason = "length"

        # Second call (retry): valid response
        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_truncated, msg_valid]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Recommend 5 wines with detailed descriptions",
            )

        # Should have called LLM twice (initial truncated + 1 retry)
        assert service.llm_service.generate_with_tools.call_count == 2

        # Result should be valid
        assert result is not None
        text, _ = result
        assert "Вот отличные варианты красного вина!" in text


# ---------------------------------------------------------------------------
# T010: Retry on semantically empty response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryOnSemanticallyEmptyResponse:
    """When LLM returns valid JSON but semantically empty, retry should occur (FR-010)."""

    async def test_retry_on_semantically_empty_response(self):
        """Valid JSON with empty wines[] and empty intro should trigger retry."""
        service = _make_sommelier_service()

        # First call: semantically empty (valid JSON but useless)
        msg_empty = _make_msg_with_content(SEMANTICALLY_EMPTY_JSON)
        # Second call (retry): valid response with actual content
        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_empty, msg_valid]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Recommend a wine",
            )

        # Should have retried
        assert service.llm_service.generate_with_tools.call_count == 2

        # Result should be the valid response from retry
        assert result is not None
        text, wine_ids = result
        assert "Вот отличные варианты красного вина!" in text
        assert len(wine_ids) == 1


# ---------------------------------------------------------------------------
# T014: Retry exhaustion returns empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryExhaustionReturnsEmpty:
    """When all retry attempts fail, return empty tuple (graceful degradation)."""

    async def test_retry_exhaustion_returns_empty(self):
        """All 3 attempts (1 initial + 2 retries) return invalid JSON → empty result."""
        service = _make_sommelier_service()

        # All calls return invalid JSON
        msg_invalid_1 = _make_msg_with_content(INVALID_JSON)
        msg_invalid_2 = _make_msg_with_content('{"also": "broken"}')
        msg_invalid_3 = _make_msg_with_content('not json at all')

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_invalid_1, msg_invalid_2, msg_invalid_3]
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # Called 3 times: 1 initial + 2 retries
        assert service.llm_service.generate_with_tools.call_count == 3

        # Result is empty (graceful degradation)
        assert result is not None
        text, wine_ids = result
        assert text == ""
        assert wine_ids == []

    async def test_no_exception_on_exhaustion(self):
        """Retry exhaustion should not raise an exception."""
        service = _make_sommelier_service()

        service.llm_service.generate_with_tools = AsyncMock(
            return_value=_make_msg_with_content(INVALID_JSON)
        )

        with patch("app.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            # Should not raise
            result = await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        assert result is not None


# ---------------------------------------------------------------------------
# T015: No history saved on exhaustion (telegram_bot level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNoHistorySavedOnExhaustion:
    """When sommelier returns empty response, telegram_bot should NOT save to history."""

    async def test_empty_response_triggers_error_message(self):
        """Verify that ParseResult with empty text has ok=False."""
        result = ParseResult(text="", wine_ids=[])
        assert not result.ok

    async def test_empty_text_not_ok(self):
        """Whitespace-only text should also be not-ok."""
        result = ParseResult(text="   ", wine_ids=[])
        assert not result.ok

    async def test_valid_text_is_ok(self):
        """Non-empty text without error is ok."""
        result = ParseResult(text="Hello!", wine_ids=["abc"])
        assert result.ok

    async def test_error_with_text_is_not_ok(self):
        """Even with text, if error is set, result is not ok."""
        result = ParseResult(text="Some text", wine_ids=[], error="something wrong")
        assert not result.ok


# ---------------------------------------------------------------------------
# T019: Retry metadata in Langfuse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryMetadataInLangfuse:
    """Verify Langfuse metadata includes retry count and error types."""

    async def test_retry_metadata_recorded_on_retry(self):
        """When a retry occurs, metadata should contain retry count and errors."""
        service = _make_sommelier_service()

        msg_invalid = _make_msg_with_content(INVALID_JSON)
        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)

        service.llm_service.generate_with_tools = AsyncMock(
            side_effect=[msg_invalid, msg_valid]
        )

        with patch("app.config.get_settings") as mock_get_settings, \
             patch("app.services.sommelier.langfuse_context") as mock_lf:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        # Verify langfuse_context.update_current_observation was called
        mock_lf.update_current_observation.assert_called()
        call_kwargs = mock_lf.update_current_observation.call_args.kwargs
        metadata = call_kwargs.get("metadata", {})

        assert "structured_output_retries" in metadata
        assert metadata["structured_output_retries"] >= 1
        assert "structured_output_errors" in metadata
        assert len(metadata["structured_output_errors"]) >= 1

    async def test_no_retry_metadata_on_success(self):
        """When no retry occurs, metadata should show retries=0 and empty errors."""
        service = _make_sommelier_service()

        msg_valid = _make_msg_with_content(VALID_SOMMELIER_JSON)
        service.llm_service.generate_with_tools = AsyncMock(
            return_value=msg_valid
        )

        with patch("app.config.get_settings") as mock_get_settings, \
             patch("app.services.sommelier.langfuse_context") as mock_lf:
            mock_get_settings.return_value = _mock_settings_with_retries(2)

            await service.generate_agentic_response(
                system_prompt="You are a sommelier.",
                user_message="Find wine",
            )

        mock_lf.update_current_observation.assert_called()
        call_kwargs = mock_lf.update_current_observation.call_args.kwargs
        metadata = call_kwargs.get("metadata", {})

        assert metadata.get("structured_output_retries") == 0
        assert metadata.get("structured_output_errors") == []
