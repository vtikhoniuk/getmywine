"""Events and holidays service for contextual wine recommendations.

Provides real-time context based on:
- Russian holidays and celebrations
- Seasonal events
- Day of week patterns
- Optional weather integration
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Type of event."""
    HOLIDAY = "holiday"
    CELEBRATION = "celebration"
    SEASONAL = "seasonal"
    CULTURAL = "cultural"
    SPORT = "sport"
    PERSONAL = "personal"


class WineStyle(str, Enum):
    """Suggested wine style for event."""
    SPARKLING = "sparkling"
    FESTIVE_RED = "festive_red"
    ELEGANT_WHITE = "elegant_white"
    ROMANTIC_ROSE = "romantic_rose"
    BOLD_RED = "bold_red"
    LIGHT_WHITE = "light_white"
    RUSSIAN = "russian"
    PREMIUM = "premium"
    CASUAL = "casual"


@dataclass
class Event:
    """Event or holiday with wine pairing context."""
    name: str
    name_ru: str
    event_type: EventType
    date: date
    days_until: int
    wine_style: WineStyle
    hook_ru: str
    description_ru: str
    is_today: bool = False
    is_upcoming: bool = False  # Within 7 days


# Russian holidays - static calendar
# Format: (month, day, name, name_ru, type, wine_style, hook, description)
RUSSIAN_HOLIDAYS = [
    # Major holidays
    (1, 1, "New Year", "Новый год", EventType.HOLIDAY, WineStyle.SPARKLING,
     "С Новым годом!", "Главный праздник года — время для шампанского и волшебства"),
    (1, 7, "Orthodox Christmas", "Рождество Христово", EventType.HOLIDAY, WineStyle.FESTIVE_RED,
     "Светлого Рождества!", "Традиционный праздник — красное вино к праздничному столу"),
    (2, 14, "Valentine's Day", "День святого Валентина", EventType.CELEBRATION, WineStyle.ROMANTIC_ROSE,
     "Любовь в воздухе", "Романтический повод для особенного вина"),
    (2, 23, "Defender's Day", "День защитника Отечества", EventType.HOLIDAY, WineStyle.BOLD_RED,
     "С праздником!", "Вино с характером для настоящих мужчин"),
    (3, 8, "Women's Day", "Международный женский день", EventType.HOLIDAY, WineStyle.ELEGANT_WHITE,
     "С 8 марта!", "Элегантное вино для прекрасных дам"),
    (5, 1, "Spring and Labor Day", "Праздник Весны и Труда", EventType.HOLIDAY, WineStyle.CASUAL,
     "С праздником весны!", "Отдых на природе — лёгкие вина для пикника"),
    (5, 9, "Victory Day", "День Победы", EventType.HOLIDAY, WineStyle.RUSSIAN,
     "С Днём Победы!", "Российские вина — дань уважения"),
    (6, 12, "Russia Day", "День России", EventType.HOLIDAY, WineStyle.RUSSIAN,
     "С Днём России!", "Гордость за отечественное виноделие"),
    (11, 4, "Unity Day", "День народного единства", EventType.HOLIDAY, WineStyle.RUSSIAN,
     "С праздником!", "Российские вина к праздничному столу"),
    (12, 31, "New Year's Eve", "Новогодняя ночь", EventType.HOLIDAY, WineStyle.SPARKLING,
     "Встречаем Новый год!", "Шампанское для главной ночи года"),

    # Cultural events
    (9, 1, "Knowledge Day", "День знаний", EventType.CULTURAL, WineStyle.CASUAL,
     "С началом учебного года!", "Повод собраться семьёй"),
    (10, 5, "Teacher's Day", "День учителя", EventType.CULTURAL, WineStyle.ELEGANT_WHITE,
     "С Днём учителя!", "Благодарность в бокале"),

    # Seasonal markers
    (3, 20, "Spring Equinox", "Весеннее равноденствие", EventType.SEASONAL, WineStyle.LIGHT_WHITE,
     "Весна пришла!", "Свежие вина для нового сезона"),
    (6, 21, "Summer Solstice", "Летнее солнцестояние", EventType.SEASONAL, WineStyle.LIGHT_WHITE,
     "Самый длинный день!", "Освежающие вина для жаркого лета"),
    (9, 22, "Autumn Equinox", "Осеннее равноденствие", EventType.SEASONAL, WineStyle.FESTIVE_RED,
     "Золотая осень", "Насыщенные вина для уютных вечеров"),
    (12, 21, "Winter Solstice", "Зимнее солнцестояние", EventType.SEASONAL, WineStyle.BOLD_RED,
     "Самая длинная ночь", "Согревающие вина для зимы"),
]

