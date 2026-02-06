"""Handler for /start command."""

import logging

from telegram import InputMediaPhoto, Update
from telegram.ext import CommandHandler, ContextTypes

from app.bot.formatters import format_welcome_message, format_wine_photo_caption
from app.bot.utils import resolve_image_url, sanitize_telegram_markdown
from app.core.database import async_session_maker
from app.services.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start command.

    Creates TelegramUser, marks age verified, creates session,
    and sends welcome message with wine suggestions.
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

            # Handle start: create user, session, get wines
            telegram_user, conversation, wines = await service.handle_start(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )

            # Determine response language
            response_language = "ru" if language_code.startswith("ru") else "en"
            if language_code.startswith("ru") or not language_code:
                response_language = "ru"

            # Format and send welcome message
            welcome_text = format_welcome_message(
                first_name=first_name,
                wines=wines,
                language=response_language,
            )
            welcome_text = sanitize_telegram_markdown(welcome_text)

            await update.message.reply_text(
                welcome_text,
                parse_mode="Markdown",
            )

            # Send wine photos as an album (best-effort)
            wine_photos = [
                wine for wine in wines
                if getattr(wine, "image_url", None)
            ]
            if wine_photos:
                try:
                    media = []
                    for wine in wine_photos:
                        url = await resolve_image_url(wine.image_url)
                        media.append(InputMediaPhoto(
                            media=url,
                            caption=format_wine_photo_caption(wine, response_language),
                        ))
                    await update.message.reply_media_group(media=media)
                except Exception as photo_err:
                    logger.warning("Failed to send wine photos: %s", photo_err)

            logger.info(
                "Sent welcome message to user %s with %d wines",
                telegram_id,
                len(wines),
            )

    except Exception as e:
        logger.exception("Error handling /start for user %s: %s", telegram_id, e)

        # Send error message
        error_message = (
            "К сожалению, произошла ошибка. Попробуйте ещё раз через несколько секунд."
            if (language_code or "").startswith("ru")
            else "Sorry, an error occurred. Please try again in a few seconds."
        )
        await update.message.reply_text(error_message)


# Handler instance for registration
start_handler = CommandHandler("start", start_command)
