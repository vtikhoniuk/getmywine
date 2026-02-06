"""Telegram bot entry point."""

import asyncio
import logging

from telegram.ext import Application

from app.config import get_settings
import app.models  # noqa: F401 — register all SQLAlchemy mappers

settings = get_settings()

logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Create and configure the Telegram bot application.

    Returns:
        Configured Application instance
    """
    if not settings.telegram_bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Please set it in your environment variables."
        )

    # Build application with token
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Register handlers
    from app.bot.handlers.start import start_handler
    from app.bot.handlers.message import message_handler

    application.add_handler(start_handler)
    application.add_handler(message_handler)  # Must be after command handlers

    # Future handlers (to be added in subsequent tasks):
    # from app.bot.handlers.help import help_handler
    # application.add_handler(help_handler)

    return application


async def run_polling() -> None:
    """Run bot in polling mode."""
    logger.info("Starting Telegram bot in polling mode...")
    application = create_application()

    # Initialize and start
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    # Run until stopped
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


async def run_webhook() -> None:
    """Run bot in webhook mode.

    Note: Webhook mode requires HTTPS endpoint.
    This is for future use when deploying to production.
    """
    if not settings.telegram_webhook_url:
        raise ValueError(
            "TELEGRAM_WEBHOOK_URL is not set. "
            "Required for webhook mode."
        )

    logger.info(
        f"Starting Telegram bot in webhook mode at {settings.telegram_webhook_url}"
    )
    application = create_application()

    # Initialize and start
    await application.initialize()
    await application.start()

    # Set webhook
    await application.bot.set_webhook(
        url=settings.telegram_webhook_url,
        drop_pending_updates=True,
    )

    logger.info("Webhook set. Bot is running.")


def main() -> None:
    """Main entry point for the bot."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    if not settings.enable_telegram_bot:
        logger.info("Telegram bot is disabled. Exiting.")
        return

    if settings.telegram_mode == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
