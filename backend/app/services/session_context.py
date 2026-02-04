"""Session context service for cross-session personalization.

Extracts insights from session history and builds context for AI personalization.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.repositories.conversation import ConversationRepository
from app.services.llm import get_llm_service, LLMError

logger = logging.getLogger(__name__)


@dataclass
class SessionInsights:
    """Extracted insights from a session."""

    liked_wines: list[str] = field(default_factory=list)
    disliked_wines: list[str] = field(default_factory=list)
    events_discussed: list[str] = field(default_factory=list)
    foods_paired: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if insights are empty."""
        return not (
            self.liked_wines
            or self.disliked_wines
            or self.events_discussed
            or self.foods_paired
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "liked_wines": self.liked_wines,
            "disliked_wines": self.disliked_wines,
            "events_discussed": self.events_discussed,
            "foods_paired": self.foods_paired,
        }


@dataclass
class CrossSessionContext:
    """Aggregated context from multiple sessions."""

    total_sessions: int
    recent_wines: list[str]  # Wines discussed recently (to avoid repeating)
    preferences: SessionInsights
    last_session_date: Optional[datetime]

    def to_prompt_text(self) -> str:
        """Format context for LLM prompt."""
        if self.total_sessions == 0:
            return ""

        lines = [f"История пользователя ({self.total_sessions} сессий):"]

        if self.recent_wines:
            lines.append(f"- Недавно обсуждали: {', '.join(self.recent_wines[:5])}")

        if self.preferences.liked_wines:
            lines.append(f"- Понравились: {', '.join(self.preferences.liked_wines[:5])}")

        if self.preferences.disliked_wines:
            lines.append(f"- Не понравились: {', '.join(self.preferences.disliked_wines[:3])}")

        if self.preferences.events_discussed:
            lines.append(f"- События: {', '.join(self.preferences.events_discussed[:3])}")

        if self.preferences.foods_paired:
            lines.append(f"- Еда: {', '.join(self.preferences.foods_paired[:3])}")

        return "\n".join(lines)


# Prompt for extracting insights from conversation
INSIGHTS_EXTRACTION_PROMPT = """Проанализируй диалог и извлеки ключевые факты.

Верни JSON с полями:
- liked_wines: список понравившихся вин (если упоминались положительно)
- disliked_wines: список не понравившихся вин (если были отклонены)
- events_discussed: упомянутые события (день рождения, ужин, праздник)
- foods_paired: блюда для сочетания с вином

Если поле не применимо, верни пустой список.

Диалог:
{conversation}

Ответ (только JSON):"""


