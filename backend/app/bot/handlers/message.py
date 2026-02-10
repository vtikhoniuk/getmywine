"""Handler for free-text messages (recommendations)."""

import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.bot.messages import ERROR_LLM_UNAVAILABLE
from app.bot.sender import send_fallback_response, send_wine_recommendations
from app.bot.utils import detect_language
from app.core.database import async_session_maker
from app.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


async def message_handler_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle free-text messages for wine recommendations.

    All messages that are not commands are treated as recommendation requests.
    Sends the response as 5 separate messages: intro, 3 wines with photos,
    closing question.
    """
    if not update.effective_user or not update.message or not update.message.text:
        return

    user = update.effective_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name
    language_code = user.language_code or "ru"
    message_text = update.message.text

    logger.info(
        "Received message from user %s: %s",
        telegram_id,
        message_text[:50] + "..." if len(message_text) > 50 else message_text,
    )

    # Detect language for response
    language = detect_language(message_text, language_code)

    try:
        async with async_session_maker() as db:
            service = TelegramBotService(db)

            # Process message and get recommendation
            response_text, wines = await service.process_message(
                telegram_id=telegram_id,
                message_text=message_text,
                telegram_locale=language_code,
                username=username,
                first_name=first_name,
            )

            # Try structured 5-message format
            sent = await send_wine_recommendations(
                update, response_text, wines, language
            )

            if not sent:
                # Fallback: single text + separate photos
                await send_fallback_response(update, response_text, wines, language)

            logger.info(
                "Sent recommendation to user %s (%d wines, structured=%s)",
                telegram_id,
                len(wines),
                sent,
            )

    except Exception as e:
        logger.exception("Error handling message for user %s: %s", telegram_id, e)

        # Send error message (always Russian — service targets RU)
        await update.message.reply_text(ERROR_LLM_UNAVAILABLE)


# Handler instance for registration
# Matches all text messages that are not commands
message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    message_handler_callback,
)
