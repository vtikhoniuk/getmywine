"""Tests for wine name normalization utility.

Covers all 4 patterns (A, B, C, D) and edge cases per research.md R-005.
"""

import json
from pathlib import Path

import pytest

from app.utils.wine_normalization import normalize_wine_name


# ---------------------------------------------------------------------------
# Pattern A: {prefix} {name}, {producer}, {year} — 36 wines
# ---------------------------------------------------------------------------

class TestPatternA:
    """Standard pattern: prefix + name + producer + year."""

    def test_standard_red_wine(self):
        result = normalize_wine_name(
            "Вино Malbec, Luigi Bosca, 2024", "Luigi Bosca", 2024
        )
        assert result == "Malbec"

    def test_russian_name(self):
        result = normalize_wine_name(
            "Вино Петрикор Красное, Шумринка, 2023", "Шумринка", 2023
        )
        assert result == "Петрикор Красное"

    def test_compound_name(self):
        result = normalize_wine_name(
            "Вино Chianti Castiglioni, Frescobaldi, 2024", "Frescobaldi", 2024
        )
        assert result == "Chianti Castiglioni"

    def test_name_with_special_chars(self):
        result = normalize_wine_name(
            "Вино Clarendelle by Haut-Brion Rouge, Clarendelle, 2022",
            "Clarendelle",
            2022,
        )
        assert result == "Clarendelle by Haut-Brion Rouge"

    def test_name_with_dash(self):
        result = normalize_wine_name(
            "Вино Renome Каберне Фран – Мерло, Фанагория, 2023",
            "Фанагория",
            2023,
        )
        assert result == "Renome Каберне Фран – Мерло"


# ---------------------------------------------------------------------------
# Pattern B: {prefix} {name_with_producer}, {year} — 8 wines
# ---------------------------------------------------------------------------

class TestPatternB:
    """Producer embedded in name without comma separation."""

    def test_producer_in_name(self):
        result = normalize_wine_name(
            "Вино Barbera d`Asti Luca Bosio, 2024", "Luca Bosio", 2024
        )
        assert result == "Barbera d`Asti Luca Bosio"

    def test_long_producer_name(self):
        result = normalize_wine_name(
            "Вино Hacienda Lopez de Haro Reserva, 2019",
            "Hacienda Lopez de Haro",
            2019,
        )
        assert result == "Hacienda Lopez de Haro Reserva"

    def test_russian_producer_in_name(self):
        result = normalize_wine_name(
            "Вино Шумринка розовое, 2023", "Шумринка", 2023
        )
        assert result == "Шумринка розовое"


# ---------------------------------------------------------------------------
# Pattern C: {prefix} {name}, {producer} — no year (4 wines)
# ---------------------------------------------------------------------------

class TestPatternC:
    """No vintage year, producer separated by comma."""

    def test_no_year_with_producer(self):
        result = normalize_wine_name(
            "Вино Crab & More White Zinfandel, Bronco Wine Company",
            "Bronco Wine Company",
            None,
        )
        assert result == "Crab & More White Zinfandel"

    def test_no_year_sparkling(self):
        result = normalize_wine_name(
            "Игристое вино Prosecco Superiore Valdobbiadene Quartese Brut, Ruggeri",
            "Ruggeri",
            None,
        )
        assert result == "Prosecco Superiore Valdobbiadene Quartese Brut"


# ---------------------------------------------------------------------------
# Pattern D: {prefix} {name_with_producer} — no year, no comma (2 wines)
# ---------------------------------------------------------------------------

class TestPatternD:
    """No vintage year, producer embedded in name."""

    def test_no_year_producer_embedded(self):
        result = normalize_wine_name(
            "Игристое вино Bruni Prosecco Brut", "Bruni", None
        )
        assert result == "Bruni Prosecco Brut"

    def test_no_year_producer_embedded_2(self):
        result = normalize_wine_name(
            "Игристое вино Santa Carolina Brut", "Santa Carolina", None
        )
        assert result == "Santa Carolina Brut"


