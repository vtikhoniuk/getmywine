"""Telegram bot service for managing Telegram user interactions."""

import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.messages import (
    ERROR_DATABASE,
    ERROR_LLM_UNAVAILABLE,
    ERROR_NO_WINES_FOUND,
    ERROR_UNKNOWN_INTENT,
)
from app.bot.utils import detect_language, get_language_instruction
from app.config import get_settings
from app.models.conversation import Conversation
from app.models.message import MessageRole
from app.models.telegram_user import TelegramUser
from app.models.wine import Wine
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.telegram_user import TelegramUserRepository
from app.repositories.wine import WineRepository
from app.services.sommelier import SommelierService

logger = logging.getLogger(__name__)
settings = get_settings()


class TelegramBotService:
    """Service for Telegram bot operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.telegram_user_repo = TelegramUserRepository(db)
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.wine_repo = WineRepository(db)
        self.sommelier = SommelierService(db)

    async def get_or_create_telegram_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru",
    ) -> tuple[TelegramUser, bool]:
        """Get or create a Telegram user.

        Per spec:
        - Creates TelegramUser if doesn't exist
        - Updates profile info if user exists
        - Sets is_age_verified=True on /start (implicit consent)

        Args:
            telegram_id: Telegram user ID
            username: Telegram username (without @)
            first_name: User's first name
            last_name: User's last name
            language_code: Preferred language code

        Returns:
            Tuple of (TelegramUser, was_created)
        """
        telegram_user, was_created = await self.telegram_user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code or "ru",
        )

        # Set age verified on /start (per spec: using bot = age consent)
        if not telegram_user.is_age_verified:
            await self.telegram_user_repo.set_age_verified(telegram_user, True)

        logger.info(
            "Telegram user %s (%s): %s",
            telegram_id,
            username or "no username",
            "created" if was_created else "retrieved",
        )

        return telegram_user, was_created

    async def create_telegram_session(
        self,
        telegram_user_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> tuple[Conversation, bool]:
        """Get or create an active Telegram session.

        Per spec:
        - Creates new ChatSession with channel='telegram'
        - Reuses active session if exists (within 24h inactivity)
        - Closes expired sessions automatically

        Args:
            telegram_user_id: TelegramUser's internal UUID
            title: Optional session title

        Returns:
            Tuple of (Conversation, was_created)
        """
        inactivity_hours = settings.telegram_session_inactivity_hours

        conversation, was_created = await self.conversation_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user_id,
            inactivity_hours=inactivity_hours,
            title=title,
        )

        logger.info(
            "Telegram session for user %s: %s",
            telegram_user_id,
            "created" if was_created else "reused",
        )

        return conversation, was_created

    async def get_welcome_wines(self, limit: int = 3) -> list[Wine]:
        """Get wines for welcome message.

        Prefers wines with photos so the bot can display them.

        Args:
            limit: Number of wines to return

        Returns:
            List of Wine objects
        """
        wines = await self.wine_repo.get_list(limit=limit, with_image=True)
        if len(wines) < limit:
            extra = await self.wine_repo.get_list(limit=limit - len(wines))
            wines.extend(extra)
        return wines

    async def handle_start(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru",
    ) -> tuple[TelegramUser, Conversation, list[Wine]]:
        """Handle /start command.

        Complete flow:
        1. Get or create TelegramUser
        2. Set age verified
        3. Get or create active session
        4. Get welcome wines

        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: Preferred language code

        Returns:
            Tuple of (TelegramUser, Conversation, list of welcome wines)
        """
        # Step 1-2: Get or create user (also sets age verified)
        telegram_user, _ = await self.get_or_create_telegram_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )

        # Step 3: Get or create session
        conversation, _ = await self.create_telegram_session(
            telegram_user_id=telegram_user.id,
        )

        # Step 4: Get welcome wines
        wines = await self.get_welcome_wines(limit=3)

        await self.db.commit()

        return telegram_user, conversation, wines

    async def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Get conversation history for LLM context.

        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages to return

        Returns:
            List of message dicts with role and content
        """
        messages = await self.message_repo.get_history(conversation_id, limit=limit)
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

    async def process_message(
        self,
        telegram_id: int,
        message_text: str,
        telegram_locale: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> tuple[str, list[Wine]]:
        """Process a free-text message and return recommendation.

        Per spec:
        - Integrates with SommelierService for recommendations
        - Uses conversation history for context
        - Detects language and responds accordingly

        Args:
            telegram_id: Telegram user ID
            message_text: User's message text
            telegram_locale: User's Telegram language code
            username: Telegram username
            first_name: User's first name

        Returns:
            Tuple of (response_text, recommended_wines)
        """
        # Get or create user
        telegram_user, _ = await self.telegram_user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=telegram_locale or "ru",
        )

        # Get or create conversation
        conversation, _ = await self.conversation_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
            inactivity_hours=settings.telegram_session_inactivity_hours,
        )

        # Detect language for response
        language = detect_language(message_text, telegram_locale)
        language_instruction = get_language_instruction(language)

        # Save user message
        await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message_text,
        )

        # Get conversation history for context
        history = await self.get_conversation_history(
            conversation.id,
            limit=10,  # Last 10 messages for context
        )

        try:
            # Get recommendation from SommelierService
            # Prepend language instruction to message for LLM context
            enhanced_message = f"{language_instruction}\n\n{message_text}"
            response_text = await self.sommelier.generate_response(
                user_message=enhanced_message,
                user_profile=None,  # TODO: Add user profile support
                conversation_history=history,
            )

            # Get wines with photos to accompany the response
            wines = await self.wine_repo.get_list(limit=3, with_image=True)

        except Exception as e:
            logger.exception("Error getting recommendation: %s", e)
            response_text = ERROR_LLM_UNAVAILABLE if language == "ru" else \
                "Sorry, the recommendation service is temporarily unavailable."
            wines = []

        # Save assistant response
        await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )

        # Update conversation timestamp
        await self.conversation_repo.update_timestamp(conversation)
        await self.db.commit()

        return response_text, wines
