"""Tests for wine seed data completeness (US3).

Validates that all 50 wines have complete structured data and
normalized names after normalization.
"""

import json
from pathlib import Path

import pytest


VALID_WINE_TYPES = {"red", "white", "rose", "sparkling"}
VALID_SWEETNESS = {"dry", "semi_dry", "semi_sweet", "sweet"}
PREFIXES = ("Вино ", "Игристое вино ", "Шампанское ")


@pytest.fixture
def wines_seed():
    seed_path = Path(__file__).parent.parent.parent / "app" / "data" / "wines_seed.json"
    with open(seed_path, encoding="utf-8") as f:
        return json.load(f)["wines"]


class TestWineSeedCompleteness:
    """Validate that all 50 wines have complete structured data."""

    def test_exactly_50_wines(self, wines_seed):
        assert len(wines_seed) == 50

    def test_name_non_empty_and_normalized(self, wines_seed):
        """Each wine name should be non-empty and not start with a prefix."""
        for i, wine in enumerate(wines_seed):
            name = wine["name"]
            assert isinstance(name, str) and len(name) > 0, (
                f"Wine #{i}: name is empty"
            )
            for prefix in PREFIXES:
                assert not name.startswith(prefix), (
                    f"Wine #{i} '{name}': still has prefix '{prefix.strip()}'"
                )

    def test_producer_non_empty(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert isinstance(wine["producer"], str) and len(wine["producer"]) > 0, (
                f"Wine #{i}: producer is empty"
            )

    def test_country_non_empty(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert isinstance(wine["country"], str) and len(wine["country"]) > 0, (
                f"Wine #{i}: country is empty"
            )

    def test_region_non_empty(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert isinstance(wine["region"], str) and len(wine["region"]) > 0, (
                f"Wine #{i}: region is empty"
            )

    def test_grape_varieties_non_empty_list(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            grapes = wine["grape_varieties"]
            assert isinstance(grapes, list) and len(grapes) > 0, (
                f"Wine #{i}: grape_varieties is empty or not a list"
            )

    def test_wine_type_valid_enum(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert wine["wine_type"] in VALID_WINE_TYPES, (
                f"Wine #{i}: invalid wine_type '{wine['wine_type']}'"
            )

    def test_sweetness_valid_enum(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert wine["sweetness"] in VALID_SWEETNESS, (
                f"Wine #{i}: invalid sweetness '{wine['sweetness']}'"
            )

    def test_price_rub_positive(self, wines_seed):
        for i, wine in enumerate(wines_seed):
            assert isinstance(wine["price_rub"], (int, float)) and wine["price_rub"] > 0, (
                f"Wine #{i}: price_rub must be positive, got {wine['price_rub']}"
            )

    def test_vintage_year_int_or_null(self, wines_seed):
        """vintage_year should be int or null (6 NV wines)."""
        nv_count = 0
        for i, wine in enumerate(wines_seed):
            vy = wine.get("vintage_year")
            if vy is None:
                nv_count += 1
            else:
                assert isinstance(vy, int), (
                    f"Wine #{i}: vintage_year should be int, got {type(vy)}"
                )
                assert 1900 <= vy <= 2030, (
                    f"Wine #{i}: vintage_year {vy} out of range"
                )
        assert nv_count == 6, f"Expected 6 NV wines, got {nv_count}"

    def test_all_names_unique(self, wines_seed):
        names = [w["name"] for w in wines_seed]
        assert len(set(names)) == 50, (
            f"Expected 50 unique names, got {len(set(names))}"
        )
