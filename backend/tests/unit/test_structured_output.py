"""Tests for structured output: Pydantic models, JSON parsing, text rendering.

T003: WineRecommendation and SommelierResponse Pydantic models
T004: parse_structured_response() handling JSON and legacy markers
T005: render_response_text() helper
"""

import json

import pytest


# =============================================================================
# T003: Pydantic model tests
# =============================================================================


class TestWineRecommendation:
    """Tests for WineRecommendation Pydantic model."""

    def test_valid_wine_recommendation(self):
        from app.services.sommelier_prompts import WineRecommendation

        wine = WineRecommendation(
            wine_name="Chateau Margaux 2018",
            description="Классическое бордо с мощными танинами.",
        )
        assert wine.wine_name == "Chateau Margaux 2018"
        assert wine.description == "Классическое бордо с мощными танинами."

    def test_wine_recommendation_from_json(self):
        from app.services.sommelier_prompts import WineRecommendation

        raw = '{"wine_name": "Barolo DOCG 2019", "description": "Итальянская классика."}'
        wine = WineRecommendation.model_validate_json(raw)
        assert wine.wine_name == "Barolo DOCG 2019"

    def test_wine_recommendation_missing_name_raises(self):
        from app.services.sommelier_prompts import WineRecommendation

        with pytest.raises(Exception):
            WineRecommendation(wine_name="", description="Some desc")

    def test_wine_recommendation_missing_description_raises(self):
        from app.services.sommelier_prompts import WineRecommendation

        with pytest.raises(Exception):
            WineRecommendation(wine_name="Wine Name", description="")


class TestSommelierResponse:
    """Tests for SommelierResponse Pydantic model."""

    def test_valid_recommendation_response(self):
        from app.services.sommelier_prompts import SommelierResponse

        resp = SommelierResponse(
            response_type="recommendation",
            intro="Вот подборка!",
            wines=[
                {"wine_name": "Wine A", "description": "Desc A"},
                {"wine_name": "Wine B", "description": "Desc B"},
                {"wine_name": "Wine C", "description": "Desc C"},
            ],
            closing="Что-нибудь ещё?",
            guard_type=None,
        )
        assert resp.response_type == "recommendation"
        assert len(resp.wines) == 3
        assert resp.wines[0].wine_name == "Wine A"
        assert resp.guard_type is None

    def test_valid_informational_response(self):
        from app.services.sommelier_prompts import SommelierResponse

        resp = SommelierResponse(
            response_type="informational",
            intro="Танины — это полифенолы.",
            wines=[],
            closing="Хотите подобрать вино?",
            guard_type=None,
        )
        assert resp.response_type == "informational"
        assert resp.wines == []

    def test_valid_off_topic_response(self):
        from app.services.sommelier_prompts import SommelierResponse

        resp = SommelierResponse(
            response_type="off_topic",
            intro="Я специализируюсь на вине!",
            wines=[],
            closing="Давайте подберём вино?",
            guard_type="off_topic",
        )
        assert resp.response_type == "off_topic"
        assert resp.guard_type == "off_topic"

    def test_null_guard_type_allowed(self):
        from app.services.sommelier_prompts import SommelierResponse

        resp = SommelierResponse(
            response_type="recommendation",
            intro="Intro",
            wines=[{"wine_name": "W", "description": "D"}],
            closing="Closing",
            guard_type=None,
        )
        assert resp.guard_type is None

    def test_0_wines_valid(self):
        from app.services.sommelier_prompts import SommelierResponse

        resp = SommelierResponse(
            response_type="informational",
            intro="Info",
            wines=[],
            closing="Ask me",
            guard_type=None,
        )
        assert len(resp.wines) == 0

    def test_3_wines_valid(self):
        from app.services.sommelier_prompts import SommelierResponse

        wines = [
            {"wine_name": f"Wine {i}", "description": f"Desc {i}"}
            for i in range(3)
        ]
        resp = SommelierResponse(
            response_type="recommendation",
            intro="Here",
            wines=wines,
            closing="More?",
            guard_type=None,
        )
        assert len(resp.wines) == 3

    def test_invalid_response_type_raises(self):
        from app.services.sommelier_prompts import SommelierResponse

        with pytest.raises(Exception):
            SommelierResponse(
                response_type="unknown_type",
                intro="Intro",
                wines=[],
                closing="Closing",
                guard_type=None,
            )

    def test_model_validate_json_full(self):
        from app.services.sommelier_prompts import SommelierResponse

        raw = json.dumps(
            {
                "response_type": "recommendation",
                "intro": "Отличный выбор!",
                "wines": [
                    {
                        "wine_name": "Chateau Margaux 2018",
                        "description": "Классическое бордо.",
                    }
                ],
                "closing": "Какой ценовой диапазон?",
                "guard_type": None,
            }
        )
        resp = SommelierResponse.model_validate_json(raw)
        assert resp.response_type == "recommendation"
        assert resp.wines[0].wine_name == "Chateau Margaux 2018"

    def test_invalid_json_raises(self):
        from app.services.sommelier_prompts import SommelierResponse

        with pytest.raises(Exception):
            SommelierResponse.model_validate_json("{not valid json")


