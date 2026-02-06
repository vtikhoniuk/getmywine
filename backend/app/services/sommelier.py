"""GetMyWine sommelier service - main integration point.

Combines proactive suggestions, prompts, wine catalog, LLM, and real events
for intelligent wine recommendations.
"""

import logging
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import Wine
from app.repositories.wine import WineRepository
from app.services.proactive_suggestions import (
    ProactiveSuggestionEngine,
    SuggestionContext,
    WineSuggestion,
    build_proactive_message,
)
from app.services.sommelier_prompts import (
    SYSTEM_PROMPT_COLD_START,
    SYSTEM_PROMPT_CONTINUATION,
    SYSTEM_PROMPT_PERSONALIZED,
    PROMPT_PROACTIVE_COLD_START,
    PROMPT_PROACTIVE_PERSONALIZED,
    PROMPT_EVENT_RECOMMENDATION,
    PROMPT_FOOD_PAIRING,
    format_wine_catalog_for_prompt,
    format_user_profile_for_prompt,
    get_pairing_hint,
)
from app.services.events import EventsService, get_events_service, Event
from app.services.llm import LLMService, get_llm_service, LLMError
from app.services.session_context import CrossSessionContext

logger = logging.getLogger(__name__)


class SommelierService:
    """Main GetMyWine sommelier service with LLM and real events integration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.wine_repo = WineRepository(db)
        self.suggestion_engine = ProactiveSuggestionEngine()
        self.events_service = get_events_service()
        self.llm_service = get_llm_service()

    async def generate_welcome_with_suggestions(
        self,
        user_profile: Optional[dict] = None,
        user_name: Optional[str] = None,
        use_llm: bool = True,
        cross_session_context: Optional[CrossSessionContext] = None,
    ) -> dict:
        """
        Generate welcome message with 3 proactive wine suggestions.

        Args:
            user_profile: User's taste profile (None for new users)
            user_name: User's name for personalization
            use_llm: Whether to use LLM for message generation
            cross_session_context: Context from previous sessions (for personalization)

        Returns:
            Dict with message, suggestions, wines, and context
        """
        now = datetime.now()
        has_profile = user_profile is not None and bool(user_profile)

        # Get real events context
        day_context = self.events_service.get_day_context(now)
        logger.info(
            "Day context: %s, season=%s, events_today=%d, upcoming=%d",
            day_context["day_of_week"],
            day_context["season"],
            len(day_context["today_events"]),
            len(day_context["upcoming_events"]),
        )

        # Build suggestion context with real events
        ctx = self._build_context_with_events(now, has_profile, day_context)

        # Generate 3 suggestions based on real context
        suggestions = self._generate_suggestions_with_events(ctx, day_context)

        # Find wines for each suggestion
        wines = []
        # Skip wine queries if Wine table doesn't exist (SQLite test environment)
        wines_available = await self._check_wines_available()
        if wines_available:
            for suggestion in suggestions:
                wine = await self._find_wine_for_suggestion(suggestion, user_profile)
                if wine:
                    wines.append(wine)

            # Fill with random wines if needed
            if len(wines) < 3:
                additional = await self.wine_repo.get_list(limit=3 - len(wines))
                wines.extend(additional)

        # Generate message
        if use_llm and self.llm_service.is_available:
            message = await self._generate_llm_welcome(
                suggestions[:len(wines)],
                wines,
                user_name,
                user_profile,
                day_context,
                cross_session_context,
            )
        else:
            message = build_proactive_message(
                suggestions[:len(wines)],
                wines,
                user_name,
            )

        return {
            "message": message,
            "suggestions": suggestions[:len(wines)],
            "wines": wines,
            "context": ctx,
            "day_context": day_context,
            "used_llm": use_llm and self.llm_service.is_available,
        }

    def _build_context_with_events(
        self,
        now: datetime,
        has_profile: bool,
        day_context: dict,
    ) -> SuggestionContext:
        """Build suggestion context enriched with real events."""
        from app.services.proactive_suggestions import Season, Holiday

        # Map season
        season_map = {
            "winter": Season.WINTER,
            "spring": Season.SPRING,
            "summer": Season.SUMMER,
            "autumn": Season.AUTUMN,
        }
        season = season_map.get(day_context["season_key"], Season.WINTER)

        # Get nearest event
        nearest = day_context.get("nearest_event")
        holiday = None
        days_until = 0

        if nearest:
            # Convert Event to Holiday for compatibility
            holiday = Holiday(
                name=nearest.name_ru,
                wine_style=nearest.wine_style.value,
                hook_ru=nearest.hook_ru,
            )
            days_until = nearest.days_until

        return SuggestionContext(
            current_date=day_context["date"],
            current_hour=now.hour,
            season=season,
            upcoming_holiday=holiday,
            days_until_holiday=days_until,
            day_of_week=day_context["day_of_week_num"],
            is_weekend=day_context["is_weekend"],
            is_friday_evening=day_context["is_friday_evening"],
            user_has_profile=has_profile,
        )

    def _generate_suggestions_with_events(
        self,
        ctx: SuggestionContext,
        day_context: dict,
    ) -> list[WineSuggestion]:
        """Generate suggestions using real events."""
        suggestions = []

        # 1. Always add seasonal
        from app.services.proactive_suggestions import SEASON_PROFILES
        season_profile = SEASON_PROFILES[ctx.season]
        suggestions.append(WineSuggestion(
            angle="Сезонное",
            hook=season_profile["hook"],
            wine_type=season_profile.get("wine_type"),
            body_min=season_profile.get("body_min"),
            body_max=season_profile.get("body_max"),
            explanation_template=f"Идеально для {day_context['season'].lower()}",
        ))

        # 2. Event-based (real events take priority)
        today_events = day_context.get("today_events", [])
        upcoming_events = day_context.get("upcoming_events", [])

        if today_events:
            event = today_events[0]
            filters = self.events_service.get_wine_style_filters(event.wine_style)
            suggestions.append(WineSuggestion(
                angle=f"Сегодня: {event.name_ru}",
                hook=event.hook_ru,
                wine_type=filters.get("wine_type"),
                body_min=filters.get("body_min"),
                body_max=filters.get("body_max"),
                country=filters.get("country"),
                explanation_template=event.description_ru,
            ))
        elif upcoming_events:
            event = upcoming_events[0]
            filters = self.events_service.get_wine_style_filters(event.wine_style)
            days_text = "завтра" if event.days_until == 1 else f"через {event.days_until} дн."
            suggestions.append(WineSuggestion(
                angle=f"{event.name_ru} ({days_text})",
                hook=event.hook_ru,
                wine_type=filters.get("wine_type"),
                body_min=filters.get("body_min"),
                body_max=filters.get("body_max"),
                country=filters.get("country"),
                explanation_template=event.description_ru,
            ))
        elif ctx.is_friday_evening:
            from app.models.wine import PriceRange
            suggestions.append(WineSuggestion(
                angle="Пятничный вечер",
                hook="Награда за трудовую неделю",
                price_range=PriceRange.MID,
                explanation_template="Побалуйте себя после рабочей недели",
            ))
        elif ctx.is_weekend:
            suggestions.append(WineSuggestion(
                angle="Выходной эксперимент",
                hook="Время попробовать новое",
                is_discovery=True,
                explanation_template="Выходные — идеальное время для открытий",
            ))
        else:
            suggestions.append(WineSuggestion(
                angle="К ужину",
                hook="Универсальное гастрономическое",
                body_min=2,
                body_max=4,
                explanation_template="Подойдёт к большинству блюд",
            ))

        # 3. Discovery or personalized
        if ctx.user_has_profile:
            suggestions.append(WineSuggestion(
                angle="Специально для вас",
                hook="На основе ваших предпочтений",
                explanation_template="Подобрано по вашему вкусовому профилю",
            ))
        else:
            import random
            from app.services.proactive_suggestions import DISCOVERY_REGIONS
            region, description = random.choice(DISCOVERY_REGIONS)
            suggestions.append(WineSuggestion(
                angle=f"Открытие: {region}",
                hook=description,
                is_discovery=True,
                explanation_template=f"Познакомьтесь с винами региона {region}",
            ))

        return suggestions[:3]

    async def _generate_llm_welcome(
        self,
        suggestions: list[WineSuggestion],
        wines: list[Wine],
        user_name: Optional[str],
        user_profile: Optional[dict],
        day_context: dict,
        cross_session_context: Optional[CrossSessionContext] = None,
    ) -> str:
        """Generate welcome message using LLM."""
        # Build events context for prompt
        events_text = self._format_events_for_prompt(day_context)

        # Build wines context
        wines_text = self._format_wines_for_prompt(wines, suggestions)

        # Build cross-session history text
        history_text = ""
        if cross_session_context and cross_session_context.total_sessions > 0:
            history_text = f"\n\nИСТОРИЯ ПОЛЬЗОВАТЕЛЯ:\n{cross_session_context.to_prompt_text()}"

        # Build user prompt
        user_prompt = f"""КОНТЕКСТ:
