"""Integration test for structured output welcome flow.

T023 [US2]: Mock LLM returns valid SommelierResponse JSON for welcome →
start handler sends 5 messages (intro + 3 photos + closing).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.sender import send_wine_recommendations
from app.services.sommelier_prompts import SOMMELIER_RESPONSE_SCHEMA, parse_structured_response


def _make_welcome_json(wine_count: int = 3) -> str:
    """Build a valid SommelierResponse JSON for welcome message."""
    wines = [
        {
            "wine_name": f"Welcome Wine {i}",
            "description": f"**Welcome Wine {i}, Region {i}, Country, 2020, {1000 + i * 500} руб.**\nОтличный выбор для знакомства.",
        }
        for i in range(1, wine_count + 1)
    ]
    return json.dumps(
        {
            "response_type": "recommendation",
            "intro": "Добро пожаловать! Вот три вина для знакомства:",
            "wines": wines,
            "closing": "Какое вино хотите попробовать?",
            "guard_type": None,
        }
    )


def _make_wine_mock(name: str, has_image: bool = True):
    """Create a mock Wine object."""
    wine = MagicMock()
    wine.name = name
    wine.image_url = "/static/images/wines/test.png" if has_image else None
    return wine


class TestStructuredWelcomeFlow:
    """Integration: JSON welcome response → parse → 5 messages."""

    def test_welcome_json_parses_correctly(self):
        """SommelierResponse JSON for welcome → ParsedResponse with wine_names."""
        raw_json = _make_welcome_json(3)
        parsed = parse_structured_response(raw_json)

        assert parsed.is_structured is True
        assert len(parsed.wines) == 3
        assert len(parsed.wine_names) == 3
        assert parsed.wine_names[0] == "Welcome Wine 1"
        assert parsed.wine_names[1] == "Welcome Wine 2"
        assert parsed.wine_names[2] == "Welcome Wine 3"
        assert "Добро пожаловать" in parsed.intro
        assert "попробовать" in parsed.closing

    @pytest.mark.asyncio
    async def test_welcome_sender_sends_5_messages(self):
        """Welcome flow: intro + 3 wine photos + closing = 5 messages."""
        raw_json = _make_welcome_json(3)
        wines = [
            _make_wine_mock("Welcome Wine 1"),
            _make_wine_mock("Welcome Wine 2"),
            _make_wine_mock("Welcome Wine 3"),
        ]

        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.message.reply_photo = AsyncMock()

        with patch("app.bot.sender.get_wine_image_path") as mock_path, \
             patch("app.bot.sender.prepare_wine_photo") as mock_photo:
            mock_path.return_value = "/fake/path.png"
            mock_photo.return_value = b"fake_image_data"

            sent = await send_wine_recommendations(
                mock_update, raw_json, wines, "ru"
            )

        assert sent is True
        # 1 intro + 1 closing = 2 reply_text calls
        assert mock_update.message.reply_text.call_count == 2
        # 3 wine photos
        assert mock_update.message.reply_photo.call_count == 3

    @pytest.mark.asyncio
    async def test_welcome_personalized_response(self):
        """Personalized welcome with user profile → same 5 messages."""
        raw_json = json.dumps(
            {
                "response_type": "recommendation",
                "intro": "С возвращением! На основе ваших предпочтений:",
                "wines": [
                    {
                        "wine_name": "Profile Wine 1",
                        "description": "**Profile Wine 1, Тоскана, Италия, 2019, 2500 руб.**\nПодходит под ваш профиль.",
                    },
                    {
                        "wine_name": "Profile Wine 2",
                        "description": "**Profile Wine 2, Бордо, Франция, 2018, 3500 руб.**\nВам понравится это вино.",
                    },
                    {
                        "wine_name": "Profile Wine 3",
                        "description": "**Profile Wine 3, Мендоса, Аргентина, 2020, 1800 руб.**\nНовый опыт для вас.",
                    },
                ],
                "closing": "Хотите узнать больше о каком-то из этих вин?",
                "guard_type": None,
            }
        )
        wines = [
            _make_wine_mock("Profile Wine 1"),
            _make_wine_mock("Profile Wine 2"),
            _make_wine_mock("Profile Wine 3"),
        ]

        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.message.reply_photo = AsyncMock()

        with patch("app.bot.sender.get_wine_image_path") as mock_path, \
             patch("app.bot.sender.prepare_wine_photo") as mock_photo:
            mock_path.return_value = "/fake/path.png"
            mock_photo.return_value = b"fake_image_data"

            sent = await send_wine_recommendations(
                mock_update, raw_json, wines, "ru"
            )

        assert sent is True
        assert mock_update.message.reply_text.call_count == 2
        assert mock_update.message.reply_photo.call_count == 3


class TestWelcomeResponseFormat:
    """Verify response_format schema is passed to LLM for welcome."""

    def test_schema_has_required_structure(self):
        """SOMMELIER_RESPONSE_SCHEMA has correct structure for response_format."""
        assert SOMMELIER_RESPONSE_SCHEMA["type"] == "json_schema"
        schema = SOMMELIER_RESPONSE_SCHEMA["json_schema"]["schema"]
        assert "response_type" in schema["properties"]
        assert "intro" in schema["properties"]
        assert "wines" in schema["properties"]
        assert "closing" in schema["properties"]
        assert "guard_type" in schema["properties"]
        assert schema["additionalProperties"] is False
