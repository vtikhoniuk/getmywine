"""Mock AI service for wine recommendations.

This is a placeholder service that returns pre-defined responses.
It will be replaced with a real LLM integration in the future.
"""
import random
from typing import Optional


class MockAIService:
    """Mock AI service that returns wine-related responses."""

    # Pre-defined response templates
    RESPONSES = [
        """Отличный выбор! Для этого случая я бы рекомендовал обратить внимание на:

**Красные вина:**
• Каберне Совиньон — насыщенный вкус с нотами черной смородины
• Мерло — более мягкое, с оттенками сливы и шоколада

**Белые вина:**
• Шардоне — полнотелое, с ванильными нотами
• Совиньон Блан — свежее, с цитрусовыми оттенками

Какой стиль вина вам ближе — более насыщенный или легкий?""",

        """Интересный вопрос! Вот что я могу посоветовать:

При выборе вина важно учитывать:
1. **К блюду** — красное мясо любит танинные красные, рыба — легкие белые
2. **Настроение** — для романтического ужина подойдет игристое или розовое
3. **Сезон** — летом освежающие белые, зимой — согревающие красные

Расскажите подробнее о вашей ситуации, и я подберу идеальное вино!""",

        """Прекрасно, давайте разберёмся!

**Несколько рекомендаций:**
• Если вы новичок — начните с полусухих вин, они универсальны
• Для особого случая — присмотритесь к винам из известных регионов (Бордо, Тоскана, Риоха)
• Для ежедневного ужина — молодые вина текущего урожая

Хотите, расскажу подробнее о каком-то конкретном регионе или сорте?""",

        """Хороший вопрос! Вот несколько советов от сомелье:

**Основные правила:**
• Температура: белые 8-12°С, красные 16-18°С
• Декантирование: молодым танинным красным нужно «подышать»
• Бокалы: широкие для красных, узкие для белых

**Мои рекомендации на сегодня:**
• Пино Нуар — элегантное красное с нотами вишни
• Рислинг — ароматное белое с медовыми оттенками

Что бы вы хотели узнать подробнее?""",

        """Отлично, помогу с выбором!

Для гастрономического сочетания:
• **К стейку** — Мальбек или Каберне Совиньон
• **К пасте** — Кьянти или Санджовезе
• **К морепродуктам** — Пино Гриджио или Верментино
• **К сыру** — зависит от сыра, но универсально — Шардоне

Подскажите, к какому блюду подбираем вино?""",
    ]

    def generate_response(self, user_message: str) -> str:
        """
        Generate a mock AI response.

        Args:
            user_message: The user's message (used for future improvements)

        Returns:
            A wine-related response string
        """
        # For now, just return a random pre-defined response
        # In a real implementation, this would call an LLM
        return random.choice(self.RESPONSES)

    async def generate_response_async(self, user_message: str) -> str:
        """
        Async version of generate_response.

        Args:
            user_message: The user's message

        Returns:
            A wine-related response string
        """
        # Mock implementation - just delegates to sync method
        # In real implementation, this would be an async LLM call
        return self.generate_response(user_message)