- Дата: {day_context['formatted_date']} ({day_context['day_of_week']})
- Сезон: {day_context['season']}
- Время суток: {day_context['time_of_day']}
{events_text}

ПОЛЬЗОВАТЕЛЬ:
- Имя: {user_name or 'не указано'}
- Профиль: {'есть' if user_profile else 'новый пользователь'}{history_text}

ПОДОБРАННЫЕ ВИНА:
{wines_text}

ЗАДАЧА:
Поприветствуй пользователя и представь эти 3 вина как проактивные предложения.
Для каждого вина объясни, почему оно подходит под текущий контекст.
{self._get_history_instruction(cross_session_context)}
Закончи вопросом для продолжения диалога."""

        try:
            response = await self.llm_service.generate_wine_recommendation(
                system_prompt=SYSTEM_PROMPT_COLD_START if not user_profile else SYSTEM_PROMPT_PERSONALIZED,
                user_prompt=user_prompt,
            )
            logger.info("Generated LLM welcome message")
            return response

        except LLMError as e:
            logger.warning("LLM generation failed, using fallback: %s", e)
            return build_proactive_message(suggestions, wines, user_name)

    def _format_events_for_prompt(self, day_context: dict) -> str:
        """Format events for LLM prompt."""
        lines = []

        today_events = day_context.get("today_events", [])
        if today_events:
            lines.append("- СЕГОДНЯ ПРАЗДНИК:")
            for event in today_events:
                lines.append(f"  * {event.name_ru}: {event.description_ru}")

        upcoming = day_context.get("upcoming_events", [])[:3]
        if upcoming:
            lines.append("- Ближайшие события:")
            for event in upcoming:
                days = "завтра" if event.days_until == 1 else f"через {event.days_until} дн."
                lines.append(f"  * {event.name_ru} ({days})")

        if not lines:
            lines.append("- Особых событий нет")

        return "\n".join(lines)

    def _format_wines_for_prompt(
        self,
        wines: list[Wine],
        suggestions: list[WineSuggestion],
    ) -> str:
        """Format wines with suggestion context for LLM prompt."""
        lines = []
        for i, (wine, suggestion) in enumerate(zip(wines, suggestions), 1):
            vintage = f", {wine.vintage_year}" if wine.vintage_year else ""
            grapes = ", ".join(wine.grape_varieties) if wine.grape_varieties else "N/A"
            pairings = ", ".join(wine.food_pairings[:3]) if wine.food_pairings else "N/A"

            lines.append(f"""[{i}] Угол: {suggestion.angle}
   Крючок: {suggestion.hook}
   Вино: {wine.name}
   Регион: {wine.region}, {wine.country}{vintage}
   Сорта: {grapes}
   Цена: {wine.price_rub}₽
   Описание: {wine.description}
   Ноты: {wine.tasting_notes or 'N/A'}
   К блюдам: {pairings}
