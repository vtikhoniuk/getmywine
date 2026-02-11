"""Tests for parse_structured_response() and strip_markdown().

T002: parse_structured_response() cases
T003: strip_markdown() cases
"""

import pytest

from app.services.sommelier_prompts import parse_structured_response, strip_markdown


# ---------------------------------------------------------------------------
# T002: parse_structured_response()
# ---------------------------------------------------------------------------


class TestParseStructuredResponse:
    """Tests for LLM response parsing with [INTRO]/[WINE:N]/[CLOSING] markers."""

    def test_full_response_with_3_wines(self):
        """Full response with intro, 3 wines, closing → is_structured=True."""
        text = (
            "[INTRO]\nВот три варианта для вас!\n[/INTRO]\n"
            "[WINE:1]\n**Château Margaux** — великолепное бордо\n[/WINE:1]\n"
            "[WINE:2]\n**Cloudy Bay** — новозеландский совиньон\n[/WINE:2]\n"
            "[WINE:3]\n**Barolo** — итальянская классика\n[/WINE:3]\n"
            "[CLOSING]\nХотите уточнить предпочтения?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.is_structured is True
        assert "Вот три варианта" in parsed.intro
        assert len(parsed.wines) == 3
        assert "Château Margaux" in parsed.wines[0]
        assert "Cloudy Bay" in parsed.wines[1]
        assert "Barolo" in parsed.wines[2]
        assert "уточнить" in parsed.closing

    def test_response_with_1_wine(self):
        """Response with intro and 1 wine → is_structured=True, wines=[1]."""
        text = (
            "[INTRO]\nВот вариант\n[/INTRO]\n"
            "[WINE:1]\nЕдинственное вино\n[/WINE:1]\n"
        )
        parsed = parse_structured_response(text)

        assert parsed.is_structured is True
        assert len(parsed.wines) == 1

    def test_response_without_markers(self):
        """Plain text without any markers → is_structured=False."""
        text = "Рекомендую вам попробовать Château Margaux."
        parsed = parse_structured_response(text)

        assert parsed.is_structured is False
        assert parsed.intro == ""
        assert parsed.wines == []

    def test_intro_without_wines(self):
        """Intro present but no wines → is_structured=True (informational response)."""
        text = "[INTRO]\nВведение\n[/INTRO]"
        parsed = parse_structured_response(text)

        assert parsed.is_structured is True
        assert parsed.intro == "Введение"
        assert parsed.wines == []

    def test_empty_string(self):
        """Empty string → is_structured=False."""
        parsed = parse_structured_response("")

        assert parsed.is_structured is False
        assert parsed.intro == ""
        assert parsed.wines == []

    def test_whitespace_inside_markers_is_stripped(self):
        """Whitespace around content inside markers should be stripped."""
        text = (
            "[INTRO]  \n  Вступление с пробелами  \n  [/INTRO]\n"
            "[WINE:1]  \n  Вино с пробелами  \n  [/WINE:1]"
        )
        parsed = parse_structured_response(text)

        assert parsed.is_structured is True
        assert parsed.intro == "Вступление с пробелами"
        assert parsed.wines[0] == "Вино с пробелами"

    def test_closing_is_optional(self):
        """Response without [CLOSING] is still structured."""
        text = (
            "[INTRO]\nВступление\n[/INTRO]\n"
            "[WINE:1]\nВино 1\n[/WINE:1]\n"
        )
        parsed = parse_structured_response(text)

        assert parsed.is_structured is True
        assert parsed.closing == ""


# ---------------------------------------------------------------------------
# T001-T005: [GUARD] marker parsing
# ---------------------------------------------------------------------------


class TestGuardMarkerParsing:
    """Tests for [GUARD:type] marker extraction from LLM responses."""

    def test_guard_off_topic_before_structured_response(self):
        """[GUARD:off_topic] before structured content → guard_type='off_topic', is_structured=True."""
        text = (
            "[GUARD:off_topic]\n"
            "[INTRO]\nЯ специализируюсь на вине!\n[/INTRO]\n"
            "[WINE:1]\nВино 1\n[/WINE:1]\n"
            "[CLOSING]\nДавайте подберём вино?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.guard_type == "off_topic"
        assert parsed.is_structured is True
        assert "специализируюсь на вине" in parsed.intro

    def test_guard_prompt_injection_parsed(self):
        """[GUARD:prompt_injection] → guard_type='prompt_injection'."""
        text = (
            "[GUARD:prompt_injection]\n"
            "[INTRO]\nЯ винный сомелье Винни.\n[/INTRO]\n"
            "[WINE:1]\nОтличный Мальбек\n[/WINE:1]\n"
            "[CLOSING]\nЧто подобрать?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.guard_type == "prompt_injection"
        assert parsed.is_structured is True

    def test_guard_social_engineering_parsed(self):
        """[GUARD:social_engineering] → guard_type='social_engineering'."""
        text = (
            "[GUARD:social_engineering]\n"
            "[INTRO]\nЯ сомелье и помогу с вином.\n[/INTRO]\n"
            "[WINE:1]\nРислинг\n[/WINE:1]\n"
            "[CLOSING]\nКакое вино вас интересует?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.guard_type == "social_engineering"
        assert parsed.is_structured is True

    def test_no_guard_marker_returns_none(self):
        """Standard response without [GUARD] → guard_type=None."""
        text = (
            "[INTRO]\nОбычный ответ\n[/INTRO]\n"
            "[WINE:1]\nВино\n[/WINE:1]\n"
            "[CLOSING]\nВопрос?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.guard_type is None
        assert parsed.is_structured is True

    def test_guard_does_not_break_intro_wine_closing(self):
        """[GUARD:off_topic] + full response → all fields parsed correctly."""
        text = (
            "[GUARD:off_topic]\n"
            "[INTRO]\nВот три варианта для вас!\n[/INTRO]\n"
            "[WINE:1]\n**Château Margaux** — великолепное бордо\n[/WINE:1]\n"
            "[WINE:2]\n**Cloudy Bay** — новозеландский совиньон\n[/WINE:2]\n"
            "[WINE:3]\n**Barolo** — итальянская классика\n[/WINE:3]\n"
            "[CLOSING]\nХотите уточнить предпочтения?\n[/CLOSING]"
        )
        parsed = parse_structured_response(text)

        assert parsed.guard_type == "off_topic"
        assert parsed.is_structured is True
        assert "Вот три варианта" in parsed.intro
        assert len(parsed.wines) == 3
        assert "Château Margaux" in parsed.wines[0]
        assert "Cloudy Bay" in parsed.wines[1]
        assert "Barolo" in parsed.wines[2]
        assert "уточнить" in parsed.closing


# ---------------------------------------------------------------------------
# T003: strip_markdown()
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    """Tests for stripping Markdown formatting from text."""

    def test_removes_bold(self):
        """**bold** → bold."""
        assert strip_markdown("**bold text**") == "bold text"

    def test_removes_italic(self):
        """*italic* → italic."""
        assert strip_markdown("*italic text*") == "italic text"

    def test_removes_underline(self):
        """_underline_ → underline."""
        assert strip_markdown("_underline text_") == "underline text"

    def test_plain_text_unchanged(self):
        """Text without markdown passes through unchanged."""
        text = "Just plain text here"
        assert strip_markdown(text) == text

    def test_combined_markdown(self):
        """Mixed markdown is all removed."""
        text = "**Bold** and *italic* and _underline_"
        result = strip_markdown(text)
        assert result == "Bold and italic and underline"