# Easter dates (Orthodox) - needs to be calculated dynamically
ORTHODOX_EASTER_DATES = {
    2024: date(2024, 5, 5),
    2025: date(2025, 4, 20),
    2026: date(2026, 4, 12),
    2027: date(2027, 5, 2),
    2028: date(2028, 4, 16),
    2029: date(2029, 4, 8),
    2030: date(2030, 4, 28),
}


class EventsService:
    """Service for getting contextual events and holidays."""

    def __init__(self):
        self.settings = get_settings()

    def get_today_events(self, target_date: Optional[date] = None) -> list[Event]:
        """Get events happening today."""
        d = target_date or date.today()
        events = []

        for holiday in RUSSIAN_HOLIDAYS:
            month, day, name, name_ru, event_type, wine_style, hook, desc = holiday
            if d.month == month and d.day == day:
                events.append(Event(
                    name=name,
                    name_ru=name_ru,
                    event_type=event_type,
                    date=d,
                    days_until=0,
                    wine_style=wine_style,
                    hook_ru=hook,
                    description_ru=desc,
                    is_today=True,
                    is_upcoming=True,
                ))

        # Check Easter
        easter = ORTHODOX_EASTER_DATES.get(d.year)
        if easter and d == easter:
            events.append(Event(
                name="Orthodox Easter",
                name_ru="Пасха",
                event_type=EventType.HOLIDAY,
                date=d,
                days_until=0,
                wine_style=WineStyle.FESTIVE_RED,
                hook_ru="Христос Воскресе!",
                description_ru="Светлое Христово Воскресение — вино к куличам и пасхе",
                is_today=True,
                is_upcoming=True,
            ))

        return events

    def get_upcoming_events(
        self,
        target_date: Optional[date] = None,
        days_ahead: int = 14,
    ) -> list[Event]:
        """Get events coming up in the next N days."""
        d = target_date or date.today()
        events = []

        for holiday in RUSSIAN_HOLIDAYS:
            month, day, name, name_ru, event_type, wine_style, hook, desc = holiday

            # Calculate event date for this year
            try:
                event_date = date(d.year, month, day)
            except ValueError:
                continue  # Invalid date (e.g., Feb 30)

            # If event already passed, check next year
            if event_date < d:
                event_date = date(d.year + 1, month, day)

            days_until = (event_date - d).days

            if 0 < days_until <= days_ahead:
                events.append(Event(
                    name=name,
                    name_ru=name_ru,
                    event_type=event_type,
                    date=event_date,
                    days_until=days_until,
                    wine_style=wine_style,
                    hook_ru=hook,
                    description_ru=desc,
                    is_today=False,
                    is_upcoming=True,
                ))

        # Check Easter
        easter = ORTHODOX_EASTER_DATES.get(d.year)
        if easter:
            days_until = (easter - d).days
            if 0 < days_until <= days_ahead:
                events.append(Event(
                    name="Orthodox Easter",
                    name_ru="Пасха",
                    event_type=EventType.HOLIDAY,
                    date=easter,
                    days_until=days_until,
                    wine_style=WineStyle.FESTIVE_RED,
                    hook_ru="Пасха приближается!",
                    description_ru="Готовьтесь к Светлому Христову Воскресению",
                    is_today=False,
                    is_upcoming=True,
                ))

        # Sort by days until
        events.sort(key=lambda e: e.days_until)

        return events

    def get_nearest_event(
        self,
        target_date: Optional[date] = None,
        days_ahead: int = 14,
    ) -> Optional[Event]:
        """Get the nearest upcoming event."""
        # First check if there's an event today
        today_events = self.get_today_events(target_date)
        if today_events:
            return today_events[0]

        # Then check upcoming
        upcoming = self.get_upcoming_events(target_date, days_ahead)
        return upcoming[0] if upcoming else None

    def get_day_context(
        self,
        target_datetime: Optional[datetime] = None,
    ) -> dict:
        """
        Get comprehensive context for the current day.

        Returns dict with:
        - today_events: Events happening today
        - upcoming_events: Events in next 14 days
        - nearest_event: The closest event
        - day_of_week: Day name in Russian
        - is_weekend: Whether it's weekend
        - is_friday_evening: Whether it's Friday after 17:00
        - season: Current season
        - time_of_day: Morning/day/evening/night
        """
        dt = target_datetime or datetime.now()
        d = dt.date()

        # Day of week
        day_names_ru = [
            "Понедельник", "Вторник", "Среда", "Четверг",
            "Пятница", "Суббота", "Воскресенье"
        ]
        day_of_week = day_names_ru[d.weekday()]
        is_weekend = d.weekday() >= 5
        is_friday_evening = d.weekday() == 4 and dt.hour >= 17

        # Season
        month = d.month
        if month in (12, 1, 2):
            season = "Зима"
            season_key = "winter"
        elif month in (3, 4, 5):
            season = "Весна"
            season_key = "spring"
        elif month in (6, 7, 8):
            season = "Лето"
            season_key = "summer"
        else:
            season = "Осень"
            season_key = "autumn"

        # Time of day
        hour = dt.hour
        if 6 <= hour < 12:
            time_of_day = "утро"
        elif 12 <= hour < 17:
            time_of_day = "день"
        elif 17 <= hour < 23:
            time_of_day = "вечер"
        else:
            time_of_day = "ночь"

        return {
            "date": d,
            "datetime": dt,
            "today_events": self.get_today_events(d),
            "upcoming_events": self.get_upcoming_events(d),
            "nearest_event": self.get_nearest_event(d),
            "day_of_week": day_of_week,
            "day_of_week_num": d.weekday(),
            "is_weekend": is_weekend,
            "is_friday_evening": is_friday_evening,
            "season": season,
            "season_key": season_key,
            "time_of_day": time_of_day,
            "formatted_date": d.strftime("%d.%m.%Y"),
        }

    def format_event_for_prompt(self, event: Event) -> str:
        """Format event for inclusion in LLM prompt."""
        if event.is_today:
            timing = "СЕГОДНЯ"
        elif event.days_until == 1:
            timing = "ЗАВТРА"
        elif event.days_until <= 7:
            timing = f"через {event.days_until} дней"
        else:
            timing = f"через {event.days_until} дней ({event.date.strftime('%d.%m')})"

        return f"{event.name_ru} ({timing}): {event.description_ru}"

    def get_wine_style_filters(self, wine_style: WineStyle) -> dict:
        """Convert wine style to repository filters."""
        from app.models.wine import WineType, Sweetness

        filters = {}

        if wine_style == WineStyle.SPARKLING:
            filters["wine_type"] = WineType.SPARKLING
        elif wine_style == WineStyle.FESTIVE_RED:
            filters["wine_type"] = WineType.RED
            filters["body_min"] = 3
        elif wine_style == WineStyle.ELEGANT_WHITE:
            filters["wine_type"] = WineType.WHITE
            filters["body_max"] = 3
        elif wine_style == WineStyle.ROMANTIC_ROSE:
            filters["wine_type"] = WineType.ROSE
        elif wine_style == WineStyle.BOLD_RED:
            filters["wine_type"] = WineType.RED
            filters["body_min"] = 4
        elif wine_style == WineStyle.LIGHT_WHITE:
            filters["wine_type"] = WineType.WHITE
            filters["body_max"] = 2
        elif wine_style == WineStyle.RUSSIAN:
            filters["country"] = "Russia"
        elif wine_style == WineStyle.PREMIUM:
            filters["price_min"] = 100
        elif wine_style == WineStyle.CASUAL:
            filters["price_max"] = 30

        return filters


# Singleton instance
_events_service: Optional[EventsService] = None


def get_events_service() -> EventsService:
    """Get or create events service singleton."""
    global _events_service
    if _events_service is None:
        _events_service = EventsService()
    return _events_service
