"""Integration test for structured output recommendation flow.

T014 [US1]: Mock LLM returns valid SommelierResponse JSON with 3 wines →
sender sends 5 messages (intro + 3 photos + closing).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.sender import send_wine_recommendations
from app.services.sommelier_prompts import parse_structured_response


def _make_json_response(wine_count: int = 3) -> str:
    """Build a valid SommelierResponse JSON string."""
    wines = [
        {
            "wine_id": f"00000000-0000-0000-0000-00000000000{i}",
            "wine_name": f"Test Wine {i}",
            "description": f"**Test Wine {i}, Region {i}, Country, 2020, {1000 + i * 500} руб.**\nОписание вина {i}.",
        }
        for i in range(1, wine_count + 1)
    ]
    return json.dumps(
        {
            "response_type": "recommendation",
            "intro": "Вот подборка вин для вас!",
            "wines": wines,
            "closing": "Какое вино вас заинтересовало?",
            "guard_type": None,
        }
    )


def _make_wine_mock(name: str, has_image: bool = True):
    """Create a mock Wine object."""
    wine = MagicMock()
    wine.name = name
    wine.image_url = "/static/images/wines/test.png" if has_image else None
    return wine


class TestStructuredRecommendationFlow:
    """Integration: JSON response → parse → 5 messages."""

    def test_json_response_parses_with_wine_names(self):
        """SommelierResponse JSON → ParsedResponse with wine_names."""
        raw_json = _make_json_response(3)
        parsed = parse_structured_response(raw_json)

        assert parsed.is_structured is True
        assert len(parsed.wines) == 3
        assert len(parsed.wine_names) == 3
        assert parsed.wine_names[0] == "Test Wine 1"
        assert parsed.wine_names[1] == "Test Wine 2"
        assert parsed.wine_names[2] == "Test Wine 3"
        assert "Вот подборка" in parsed.intro
        assert "заинтересовало" in parsed.closing

    @pytest.mark.asyncio
    async def test_sender_sends_5_messages_for_3_wines(self):
        """Structured sender: intro + 3 wine photos + closing = 5 messages."""
        raw_json = _make_json_response(3)
        wines = [
            _make_wine_mock("Test Wine 1"),
            _make_wine_mock("Test Wine 2"),
            _make_wine_mock("Test Wine 3"),
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
    async def test_sender_handles_1_wine(self):
        """Structured sender: intro + 1 wine photo + closing = 3 messages."""
        raw_json = _make_json_response(1)
        wines = [_make_wine_mock("Test Wine 1")]

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
        assert mock_update.message.reply_text.call_count == 2  # intro + closing
        assert mock_update.message.reply_photo.call_count == 1

    @pytest.mark.asyncio
    async def test_sender_handles_informational_no_wines(self):
        """Informational response: single combined message."""
        raw_json = json.dumps(
            {
                "response_type": "informational",
                "intro": "Танины — это полифенолы.",
                "wines": [],
                "closing": "Хотите подобрать вино?",
                "guard_type": None,
            }
        )

        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_update.message.reply_photo = AsyncMock()

        sent = await send_wine_recommendations(
            mock_update, raw_json, [], "ru"
        )

        assert sent is True
        assert mock_update.message.reply_text.call_count == 1  # combined intro+closing
        assert mock_update.message.reply_photo.call_count == 0
