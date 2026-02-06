"""Handler for free-text messages (recommendations)."""

import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.bot.formatters import format_wine_photo_caption
from app.bot.messages import ERROR_LLM_UNAVAILABLE
from app.bot.utils import detect_language, resolve_image_url, sanitize_telegram_markdown
from app.core.database import async_session_maker
from app.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


async def message_handler_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle free-text messages for wine recommendations.

    All messages that are not commands are treated as recommendation requests.
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

            # Sanitize markdown for Telegram and send
            response_text = sanitize_telegram_markdown(response_text)
            await update.message.reply_text(
                response_text,
                parse_mode="Markdown",
            )

            # Send wine photos individually (best-effort)
            for wine in wines[:3]:
                if not getattr(wine, "image_url", None):
                    continue
                try:
                    url = await resolve_image_url(wine.image_url)
                    await update.message.reply_photo(
                        photo=url,
                        caption=format_wine_photo_caption(wine, language),
                    )
                except Exception as photo_err:
                    logger.warning(
                        "Failed to send photo for %s: %s", wine.name, photo_err,
                    )

            logger.info(
                "Sent recommendation to user %s with %d wines",
                telegram_id,
                len(wines),
            )

    except Exception as e:
        logger.exception("Error handling message for user %s: %s", telegram_id, e)

        # Send error message
        error_message = (
            ERROR_LLM_UNAVAILABLE
            if language == "ru"
            else "Sorry, an error occurred. Please try again."
        )
        await update.message.reply_text(error_message)


# Handler instance for registration
# Matches all text messages that are not commands
message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    message_handler_callback,
)
