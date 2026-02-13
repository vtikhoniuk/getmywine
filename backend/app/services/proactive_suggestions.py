"""Proactive suggestion engine for GetMyWine sommelier.

Generates contextual wine suggestions based on:
- Season and weather
- Upcoming holidays
- Day of week / time of day
- User taste profile (if available)
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

from app.models.wine import PriceRange, Sweetness, Wine, WineType


class Season(str, Enum):
    """Season enum."""

    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"


@dataclass
class Holiday:
    """Holiday definition."""

    name: str
    wine_style: str
    hook_ru: str
    wine_type: Optional[WineType] = None
    sweetness: Optional[Sweetness] = None
    body_min: Optional[int] = None
    body_max: Optional[int] = None
    country: Optional[str] = None


@dataclass
class SuggestionContext:
    """Context for generating suggestions."""

    current_date: date
    current_hour: int
    season: Season
    upcoming_holiday: Optional[Holiday]
    days_until_holiday: int
    day_of_week: int  # 0=Monday, 6=Sunday
    is_weekend: bool
    is_friday_evening: bool
    user_has_profile: bool


@dataclass
class WineSuggestion:
    """Single wine suggestion."""

    angle: str
    hook: str
    wine_type: Optional[WineType] = None
    sweetness: Optional[Sweetness] = None
    body_min: Optional[int] = None
    body_max: Optional[int] = None
    price_range: Optional[PriceRange] = None
    country: Optional[str] = None
    is_discovery: bool = False
    explanation_template: str = ""


# Holiday definitions (month_start, day_start, month_end, day_end)
HOLIDAYS_RU: dict[tuple[int, int, int, int], Holiday] = {
    (12, 20, 1, 10): Holiday(
        name="Новый год",
        wine_style="sparkling",
        hook_ru="Время шампанского и праздника!",
        wine_type=WineType.SPARKLING,
    ),
    (2, 10, 2, 14): Holiday(
        name="День влюблённых",
        wine_style="romantic",
        hook_ru="Романтика в бокале",
        wine_type=WineType.ROSE,
    ),
    (2, 20, 2, 23): Holiday(
        name="23 февраля",
        wine_style="bold_red",
        hook_ru="Вино с характером",
        wine_type=WineType.RED,
        body_min=4,
    ),
    (3, 5, 3, 8): Holiday(
        name="8 марта",
        wine_style="elegant",
        hook_ru="Элегантный подарок",
        wine_type=WineType.WHITE,
    ),
    (5, 7, 5, 9): Holiday(
        name="День Победы",
        wine_style="russian",
        hook_ru="Российское виноделие",
        country="Russia",
    ),
    (6, 10, 6, 12): Holiday(
        name="День России",
        wine_style="russian",
        hook_ru="Гордость отечественного виноделия",
        country="Russia",
    ),
}

SEASON_PROFILES: dict[Season, dict] = {
    Season.WINTER: {
        "hook": "Согревающее для зимнего вечера",
        "wine_type": WineType.RED,
        "body_min": 4,
    },
    Season.SPRING: {
        "hook": "Свежее для весеннего настроения",
        "wine_type": WineType.WHITE,
        "body_max": 3,
    },
    Season.SUMMER: {
        "hook": "Освежающее для жаркого дня",
        "wine_type": WineType.ROSE,
        "body_max": 2,
    },
    Season.AUTUMN: {
        "hook": "Уютное для осеннего вечера",
        "wine_type": WineType.RED,
        "body_min": 3,
        "body_max": 4,
    },
}

DISCOVERY_REGIONS = [
    ("Грузия", "Кахетинские вина с тысячелетней историей"),
    ("Португалия", "Не только портвейн — сухие вина Дору"),
    ("Греция", "Возрождение древних традиций"),
    ("Австрия", "Элегантные грюнер вельтлинеры"),
    ("Аргентина", "Высокогорные мальбеки Мендосы"),
    ("Чили", "Карменер — забытый сорт Бордо"),
    ("ЮАР", "Уникальный пинотаж"),
]

EVENT_SUGGESTIONS = {
    "dinner_for_two": WineSuggestion(
        angle="Ужин на двоих",
        hook="Романтический вечер",
        wine_type=WineType.RED,
        body_min=2,
        body_max=4,
        explanation_template="Элегантное вино для особенного вечера",
    ),
    "friends_gathering": WineSuggestion(
        angle="Посиделки с друзьями",
        hook="Для шумной компании",
        wine_type=WineType.RED,
        body_max=3,
        explanation_template="Лёгкое для питья, понравится всем",
    ),
    "bbq": WineSuggestion(
        angle="Барбекю",
        hook="К мясу на гриле",
        wine_type=WineType.RED,
        body_min=4,
        explanation_template="Насыщенное красное — идеальная пара к мясу",
    ),
    "seafood": WineSuggestion(
        angle="К морепродуктам",
        hook="Свежесть океана",
        wine_type=WineType.WHITE,
        body_max=2,
        explanation_template="Минеральность и свежесть для даров моря",
    ),
    "gift": WineSuggestion(
        angle="В подарок",
        hook="Впечатляющий презент",
        price_range=PriceRange.PREMIUM,
        explanation_template="Премиальное вино с красивой этикеткой",
    ),
}


class ProactiveSuggestionEngine:
    """Engine for generating proactive wine suggestions."""

    def get_season(self, d: date) -> Season:
        """Determine season from date."""
        month = d.month
        if month in (12, 1, 2):
            return Season.WINTER
        elif month in (3, 4, 5):
            return Season.SPRING
        elif month in (6, 7, 8):
            return Season.SUMMER
        return Season.AUTUMN

    def get_upcoming_holiday(self, d: date) -> tuple[Optional[Holiday], int]:
        """Find upcoming holiday within 14 days."""
        for (m_start, d_start, m_end, d_end), holiday in HOLIDAYS_RU.items():
            # Check if current date falls within holiday period
            current_month_day = (d.month, d.day)

            # Handle year wrap (e.g., Dec 20 - Jan 10)
            if m_start > m_end:
                in_period = (
                    current_month_day >= (m_start, d_start)
                    or current_month_day <= (m_end, d_end)
                )
            else:
                in_period = (
                    (m_start, d_start) <= current_month_day <= (m_end, d_end)
                )

            if in_period:
                # Calculate days until end of holiday period
                holiday_end = date(d.year, m_end, d_end)
                if m_start > m_end and d.month <= m_end:
                    pass  # Already in correct year
                elif m_start > m_end:
                    holiday_end = date(d.year + 1, m_end, d_end)

                days_until = (holiday_end - d).days
                return holiday, max(0, days_until)

        return None, 0

    def build_context(
        self, dt: datetime, user_has_profile: bool = False
    ) -> SuggestionContext:
        """Build context for suggestion generation."""
        d = dt.date()
        holiday, days_until = self.get_upcoming_holiday(d)

        return SuggestionContext(
            current_date=d,
            current_hour=dt.hour,
            season=self.get_season(d),
            upcoming_holiday=holiday,
            days_until_holiday=days_until,
            day_of_week=d.weekday(),
            is_weekend=d.weekday() >= 5,
            is_friday_evening=d.weekday() == 4 and dt.hour >= 17,
            user_has_profile=user_has_profile,
        )

    def generate_suggestions(
        self, ctx: SuggestionContext
    ) -> list[WineSuggestion]:
        """Generate 3 contextual wine suggestions."""
        suggestions = []

        # 1. Seasonal suggestion (always)
        season_profile = SEASON_PROFILES[ctx.season]
        suggestions.append(
            WineSuggestion(
                angle="Сезонное",
                hook=season_profile["hook"],
                wine_type=season_profile.get("wine_type"),
                body_min=season_profile.get("body_min"),
                body_max=season_profile.get("body_max"),
                explanation_template=f"Идеально для {self._season_name_ru(ctx.season)}",
            )
        )

        # 2. Holiday / Event based
        if ctx.upcoming_holiday:
            h = ctx.upcoming_holiday
            suggestions.append(
                WineSuggestion(
                    angle=f"К празднику: {h.name}",
                    hook=h.hook_ru,
                    wine_type=h.wine_type,
                    sweetness=h.sweetness,
                    body_min=h.body_min,
                    body_max=h.body_max,
                    country=h.country,
                    explanation_template=f"Отличный выбор для {h.name}",
                )
            )
        elif ctx.is_friday_evening:
            suggestions.append(
                WineSuggestion(
                    angle="Пятничный вечер",
                    hook="Награда за трудовую неделю",
                    price_range=PriceRange.MID,
                    explanation_template="Побалуйте себя после рабочей недели",
                )
            )
        elif ctx.is_weekend:
            suggestions.append(
                WineSuggestion(
                    angle="Выходной эксперимент",
                    hook="Время попробовать новое",
                    is_discovery=True,
                    explanation_template="Выходные — идеальное время для открытий",
                )
            )
        else:
            suggestions.append(
                WineSuggestion(
                    angle="К ужину",
                    hook="Универсальное гастрономическое",
                    body_min=2,
                    body_max=4,
                    explanation_template="Подойдёт к большинству блюд",
                )
            )

        # 3. Discovery or personalized
        if ctx.user_has_profile:
            suggestions.append(
                WineSuggestion(
                    angle="Специально для вас",
                    hook="На основе ваших предпочтений",
                    explanation_template="Подобрано по вашему вкусовому профилю",
                )
            )
        else:
            # Pick a discovery region
            import random

            region, description = random.choice(DISCOVERY_REGIONS)
            suggestions.append(
                WineSuggestion(
                    angle=f"Открытие: {region}",
                    hook=description,
                    is_discovery=True,
                    explanation_template=f"Познакомьтесь с винами {region}",
                )
            )

        return suggestions[:3]

    def _season_name_ru(self, season: Season) -> str:
        """Get Russian season name."""
        names = {
            Season.WINTER: "зимы",
            Season.SPRING: "весны",
            Season.SUMMER: "лета",
            Season.AUTUMN: "осени",
        }
        return names[season]

    def get_event_suggestion(self, event_key: str) -> Optional[WineSuggestion]:
        """Get suggestion for specific event."""
        return EVENT_SUGGESTIONS.get(event_key)


def format_wine_recommendation(
    wine: Wine,
    suggestion: WineSuggestion,
    user_profile: Optional[dict] = None,
) -> str:
    """Format wine recommendation as text."""
    lines = []

    # Header
    lines.append(f"**{wine.name}**")
    lines.append(f"{wine.region}, {wine.country}", )
    if wine.vintage_year:
        lines[-1] += f" · {wine.vintage_year}"
    lines.append(f"~{wine.price_rub:.0f}₽")

    # Grapes
    if wine.grape_varieties:
        lines.append(f"Сорта: {', '.join(wine.grape_varieties)}")

    # Why it fits
    lines.append("")
    explanation_parts = []

    # Context-based explanation
    if suggestion.explanation_template:
        explanation_parts.append(suggestion.explanation_template)

    # Taste notes
    if wine.tasting_notes:
        explanation_parts.append(f"Ноты: {wine.tasting_notes}")

    # Food pairings
    if wine.food_pairings:
        pairings = ", ".join(wine.food_pairings[:3])
        explanation_parts.append(f"Сочетается с: {pairings}")

    lines.append(" ".join(explanation_parts))

    return "\n".join(lines)


def build_proactive_message(
    suggestions: list[WineSuggestion],
    wines: list[Wine],
    user_name: Optional[str] = None,
) -> str:
    """Build complete proactive message with 3 wine suggestions."""
    greeting = "Привет!" if not user_name else f"Привет, {user_name}!"

    lines = [
        greeting,
        "",
        "Вот три идеи для вас сегодня:",
        "",
    ]

    for i, (suggestion, wine) in enumerate(zip(suggestions, wines), 1):
        # Separator
        lines.append("━" * 40)
        lines.append("")

        # Angle badge
        lines.append(f"**{suggestion.angle}**")
        lines.append(f"_{suggestion.hook}_")
        lines.append("")

        # Wine details
        lines.append(format_wine_recommendation(wine, suggestion))
        lines.append("")

    lines.append("━" * 40)
    lines.append("")
    lines.append(
        "Какой вариант вам ближе? Или расскажите, что планируете — "
        "подберу что-то более точное!"
    )

    return "\n".join(lines)