class SessionContextService:
    """Service for extracting and building cross-session context."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self._llm = None

    @property
    def llm(self):
        """Lazy initialization of LLM service."""
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm

    async def extract_session_insights(
        self,
        conversation: Conversation,
    ) -> SessionInsights:
        """
        Extract insights from a single session's messages.

        Uses LLM to analyze conversation and extract preferences.
        Falls back to empty insights on failure.

        Args:
            conversation: The conversation to analyze

        Returns:
            Extracted insights
        """
        if not conversation.messages:
            return SessionInsights()

        # Build conversation text (skip welcome messages)
        messages_text = []
        for msg in conversation.messages:
            if msg.is_welcome:
                continue
            role = "Пользователь" if msg.role.value == "user" else "AI"
            messages_text.append(f"{role}: {msg.content}")

        if not messages_text:
            return SessionInsights()

        conversation_text = "\n".join(messages_text[-20:])  # Last 20 messages

        try:
            if not self.llm.is_available:
                logger.debug("LLM not available, returning empty insights")
                return SessionInsights()

            prompt = INSIGHTS_EXTRACTION_PROMPT.format(conversation=conversation_text)

            response = await self.llm.generate(
                system_prompt="Ты помощник для анализа диалогов о вине.",
                user_prompt=prompt,
                temperature=0.3,  # More deterministic
                max_tokens=500,
            )

            return self._parse_insights_response(response)

        except LLMError as e:
            logger.warning("LLM error extracting insights: %s", e)
            return SessionInsights()
        except Exception as e:
            logger.error("Error extracting insights: %s", e)
            return SessionInsights()

    def _parse_insights_response(self, response: str) -> SessionInsights:
        """Parse LLM response into SessionInsights."""
        try:
            # Try to extract JSON from response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                # Remove first and last lines (```json and ```)
                json_lines = [
                    line for line in lines[1:-1] if not line.startswith("```")
                ]
                response = "\n".join(json_lines)

            data = json.loads(response)

            return SessionInsights(
                liked_wines=data.get("liked_wines", [])[:10],
                disliked_wines=data.get("disliked_wines", [])[:10],
                events_discussed=data.get("events_discussed", [])[:5],
                foods_paired=data.get("foods_paired", [])[:5],
            )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse insights JSON: %s", e)
            return SessionInsights()

    async def build_cross_session_context(
        self,
        user_id,
        exclude_session_id=None,
        max_sessions: int = 5,
    ) -> CrossSessionContext:
        """
        Build aggregated context from user's recent sessions.

        Args:
            user_id: User's UUID
            exclude_session_id: Session to exclude (e.g., current session)
            max_sessions: Maximum sessions to analyze

        Returns:
            Aggregated cross-session context
        """
        # Get recent sessions
        conversations, total = await self.conversation_repo.get_all_by_user_id(
            user_id, limit=max_sessions + 1  # +1 in case we need to exclude current
        )

        # Filter out excluded session
        if exclude_session_id:
            conversations = [c for c in conversations if c.id != exclude_session_id]

        conversations = conversations[:max_sessions]

        if not conversations:
            return CrossSessionContext(
                total_sessions=0,
                recent_wines=[],
                preferences=SessionInsights(),
                last_session_date=None,
            )

        # Aggregate insights
        all_liked = []
        all_disliked = []
        all_events = []
        all_foods = []
        recent_wines = []

        for conv in conversations:
            # Simple heuristic extraction without LLM for speed
            insights = self._extract_simple_insights(conv)
            all_liked.extend(insights.liked_wines)
            all_disliked.extend(insights.disliked_wines)
            all_events.extend(insights.events_discussed)
            all_foods.extend(insights.foods_paired)

            # Extract wine names mentioned (for avoiding repetition)
            for msg in conv.messages:
                if msg.role.value == "assistant" and not msg.is_welcome:
                    # Simple extraction of potential wine names
                    wines = self._extract_wine_mentions(msg.content)
                    recent_wines.extend(wines)

        # Deduplicate and limit
        aggregated = SessionInsights(
            liked_wines=list(dict.fromkeys(all_liked))[:10],
            disliked_wines=list(dict.fromkeys(all_disliked))[:5],
            events_discussed=list(dict.fromkeys(all_events))[:5],
            foods_paired=list(dict.fromkeys(all_foods))[:5],
        )

        return CrossSessionContext(
            total_sessions=total,
            recent_wines=list(dict.fromkeys(recent_wines))[:10],
            preferences=aggregated,
            last_session_date=conversations[0].updated_at if conversations else None,
        )

    def _extract_simple_insights(self, conversation: Conversation) -> SessionInsights:
        """
        Extract insights using simple keyword matching (no LLM).

        Faster but less accurate than LLM extraction.
        """
        liked = []
        disliked = []
        events = []
        foods = []

        # Event keywords
        event_keywords = {
            "день рождения": "день рождения",
            "юбилей": "юбилей",
            "свадьба": "свадьба",
            "праздник": "праздник",
            "новый год": "Новый год",
            "рождество": "Рождество",
            "8 марта": "8 марта",
            "ужин": "ужин",
            "вечеринка": "вечеринка",
        }

        # Food keywords
        food_keywords = [
            "стейк", "мясо", "рыба", "морепродукты", "сыр", "паста",
            "пицца", "курица", "утка", "баранина", "свинина", "говядина",
            "салат", "десерт", "шоколад", "фрукты",
        ]

        for msg in conversation.messages:
            if msg.is_welcome:
                continue

            content_lower = msg.content.lower()

            # Check for events
            for keyword, event_name in event_keywords.items():
                if keyword in content_lower:
                    events.append(event_name)

            # Check for foods (in user messages)
            if msg.role.value == "user":
                for food in food_keywords:
                    if food in content_lower:
                        foods.append(food)

        return SessionInsights(
            liked_wines=liked,
            disliked_wines=disliked,
            events_discussed=list(set(events)),
            foods_paired=list(set(foods)),
        )

    def _extract_wine_mentions(self, text: str) -> list[str]:
        """Extract potential wine names from AI response."""
        wines = []

        # Common wine indicators
        wine_patterns = [
            "рекомендую", "предлагаю", "попробуйте",
            "отлично подойдёт", "хороший выбор",
        ]

        # Simple heuristic: look for capitalized words after wine indicators
        lines = text.split("\n")
        for line in lines:
            line_lower = line.lower()
            for pattern in wine_patterns:
                if pattern in line_lower:
                    # Extract potential wine name (words with capital letters)
                    words = line.split()
                    for i, word in enumerate(words):
                        if word and word[0].isupper() and len(word) > 3:
                            # Could be a wine name
                            potential_name = word.strip(".,!?:;\"'")
                            if potential_name and potential_name not in [
                                "Для", "При", "Это", "Вам", "Если",
                            ]:
                                wines.append(potential_name)

        return wines[:5]  # Limit to 5 per message
