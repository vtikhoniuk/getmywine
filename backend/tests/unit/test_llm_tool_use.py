"""Tests for LLM tool use: generate_with_tools() and get_query_embedding().

T003: TDD Red phase — tests for methods not yet implemented.

Tests:
1. generate_with_tools() accepts tools param and returns full message object
2. generate_with_tools() handles response with tool_calls
3. generate_with_tools() handles response with content only (no tool_calls)
4. Existing generate() still returns str (not broken by new methods)
5. get_query_embedding() calls embeddings API and returns list[float]
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings():
    """Override settings with OpenRouter config for tests."""
    with patch("app.services.llm.get_settings") as mock_settings:
        s = MagicMock()
        s.llm_provider = "openrouter"
        s.openrouter_api_key = "test-key"
        s.openrouter_base_url = "https://openrouter.ai/api/v1"
        s.llm_model = "anthropic/claude-sonnet-4"
        s.llm_temperature = 0.7
        s.llm_max_tokens = 2000
        s.llm_max_history_messages = 10
        s.embedding_model = "BAAI/bge-m3"
        mock_settings.return_value = s
        yield s


@pytest.fixture
def mock_openai_client():
    """Mock openai.AsyncOpenAI client."""
    client = AsyncMock()
    with patch("openai.AsyncOpenAI", return_value=client):
        yield client


@pytest.fixture
def sample_tools():
    """Sample tool definitions for testing."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_wines",
                "description": "Search wines in catalog by criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wine_type": {
                            "type": "string",
                            "enum": ["red", "white", "rose", "sparkling"],
                        },
                        "price_max": {
                            "type": "number",
                            "description": "Max price in RUB",
                        },
                    },
                    "required": [],
                },
            },
        }
    ]


@pytest.fixture
def mock_tool_call():
    """Mock tool_call object from OpenAI response."""
    tc = MagicMock()
    tc.id = "call_123"
    tc.type = "function"
    tc.function.name = "search_wines"
    tc.function.arguments = '{"wine_type": "red", "price_max": 2000}'
    return tc


@pytest.fixture
def mock_message_with_tool_calls(mock_tool_call):
    """Mock ChatCompletionMessage with tool_calls (no content)."""
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [mock_tool_call]
    return msg


@pytest.fixture
def mock_message_content_only():
    """Mock ChatCompletionMessage with content only (no tool_calls)."""
    msg = MagicMock()
    msg.content = "Here are some wine recommendations..."
    msg.tool_calls = None
    return msg


# ---------------------------------------------------------------------------
# T003-1: generate_with_tools() returns full message object
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateWithToolsReturnsMessage:
    """generate_with_tools() should return full ChatCompletionMessage."""

    async def test_returns_message_object_with_tool_calls(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_with_tool_calls,
    ):
        """Should return message object (not str) when LLM invokes a tool."""
        from app.services.llm import OpenRouterService

        # Set up mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_with_tool_calls
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Find me a red wine under 2000 RUB",
            tools=sample_tools,
        )

        # Must return full message object, not str
        assert result is mock_message_with_tool_calls
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.content is None

    async def test_returns_message_object_with_content(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_content_only,
    ):
        """Should return message object when LLM responds with content only."""
        from app.services.llm import OpenRouterService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_content_only
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Tell me about Merlot",
            tools=sample_tools,
        )

        assert result is mock_message_content_only
        assert result.content == "Here are some wine recommendations..."
        assert result.tool_calls is None


# ---------------------------------------------------------------------------
# T003-2: generate_with_tools() with tool_calls in response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateWithToolsToolCalls:
    """Verify tool_calls details are correctly passed through."""

    async def test_tool_call_has_function_name_and_arguments(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_with_tool_calls,
    ):
        """tool_calls[0] should have function name and JSON arguments."""
        from app.services.llm import OpenRouterService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_with_tool_calls
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Find red wine",
            tools=sample_tools,
        )

        tool_call = result.tool_calls[0]
        assert tool_call.id == "call_123"
        assert tool_call.type == "function"
        assert tool_call.function.name == "search_wines"
        assert '"wine_type"' in tool_call.function.arguments
        assert '"red"' in tool_call.function.arguments

    async def test_tools_passed_to_api_call(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_with_tool_calls,
    ):
        """tools parameter should be forwarded to the OpenAI API call."""
        from app.services.llm import OpenRouterService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_with_tool_calls
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Find red wine",
            tools=sample_tools,
        )

        # Verify tools were passed to the API
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == sample_tools


# ---------------------------------------------------------------------------
# T003-3: generate_with_tools() content-only response (no tool_calls)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateWithToolsContentOnly:
    """When LLM decides not to use tools, tool_calls should be None."""

    async def test_content_only_response(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_content_only,
    ):
        """When model returns text (no tool use), tool_calls is None."""
        from app.services.llm import OpenRouterService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_content_only
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="What is Merlot?",
            tools=sample_tools,
        )

        assert result.tool_calls is None
        assert isinstance(result.content, str)
        assert len(result.content) > 0


# ---------------------------------------------------------------------------
# T003-4: Existing generate() still returns str
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateNotAffected:
    """Adding generate_with_tools() must not break existing generate()."""

    async def test_generate_still_returns_str(
        self,
        settings,
        mock_openai_client,
    ):
        """generate() should still return a plain string, not a message object."""
        from app.services.llm import OpenRouterService

        mock_message = MagicMock()
        mock_message.content = "I recommend a nice Pinot Noir."

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.generate(
            system_prompt="You are a sommelier.",
            user_prompt="Recommend a wine",
        )

        assert isinstance(result, str)
        assert result == "I recommend a nice Pinot Noir."


