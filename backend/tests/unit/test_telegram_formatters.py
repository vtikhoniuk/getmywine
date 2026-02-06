"""Unit tests for Telegram wine card formatters.

T028 [US3]: Tests for wine card formatter per TDD requirement.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.models.wine import Wine, WineType, Sweetness, PriceRange


def create_mock_wine(
    name: str = "Test Wine",
    region: str = "Bordeaux",
    country: str = "France",
    grape_varieties: list = None,
    sweetness: Sweetness = Sweetness.DRY,
    acidity: int = 3,
    tannins: int = 4,
    body: int = 4,
    price_rub: float = 4000.0,
    wine_type: WineType = WineType.RED,
) -> Wine:
    """Create a mock Wine for testing."""
    wine = MagicMock(spec=Wine)
    wine.id = uuid.uuid4()
    wine.name = name
    wine.region = region
    wine.country = country
    wine.grape_varieties = grape_varieties or ["Cabernet Sauvignon", "Merlot"]
    wine.sweetness = sweetness
    wine.acidity = acidity
    wine.tannins = tannins
    wine.body = body
    wine.price_rub = price_rub
    wine.wine_type = wine_type
    wine.description = "A wonderful wine."
    return wine


class TestWineCardFormatter:
    """Tests for wine card formatting."""

    def test_formats_wine_name(self):
        """Should include wine name in bold."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine(name="Château Margaux 2015")
        result = format_wine_card(wine)

        assert "*Château Margaux 2015*" in result

    def test_formats_region_and_country(self):
        """Should include region and country."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine(region="Bordeaux", country="France")
        result = format_wine_card(wine)

        assert "Bordeaux" in result
        assert "France" in result

    def test_formats_grape_varieties(self):
        """Should include grape varieties."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine(grape_varieties=["Cabernet Sauvignon", "Merlot"])
        result = format_wine_card(wine)

        assert "Cabernet Sauvignon" in result

    def test_formats_sweetness(self):
        """Should include sweetness level."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine(sweetness=Sweetness.DRY)
        result = format_wine_card(wine, language="ru")

        assert "сухое" in result.lower() or "Сладость" in result

    def test_formats_price(self):
        """Should include price."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine(price_rub=28000.0)
        result = format_wine_card(wine)

        assert "28000" in result


class TestCharacteristicVisualizer:
    """Tests for characteristic bar visualization."""

    def test_full_bar(self):
        """Should show 5 filled blocks for max value."""
        from app.bot.formatters import format_characteristic_bar

        result = format_characteristic_bar(5)

        assert result.count("\u2B1B") == 5
        assert result.count("\u2B1C") == 0

    def test_empty_bar(self):
        """Should show 5 empty blocks for min value."""
        from app.bot.formatters import format_characteristic_bar

        result = format_characteristic_bar(0)

        assert result.count("\u2B1B") == 0
        assert result.count("\u2B1C") == 5

    def test_partial_bar(self):
        """Should show mix of filled and empty for middle values."""
        from app.bot.formatters import format_characteristic_bar

        result = format_characteristic_bar(3)

        assert result.count("\u2B1B") == 3
        assert result.count("\u2B1C") == 2

    def test_bar_length_always_five(self):
        """Bar should always be 5 characters total."""
        from app.bot.formatters import format_characteristic_bar

        for value in range(6):
            result = format_characteristic_bar(value)
            total = result.count("\u2B1B") + result.count("\u2B1C")
            assert total == 5


class TestSweetnessLabels:
    """Tests for sweetness label formatting."""

    def test_dry_in_russian(self):
        """Should translate 'dry' to Russian."""
        from app.bot.formatters import get_sweetness_label

        assert get_sweetness_label(Sweetness.DRY, "ru") == "сухое"

    def test_dry_in_english(self):
        """Should keep 'dry' in English."""
        from app.bot.formatters import get_sweetness_label

        assert get_sweetness_label(Sweetness.DRY, "en") == "dry"

    def test_semi_sweet_in_russian(self):
        """Should translate 'semi_sweet' to Russian."""
        from app.bot.formatters import get_sweetness_label

        assert get_sweetness_label(Sweetness.SEMI_SWEET, "ru") == "полусладкое"


class TestLanguageSupport:
    """Tests for multi-language support in formatting."""

    def test_russian_labels(self):
        """Should use Russian labels when language is 'ru'."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine()
        result = format_wine_card(wine, language="ru")

        # Should have Russian characteristic labels
        assert "Характеристики" in result or "Сладость" in result

    def test_english_labels(self):
        """Should use English labels when language is 'en'."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine()
        result = format_wine_card(wine, language="en")

        # Should have English characteristic labels
        assert "Characteristics" in result or "Sweetness" in result


class TestRecommendationReason:
    """Tests for recommendation reason formatting."""

    def test_includes_reason_when_provided(self):
        """Should include recommendation reason in card."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine()
        reason = "This wine pairs perfectly with steak."
        result = format_wine_card(wine, reason=reason)

        assert "steak" in result.lower() or reason in result

    def test_omits_reason_when_empty(self):
        """Should not add empty reason section."""
        from app.bot.formatters import format_wine_card

        wine = create_mock_wine()
        result = format_wine_card(wine, reason="")

        # Should not have empty "Why this wine" section
        assert "Почему это вино:\n\n" not in result
