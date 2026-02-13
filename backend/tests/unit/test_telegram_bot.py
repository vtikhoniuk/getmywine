"""Unit tests for TelegramBotService helper methods.

Tests for _truncate_for_storage with updated limits (021-message-length-limit).
"""

from app.services.telegram_bot import TelegramBotService


class TestTruncateForStorage:
    """Tests for _truncate_for_storage static method."""

    def test_preserves_normal_responses(self):
        """T003: A 5000-char response should NOT be truncated (normal LLM output range)."""
        text = "А" * 5000
        result = TelegramBotService._truncate_for_storage(text)
        assert len(result) == 5000, (
            f"Expected 5000 chars preserved, got {len(result)} — "
            "normal LLM responses must not be truncated"
        )

    def test_preserves_long_response_with_paragraphs(self):
        """A response with paragraphs around 4000 chars should be fully preserved."""
        paragraphs = ["Это параграф о вине. " * 10 + "\n\n"] * 10  # ~2100 chars
        text = "".join(paragraphs)
        result = TelegramBotService._truncate_for_storage(text)
        assert result == text

    def test_safety_net_for_extreme_input(self):
        """T004: A 100000-char string should be truncated to at most 50000 (safety net)."""
        text = "x" * 100_000
        result = TelegramBotService._truncate_for_storage(text)
        assert len(result) <= 50_000, (
            f"Expected at most 50000 chars (safety net), got {len(result)}"
        )

    def test_safety_net_truncates_at_paragraph_boundary(self):
        """Safety net should still prefer paragraph boundaries when possible."""
        # Build text with a paragraph break just before 50000
        chunk = "A" * 49_990 + "\n\n" + "B" * 50_010
        result = TelegramBotService._truncate_for_storage(chunk)
        assert len(result) <= 50_000
        assert result.endswith("A")  # Truncated at paragraph boundary

    def test_short_text_unchanged(self):
        """Text shorter than limit should pass through unchanged."""
        text = "Hello, world!"
        result = TelegramBotService._truncate_for_storage(text)
        assert result == text

    def test_empty_text_unchanged(self):
        """Empty string should pass through unchanged."""
        result = TelegramBotService._truncate_for_storage("")
        assert result == ""
