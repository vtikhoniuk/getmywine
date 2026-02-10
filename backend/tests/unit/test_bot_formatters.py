"""Tests for bot formatters.

T006: format_wine_photo_caption() cases
T007: get_sweetness_label() cases
"""

import pytest

from app.bot.formatters import format_wine_photo_caption, get_sweetness_label
from app.models.wine import Sweetness


# ---------------------------------------------------------------------------
# T006: format_wine_photo_caption()
# ---------------------------------------------------------------------------


class TestFormatWinePhotoCaption:
    """Tests for plain-text photo caption formatting."""

    def test_all_fields_present(self, mock_wine):
        """Wine with all fields → 4-line caption."""
        caption = format_wine_photo_caption(mock_wine, "ru")

        assert mock_wine.name in caption
        assert mock_wine.region in caption
        assert mock_wine.country in caption
        assert "Cabernet Sauvignon" in caption
        assert "сухое" in caption
        assert "₽" in caption

    def test_without_grape_varieties(self, mock_wine):
        """Wine without grapes → 3-line caption (no grape line)."""
        mock_wine.grape_varieties = []
        caption = format_wine_photo_caption(mock_wine, "ru")

        lines = caption.strip().split("\n")
        assert len(lines) == 3  # name, region, sweetness+price

    def test_plain_text_no_markdown(self, mock_wine):
        """Caption must be plain text without any markdown."""
        caption = format_wine_photo_caption(mock_wine, "ru")

        assert "**" not in caption
        assert "*" not in caption or caption.count("*") == 0

    def test_english_sweetness(self, mock_wine):
        """English locale should use English sweetness label."""
        caption = format_wine_photo_caption(mock_wine, "en")

        assert "dry" in caption


# ---------------------------------------------------------------------------
# T007: get_sweetness_label()
# ---------------------------------------------------------------------------


class TestGetSweetnessLabel:
    """Tests for localized sweetness labels."""

    def test_dry_russian(self):
        assert get_sweetness_label(Sweetness.DRY, "ru") == "сухое"

    def test_dry_english(self):
        assert get_sweetness_label(Sweetness.DRY, "en") == "dry"

    def test_semi_dry_russian(self):
        assert get_sweetness_label(Sweetness.SEMI_DRY, "ru") == "полусухое"

    def test_semi_dry_english(self):
        assert get_sweetness_label(Sweetness.SEMI_DRY, "en") == "semi-dry"

    def test_sweet_russian(self):
        assert get_sweetness_label(Sweetness.SWEET, "ru") == "сладкое"

    def test_sweet_english(self):
        assert get_sweetness_label(Sweetness.SWEET, "en") == "sweet"

    def test_semi_sweet_russian(self):
        assert get_sweetness_label(Sweetness.SEMI_SWEET, "ru") == "полусладкое"

    def test_semi_sweet_english(self):
        assert get_sweetness_label(Sweetness.SEMI_SWEET, "en") == "semi-sweet"