class TestSommelierResponseSchema:
    """Tests for SOMMELIER_RESPONSE_SCHEMA constant."""

    def test_schema_exists_and_has_correct_structure(self):
        from app.services.sommelier_prompts import SOMMELIER_RESPONSE_SCHEMA

        assert SOMMELIER_RESPONSE_SCHEMA["type"] == "json_schema"
        assert "json_schema" in SOMMELIER_RESPONSE_SCHEMA
        js = SOMMELIER_RESPONSE_SCHEMA["json_schema"]
        assert js["name"] == "sommelier_response"
        assert js["strict"] is True
        schema = js["schema"]
        assert "response_type" in schema["properties"]
        assert "intro" in schema["properties"]
        assert "wines" in schema["properties"]
        assert "closing" in schema["properties"]
        assert "guard_type" in schema["properties"]
        assert schema["additionalProperties"] is False


# =============================================================================
# T004: parse_structured_response() — JSON and legacy markers
# =============================================================================


class TestParseStructuredResponseJSON:
    """Tests for parse_structured_response() handling JSON input."""

    def test_json_recommendation_parsed_correctly(self):
        from app.services.sommelier_prompts import parse_structured_response

        raw_json = json.dumps(
            {
                "response_type": "recommendation",
                "intro": "К рыбе подойдут эти вина.",
                "wines": [
                    {"wine_name": "Chablis 2022", "description": "Шардоне из Бургундии."},
                    {"wine_name": "Sancerre 2021", "description": "Совиньон Блан из Луары."},
                    {"wine_name": "Riesling 2020", "description": "Немецкий рислинг."},
                ],
                "closing": "Какое вино вас заинтересовало?",
                "guard_type": None,
            }
        )
        parsed = parse_structured_response(raw_json)
        assert parsed.is_structured is True
        assert "К рыбе" in parsed.intro
        assert len(parsed.wines) == 3
        assert len(parsed.wine_names) == 3
        assert parsed.wine_names[0] == "Chablis 2022"
        assert parsed.wine_names[1] == "Sancerre 2021"
        assert parsed.wine_names[2] == "Riesling 2020"
        assert "Шардоне" in parsed.wines[0]
        assert "заинтересовало" in parsed.closing
        assert parsed.guard_type is None

    def test_json_informational_parsed_correctly(self):
        from app.services.sommelier_prompts import parse_structured_response

        raw_json = json.dumps(
            {
                "response_type": "informational",
                "intro": "Танины — это полифенолы.",
                "wines": [],
                "closing": "Хотите подобрать вино с танинами?",
                "guard_type": None,
            }
        )
        parsed = parse_structured_response(raw_json)
        assert parsed.is_structured is True
        assert parsed.wine_names == []
        assert parsed.wines == []
        assert "Танины" in parsed.intro

    def test_json_off_topic_with_guard(self):
        from app.services.sommelier_prompts import parse_structured_response

        raw_json = json.dumps(
            {
                "response_type": "off_topic",
                "intro": "Я специализируюсь на вине!",
                "wines": [],
                "closing": "Давайте подберём вино?",
                "guard_type": "off_topic",
            }
        )
        parsed = parse_structured_response(raw_json)
        assert parsed.is_structured is True
        assert parsed.guard_type == "off_topic"

    def test_json_with_1_wine(self):
        from app.services.sommelier_prompts import parse_structured_response

        raw_json = json.dumps(
            {
                "response_type": "recommendation",
                "intro": "Нашёл одно вино.",
                "wines": [
                    {"wine_name": "Solo Wine", "description": "Единственный вариант."},
                ],
                "closing": "Хотите расширить поиск?",
                "guard_type": None,
            }
        )
        parsed = parse_structured_response(raw_json)
        assert parsed.is_structured is True
        assert len(parsed.wine_names) == 1
        assert parsed.wine_names[0] == "Solo Wine"


