"""Tests for proactive suggestion engine."""

from datetime import date, datetime

import pytest

from app.services.proactive_suggestions import (
    ProactiveSuggestionEngine,
    Season,
    SuggestionContext,
    WineSuggestion,
)


class TestProactiveSuggestionEngine:
    """Tests for ProactiveSuggestionEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ProactiveSuggestionEngine()

    # =========================================================================
    # Season Detection Tests
    # =========================================================================

    @pytest.mark.parametrize(
        "month,expected_season",
        [
            (1, Season.WINTER),
            (2, Season.WINTER),
            (3, Season.SPRING),
            (4, Season.SPRING),
            (5, Season.SPRING),
            (6, Season.SUMMER),
            (7, Season.SUMMER),
            (8, Season.SUMMER),
            (9, Season.AUTUMN),
            (10, Season.AUTUMN),
            (11, Season.AUTUMN),
            (12, Season.WINTER),
        ],
    )
    def test_get_season(self, month: int, expected_season: Season):
        """Test season detection for each month."""
        d = date(2026, month, 15)
        assert self.engine.get_season(d) == expected_season

    # =========================================================================
    # Holiday Detection Tests
    # =========================================================================

    def test_new_year_holiday_detection(self):
        """Test New Year holiday is detected in late December."""
        d = date(2026, 12, 25)
        holiday, days_until = self.engine.get_upcoming_holiday(d)

        assert holiday is not None
        assert holiday.name == "Новый год"
        assert "шампанского" in holiday.hook_ru.lower()

    def test_valentines_day_detection(self):
        """Test Valentine's Day is detected in early February."""
        d = date(2026, 2, 12)
        holiday, days_until = self.engine.get_upcoming_holiday(d)

        assert holiday is not None
        assert holiday.name == "День влюблённых"

    def test_no_holiday_in_april(self):
        """Test no holiday detected in mid-April."""
        d = date(2026, 4, 15)
        holiday, _ = self.engine.get_upcoming_holiday(d)

        assert holiday is None

    # =========================================================================
    # Context Building Tests
    # =========================================================================

    def test_build_context_friday_evening(self):
        """Test context correctly identifies Friday evening."""
        # Friday at 18:00
        dt = datetime(2026, 2, 6, 18, 0)  # Feb 6, 2026 is Friday
        ctx = self.engine.build_context(dt, user_has_profile=False)

        assert ctx.is_friday_evening is True
        assert ctx.is_weekend is False
        assert ctx.day_of_week == 4  # Friday

    def test_build_context_weekend(self):
        """Test context correctly identifies weekend."""
        # Saturday
        dt = datetime(2026, 2, 7, 14, 0)  # Saturday
        ctx = self.engine.build_context(dt, user_has_profile=False)

        assert ctx.is_weekend is True
        assert ctx.is_friday_evening is False

    def test_build_context_with_profile(self):
        """Test context correctly sets user_has_profile."""
        dt = datetime(2026, 2, 3, 12, 0)

        ctx_no_profile = self.engine.build_context(dt, user_has_profile=False)
        ctx_with_profile = self.engine.build_context(dt, user_has_profile=True)

        assert ctx_no_profile.user_has_profile is False
        assert ctx_with_profile.user_has_profile is True

    # =========================================================================
    # Suggestion Generation Tests
    # =========================================================================

    def test_generates_three_suggestions(self):
        """Test that exactly 3 suggestions are generated."""
        dt = datetime(2026, 2, 3, 12, 0)
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        assert len(suggestions) == 3

    def test_suggestions_have_required_fields(self):
        """Test that suggestions have all required fields."""
        dt = datetime(2026, 2, 3, 12, 0)
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        for s in suggestions:
            assert isinstance(s, WineSuggestion)
            assert s.angle  # Not empty
            assert s.hook  # Not empty
            assert s.explanation_template  # Not empty

    def test_first_suggestion_is_seasonal(self):
        """Test that first suggestion is always seasonal."""
        dt = datetime(2026, 7, 15, 12, 0)  # Summer
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        assert suggestions[0].angle == "Сезонное"
        assert "лето" in suggestions[0].hook.lower() or "жар" in suggestions[0].hook.lower()

    def test_winter_suggests_red_wine(self):
        """Test that winter seasonal suggestion prefers red wine."""
        dt = datetime(2026, 1, 15, 12, 0)  # Winter
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)
        seasonal = suggestions[0]

        from app.models.wine import WineType
        assert seasonal.wine_type == WineType.RED
        assert seasonal.body_min >= 4  # Full-bodied

    def test_summer_suggests_light_wine(self):
        """Test that summer seasonal suggestion prefers light wine."""
        dt = datetime(2026, 7, 15, 12, 0)  # Summer
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)
        seasonal = suggestions[0]

        from app.models.wine import WineType
        assert seasonal.wine_type in [WineType.WHITE, WineType.ROSE, WineType.SPARKLING]
        assert seasonal.body_max is not None and seasonal.body_max <= 3

    def test_holiday_suggestion_when_holiday_active(self):
        """Test that holiday suggestion appears when holiday is active."""
        dt = datetime(2026, 12, 25, 12, 0)  # Near New Year
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        # Second suggestion should be holiday-related
        holiday_suggestion = suggestions[1]
        assert "праздник" in holiday_suggestion.angle.lower() or "Новый год" in holiday_suggestion.angle

    def test_friday_evening_suggestion(self):
        """Test that Friday evening gets special suggestion."""
        dt = datetime(2026, 4, 10, 19, 0)  # Friday evening, no holidays
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        # Check for Friday-specific suggestion
        angles = [s.angle for s in suggestions]
        assert "Пятничный вечер" in angles

    def test_weekend_discovery_suggestion(self):
        """Test that weekends get discovery suggestion."""
        dt = datetime(2026, 4, 11, 14, 0)  # Saturday, no holidays
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        # Check for weekend/discovery suggestion
        angles = [s.angle for s in suggestions]
        assert any("эксперимент" in a.lower() or "открыт" in a.lower() for a in angles)

    def test_personalized_suggestion_for_users_with_profile(self):
        """Test that users with profile get personalized suggestion."""
        dt = datetime(2026, 2, 3, 12, 0)
        ctx = self.engine.build_context(dt, user_has_profile=True)

        suggestions = self.engine.generate_suggestions(ctx)

        # Third suggestion should be personalized
        personal = suggestions[2]
        assert "для вас" in personal.angle.lower() or "специально" in personal.angle.lower()

    def test_discovery_suggestion_for_new_users(self):
        """Test that new users get discovery suggestion."""
        dt = datetime(2026, 2, 3, 12, 0)
        ctx = self.engine.build_context(dt, user_has_profile=False)

        suggestions = self.engine.generate_suggestions(ctx)

        # Third suggestion should be discovery
        discovery = suggestions[2]
        assert "открытие" in discovery.angle.lower()
        assert discovery.is_discovery is True


