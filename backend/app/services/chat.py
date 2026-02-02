"""Chat service for managing conversations and messages."""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.ai_mock import MockAIService

logger = logging.getLogger(__name__)

# Welcome message content
WELCOME_MESSAGE = """Привет! Я AI-сомелье, и я помогу вам разобраться в мире вина. 🍷

Я могу:
• Подобрать вино под ваши предпочтения
• Рекомендовать вино к блюду или случаю
• Рассказать о сортах винограда и регионах
• Помочь понять винную терминологию

Хотите начать с определения ваших вкусовых предпочтений? Просто напишите мне!"""


class ChatService:
    """Service for chat operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    async def get_or_create_conversation(
        self, user_id: uuid.UUID
    ) -> tuple[Conversation, bool]:
        """
        Get existing conversation or create a new one with welcome message.

        Returns:
            Tuple of (conversation, is_new)
        """
        # Try to get existing conversation
        conversation = await self.conversation_repo.get_by_user_id(user_id)

        if conversation:
            logger.debug("Found existing conversation for user: %s", user_id)
            return conversation, False

        # Create new conversation
        conversation = await self.conversation_repo.create(user_id)
        logger.info("Created new conversation for user: %s", user_id)

        # Add welcome message
        await self._create_welcome_message(conversation.id)

        # Refresh to get the messages
        conversation = await self.conversation_repo.get_by_user_id(user_id)

        return conversation, True

    async def _create_welcome_message(self, conversation_id: uuid.UUID) -> Message:
        """Create the welcome message for a new conversation."""
        message = await self.message_repo.create(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=WELCOME_MESSAGE,
            is_welcome=True,
        )
        logger.debug("Created welcome message for conversation: %s", conversation_id)
        return message

    async def send_message(
        self, user_id: uuid.UUID, content: str
    ) -> tuple[Message, Message]:
        """
        Send a user message and get AI response.

        Args:
            user_id: The user's ID
            content: The message content

        Returns:
            Tuple of (user_message, ai_message)

        Raises:
            ValueError: If conversation doesn't exist
        """
        # Get conversation
        conversation = await self.conversation_repo.get_by_user_id(user_id)
        if not conversation:
            raise ValueError("Conversation not found")

        # Save user message
        user_message = await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
        )
        logger.debug("Saved user message: %s", user_message.id)

        # Generate AI response
        ai_service = MockAIService()
        ai_response_content = await ai_service.generate_response_async(content)

        # Save AI response
        ai_message = await self.message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=ai_response_content,
        )
        logger.debug("Saved AI response: %s", ai_message.id)

        # Update conversation timestamp
        await self.conversation_repo.update_timestamp(conversation)

        return user_message, ai_message
