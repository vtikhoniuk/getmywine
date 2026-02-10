"""Tests for bot sender module.

T009: send_wine_recommendations() — structured path
T010: send_wine_recommendations() — send order
T014: returning user (no greeting in intro)
T017: wine without image → reply_text fallback
T018: caption truncation to ≤1024
T019: fewer than 3 wines
T021: fallback path (is_structured=False → returns False)
T022: send_fallback_response() tests
"""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.models.wine import Sweetness, WineType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_structured_text(
    intro: str = "Вот подборка!",
    wines: list[str] | None = None,
    closing: str = "Хотите уточнить?",
) -> str:
    """Build a structured LLM response string."""
    if wines is None:
        wines = [
            "**Château Margaux** — великолепное бордо",
            "**Cloudy Bay** — новозеландский совиньон",
            "**Barolo** — итальянская классика",
        ]
    text = f"[INTRO]\n{intro}\n[/INTRO]\n"
    for i, w in enumerate(wines, 1):
        text += f"[WINE:{i}]\n{w}\n[/WINE:{i}]\n"
    if closing:
        text += f"[CLOSING]\n{closing}\n[/CLOSING]"
    return text


def _make_wines(count: int = 3, with_images: bool = True) -> list[MagicMock]:
    """Create a list of mock Wine objects."""
    import uuid

    wines = []
    for i in range(count):
        wine = MagicMock()
        wine.id = uuid.uuid4()
        wine.name = f"Wine {i + 1}"
        wine.region = "Region"
        wine.country = "Country"
        wine.grape_varieties = ["Grape"]
        wine.sweetness = Sweetness.DRY
        wine.price_rub = 2000.0
        wine.wine_type = WineType.RED
        wine.image_url = f"/static/images/wines/{i}.png" if with_images else None
        wines.append(wine)
    return wines


def _patch_file_io():
    """Patch prepare_wine_photo and InputFile to avoid real file/image I/O."""
    fake_buf = MagicMock()
    return (
        patch("app.bot.sender.prepare_wine_photo", return_value=fake_buf),
        patch("app.bot.sender.InputFile", return_value=MagicMock()),
    )


# ---------------------------------------------------------------------------
# T009: send_wine_recommendations() — structured path
# ---------------------------------------------------------------------------

class TestSendWineRecommendationsStructured:
    """Structured path: intro → 3 photos → closing."""

    @pytest.mark.asyncio
    async def test_structured_3_wines_sends_5_messages(self, mock_update):
        """3 wines with images → 5 calls: reply_text, 3× reply_photo, reply_text."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text()
        wines = _make_wines(3)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            result = await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        assert result is True
        assert mock_update.message.reply_text.call_count == 2  # intro + closing
        assert mock_update.message.reply_photo.call_count == 3

    @pytest.mark.asyncio
    async def test_captions_are_plain_text(self, mock_update):
        """Photo captions should have markdown stripped."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text(
            wines=["**Bold wine** description"] * 3
        )
        wines = _make_wines(3)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        for c in mock_update.message.reply_photo.call_args_list:
            caption = c.kwargs.get("caption", "")
            assert "**" not in caption

    @pytest.mark.asyncio
    async def test_captions_within_1024_limit(self, mock_update):
        """Each photo caption must be ≤1024 chars."""
        from app.bot.sender import send_wine_recommendations

        long_text = "A" * 2000
        response_text = _make_structured_text(wines=[long_text] * 3)
        wines = _make_wines(3)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        for c in mock_update.message.reply_photo.call_args_list:
            caption = c.kwargs.get("caption", "")
            assert len(caption) <= 1024


# ---------------------------------------------------------------------------
# T010: send_wine_recommendations() — send order
# ---------------------------------------------------------------------------

class TestSendOrder:
    """Messages must be sent in strict order: intro → wine1 → wine2 → wine3 → closing."""

    @pytest.mark.asyncio
    async def test_sequential_order(self, mock_update):
        """Calls must be: reply_text(intro), reply_photo×3, reply_text(closing)."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text()
        wines = _make_wines(3)

        call_order = []

        async def track_reply_text(*args, **kwargs):
            call_order.append(("text", args, kwargs))

        async def track_reply_photo(*args, **kwargs):
            call_order.append(("photo", args, kwargs))

        mock_update.message.reply_text = AsyncMock(side_effect=track_reply_text)
        mock_update.message.reply_photo = AsyncMock(side_effect=track_reply_photo)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        assert len(call_order) == 5
        assert call_order[0][0] == "text"   # intro
        assert call_order[1][0] == "photo"  # wine 1
        assert call_order[2][0] == "photo"  # wine 2
        assert call_order[3][0] == "photo"  # wine 3
        assert call_order[4][0] == "text"   # closing


# ---------------------------------------------------------------------------
# T014: returning user — no greeting in intro
# ---------------------------------------------------------------------------

class TestReturningUser:
    """Returning user: intro should not contain greeting."""

    @pytest.mark.asyncio
    async def test_intro_passed_as_is(self, mock_update):
        """Intro content from parsed response is sent directly."""
        from app.bot.sender import send_wine_recommendations

        intro = "Подобрал для вас вина к стейку."
        response_text = _make_structured_text(intro=intro)
        wines = _make_wines(3)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        first_call_args = mock_update.message.reply_text.call_args_list[0]
        sent_text = first_call_args[0][0] if first_call_args[0] else first_call_args.kwargs.get("text", "")
        assert "Подобрал" in sent_text


# ---------------------------------------------------------------------------
# T017: wine without image → reply_text fallback
# ---------------------------------------------------------------------------

class TestWineWithoutImage:
    """Wine with no image → sent as text instead of photo."""

    @pytest.mark.asyncio
    async def test_no_image_sends_text(self, mock_update):
        """Wine without image_url → reply_text for that wine."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text(wines=["Wine 1", "Wine 2", "Wine 3"])
        wines = _make_wines(3)

        def image_path_side_effect(wine):
            # Only first wine has image
            if wine == wines[0]:
                return "/fake/path.png"
            return None

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", side_effect=image_path_side_effect):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        # 1 photo (wine 0) + 2 text (wine 1, 2) + intro + closing = 4 text, 1 photo
        assert mock_update.message.reply_photo.call_count == 1
        assert mock_update.message.reply_text.call_count == 4  # intro + 2 wines + closing


