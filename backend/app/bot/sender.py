"""Shared wine recommendation sending logic.

Extracted from handlers/start.py and handlers/message.py
to eliminate duplication (DRY).
"""

import io
import json
import logging
import re
from pathlib import Path

from PIL import Image
from telegram import InputFile, Update

from app.bot.formatters import format_wine_photo_caption
from app.bot.utils import get_wine_image_path, sanitize_telegram_markdown
from app.config import get_settings
from app.services.sommelier_prompts import parse_structured_response, strip_markdown

# Pattern to strip [INTRO], [/INTRO], [WINE:1], [/WINE:1], [CLOSING], [/CLOSING], [GUARD:*]
_SECTION_MARKERS_RE = re.compile(
    r"\[/?(?:INTRO|WINE:\d+|CLOSING|GUARD:\w+)\]", re.IGNORECASE
)

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
    logger.debug(
        "Structured parse result: is_structured=%s, wines=%d, intro_len=%d, closing_len=%d, text_start=%r",
        parsed.is_structured,
        len(parsed.wines),
        len(parsed.intro),
        len(parsed.closing),
        response_text[:150],
    )
    if not parsed.is_structured:
        return False

    # No wine sections → combine intro + closing into a single message
    if not parsed.wines:
        parts = [parsed.intro]
        if parsed.closing:
            parts.append(parsed.closing)
        combined = "\n\n".join(parts)
        await update.message.reply_text(
            sanitize_telegram_markdown(combined),
            parse_mode="Markdown",
        )
        return True

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
            caption = sanitize_telegram_markdown(wine_text)[:1024]
            photo_buf = prepare_wine_photo(image_path)
            await update.message.reply_photo(
                photo=InputFile(photo_buf, filename="wine.png"),
                caption=caption,
                parse_mode="Markdown",
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


def _extract_and_render_json(text: str) -> str | None:
    """Try to extract JSON from text and render it as human-readable message.

    Returns rendered text or None if no valid JSON found.
    """
    stripped = text.strip()

    # Try direct parse
    json_str = None
    if stripped.startswith("{") and stripped.endswith("}"):
        json_str = stripped
    else:
        # Try markdown code fences
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
        if fence_match:
            json_str = fence_match.group(1).strip()
        else:
            # Find first { to last }
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end > start:
                json_str = stripped[start:end + 1]

    if not json_str:
        return None

    # Try parse_structured_response (Pydantic-backed)
    parsed = parse_structured_response(json_str)
    if parsed.is_structured:
        parts = [p for p in [parsed.intro] + parsed.wines + [parsed.closing] if p]
        return "\n\n".join(parts)

    # Last resort: raw json.loads
    try:
        data = json.loads(json_str)
        if isinstance(data, dict) and "intro" in data:
            parts = [data.get("intro", "")]
            for w in data.get("wines", []):
                if isinstance(w, dict) and w.get("description"):
                    parts.append(w["description"])
            if data.get("closing"):
                parts.append(data["closing"])
            return "\n\n".join(p for p in parts if p)
    except (json.JSONDecodeError, TypeError):
        pass

    return None


async def send_fallback_response(
    update: Update,
    response_text: str,
    wines: list,
    language: str,
) -> None:
    """Send fallback response: single text + separate wine photos.

    Used when structured parsing fails (is_structured=False).
    """
    # Safety: never display raw JSON to user — render it first
    rendered = _extract_and_render_json(response_text)
    if rendered:
        response_text = rendered

    # Strip any leftover section markers so tags aren't visible to user
    clean_text = _SECTION_MARKERS_RE.sub("", response_text).strip()
    if not clean_text:
        logger.warning("Fallback response text is empty after cleanup, using error message")
        from app.bot.messages import ERROR_LLM_UNAVAILABLE
        clean_text = ERROR_LLM_UNAVAILABLE
    await update.message.reply_text(
        sanitize_telegram_markdown(clean_text),
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