# ---------------------------------------------------------------------------
# T003-5: LLMService wrapper delegates generate_with_tools()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLLMServiceWrapperToolUse:
    """LLMService (wrapper) should delegate generate_with_tools() to provider."""

    async def test_wrapper_delegates_generate_with_tools(
        self,
        settings,
        sample_tools,
        mock_message_with_tool_calls,
    ):
        """LLMService.generate_with_tools() should call provider's method."""
        from app.services.llm import LLMService, reset_llm_service

        reset_llm_service()
        service = LLMService()
        service._initialized = True

        # Mock the provider
        mock_provider = AsyncMock()
        mock_provider.generate_with_tools = AsyncMock(
            return_value=mock_message_with_tool_calls
        )
        service._provider = mock_provider

        result = await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Find red wine",
            tools=sample_tools,
        )

        assert result is mock_message_with_tool_calls
        mock_provider.generate_with_tools.assert_awaited_once()

    async def test_wrapper_raises_without_provider(self, settings):
        """LLMService.generate_with_tools() should raise LLMError if no provider."""
        from app.services.llm import LLMError, LLMService, reset_llm_service

        reset_llm_service()
        service = LLMService()
        service._initialized = True
        service._provider = None

        with pytest.raises(LLMError):
            await service.generate_with_tools(
                system_prompt="You are a sommelier.",
                user_prompt="Find wine",
                tools=[],
            )


# ---------------------------------------------------------------------------
# T003-5 (cont): AnthropicService and OpenAIService raise NotImplementedError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUnsupportedProviders:
    """AnthropicService and OpenAIService should not support tool use yet."""

    async def test_anthropic_raises_not_implemented(self):
        """AnthropicService.generate_with_tools() should raise NotImplementedError."""
        from app.services.llm import AnthropicService

        service = AnthropicService(api_key="test-key")

        with pytest.raises(NotImplementedError):
            await service.generate_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools=[],
            )

    async def test_openai_raises_not_implemented(self):
        """OpenAIService.generate_with_tools() should raise NotImplementedError."""
        from app.services.llm import OpenAIService

        service = OpenAIService(api_key="test-key")

        with pytest.raises(NotImplementedError):
            await service.generate_with_tools(
                system_prompt="test",
                user_prompt="test",
                tools=[],
            )


# ---------------------------------------------------------------------------
# T003-6: generate_with_tools() accepts messages parameter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGenerateWithToolsMessages:
    """generate_with_tools() should accept optional messages for multi-turn."""

    async def test_messages_passed_to_api(
        self,
        settings,
        mock_openai_client,
        sample_tools,
        mock_message_content_only,
    ):
        """When messages are provided, they should be included in the API call."""
        from app.services.llm import OpenRouterService

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_message_content_only
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        # Multi-turn messages (e.g., after tool call result)
        messages = [
            {"role": "user", "content": "Find red wine under 2000"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search_wines",
                            "arguments": '{"wine_type": "red"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "content": '[{"name": "Malbec", "price_rub": 1500}]',
            },
        ]

        await service.generate_with_tools(
            system_prompt="You are a sommelier.",
            user_prompt="Find red wine under 2000",
            tools=sample_tools,
            messages=messages,
        )

        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        api_messages = call_kwargs["messages"]
        # When messages is provided, it IS the full message list (used as-is)
        assert api_messages == messages
        assert len(api_messages) == 3


# ---------------------------------------------------------------------------
# T003-7: get_query_embedding() returns list[float]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetQueryEmbedding:
    """get_query_embedding() should call embeddings API and return list[float]."""

    async def test_returns_list_of_floats(
        self,
        settings,
        mock_openai_client,
    ):
        """Should call embeddings.create and return embedding vector."""
        from app.services.llm import OpenRouterService

        # Mock embeddings response
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [mock_embedding_data]

        mock_openai_client.embeddings.create = AsyncMock(
            return_value=mock_embedding_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        result = await service.get_query_embedding("red wine for steak")

        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

    async def test_calls_embeddings_api_with_correct_model(
        self,
        settings,
        mock_openai_client,
    ):
        """Should use the embedding_model from settings."""
        from app.services.llm import OpenRouterService

        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.0] * 1024

        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [mock_embedding_data]

        mock_openai_client.embeddings.create = AsyncMock(
            return_value=mock_embedding_response
        )

        service = OpenRouterService(
            api_key="test-key",
            model="anthropic/claude-sonnet-4",
        )
        service._client = mock_openai_client

        await service.get_query_embedding("full-bodied red wine")

        call_kwargs = mock_openai_client.embeddings.create.call_args.kwargs
        assert call_kwargs["model"] == "BAAI/bge-m3"
        assert call_kwargs["input"] == "full-bodied red wine"

    async def test_llm_service_wrapper_delegates_embedding(
        self,
        settings,
    ):
        """LLMService.get_query_embedding() should delegate to provider."""
        from app.services.llm import LLMService, reset_llm_service

        reset_llm_service()
        service = LLMService()
        service._initialized = True

        expected_embedding = [0.1, 0.2, 0.3]
        mock_provider = AsyncMock()
        mock_provider.get_query_embedding = AsyncMock(
            return_value=expected_embedding
        )
        service._provider = mock_provider

        result = await service.get_query_embedding("dry white wine")

        assert result == expected_embedding
        mock_provider.get_query_embedding.assert_awaited_once_with(
            "dry white wine"
        )
