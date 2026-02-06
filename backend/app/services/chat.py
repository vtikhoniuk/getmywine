"""Chat service for managing conversations and messages."""
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.wine import Wine
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.wine import WineRepository
from app.services.ai_mock import MockAIService
from app.services.session_context import SessionContextService
from app.services.sommelier import (
    SommelierService,
    detect_event,
    detect_food,
)

logger = logging.getLogger(__name__)

# Fallback welcome message (used if sommelier service fails)
WELCOME_MESSAGE_FALLBACK = """Привет! Я GetMyWine, и я помогу вам разобраться в мире вина.

Я могу:
- Подобрать вино под ваши предпочтения
- Рекомендовать вино к блюду или случаю
- Рассказать о сортах винограда и регионах
- Помочь понять винную терминологию

Хотите начать с определения ваших вкусовых предпочтений? Просто напишите мне!"""


class ChatService:
    """Service for chat operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.wine_repo = WineRepository(db)
        self.sommelier = SommelierService(db)

    async def get_or_create_conversation(
        self,
        user_id: uuid.UUID,
        user_name: Optional[str] = None,
        user_profile: Optional[dict] = None,
    ) -> tuple[Conversation, bool, list[Wine]]:
        """
        Get existing conversation or create a new one with welcome message.

        Args:
            user_id: The user's ID
            user_name: Optional user name for personalization
            user_profile: Optional user taste profile

        Returns:
            Tuple of (conversation, is_new, suggested_wines)
        """
        # Try to get existing conversation
        conversation = await self.conversation_repo.get_by_user_id(user_id)

        if conversation:
            logger.debug("Found existing conversation for user: %s", user_id)
            return conversation, False, []

        # Create new conversation
        conversation = await self.conversation_repo.create(user_id)
        conversation_id = conversation.id  # Save ID before expire_all
        # Flush to ensure conversation is visible to subsequent queries
        await self.db.flush()
        logger.info("Created new conversation for user: %s", user_id)

        # Add proactive welcome message with wine suggestions
        _, wines = await self._create_welcome_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_name=user_name,
            user_profile=user_profile,
        )

        # Save wine IDs before expire_all (wines will be expired too)
        wine_ids = [w.id for w in wines]

        # Flush to ensure message is visible for refresh
        await self.db.flush()

        # Expire cached objects to force fresh load with messages
        self.db.expire_all()

        # Refresh to get the messages
        conversation = await self.conversation_repo.get_by_user_id(user_id)

        # Reload wines after expire_all
        wines = await self.wine_repo.get_by_ids(wine_ids) if wine_ids else []

        return conversation, True, wines

    async def create_new_session(
        self,
        user_id: uuid.UUID,
        user_name: Optional[str] = None,
        user_profile: Optional[dict] = None,
    ) -> tuple[Conversation, list[Wine]]:
        """
        Create a new session, closing any existing active session.

        Used for "Новый диалог" button - always creates a fresh session.

        Args:
            user_id: The user's ID
            user_name: Optional user name for personalization
            user_profile: Optional user taste profile

        Returns:
            Tuple of (conversation, suggested_wines)
        """
        # Close any existing active session
        active_session = await self.conversation_repo.get_active_by_user_id(user_id)
        if active_session:
            await self.conversation_repo.close_session(active_session)
            logger.info("Closed active session %s for user %s", active_session.id, user_id)

        # Create new conversation
        conversation = await self.conversation_repo.create(user_id)
        conversation_id = conversation.id  # Save ID before expire_all
        logger.info("Created new session %s for user %s", conversation_id, user_id)

        # Add welcome message (with cross-session context)
        _, wines = await self._create_welcome_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_name=user_name,
            user_profile=user_profile,
        )

        # Save wine IDs before expire_all (wines will be expired too)
        wine_ids = [w.id for w in wines]

        # Flush to ensure message is visible for refresh
        await self.db.flush()

        # Expire cached objects to force fresh load with messages
        self.db.expire_all()

        # Refresh to get the messages
        conversation = await self.conversation_repo.get_by_id(
            conversation_id, user_id=user_id
        )

        # Reload wines after expire_all
        wines = await self.wine_repo.get_by_ids(wine_ids) if wine_ids else []

        return conversation, wines

    async def _create_welcome_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        user_name: Optional[str] = None,
        user_profile: Optional[dict] = None,
    ) -> tuple[Message, list[Wine]]:
        """
        Create proactive welcome message with wine suggestions.

        Uses SommelierService to generate contextual suggestions based on:
        - Current season
        - Upcoming holidays
        - Day of week / time of day
        - User profile (if available)
        - Cross-session context from previous conversations

        Returns:
            Tuple of (message, suggested_wines)
        """
        wines: list[Wine] = []
        try:
            # Build cross-session context from previous conversations
            context_service = SessionContextService(self.db)
            cross_session_context = await context_service.build_cross_session_context(
                user_id=user_id,
                exclude_session_id=conversation_id,  # Exclude current session
            )

            if cross_session_context.total_sessions > 0:
                logger.info(
                    "Built cross-session context: %d sessions, %d recent wines",
                    cross_session_context.total_sessions,
                    len(cross_session_context.recent_wines),
                )

            # Generate proactive welcome with 3 wine suggestions
            result = await self.sommelier.generate_welcome_with_suggestions(
                user_profile=user_profile,
                user_name=user_name,
                cross_session_context=cross_session_context,
            )
            welcome_content = result["message"]
            wines = result.get("wines", [])
            logger.info(
                "Generated proactive welcome with %d suggestions",
                len(wines),
            )
        except Exception as e:
            # Fallback to static message if sommelier fails
            logger.warning("Sommelier service failed, using fallback: %s", e)
            welcome_content = WELCOME_MESSAGE_FALLBACK

        message = await self.message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=welcome_content,
            is_welcome=True,
        )
        logger.debug("Created welcome message for conversation: %s", conversation_id)
        return message, wines

    async def send_message(
        self,
        user_id: uuid.UUID,
        content: str,
        user_profile: Optional[dict] = None,
    ) -> tuple[Message, Message]:
        """
        Send a user message and get AI response with conversation history.

        Detects events/food in user message and generates contextual response.
        Includes conversation history for better context understanding.

        Args:
            user_id: The user's ID
            content: The message content
            user_profile: Optional user taste profile for personalization

        Returns:
            Tuple of (user_message, ai_message)

        Raises:
            ValueError: If conversation doesn't exist
        """
        # Get conversation
        conversation = await self.conversation_repo.get_by_user_id(user_id)
        if not conversation:
            raise ValueError("Conversation not found")

        # Get conversation history BEFORE saving new message
        # Limit to last 10 messages for LLM context
        history = await self._get_conversation_history(conversation.id, limit=10)

        # Save user message
        user_message = await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
        )
        logger.debug("Saved user message: %s", user_message.id)

        # Detect context from user message
        detected_event = detect_event(content)
        detected_food = detect_food(content)

        # Generate AI response with context and history
        ai_response_content = await self._generate_contextual_response(
            user_id=user_id,
            conversation_id=conversation.id,
            user_message=content,
            detected_event=detected_event,
            detected_food=detected_food,
            user_profile=user_profile,
            conversation_history=history,
        )

        # Save AI response
        ai_message = await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=ai_response_content,
        )
        logger.debug("Saved AI response: %s", ai_message.id)

        # Update conversation timestamp
        await self.conversation_repo.update_timestamp(conversation)

        # Auto-generate session title on first exchange (if not already set)
        await self._maybe_generate_session_title(
            conversation=conversation,
            user_message=content,
            ai_response=ai_response_content,
        )

        return user_message, ai_message

    async def _maybe_generate_session_title(
        self,
        conversation,
        user_message: str,
        ai_response: str,
    ) -> None:
        """
        Generate session title if this is the first non-welcome exchange.

        Conditions for title generation:
        - Conversation has no title yet
        - This is the first user message (only welcome + user + ai = 3 messages)

        Title generation is fire-and-forget to not block the response.
        """
        try:
            # Skip if already has title
            if conversation.title:
                return

            # Check if LLM is configured before doing any work
            from app.services.session_naming import get_session_naming_service
            naming_service = get_session_naming_service()

            if not naming_service.is_llm_configured():
                # No LLM configured, use date fallback immediately
                title = naming_service._generate_date_fallback()
            else:
                # Check if this is the first exchange (welcome + user + ai = 3 messages)
                # Need to refresh to get updated message count
                await self.db.refresh(conversation)
                message_count = len(conversation.messages)

                if message_count != 3:
                    # Not the first exchange, skip
                    return

                logger.info(
                    "Triggering session title generation for conversation %s",
                    conversation.id,
                )

                title = await naming_service.generate_session_title(
                    user_message=user_message,
                    ai_response=ai_response,
                )

            # Update conversation title
            await self.conversation_repo.update_title(conversation, title)
            logger.info("Set session title: %s", title)

        except Exception as e:
            # Don't fail the response if naming fails
            logger.warning("Failed to generate session title: %s", e)

    async def _get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get conversation history formatted for LLM.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of messages in format: [{"role": "user"|"assistant", "content": "..."}]
        """
        messages = await self.message_repo.get_history(
            conversation_id=conversation_id,
            limit=limit,
        )

        history = []
        for msg in messages:
            # Skip welcome messages from history (they're part of system prompt)
            if msg.is_welcome:
                continue

            role = "user" if msg.role == MessageRole.USER else "assistant"
            history.append({
                "role": role,
                "content": msg.content,
            })

        return history

    async def _generate_contextual_response(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message: str,
        detected_event: Optional[str],
        detected_food: Optional[str],
        user_profile: Optional[dict],
        conversation_history: Optional[list[dict]] = None,
    ) -> str:
        """
        Generate contextual AI response using LLM or mock.

        Uses SommelierService.generate_response() which:
        - Detects context (events, food, etc.)
        - Gets real calendar events
        - Builds LLM prompt with wine catalog
        - Includes conversation history for context
        - Includes cross-session context to avoid repetition
        - Falls back to mock if LLM unavailable
        """
        # Log detected context for debugging
        if detected_event:
            logger.info("Detected event: %s", detected_event)
        if detected_food:
            logger.info("Detected food: %s", detected_food)
        if conversation_history:
            logger.debug("Using %d messages from history", len(conversation_history))

        try:
            # Build cross-session context
            context_service = SessionContextService(self.db)
            cross_session_context = await context_service.build_cross_session_context(
                user_id=user_id,
                exclude_session_id=conversation_id,
            )

            # Use SommelierService which handles LLM + fallback
            response = await self.sommelier.generate_response(
                user_message=user_message,
                user_profile=user_profile,
                conversation_history=conversation_history,
                cross_session_context=cross_session_context,
            )
            return response

        except Exception as e:
            logger.warning("Sommelier response failed, using basic mock: %s", e)
            ai_service = MockAIService()
            return await ai_service.generate_response_with_context(
                user_message=user_message,
                detected_event=detected_event,
                detected_food=detected_food,
            )
