"""Tests for bot utility functions.

T004: sanitize_telegram_markdown() cases
T005: get_wine_image_path() cases
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.bot.utils import get_wine_image_path, sanitize_telegram_markdown
from app.models.wine import Wine


# ---------------------------------------------------------------------------
# T004: sanitize_telegram_markdown()
# ---------------------------------------------------------------------------


class TestSanitizeTelegramMarkdown:
    """Tests for Markdown sanitization for Telegram v1 parser."""

    def test_heading_to_bold(self):
        """### heading → *heading*."""
        assert sanitize_telegram_markdown("### My Heading") == "*My Heading*"

    def test_double_asterisk_to_single(self):
        """**bold** → *bold*."""
        assert sanitize_telegram_markdown("**bold text**") == "*bold text*"

    def test_plain_text_unchanged(self):
        """Text without markdown passes through unchanged."""
        text = "Just plain text"
        assert sanitize_telegram_markdown(text) == text

    def test_multiple_headings(self):
        """Multiple headings in text are all converted."""
        text = "### First\nSome text\n## Second"
        result = sanitize_telegram_markdown(text)
        assert "*First*" in result
        assert "*Second*" in result

    def test_h1_heading(self):
        """# heading also converts to *heading*."""
        assert sanitize_telegram_markdown("# Title") == "*Title*"


# ---------------------------------------------------------------------------
# T005: get_wine_image_path()
# ---------------------------------------------------------------------------


class TestGetWineImagePath:
    """Tests for resolving wine image_url to local file path."""

    def test_existing_file_returns_path(self, mock_wine, tmp_path):
        """Wine with image_url pointing to existing file → Path."""
        mock_wine.image_url = "/static/images/wines/abc.png"

        # Create actual file in tmp dir to simulate existing image
        images_dir = tmp_path / "images" / "wines"
        images_dir.mkdir(parents=True)
        image_file = images_dir / "abc.png"
        image_file.touch()

        with patch("app.bot.utils._STATIC_DIR", tmp_path):
            result = get_wine_image_path(mock_wine)

        assert result is not None
        assert result == image_file

    def test_none_image_url_returns_none(self, mock_wine_no_image):
        """Wine with image_url=None → None."""
        result = get_wine_image_path(mock_wine_no_image)
        assert result is None

    def test_nonexistent_file_returns_none(self, mock_wine, tmp_path):
        """Wine with image_url pointing to nonexistent file → None."""
        mock_wine.image_url = "/static/images/wines/missing.png"

        with patch("app.bot.utils._STATIC_DIR", tmp_path):
            result = get_wine_image_path(mock_wine)

        assert result is None