""")
        return "\n".join(lines)

    def _get_history_instruction(
        self,
        cross_session_context: Optional[CrossSessionContext],
    ) -> str:
        """Get instruction for handling user history."""
        if not cross_session_context or cross_session_context.total_sessions == 0:
            return ""

        lines = []

        # Add instruction to avoid recent wines
        if cross_session_context.recent_wines:
            recent = ", ".join(cross_session_context.recent_wines[:5])
            lines.append(f"ВАЖНО: Старайся НЕ повторять вина из недавних сессий: {recent}")

        # Add instruction to consider preferences
        prefs = cross_session_context.preferences
        if prefs.liked_wines:
            lines.append("Учитывай, что пользователю понравились похожие вина.")
        if prefs.disliked_wines:
            lines.append("Избегай вин, которые пользователь отклонял ранее.")

        return "\n".join(lines)

    async def generate_response(
        self,
        user_message: str,
        user_profile: Optional[dict] = None,
        conversation_history: Optional[list[dict]] = None,
        cross_session_context: Optional[CrossSessionContext] = None,
        is_continuation: bool = False,
    ) -> str:
        """
        Generate AI response to user message using LLM with conversation history.

        Args:
            user_message: User's message
            user_profile: User's taste profile
            conversation_history: Previous messages for context
                Format: [{"role": "user"|"assistant", "content": "..."}]
            cross_session_context: Context from previous sessions

        Returns:
            AI response string
        """
        from app.services.llm import ChatMessage

        # Detect context
        detected_event = detect_event(user_message)
        detected_food = detect_food(user_message)

        # Get prompt data
        if detected_event:
            prompt_data = await self.get_llm_prompt_for_event(
                user_message=user_message,
                event=detected_event,
                food=detected_food,
                user_profile=user_profile,
            )
        elif detected_food:
            prompt_data = await self.get_llm_prompt_for_food_pairing(
                user_message=user_message,
                food_item=detected_food,
                user_profile=user_profile,
            )
        else:
            # Generic request
            if user_profile:
                prompt_data = await self.get_llm_prompt_for_personalized(
                    user_profile=user_profile,
                )
            else:
                prompt_data = await self.get_llm_prompt_for_cold_start()

        # Add real events context
        day_context = self.events_service.get_day_context()
        events_context = self._format_events_for_prompt(day_context)

        # Build cross-session history text
        history_text = ""
        history_instruction = ""
        if cross_session_context and cross_session_context.total_sessions > 0:
            history_text = f"\n\n{cross_session_context.to_prompt_text()}"
            history_instruction = self._get_history_instruction(cross_session_context)
            if history_instruction:
                history_instruction = f"\n\n{history_instruction}"

        # Enhance user prompt with events
        enhanced_prompt = f"""ТЕКУЩИЙ КОНТЕКСТ:
{events_context}{history_text}

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{user_message}{history_instruction}

