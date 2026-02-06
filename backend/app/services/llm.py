"""LLM service for GetMyWine sommelier.

Supports:
- OpenRouter (recommended) - access to multiple models via single API
- Anthropic Claude (direct)
- OpenAI GPT (direct)

Includes conversation history support for contextual responses.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in conversation history."""
    role: str  # "user", "assistant", or "system"
    content: str


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from the LLM."""
        pass


class OpenRouterService(BaseLLMService):
    """OpenRouter LLM service - access multiple models via OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-sonnet-4",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client with OpenRouter base URL."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate response using OpenRouter."""
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=temp,
                max_tokens=tokens,
                messages=messages,
                # OpenRouter-specific headers
                extra_headers={
                    "HTTP-Referer": "https://getmywine.local",
                    "X-Title": "GetMyWine",
                },
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error("OpenRouter API error: %s", e)
            raise LLMError(f"Failed to generate response: {e}") from e


class AnthropicService(BaseLLMService):
    """Anthropic Claude LLM service (direct API)."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate response using Claude."""
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        # Build messages list (Anthropic format)
        messages = []

        # Add conversation history
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=tokens,
                temperature=temp,
                system=system_prompt,
                messages=messages,
            )
            return message.content[0].text

        except Exception as e:
            logger.error("Anthropic API error: %s", e)
            raise LLMError(f"Failed to generate response: {e}") from e


class OpenAIService(BaseLLMService):
    """OpenAI GPT LLM service (direct API)."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate response using GPT."""
        settings = get_settings()
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=temp,
                max_tokens=tokens,
                messages=messages,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            raise LLMError(f"Failed to generate response: {e}") from e


class LLMError(Exception):
    """Exception raised when LLM call fails."""
    pass


class LLMService:
    """
    Main LLM service that wraps provider-specific implementations.

    Automatically selects provider based on configuration.
    Falls back to mock responses if no API key is configured.
    """

    def __init__(self):
        self.settings = get_settings()
        self._provider: Optional[BaseLLMService] = None
        self._initialized = False

    def _initialize(self):
        """Initialize the appropriate LLM provider."""
        if self._initialized:
            return

        provider = self.settings.llm_provider.lower()

        # OpenRouter (recommended)
        if provider == "openrouter" and self.settings.openrouter_api_key:
            self._provider = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                model=self.settings.llm_model,
                base_url=self.settings.openrouter_base_url,
            )
            logger.info(
                "LLM initialized with OpenRouter: %s",
                self.settings.llm_model,
            )

        # Anthropic (direct)
        elif provider == "anthropic" and self.settings.anthropic_api_key:
            self._provider = AnthropicService(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.llm_model,
            )
            logger.info(
                "LLM initialized with Anthropic Claude: %s",
                self.settings.llm_model,
            )

        # OpenAI (direct)
        elif provider == "openai" and self.settings.openai_api_key:
            self._provider = OpenAIService(
                api_key=self.settings.openai_api_key,
                model=self.settings.llm_model,
            )
            logger.info("LLM initialized with OpenAI: %s", self.settings.llm_model)

        else:
            logger.warning(
                "No LLM API key configured for provider '%s'. "
                "Will use mock responses. "
                "Set OPENROUTER_API_KEY in .env for LLM support.",
                provider,
            )

        self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if real LLM is available."""
        self._initialize()
        return self._provider is not None

    @property
    def provider_name(self) -> str:
        """Get current provider name."""
        self._initialize()
        if isinstance(self._provider, OpenRouterService):
            return "openrouter"
        elif isinstance(self._provider, AnthropicService):
            return "anthropic"
        elif isinstance(self._provider, OpenAIService):
            return "openai"
        return "mock"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate LLM response with optional conversation history.

        Args:
            system_prompt: System instructions for the model
            user_prompt: Current user message/prompt
            history: Previous conversation messages (user + assistant)
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Model response text

        Raises:
            LLMError: If no provider configured or API call fails
        """
        self._initialize()

        if not self._provider:
            raise LLMError("No LLM provider configured")

        # Trim history to max messages
        trimmed_history = None
        if history:
            max_history = self.settings.llm_max_history_messages
            trimmed_history = history[-max_history:]

        return await self._provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=trimmed_history,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_wine_recommendation(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[list[ChatMessage]] = None,
    ) -> str:
        """
        Generate wine recommendation with optimized settings.

        Uses slightly lower temperature for more consistent recommendations.
        """
        return await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
            temperature=0.6,  # More focused for recommendations
            max_tokens=2000,
        )


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def reset_llm_service():
    """Reset LLM service singleton (useful for testing)."""
    global _llm_service
    _llm_service = None
