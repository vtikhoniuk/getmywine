"""Unit tests for MockAIService.

Tests:
- T022: MockAIService returns wine-related responses
"""
import pytest


class TestMockAIService:
    """Tests for MockAIService."""

    def test_generate_response_returns_string(self):
        """Should return a non-empty string response."""
        from app.services.ai_mock import MockAIService

        service = MockAIService()
        response = service.generate_response("Hello")

        assert isinstance(response, str)
        assert len(response) > 0

    def test_response_is_wine_related(self):
        """Response should contain wine-related content."""
        from app.services.ai_mock import MockAIService

        service = MockAIService()
        response = service.generate_response("Посоветуй вино").lower()

        wine_terms = ["вин", "сорт", "белое", "красное", "рекомендую", "букет"]
        assert any(term in response for term in wine_terms)

    def test_different_inputs_give_responses(self):
        """Different inputs should produce valid responses."""
        from app.services.ai_mock import MockAIService

        service = MockAIService()

        inputs = [
            "Какое вино к рыбе?",
            "Расскажи о Каберне",
            "Что такое танины?",
        ]

        for input_text in inputs:
            response = service.generate_response(input_text)
            assert len(response) > 0

    def test_handles_empty_input(self):
        """Should handle empty input gracefully."""
        from app.services.ai_mock import MockAIService

        service = MockAIService()
        response = service.generate_response("")

        assert isinstance(response, str)
        assert len(response) > 0

    def test_response_not_too_long(self):
        """Response should be within reasonable length."""
        from app.services.ai_mock import MockAIService

        service = MockAIService()
        response = service.generate_response("Какое вино выбрать?")

        # Mock responses should be under 2000 chars
        assert len(response) <= 2000
