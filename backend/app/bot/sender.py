"""Shared wine recommendation sending logic.

Extracted from handlers/start.py and handlers/message.py
to eliminate duplication (DRY).
"""

import io
import logging
from pathlib import Path

from PIL import Image
from telegram import InputFile, Update

from app.bot.formatters import format_wine_photo_caption
from app.bot.utils import get_wine_image_path, sanitize_telegram_markdown
from app.config import get_settings
from app.services.sommelier_prompts import parse_structured_response, strip_markdown

logger = logging.getLogger(__name__)

# Target width for Telegram inline photos (px)
_TELEGRAM_PHOTO_WIDTH = 800


def prepare_wine_photo(image_path: Path) -> io.BytesIO:
    """Resize wine bottle image and center on white background.

    Creates a wide image (800px) with white background and the bottle
    centered, so it looks clean in Telegram chat.
    Target height is configured via TELEGRAM_WINE_PHOTO_HEIGHT env var.
    """
    target_height = get_settings().telegram_wine_photo_height
    img = Image.open(image_path).convert("RGBA")

    # Scale to target height, preserving aspect ratio
    scale = target_height / img.height
    new_w = int(img.width * scale)
    new_h = target_height
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Create white canvas: full Telegram width × target height
    canvas = Image.new("RGB", (_TELEGRAM_PHOTO_WIDTH, new_h), (255, 255, 255))

    # Center the bottle horizontally
    x_offset = (_TELEGRAM_PHOTO_WIDTH - new_w) // 2
    canvas.paste(img, (x_offset, 0), mask=img)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def send_wine_recommendations(
    update: Update,
    response_text: str,
    wines: list,
    language: str,
) -> bool:
    """Send structured 5-message wine recommendations.

    Parses the LLM response and, if structured markers are found,
    sends: intro → wine photos → closing.

    Returns True if structured sending succeeded, False to fall back.
    """
    parsed = parse_structured_response(response_text)
    if not parsed.is_structured:
        return False

    # 1. Intro
    await update.message.reply_text(
        sanitize_telegram_markdown(parsed.intro),
        parse_mode="Markdown",
    )

    # 2-4. Wine sections with photos
    for i, wine_text in enumerate(parsed.wines):
        wine = wines[i] if i < len(wines) else None
        image_path = get_wine_image_path(wine) if wine else None

        if image_path:
            caption = strip_markdown(wine_text)[:1024]
            photo_buf = prepare_wine_photo(image_path)
            await update.message.reply_photo(
                photo=InputFile(photo_buf, filename="wine.png"),
                caption=caption,
            )
        else:
            await update.message.reply_text(
                sanitize_telegram_markdown(wine_text),
                parse_mode="Markdown",
            )

    # 5. Closing
    if parsed.closing:
        await update.message.reply_text(
            sanitize_telegram_markdown(parsed.closing),
            parse_mode="Markdown",
        )

    return True


async def send_fallback_response(
    update: Update,
    response_text: str,
    wines: list,
    language: str,
) -> None:
    """Send fallback response: single text + separate wine photos.

    Used when structured parsing fails (is_structured=False).
    """
    await update.message.reply_text(
        sanitize_telegram_markdown(response_text),
        parse_mode="Markdown",
    )

    for wine in wines:
        image_path = get_wine_image_path(wine)
        if not image_path:
            continue
        caption = format_wine_photo_caption(wine, language)
        photo_buf = prepare_wine_photo(image_path)
        await update.message.reply_photo(
            photo=InputFile(photo_buf, filename="wine.png"),
            caption=caption,
        )
