"""Utility functions for Telegram bot."""

import re
from pathlib import Path
from typing import Optional

from app.models.wine import Wine


def sanitize_telegram_markdown(text: str) -> str:
    """Sanitize markdown for Telegram's legacy Markdown parser.

    Telegram parse_mode="Markdown" (v1) only supports:
      *bold*, _italic_, `code`, ```pre```, [link](url)

    This function converts unsupported markdown:
      - ### heading  →  *heading*
      - **bold**     →  *bold*
    """
    # Convert ATX headers (# ## ### etc.) to bold
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Convert **double-asterisk bold** to *single-asterisk bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Replace backticks — Telegram Markdown v1 treats ` as inline code.
    # Wine names like "Barbera d`Asti" have unpaired backticks that break parsing.
    # Use visually identical apostrophe instead.
    text = text.replace("`", "'")

    return text


async def resolve_image_url(url: str) -> str:
    """Resolve redirect-based image URLs to direct URLs.

    Telegram's sendPhoto fails on URLs that require multiple HTTP
    redirects (e.g. Wikimedia Special:FilePath returns 302 chains).
    Seed data was updated to use direct upload.wikimedia.org URLs,
    but this handles any remaining redirect-based URLs at runtime.
    """
    if "Special:FilePath" not in url and "Special:Redirect" not in url:
        return url

    import httpx

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=5.0,
            headers={"User-Agent": "GetMyWineBot/1.0"},
        ) as client:
            resp = await client.head(url)
            if resp.status_code == 200:
                return str(resp.url)
    except Exception:
        pass
    return url


_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def get_wine_image_path(wine: Wine) -> Optional[Path]:
    """Resolve wine's image_url to a local file path.

    Args:
        wine: Wine model instance

    Returns:
        Path to the image file, or None if not available
    """
    if not wine.image_url:
        return None
    # image_url example: /static/images/wines/39a5ce9f58.png
    rel = wine.image_url.lstrip("/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]
    path = _STATIC_DIR / rel
    return path if path.exists() else None


def detect_language(message_text: str, telegram_locale: str | None = None) -> str:
    """Detect language from message text, fallback to Telegram locale.

    Bot always responds in Russian — wine names in Latin script
    should not switch the response language.

    Args:
        message_text: The message text to analyze
        telegram_locale: User's Telegram language_code (e.g., "ru", "en")

    Returns:
        Language code: always "ru" (bot targets Russian-speaking audience)
    """
    return "ru"


def get_language_instruction(language: str) -> str:
    """Get LLM language instruction based on detected language.

    Args:
        language: Language code ("ru" or "en")

    Returns:
        Instruction string for LLM
    """
    if language == "ru":
        return "Отвечай на русском языке."
    return "Respond in English."