class TestEventDetection:
    """Tests for event and food detection."""

    def test_detect_romantic_event(self):
        """Test detection of romantic dinner."""
        from app.services.sommelier import detect_event

        messages = [
            "Хочу вино для романтического ужина",
            "Планируем свидание, что посоветуешь?",
            "Ужин на двоих",
        ]

        for msg in messages:
            assert detect_event(msg) == "dinner_for_two"

    def test_detect_friends_event(self):
        """Test detection of friends gathering."""
        from app.services.sommelier import detect_event

        messages = [
            "Друзья придут в гости",
            "Вечеринка у меня дома",
            "Посиделки с друзьями",
        ]

        for msg in messages:
            assert detect_event(msg) == "friends_gathering"

    def test_detect_bbq_event(self):
        """Test detection of BBQ."""
        from app.services.sommelier import detect_event

        messages = [
            "Едем на шашлыки",
            "Барбекю на даче",
            "Готовим на гриле",
        ]

        for msg in messages:
            assert detect_event(msg) == "bbq"

    def test_detect_food_steak(self):
        """Test food detection for steak."""
        from app.services.sommelier import detect_food

        assert detect_food("Что взять к стейку?") == "стейк"

    def test_detect_food_seafood(self):
        """Test food detection for seafood."""
        from app.services.sommelier import detect_food

        assert detect_food("Вино к морепродуктам") == "морепродукты"

    def test_no_event_detected(self):
        """Test that generic message doesn't trigger event detection."""
        from app.services.sommelier import detect_event

        assert detect_event("Посоветуй хорошее красное вино") is None
