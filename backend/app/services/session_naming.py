"""Session naming service for auto-generating session titles.

Uses LLM (Claude haiku) to generate short, meaningful titles based on
the first user message and AI response. Falls back to date format on failure.
"""
import logging
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.services.llm import LLMError, get_llm_service

logger = logging.getLogger(__name__)

# Russian month names for date fallback
RUSSIAN_MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

# Prompt template for session naming
SESSION_NAMING_PROMPT = """Сгенерируй короткое название (1-3 слова, максимум 30 символов) для диалога на основе первых сообщений.
Название должно отражать тему: тип вина, событие или блюдо.

Примеры хороших названий:
- "Вино к стейку"
- "Бордо на ДР"
- "Розовое для пикника"
- "Новое шардоне"
- "Вино на ужин"
- "Красное к мясу"

Первое сообщение пользователя: {user_message}
Ответ AI: {ai_response}

Верни ТОЛЬКО название, без кавычек и пояснений."""


class SessionNamingService:
    """Service for generating session titles using LLM with date fallback."""

    def __init__(self):
        self.settings = get_settings()
        self._llm = None

    @property
    def llm(self):
        """Lazy initialization of LLM service."""
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm

    def is_llm_configured(self) -> bool:
        """Check if LLM is configured without initializing it."""
        settings = self.settings
        provider = settings.llm_provider.lower()

        if provider == "openrouter" and settings.openrouter_api_key:
            return True
        elif provider == "anthropic" and settings.anthropic_api_key:
            return True
        elif provider == "openai" and settings.openai_api_key:
            return True

        return False

    async def generate_session_title(
        self,
        user_message: str,
        ai_response: str,
    ) -> str:
        """
        Generate a short title for the session based on first exchange.

        Args:
            user_message: First user message in the conversation
            ai_response: First AI response (non-welcome)

        Returns:
            Generated title (max 30 chars) or date fallback
        """
        try:
            if not self.llm.is_available:
                logger.info("LLM not available, using date fallback for title")
                return self._generate_date_fallback()

            # Build the prompt
            prompt = SESSION_NAMING_PROMPT.format(
                user_message=user_message[:500],  # Limit input size
                ai_response=ai_response[:500],
            )

            # Generate title using LLM
            title = await self.llm.generate(
                system_prompt="Ты помощник для генерации коротких названий.",
                user_prompt=prompt,
                temperature=0.7,  # Some creativity for variety
                max_tokens=50,    # Short response expected
            )

            # Clean and validate title
            title = self._clean_title(title)

            if not title or len(title) < 2:
                logger.warning("LLM returned invalid title, using fallback")
                return self._generate_date_fallback()

            logger.info("Generated session title: %s", title)
            return title

        except LLMError as e:
            logger.warning("LLM error during title generation: %s", e)
            return self._generate_date_fallback()
        except Exception as e:
            logger.error("Unexpected error during title generation: %s", e)
            return self._generate_date_fallback()

    def _clean_title(self, title: str) -> str:
        """
        Clean and validate the generated title.

        - Remove quotes
        - Remove extra whitespace
        - Truncate to 30 chars
        """
        if not title:
            return ""

        # Remove surrounding quotes (including various Unicode quotes)
        # U+0022 " ASCII double quote
        # U+0027 ' ASCII single quote
        # U+00AB « Left-pointing double angle
        # U+00BB » Right-pointing double angle
        # U+2018 ' Left single quotation
        # U+2019 ' Right single quotation
        # U+201A ‚ Single low-9 quotation
        # U+201B ‛ Single high-reversed-9
        # U+201C " Left double quotation
        # U+201D " Right double quotation
        # U+201E „ Double low-9 quotation
        # U+201F ‟ Double high-reversed-9
        quote_chars = '"\'\u00ab\u00bb\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f'
        title = title.strip().strip(quote_chars)

        # Remove extra whitespace
        title = " ".join(title.split())

        # Truncate to max length
        if len(title) > 30:
            # Try to cut at word boundary
            title = title[:30].rsplit(" ", 1)[0]
            if len(title) < 10:  # Too short after cut
                title = title[:30]

        return title

    def _generate_date_fallback(self, dt: Optional[datetime] = None) -> str:
        """
        Generate a date-based title as fallback.

        Format: "D месяца" (e.g., "3 февраля")

        Args:
            dt: Optional datetime, defaults to now

        Returns:
            Date-formatted title
        """
        if dt is None:
            dt = datetime.now()

        day = dt.day
        month_name = RUSSIAN_MONTHS[dt.month - 1]

        return f"{day} {month_name}"


# Singleton instance
_naming_service: Optional[SessionNamingService] = None


def get_session_naming_service() -> SessionNamingService:
    """Get or create session naming service singleton."""
    global _naming_service
    if _naming_service is None:
        _naming_service = SessionNamingService()
    return _naming_service


def reset_session_naming_service():
    """Reset session naming service singleton (for testing)."""
    global _naming_service
    _naming_service = None
