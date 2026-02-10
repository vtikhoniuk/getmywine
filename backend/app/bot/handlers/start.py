"""Handler for /start command."""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.sender import send_fallback_response, send_wine_recommendations
from app.core.database import async_session_maker
from app.services.sommelier import SommelierService
from app.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start command.

    Creates TelegramUser, marks age verified, creates session,
    and sends LLM-generated welcome as 5 messages:
    intro, 3 wines with photos, closing question.
    """
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    language_code = user.language_code or "ru"

    logger.info(
        "Received /start from user %s (%s)",
        telegram_id,
        username or "no username",
    )

    try:
        async with async_session_maker() as db:
            service = TelegramBotService(db)

            # Handle start: create user, session
            telegram_user, conversation, _ = await service.handle_start(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )

            # Generate welcome via LLM
            sommelier = SommelierService(db)
            result = await sommelier.generate_welcome_with_suggestions(
                user_name=first_name,
            )

            wines = result.get("wines", [])
            welcome_text = result["message"]

            # Try structured 5-message format
            sent = await send_wine_recommendations(
                update, welcome_text, wines, language_code
            )

            if not sent:
                # Fallback: single text + separate photos
                await send_fallback_response(update, welcome_text, wines, language_code)

            logger.info(
                "Sent welcome to user %s (%d wines, structured=%s)",
                telegram_id,
                len(wines),
                sent,
            )

    except Exception as e:
        logger.exception("Error handling /start for user %s: %s", telegram_id, e)

        # Send error message (always Russian — service targets RU)
        await update.message.reply_text(
            "К сожалению, произошла ошибка. Попробуйте ещё раз через несколько секунд."
        )


# Handler instance for registration
start_handler = CommandHandler("start", start_command)