---

{prompt_data['user_prompt']}"""

        # Convert conversation history to ChatMessage format
        history: Optional[list[ChatMessage]] = None
        if conversation_history:
            history = [
                ChatMessage(role=msg["role"], content=msg["content"])
                for msg in conversation_history
                if msg.get("role") in ("user", "assistant")
            ]
            logger.debug("Using %d messages from conversation history", len(history))

        # Append continuation instruction when not the first message
        system_prompt = prompt_data["system_prompt"]
        if is_continuation:
            system_prompt += SYSTEM_PROMPT_CONTINUATION

        # Try LLM, fallback to mock
        if self.llm_service.is_available:
            try:
                response = await self.llm_service.generate_wine_recommendation(
                    system_prompt=system_prompt,
                    user_prompt=enhanced_prompt,
                    history=history,
                )
                logger.info(
                    "Generated LLM response for: %s (history: %d msgs)",
                    user_message[:50],
                    len(history) if history else 0,
                )
                return response

            except LLMError as e:
                logger.warning("LLM failed, using mock: %s", e)

        # Fallback to mock
        from app.services.ai_mock import MockAIService
        mock = MockAIService()
        return await mock.generate_response_with_context(
            user_message=user_message,
            detected_event=detected_event,
            detected_food=detected_food,
        )

    async def _find_wine_for_suggestion(
        self,
        suggestion: WineSuggestion,
        user_profile: Optional[dict] = None,
    ) -> Optional[Wine]:
        """Find a wine matching the suggestion criteria."""
        filters = {}

        if suggestion.wine_type:
            filters["wine_type"] = suggestion.wine_type
        if suggestion.sweetness:
            filters["sweetness"] = suggestion.sweetness
        if suggestion.body_min:
            filters["body_min"] = suggestion.body_min
        if suggestion.body_max:
            filters["body_max"] = suggestion.body_max

        # Apply price range filter
        if suggestion.price_range:
            from app.models.wine import PriceRange
            if suggestion.price_range == PriceRange.BUDGET:
                filters["price_max"] = 30
            elif suggestion.price_range == PriceRange.MID:
                filters["price_min"] = 30
                filters["price_max"] = 100
            elif suggestion.price_range == PriceRange.PREMIUM:
                filters["price_min"] = 100

        # Apply user profile preferences
        if user_profile:
            if user_profile.get("budget_max"):
                filters["price_max"] = min(
                    filters.get("price_max", 9999),
                    user_profile["budget_max"]
                )

        # Get wines
        wines = await self.wine_repo.get_list(limit=1, **filters)

        # Fallback if no wines found with strict criteria
        if not wines:
            wines = await self.wine_repo.get_list(limit=1)

        return wines[0] if wines else None

    _wines_available: bool | None = None  # Cache: True/False/None(unchecked)

    async def _check_wines_available(self) -> bool:
        """Check if Wine table is available (may not exist in SQLite tests)."""
        # Return cached result if available
        if SommelierService._wines_available is not None:
            return SommelierService._wines_available

        from sqlalchemy import text
        try:
            # Use savepoint to protect the transaction
            # This works for both PostgreSQL and SQLite
            async with self.db.begin_nested():
                result = await self.db.execute(text("SELECT 1 FROM wines LIMIT 0"))
            SommelierService._wines_available = True
        except Exception:
            # Table doesn't exist or query failed
            SommelierService._wines_available = False

        return SommelierService._wines_available

    async def get_llm_prompt_for_cold_start(self) -> dict:
        """
        Get complete LLM prompt for cold start scenario.

        Returns system prompt and user prompt with wine catalog.
        """
        now = datetime.now()
        ctx = self.suggestion_engine.build_context(now, user_has_profile=False)
        suggestions = self.suggestion_engine.generate_suggestions(ctx)

        # Get diverse wine selection for catalog
        wines = await self.wine_repo.get_list(limit=20)
        catalog_text = format_wine_catalog_for_prompt(wines)

        # Build context strings
        day_names_ru = {
            0: "Понедельник", 1: "Вторник", 2: "Среда",
            3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
        }
        season_names_ru = {
            "winter": "Зима", "spring": "Весна",
            "summer": "Лето", "autumn": "Осень"
        }
        time_of_day = "вечер" if 17 <= now.hour <= 23 else (
            "утро" if 6 <= now.hour <= 11 else "день"
        )

        user_prompt = PROMPT_PROACTIVE_COLD_START.format(
            current_date=now.strftime("%d.%m.%Y"),
            day_of_week=day_names_ru[now.weekday()],
            season=season_names_ru[ctx.season.value],
            upcoming_holiday=ctx.upcoming_holiday.name if ctx.upcoming_holiday else "нет",
            days_until=ctx.days_until_holiday if ctx.upcoming_holiday else "—",
            time_of_day=time_of_day,
            season_hook=suggestions[0].hook if suggestions else "",
            holiday_hook=suggestions[1].hook if len(suggestions) > 1 and ctx.upcoming_holiday else "—",
            event_hook=suggestions[1].hook if len(suggestions) > 1 else "",
            wine_catalog=catalog_text,
        )

        return {
            "system_prompt": SYSTEM_PROMPT_COLD_START,
            "user_prompt": user_prompt,
            "context": ctx,
            "wines_in_prompt": len(wines),
        }

    async def get_llm_prompt_for_personalized(
        self,
        user_profile: dict,
        user_name: str = "пользователь",
        liked_wines: Optional[list[str]] = None,
        disliked_wines: Optional[list[str]] = None,
    ) -> dict:
        """
        Get complete LLM prompt for personalized recommendations.

        Args:
            user_profile: User's taste profile
            user_name: User's name
            liked_wines: List of wine names user liked
            disliked_wines: List of wine names user disliked

        Returns system prompt and user prompt with filtered catalog.
        """
        now = datetime.now()
        ctx = self.suggestion_engine.build_context(now, user_has_profile=True)

        # Filter wines based on profile
        filters = {}
        if user_profile.get("preferred_sweetness"):
            filters["sweetness"] = user_profile["preferred_sweetness"]
        if user_profile.get("budget_max"):
            filters["price_max"] = user_profile["budget_max"]

        wines = await self.wine_repo.get_list(limit=20, **filters)
        catalog_text = format_wine_catalog_for_prompt(wines)

        day_names_ru = {
            0: "Понедельник", 1: "Вторник", 2: "Среда",
            3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
        }
        season_names_ru = {
            "winter": "Зима", "spring": "Весна",
            "summer": "Лето", "autumn": "Осень"
        }

        user_prompt = PROMPT_PROACTIVE_PERSONALIZED.format(
            user_name=user_name,
            sweetness_pref=user_profile.get("sweetness_pref", "не указано"),
            body_pref=user_profile.get("body_pref", "не указано"),
            favorite_regions=", ".join(user_profile.get("favorite_regions", [])) or "не указано",
            dislikes=", ".join(user_profile.get("dislikes", [])) or "нет",
            budget_range=user_profile.get("budget", "не указан"),
            liked_wines=", ".join(liked_wines or []) or "пока нет",
            disliked_wines=", ".join(disliked_wines or []) or "пока нет",
            current_date=now.strftime("%d.%m.%Y"),
            day_of_week=day_names_ru[now.weekday()],
            season=season_names_ru[ctx.season.value],
            upcoming_holiday=ctx.upcoming_holiday.name if ctx.upcoming_holiday else "нет",
            filtered_catalog=catalog_text,
        )

        return {
            "system_prompt": SYSTEM_PROMPT_PERSONALIZED,
            "user_prompt": user_prompt,
            "context": ctx,
            "wines_in_prompt": len(wines),
        }

    async def get_llm_prompt_for_event(
        self,
        user_message: str,
        event: str,
        food: Optional[str] = None,
        guest_count: Optional[int] = None,
        user_profile: Optional[dict] = None,
    ) -> dict:
        """
        Get LLM prompt for event-based recommendation.

        Args:
            user_message: Original user message
            event: Detected event type
            food: Detected food/dish (if any)
            guest_count: Number of guests (if mentioned)
            user_profile: User's taste profile

        Returns system prompt and user prompt.
        """
        wines = await self.wine_repo.get_list(limit=20)
        catalog_text = format_wine_catalog_for_prompt(wines)
        profile_text = format_user_profile_for_prompt(user_profile)

        user_prompt = PROMPT_EVENT_RECOMMENDATION.format(
            user_message=user_message,
            detected_event=event,
            detected_food=food or "не указано",
            guest_count=guest_count or "не указано",
            special_requirements="нет",
            user_profile=profile_text,
            wine_catalog=catalog_text,
        )

        system = SYSTEM_PROMPT_PERSONALIZED if user_profile else SYSTEM_PROMPT_COLD_START

        return {
            "system_prompt": system,
            "user_prompt": user_prompt,
            "wines_in_prompt": len(wines),
        }

    async def get_llm_prompt_for_food_pairing(
        self,
        user_message: str,
        food_item: str,
        user_profile: Optional[dict] = None,
    ) -> dict:
        """
        Get LLM prompt for food pairing recommendation.

        Args:
            user_message: Original user message
            food_item: Detected food/dish
            user_profile: User's taste profile

        Returns system prompt and user prompt.
        """
        wines = await self.wine_repo.get_list(limit=20)
        catalog_text = format_wine_catalog_for_prompt(wines)
        profile_text = format_user_profile_for_prompt(user_profile)
        pairing_hint = get_pairing_hint(food_item)

        user_prompt = PROMPT_FOOD_PAIRING.format(
            user_message=user_message,
            food_item=food_item,
            pairing_hints=pairing_hint,
            user_profile=profile_text,
            wine_catalog=catalog_text,
        )

        system = SYSTEM_PROMPT_PERSONALIZED if user_profile else SYSTEM_PROMPT_COLD_START

        return {
            "system_prompt": system,
            "user_prompt": user_prompt,
            "wines_in_prompt": len(wines),
        }


# =============================================================================
# EVENT DETECTION (simple keyword-based)
# =============================================================================

EVENT_KEYWORDS = {
    "dinner_for_two": ["романтический", "свидание", "вдвоём", "на двоих", "романтика"],
    "friends_gathering": ["друзья", "компания", "вечеринка", "посиделки", "гости"],
    "bbq": ["шашлык", "барбекю", "гриль", "мангал", "дача"],
    "business": ["деловой", "партнёры", "коллеги", "бизнес", "переговоры"],
    "gift": ["подарок", "подарить", "в подарок", "презент"],
    "celebration": ["праздник", "день рождения", "юбилей", "отмечаем"],
}

FOOD_KEYWORDS = [
    "стейк", "мясо", "рыба", "морепродукты", "паста", "пицца",
    "сыр", "салат", "десерт", "шоколад", "фрукты", "курица",
    "свинина", "баранина", "утка", "устрицы", "креветки",
]


def detect_event(message: str) -> Optional[str]:
    """Detect event type from user message."""
    message_lower = message.lower()
    for event_type, keywords in EVENT_KEYWORDS.items():
        if any(kw in message_lower for kw in keywords):
            return event_type
    return None


def detect_food(message: str) -> Optional[str]:
    """Detect food item from user message."""
    message_lower = message.lower()
    for food in FOOD_KEYWORDS:
        if food in message_lower:
            return food
    return None