class TestParseStructuredResponseLegacyFallback:
    """Tests for parse_structured_response() falling back to legacy markers."""

    def test_legacy_markers_still_work(self):
        from app.services.sommelier_prompts import parse_structured_response

        text = (
            "[INTRO]\nВот три варианта!\n[/INTRO]\n"
            "[WINE:1]\n**Château Margaux** — бордо\n[/WINE:1]\n"
            "[WINE:2]\n**Cloudy Bay** — совиньон\n[/WINE:2]\n"
            "[WINE:3]\n**Barolo** — классика\n[/WINE:3]\n"
            "[CLOSING]\nУточнить?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)
        assert parsed.is_structured is True
        assert len(parsed.wines) == 3
        assert "Château Margaux" in parsed.wines[0]

    def test_heuristic_fallback_still_works(self):
        from app.services.sommelier_prompts import parse_structured_response

        text = (
            "Вот подборка для вас:\n\n"
            "**Malbec Reserva, Мендоса, Аргентина, 2020, 1800 руб.**\n"
            "Насыщенный мальбек.\n\n"
            "Хотите ещё?"
        )
        parsed = parse_structured_response(text)
        assert parsed.is_structured is True
        assert len(parsed.wines) >= 1

    def test_invalid_json_falls_back_to_markers(self):
        from app.services.sommelier_prompts import parse_structured_response

        text = (
            "{ broken json\n"
            "[INTRO]\nFallback intro\n[/INTRO]\n"
            "[WINE:1]\nFallback wine\n[/WINE:1]\n"
            "[CLOSING]\nFallback closing\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)
        assert parsed.is_structured is True
        assert "Fallback intro" in parsed.intro


# =============================================================================
# T005: render_response_text()
# =============================================================================


class TestRenderResponseText:
    """Tests for render_response_text() helper."""

    def test_render_recommendation_with_3_wines(self):
        from app.services.sommelier_prompts import SommelierResponse, render_response_text

        resp = SommelierResponse(
            response_type="recommendation",
            intro="К стейку подойдут:",
            wines=[
                {"wine_name": "Wine A", "description": "**Wine A, Bordeaux, 2018, 4500 руб.**\nОписание A."},
                {"wine_name": "Wine B", "description": "**Wine B, Piedmont, 2019, 3200 руб.**\nОписание B."},
                {"wine_name": "Wine C", "description": "**Wine C, Mendoza, 2020, 1800 руб.**\nОписание C."},
            ],
            closing="Какой ценовой диапазон?",
            guard_type=None,
        )
        text = render_response_text(resp)
        assert "К стейку подойдут:" in text
        assert "Описание A." in text
        assert "Описание B." in text
        assert "Описание C." in text
        assert "Какой ценовой диапазон?" in text

    def test_render_informational_no_wines(self):
        from app.services.sommelier_prompts import SommelierResponse, render_response_text

        resp = SommelierResponse(
            response_type="informational",
            intro="Танины — это полифенолы, содержащиеся в кожице винограда.",
            wines=[],
            closing="Хотите подобрать вино?",
            guard_type=None,
        )
        text = render_response_text(resp)
        assert "Танины" in text
        assert "подобрать вино" in text

    def test_render_off_topic(self):
        from app.services.sommelier_prompts import SommelierResponse, render_response_text

        resp = SommelierResponse(
            response_type="off_topic",
            intro="Я специализируюсь на вине!",
            wines=[],
            closing="Давайте подберём вино?",
            guard_type="off_topic",
        )
        text = render_response_text(resp)
        assert "специализируюсь на вине" in text
        assert "подберём вино" in text

    def test_render_single_wine(self):
        from app.services.sommelier_prompts import SommelierResponse, render_response_text

        resp = SommelierResponse(
            response_type="recommendation",
            intro="Одно вино:",
            wines=[{"wine_name": "Solo", "description": "Единственное."}],
            closing="Ещё?",
            guard_type=None,
        )
        text = render_response_text(resp)
        assert "Одно вино:" in text
        assert "Единственное." in text
        assert "Ещё?" in text

    def test_render_produces_no_json(self):
        """Rendered text should NOT contain JSON artifacts."""
        from app.services.sommelier_prompts import SommelierResponse, render_response_text

        resp = SommelierResponse(
            response_type="recommendation",
            intro="Intro",
            wines=[{"wine_name": "W", "description": "D"}],
            closing="Closing",
            guard_type=None,
        )
        text = render_response_text(resp)
        assert "{" not in text
        assert "response_type" not in text
        assert "wine_name" not in text
