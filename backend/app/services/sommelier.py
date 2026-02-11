"""GetMyWine sommelier service - main integration point.

Combines proactive suggestions, prompts, wine catalog, LLM, and real events
for intelligent wine recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Optional
import uuid

try:
    from langfuse.decorators import observe, langfuse_context
except ImportError:
    def observe(**kwargs):
        def decorator(func):
            return func
        return decorator
    langfuse_context = None

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
        Generate AI response to user message using agentic RAG with tool use.

        The LLM decides which tools to call (search_wines, semantic_search)
        based on the user's message. Replaces the previous 4-path routing.

        Args:
            user_message: User's message
            user_profile: User's taste profile
            conversation_history: Previous messages for context
                Format: [{"role": "user"|"assistant", "content": "..."}]
            cross_session_context: Context from previous sessions
            is_continuation: Whether this continues an existing conversation

        Returns:
            AI response string
        """
        from app.services.sommelier_prompts import SYSTEM_PROMPT_AGENTIC

        # Build events context
        day_context = self.events_service.get_day_context()
        events_context = self._format_events_for_prompt(day_context)

        # Enrich events context with cross-session data
        if cross_session_context and cross_session_context.total_sessions > 0:
            events_context += f"\n\n{cross_session_context.to_prompt_text()}"
            history_instruction = self._get_history_instruction(cross_session_context)
            if history_instruction:
                events_context += f"\n\n{history_instruction}"

        # Build system prompt
        system_prompt = SYSTEM_PROMPT_AGENTIC
        if is_continuation:
            system_prompt += SYSTEM_PROMPT_CONTINUATION

        # Try agentic response
        if self.llm_service.is_available:
            result = await self.generate_agentic_response(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history,
                user_profile=user_profile,
                events_context=events_context,
            )

            if result is not None:
                logger.info(
                    "Generated agentic response for: %s (history: %d msgs)",
                    user_message[:50],
                    len(conversation_history) if conversation_history else 0,
                )
                return result

            logger.warning("Agent loop returned None, trying LLM without tools")

            # Fallback: regular LLM call with wines embedded in prompt
            fallback = await self._generate_llm_with_catalog(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history,
                user_profile=user_profile,
                events_context=events_context,
            )
            if fallback is not None:
                return fallback

            logger.warning("LLM fallback also failed, using mock")

        # Final fallback to mock (no LLM available at all)
        from app.services.ai_mock import MockAIService
        mock = MockAIService()
        return await mock.generate_response_with_context(
            user_message=user_message,
            detected_event=detect_event(user_message),
            detected_food=detect_food(user_message),
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
                filters["price_max"] = 1500
            elif suggestion.price_range == PriceRange.MID:
                filters["price_min"] = 1500
                filters["price_max"] = 5000
            elif suggestion.price_range == PriceRange.PREMIUM:
                filters["price_min"] = 5000

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

    async def _generate_llm_with_catalog(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
        user_profile: Optional[dict] = None,
        events_context: Optional[str] = None,
    ) -> Optional[str]:
        """Fallback: regular LLM call with wines embedded in the prompt.

        Used when tool-use (generate_with_tools) is not supported by the
        current LLM provider. Loads wines from the catalog and passes them
        directly in the prompt, similar to the pre-agentic flow.
        """
        from app.services.sommelier_prompts import (
            SYSTEM_PROMPT_BASE,
            build_unified_user_prompt,
        )

        try:
            wines = await self.wine_repo.get_list(limit=20, with_image=True)
            if not wines:
                wines = await self.wine_repo.get_list(limit=20)

            wines_text = self._format_catalog_for_fallback(wines)

            user_prompt = build_unified_user_prompt(
                user_message=user_message,
                user_profile=user_profile,
                events_context=events_context,
            )
            user_prompt += f"\n\nКАТАЛОГ ВИН ДЛЯ РЕКОМЕНДАЦИИ:\n{wines_text}"

            # Build history
            history = None
            if conversation_history:
                from app.services.llm import ChatMessage
                history = [
                    ChatMessage(role=m["role"], content=m["content"])
                    for m in conversation_history
                ]

            result = await self.llm_service.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=history,
            )
            logger.info("Generated LLM fallback response (no tools)")
            return result

        except Exception as e:
            logger.exception("LLM fallback with catalog also failed: %s", e)
            return None

    @staticmethod
    def _format_catalog_for_fallback(wines: list[Wine]) -> str:
        """Format wines for inclusion in fallback prompt."""
        lines = []
        for wine in wines:
            grapes = ", ".join(wine.grape_varieties) if wine.grape_varieties else ""
            pairings = ", ".join(wine.food_pairings[:3]) if wine.food_pairings else ""
            line = (
                f"- {wine.name} | {wine.producer} | {wine.country}, {wine.region} | "
                f"{wine.wine_type.value}, {wine.sweetness.value} | "
                f"{wine.price_rub}₽ | Сорта: {grapes} | К блюдам: {pairings}"
            )
            if wine.description:
                line += f" | {wine.description[:80]}"
            lines.append(line)
        return "\n".join(lines)

    @observe(name="execute_search_wines")
    async def execute_search_wines(self, arguments: dict) -> str:
        """Execute search_wines tool: map arguments to WineRepository.get_list().

        Validates enum values (invalid silently ignored), handles price logic,
        and returns formatted JSON response.
        """
        from app.models.wine import Sweetness, WineType

        filters = {}
        filters_applied = {}

        # Map wine_type enum
        wine_type_str = arguments.get("wine_type")
        if wine_type_str:
            try:
                filters["wine_type"] = WineType(wine_type_str)
                filters_applied["wine_type"] = wine_type_str
            except ValueError:
                pass  # Invalid enum value, silently ignore

        # Map sweetness enum
        sweetness_str = arguments.get("sweetness")
        if sweetness_str:
            try:
                filters["sweetness"] = Sweetness(sweetness_str)
                filters_applied["sweetness"] = sweetness_str
            except ValueError:
                pass

        # Pass through string filters
        for key in ("country", "region", "grape_variety", "food_pairing"):
            value = arguments.get(key)
            if value:
                filters[key] = value
                filters_applied[key] = value

        # Handle price range
        price_min = arguments.get("price_min")
        price_max = arguments.get("price_max")

        if price_min is not None and price_max is not None and price_min > price_max:
            price_min = None  # Drop invalid price_min

        if price_max is not None:
            filters["price_max"] = price_max
            filters_applied["price_max"] = price_max
        if price_min is not None:
            filters["price_min"] = price_min
            filters_applied["price_min"] = price_min

        wines = await self.wine_repo.get_list(**filters)

        # Progressive auto-broadening: drop filters in order of priority until results found
        # Step 1: drop wine_type/sweetness (LLM often guesses these)
        # Step 2: also drop country (catalog may not have wines from requested country)
        _BROADENING_STEPS = [
            ("wine_type", "sweetness"),
            ("country",),
        ]
        if not wines:
            current = dict(filters)
            all_dropped: list[str] = []
            for drop_keys in _BROADENING_STEPS:
                droppable = [k for k in drop_keys if k in current]
                if not droppable:
                    continue
                for k in droppable:
                    current.pop(k)
                    all_dropped.append(k)
                wines = await self.wine_repo.get_list(**current)
                if wines:
                    logger.info(
                        "search_wines: broadened search (dropped %s), found=%d",
                        all_dropped, len(wines),
                    )
                    for k in all_dropped:
                        filters_applied.pop(k, None)
                    filters_applied["broadened"] = True
                    break

        logger.info("search_wines tool: filters=%s, found=%d", filters_applied, len(wines))

        return format_tool_response(wines, filters_applied)

    @observe(name="execute_semantic_search")
    async def execute_semantic_search(self, arguments: dict) -> str:
        """Execute semantic_search tool: embed query and search via pgvector.

        Generates embedding for the query text, calls WineRepository.semantic_search()
        with optional filters (wine_type, price_max), and returns formatted JSON response
        with similarity scores.
        """
        from app.models.wine import WineType

        query = arguments.get("query", "")
        filters_applied = {"query": query}

        # Generate embedding for user's query
        embedding = await self.llm_service.get_query_embedding(query)

        # Build optional filters
        search_kwargs: dict = {}

        wine_type_str = arguments.get("wine_type")
        if wine_type_str:
            try:
                search_kwargs["wine_type"] = WineType(wine_type_str)
                filters_applied["wine_type"] = wine_type_str
            except ValueError:
                pass

        price_max = arguments.get("price_max")
        if price_max is not None:
            search_kwargs["price_max"] = price_max
            filters_applied["price_max"] = price_max

        results = await self.wine_repo.semantic_search(embedding, **search_kwargs)

        logger.info("semantic_search tool: query=%r, found=%d", query[:50], len(results))

        return format_semantic_response(results, filters_applied)

    @observe(name="generate_agentic_response")
    async def generate_agentic_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
        user_profile: Optional[dict] = None,
        events_context: Optional[str] = None,
    ) -> Optional[str]:
        """Agent loop: LLM -> tool_calls -> execute -> repeat (max iterations).

        Returns the final text content from LLM, or None on error (caller handles fallback).
        """
        from app.config import get_settings
        from app.services.sommelier_prompts import WINE_TOOLS, build_unified_user_prompt

        settings = get_settings()
        max_iterations = settings.agent_max_iterations

        # Build user prompt with context
        user_prompt = build_unified_user_prompt(
            user_message=user_message,
            user_profile=user_profile,
            events_context=events_context,
        )

        # Build initial messages
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_prompt})

        tools_used: list[str] = []

        try:
            iteration = 0
            while iteration < max_iterations:
                response = await self.llm_service.generate_with_tools(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=WINE_TOOLS,
                    messages=messages,
                )

                # No tool calls — return content directly
                if not response.tool_calls:
                    self._update_langfuse_metadata(tools_used, iteration)
                    logger.debug(
                        "Agent loop done: iterations=%d, tools_used=%s, content_start=%r",
                        iteration, tools_used, (response.content or "")[:150],
                    )
                    return response.content

                # Append assistant message with tool_calls as a dict
                assistant_msg = {"role": "assistant", "content": response.content}
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.tool_calls
                ]
                messages.append(assistant_msg)

                # Execute each tool call and append results
                for tool_call in response.tool_calls:
                    name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    tools_used.append(name)

                    if name == "search_wines":
                        result = await self.execute_search_wines(arguments)
                    elif name == "semantic_search":
                        result = await self.execute_semantic_search(arguments)
                    else:
                        result = json.dumps({"error": f"Unknown tool: {name}"})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

                iteration += 1

            # Max iterations reached — final call without tools
            response = await self.llm_service.generate_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=None,
                messages=messages,
            )
            self._update_langfuse_metadata(tools_used, iteration)
            return response.content

        except Exception as e:
            logger.exception("Agent loop error (tool use may not be supported): %s", e)
            return None

    @staticmethod
    def _update_langfuse_metadata(tools_used: list[str], iterations: int) -> None:
        """Update current Langfuse observation with agent loop metadata."""
        if langfuse_context is None:
            return
        try:
            langfuse_context.update_current_observation(
                metadata={
                    "tools_used": tools_used,
                    "iterations": iterations,
                },
            )
        except Exception:
            pass  # Non-critical: don't break agent loop if Langfuse fails