# ---------------------------------------------------------------------------
# T018: caption truncation
# ---------------------------------------------------------------------------

class TestCaptionTruncation:
    """Caption >1024 chars must be truncated."""

    @pytest.mark.asyncio
    async def test_long_caption_truncated(self, mock_update):
        """Wine text >1024 → caption ≤1024, still contains wine name."""
        from app.bot.sender import send_wine_recommendations

        long_wine_text = "Château Margaux " + "x" * 2000
        response_text = _make_structured_text(wines=[long_wine_text])
        wines = _make_wines(1)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        caption = mock_update.message.reply_photo.call_args.kwargs.get("caption", "")
        assert len(caption) <= 1024
        assert "Margaux" in caption


# ---------------------------------------------------------------------------
# T019: fewer than 3 wines
# ---------------------------------------------------------------------------

class TestFewerThanThreeWines:
    """System handles 1 or 2 wines gracefully."""

    @pytest.mark.asyncio
    async def test_one_wine(self, mock_update):
        """1 wine → intro + 1 photo + closing = 3 messages."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text(wines=["Единственное вино"])
        wines = _make_wines(1)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            result = await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        assert result is True
        assert mock_update.message.reply_photo.call_count == 1
        assert mock_update.message.reply_text.call_count == 2  # intro + closing

    @pytest.mark.asyncio
    async def test_two_wines(self, mock_update):
        """2 wines → intro + 2 photos + closing = 4 messages."""
        from app.bot.sender import send_wine_recommendations

        response_text = _make_structured_text(wines=["Вино 1", "Вино 2"])
        wines = _make_wines(2)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            result = await send_wine_recommendations(
                mock_update, response_text, wines, "ru"
            )

        assert result is True
        assert mock_update.message.reply_photo.call_count == 2
        assert mock_update.message.reply_text.call_count == 2  # intro + closing


# ---------------------------------------------------------------------------
# T021: fallback path — is_structured=False → returns False
# ---------------------------------------------------------------------------

class TestFallbackReturnsFlag:
    """send_wine_recommendations() returns False when not structured."""

    @pytest.mark.asyncio
    async def test_unstructured_returns_false(self, mock_update):
        """Plain text (no markers) → returns False, nothing sent."""
        from app.bot.sender import send_wine_recommendations

        response_text = "Рекомендую попробовать Château Margaux."
        wines = _make_wines(3)

        result = await send_wine_recommendations(
            mock_update, response_text, wines, "ru"
        )

        assert result is False
        mock_update.message.reply_text.assert_not_called()
        mock_update.message.reply_photo.assert_not_called()


# ---------------------------------------------------------------------------
# T022: send_fallback_response() tests
# ---------------------------------------------------------------------------

class TestSendFallbackResponse:
    """Fallback: single text message + separate wine photos."""

    @pytest.mark.asyncio
    async def test_sends_text_plus_photos(self, mock_update):
        """Fallback sends 1 text + N photos."""
        from app.bot.sender import send_fallback_response

        response_text = "Вот несколько рекомендаций."
        wines = _make_wines(3)

        p_open, p_input = _patch_file_io()
        with p_open, p_input, patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"):
            await send_fallback_response(
                mock_update, response_text, wines, "ru"
            )

        assert mock_update.message.reply_text.call_count == 1
        assert mock_update.message.reply_photo.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_wines_without_images(self, mock_update):
        """Wines without images are skipped in fallback."""
        from app.bot.sender import send_fallback_response

        response_text = "Рекомендации"
        wines = _make_wines(3)

        with patch("app.bot.sender.get_wine_image_path", return_value=None):
            await send_fallback_response(
                mock_update, response_text, wines, "ru"
            )

        assert mock_update.message.reply_text.call_count == 1
        assert mock_update.message.reply_photo.call_count == 0

    @pytest.mark.asyncio
    async def test_uses_format_wine_photo_caption(self, mock_update):
        """Fallback uses format_wine_photo_caption() for captions."""
        from app.bot.sender import send_fallback_response

        wines = _make_wines(1)

        p_open, p_input = _patch_file_io()
        with (
            p_open,
            p_input,
            patch("app.bot.sender.get_wine_image_path", return_value="/fake/path.png"),
            patch("app.bot.sender.format_wine_photo_caption", return_value="Formatted caption") as mock_fmt,
        ):
            await send_fallback_response(
                mock_update, "text", wines, "ru"
            )

        mock_fmt.assert_called_once_with(wines[0], "ru")
        caption = mock_update.message.reply_photo.call_args.kwargs.get("caption", "")
        assert caption == "Formatted caption"