# ---------------------------------------------------------------------------
# Edge Cases (research.md R-005)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Special cases from the wine catalog."""

    def test_trailing_space_wine_39(self):
        """Wine #39: trailing space after name should be trimmed."""
        result = normalize_wine_name(
            "Вино Cielo Pinot Grigio Rose , 2024", "Cielo", 2024
        )
        assert result == "Cielo Pinot Grigio Rose"

    def test_trailing_period_wine_26(self):
        """Wine #26: trailing period is part of the name."""
        result = normalize_wine_name(
            "Вино Ballet Blanc. Красная Горка., Галицкий и Галицкий, 2024",
            "Галицкий и Галицкий",
            2024,
        )
        assert result == "Ballet Blanc. Красная Горка."

    def test_gift_packaging_wine_45(self):
        """Wine #45: 'в подарочной упаковке' stays as part of the name."""
        result = normalize_wine_name(
            "Шампанское Le Black Creation Brut в подарочной упаковке, Lanson",
            "Lanson",
            None,
        )
        assert result == "Le Black Creation Brut в подарочной упаковке"

    def test_champagne_prefix(self):
        """Only one wine has Шампанское prefix — ensure it's stripped."""
        result = normalize_wine_name(
            "Шампанское Le Black Creation Brut в подарочной упаковке, Lanson",
            "Lanson",
            None,
        )
        assert not result.startswith("Шампанское")

    def test_sparkling_prefix(self):
        """Игристое вино prefix stripped."""
        result = normalize_wine_name(
            "Игристое вино Bruni Asti, 2024", "Bruni", 2024
        )
        assert result == "Bruni Asti"
        assert not result.startswith("Игристое")


# ---------------------------------------------------------------------------
# Full Catalog Validation
# ---------------------------------------------------------------------------

class TestFullCatalog:
    """Validate normalization against the complete wine catalog."""

    @pytest.fixture
    def wines_seed(self):
        seed_path = Path(__file__).parent.parent.parent / "app" / "data" / "wines_seed.json"
        with open(seed_path, encoding="utf-8") as f:
            return json.load(f)["wines"]

    def test_all_50_wines_loaded(self, wines_seed):
        assert len(wines_seed) == 50

    def test_no_prefixes_after_normalization(self, wines_seed):
        """No normalized name should start with any category prefix."""
        prefixes = ("Вино ", "Игристое вино ", "Шампанское ")
        for i, wine in enumerate(wines_seed):
            normalized = normalize_wine_name(
                wine["name"], wine["producer"], wine.get("vintage_year")
            )
            for prefix in prefixes:
                assert not normalized.startswith(prefix), (
                    f"Wine #{i} '{normalized}' still has prefix '{prefix.strip()}'"
                )

    def test_all_50_names_unique_after_normalization(self, wines_seed):
        """All 50 normalized names must be unique."""
        normalized_names = [
            normalize_wine_name(
                w["name"], w["producer"], w.get("vintage_year")
            )
            for w in wines_seed
        ]
        assert len(set(normalized_names)) == 50, (
            f"Expected 50 unique names, got {len(set(normalized_names))}"
        )

    def test_all_names_non_empty(self, wines_seed):
        """No normalized name should be empty."""
        for i, wine in enumerate(wines_seed):
            normalized = normalize_wine_name(
                wine["name"], wine["producer"], wine.get("vintage_year")
            )
            assert len(normalized) > 0, f"Wine #{i} has empty normalized name"

    def test_no_leading_trailing_whitespace(self, wines_seed):
        """No normalized name should have leading/trailing whitespace."""
        for i, wine in enumerate(wines_seed):
            normalized = normalize_wine_name(
                wine["name"], wine["producer"], wine.get("vintage_year")
            )
            assert normalized == normalized.strip(), (
                f"Wine #{i} '{normalized}' has whitespace"
            )