# =============================================================================
# TOOL RESPONSE FORMATTING
# =============================================================================


def format_tool_response(wines: list, filters_applied: dict) -> str:
    """Format wine search results as JSON string for tool response."""
    wine_list = []
    for wine in wines:
        wine_data = {
            "name": wine.name,
            "producer": wine.producer,
            "region": wine.region,
            "country": wine.country,
            "vintage_year": wine.vintage_year,
            "grape_varieties": wine.grape_varieties,
            "wine_type": wine.wine_type.value,
            "sweetness": wine.sweetness.value,
            "body": wine.body,
            "tannins": wine.tannins,
            "acidity": wine.acidity,
            "price_rub": float(wine.price_rub),
            "description": wine.description,
            "tasting_notes": wine.tasting_notes,
            "food_pairings": wine.food_pairings,
        }
        wine_list.append(wine_data)

    return json.dumps(
        {
            "found": len(wine_list),
            "wines": wine_list,
            "filters_applied": filters_applied,
        },
        ensure_ascii=False,
    )


def format_semantic_response(
    results: list[tuple], filters_applied: dict
) -> str:
    """Format semantic search results as JSON string for tool response.

    Args:
        results: List of (Wine, similarity_score) tuples from WineRepository.semantic_search()
        filters_applied: Dict of filters used in the search
    """
    wine_list = []
    for wine, similarity_score in results:
        wine_data = {
            "name": wine.name,
            "producer": wine.producer,
            "region": wine.region,
            "country": wine.country,
            "vintage_year": wine.vintage_year,
            "grape_varieties": wine.grape_varieties,
            "wine_type": wine.wine_type.value,
            "sweetness": wine.sweetness.value,
            "body": wine.body,
            "tannins": wine.tannins,
            "acidity": wine.acidity,
            "price_rub": float(wine.price_rub),
            "description": wine.description,
            "tasting_notes": wine.tasting_notes,
            "food_pairings": wine.food_pairings,
            "similarity_score": similarity_score,
        }
        wine_list.append(wine_data)

    return json.dumps(
        {
            "found": len(wine_list),
            "wines": wine_list,
            "filters_applied": filters_applied,
        },
        ensure_ascii=False,
    )


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
