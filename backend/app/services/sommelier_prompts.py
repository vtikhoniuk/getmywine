"""LLM prompts for GetMyWine sommelier.

Contains system prompts and templates for different scenarios.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_BASE = """Ты — GetMyWine, виртуальный сомелье по имени Винни. Твоя задача — помогать людям выбирать вино.

КЛЮЧЕВЫЕ ПРИНЦИПЫ:
1. Дружелюбный тон без снобизма — вино для всех, независимо от опыта
2. Всегда предлагай ровно 3 варианта вин из каталога
3. Объясняй ПОЧЕМУ каждое вино подходит (связь с контекстом или профилем)
4. Никогда не выдумывай вина — только из предоставленного каталога
5. Если нет подходящего вина — честно скажи и предложи ближайшую альтернативу

ФОРМАТ ОТВЕТА (обязательно используй маркеры секций):

[INTRO]
Краткое вступление (1-2 предложения, связь с контекстом)
[/INTRO]

[WINE:1]
Название вина (ТОЧНО как в каталоге), регион, страна, год, цена
Описание вкуса и почему подходит (2-3 предложения)
[/WINE:1]

[WINE:2]
(аналогично)
[/WINE:2]

[WINE:3]
(аналогично)
[/WINE:3]

[CLOSING]
Вопрос для продолжения диалога
[/CLOSING]

Всегда используй маркеры [INTRO], [WINE:1], [WINE:2], [WINE:3], [CLOSING].

СТИЛЬ:
- Отвечай только на русском языке
- Используй markdown для форматирования
- Избегай винного снобизма и сложной терминологии
- Объясняй термины, если используешь их

ОГРАНИЧЕНИЯ:
- Не рекомендуй алкоголь лицам до 18 лет
- При необходимости напоминай об умеренном потреблении
- Не давай медицинских советов"""


SYSTEM_PROMPT_COLD_START = SYSTEM_PROMPT_BASE + """

ОСОБЕННОСТИ ТЕКУЩЕЙ СЕССИИ:
Это новый пользователь, вкусовой профиль ещё не определён.
Твоя задача — дать интересные предложения на основе контекста и начать узнавать предпочтения.

При первом контакте:
- Не спрашивай слишком много вопросов сразу
- Предложи 3 разноплановых варианта, чтобы понять предпочтения
- В конце мягко спроси о предпочтениях (сладкое/сухое, красное/белое)"""


SYSTEM_PROMPT_PERSONALIZED = SYSTEM_PROMPT_BASE + """

ОСОБЕННОСТИ ТЕКУЩЕЙ СЕССИИ:
У пользователя есть вкусовой профиль. Используй его для персонализации.

При рекомендациях:
- Учитывай известные предпочтения
- Объясняй выбор через призму профиля ("Вам понравится, потому что вы любите...")
- Один из 3 вариантов может быть "расширением горизонтов" — что-то новое, но близкое к профилю"""


SYSTEM_PROMPT_CONTINUATION = """
ВАЖНО — ЭТО ПРОДОЛЖЕНИЕ ДИАЛОГА:
- НЕ здоровайся, НЕ представляйся, НЕ говори кто ты
- Сразу переходи к ответу на запрос пользователя
- Используй контекст предыдущих сообщений"""


# =============================================================================
# USER PROMPTS TEMPLATES
# =============================================================================

PROMPT_PROACTIVE_COLD_START = """КОНТЕКСТ:
- Текущая дата: {current_date}
- День недели: {day_of_week}
- Сезон: {season}
- Ближайший праздник: {upcoming_holiday} (через {days_until} дней)
- Время суток: {time_of_day}

ЗАДАЧА:
Поприветствуй нового пользователя и предложи 3 идеи для выбора вина.
Выбери ТРИ РАЗНЫХ угла из списка:

1. Сезонное: {season_hook}
2. К празднику: {holiday_hook}
3. Событие: {event_hook}
4. Гастрономическое: к популярному блюду сезона
5. Открытие: новый регион или сорт
6. Бюджетное: отличное вино до $30
7. Премиальное: для особого случая

Для каждой идеи подбери КОНКРЕТНОЕ вино из каталога ниже.

КАТАЛОГ ВИН:
{wine_catalog}"""


PROMPT_PROACTIVE_PERSONALIZED = """КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Имя: {user_name}
- Предпочтения:
  * Сладость: {sweetness_pref}
  * Тело вина: {body_pref}
  * Любимые регионы: {favorite_regions}
  * Избегает: {dislikes}
  * Бюджет: {budget_range}
- Понравилось ранее: {liked_wines}
- Не понравилось: {disliked_wines}

ТЕКУЩИЙ КОНТЕКСТ:
- Дата: {current_date}, {day_of_week}
- Сезон: {season}
- Ближайший праздник: {upcoming_holiday}

ЗАДАЧА:
Поприветствуй {user_name} и предложи 3 персонализированных варианта:

1. **"Проверенный выбор"** — похоже на то, что уже понравилось
2. **"Для момента"** — под текущий сезон или праздник
3. **"Расширение горизонтов"** — что-то новое, но с учётом профиля

КАТАЛОГ ВИН (отфильтрован по профилю):
{filtered_catalog}"""


PROMPT_EVENT_RECOMMENDATION = """ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{user_message}"

ИЗВЛЕЧЁННЫЙ КОНТЕКСТ:
- Событие: {detected_event}
- Блюдо/еда (если указано): {detected_food}
- Количество гостей: {guest_count}
- Особые требования: {special_requirements}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{user_profile}

ЗАДАЧА:
Подбери 3 вина из каталога, идеально подходящих для указанного события.

УЧТИ:
- Если много гостей — предложи вина разных стилей
- Для формального события — проверенные регионы (Бордо, Тоскана, Риоха)
- Для неформального — можно экспериментировать
- Если указана еда — учти гастрономические сочетания

КАТАЛОГ ВИН:
{wine_catalog}"""


PROMPT_FOOD_PAIRING = """ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{user_message}"

БЛЮДО/ПРОДУКТ: {food_item}

КЛАССИЧЕСКИЕ СОЧЕТАНИЯ:
{pairing_hints}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{user_profile}

ЗАДАЧА:
Подбери 3 вина из каталога, которые отлично сочетаются с {food_item}.

Объясни каждое сочетание:
- Почему это работает (вкусовые мосты, контрасты, текстуры)
- Как это связано с профилем пользователя (если есть)

КАТАЛОГ ВИН:
{wine_catalog}"""


PROMPT_DISCOVERY = """КОНТЕКСТ:
Пользователь хочет попробовать что-то новое.

ПРОФИЛЬ (если есть):
{user_profile}

ИСТОРИЯ ПОПРОБОВАННЫХ ВИН:
{tried_wines}

ЗАДАЧА:
Предложи 3 "открытия" — вина, которые расширят горизонты пользователя:

1. **Новый регион** — страна/регион, который пользователь ещё не пробовал
2. **Новый сорт** — автохтонный или редкий сорт винограда
3. **Новый стиль** — необычный способ производства (оранжевое, натуральное, петнат)

Объясни, почему каждое открытие может понравиться, учитывая известные предпочтения.

КАТАЛОГ ВИН:
{wine_catalog}"""


# =============================================================================
# RESPONSE FORMATTING
# =============================================================================

WINE_CARD_TEMPLATE = """**{name}**
{region}, {country}{vintage}
Цена: ~${price}

{description}

_Почему подходит:_ {why_fits}"""


def format_wine_catalog_for_prompt(wines: list, max_wines: int = 20) -> str:
    """Format wine list for inclusion in prompt."""
    lines = []
    for i, wine in enumerate(wines[:max_wines], 1):
        vintage = f", {wine.vintage_year}" if wine.vintage_year else ""
        grapes = ", ".join(wine.grape_varieties) if wine.grape_varieties else "N/A"
        pairings = ", ".join(wine.food_pairings[:3]) if wine.food_pairings else "N/A"

        lines.append(f"""[{i}] {wine.name}
   Регион: {wine.region}, {wine.country}{vintage}
   Сорта: {grapes}
   Тип: {wine.wine_type.value}, Сладость: {wine.sweetness.value}
   Тело: {wine.body}/5, Танины: {wine.tannins}/5, Кислотность: {wine.acidity}/5
   Цена: {wine.price_rub}₽ ({wine.price_range.value})
   Описание: {wine.description}
   Ноты: {wine.tasting_notes or 'N/A'}
   К блюдам: {pairings}
""")
    return "\n".join(lines)


def format_user_profile_for_prompt(profile: Optional[dict]) -> str:
    """Format user profile for inclusion in prompt."""
    if not profile:
        return "Профиль не определён (новый пользователь)"

    lines = []
    if profile.get("sweetness_pref"):
        lines.append(f"- Сладость: {profile['sweetness_pref']}")
    if profile.get("body_pref"):
        lines.append(f"- Тело вина: {profile['body_pref']}")
    if profile.get("favorite_regions"):
        lines.append(f"- Любимые регионы: {', '.join(profile['favorite_regions'])}")
    if profile.get("dislikes"):
        lines.append(f"- Не любит: {', '.join(profile['dislikes'])}")
    if profile.get("budget"):
        lines.append(f"- Бюджет: {profile['budget']}")

    return "\n".join(lines) if lines else "Профиль частично заполнен"


# =============================================================================
# FOOD PAIRING HINTS
# =============================================================================

FOOD_PAIRING_HINTS = {
    "стейк": "Танинные красные (Каберне Совиньон, Мальбек) — танины смягчают жир",
    "рыба": "Лёгкие белые с кислотностью (Совиньон Блан, Альбариньо) — свежесть к морю",
    "паста": "Итальянские красные (Кьянти, Санджовезе) — кислотность к томатам",
    "сыр": "Зависит от сыра: мягкие → белые, выдержанные → красные",
    "морепродукты": "Минеральные белые (Шабли, Мюскаде) — йод и минералы",
    "острое": "Сладковатые белые (Гевюрцтраминер, Рислинг) — сладость гасит остроту",
    "десерт": "Сладкие вина (Москато, Сотерн) — сладкое к сладкому",
    "шашлык": "Яркие красные (Ширáз, GSM) — дым и специи",
    "салат": "Лёгкие белые или розовые — не перебивать свежесть",
    "пицца": "Неформальные красные (Примитиво, Зинфандель) — сочность к сыру",
}


def get_pairing_hint(food: str) -> str:
    """Get pairing hint for food item."""
    food_lower = food.lower()
    for key, hint in FOOD_PAIRING_HINTS.items():
        if key in food_lower:
            return hint
    return "Универсальное правило: вес вина = вес блюда"


# =============================================================================
# STRUCTURED RESPONSE PARSING
# =============================================================================


@dataclass
class ParsedResponse:
    """Parsed LLM response split into sections."""

    intro: str = ""
    wines: list[str] = field(default_factory=list)
    closing: str = ""
    is_structured: bool = False


def parse_structured_response(text: str) -> ParsedResponse:
    """Parse LLM response with [INTRO]/[WINE:N]/[CLOSING] markers.

    Returns ParsedResponse with is_structured=True if at least
    intro and one wine section were found.
    """
    result = ParsedResponse()

    intro_match = re.search(r"\[INTRO\](.*?)\[/INTRO\]", text, re.DOTALL)
    if intro_match:
        result.intro = intro_match.group(1).strip()

    for i in range(1, 4):
        wine_match = re.search(
            rf"\[WINE:{i}\](.*?)\[/WINE:{i}\]", text, re.DOTALL
        )
        if wine_match:
            result.wines.append(wine_match.group(1).strip())

    closing_match = re.search(r"\[CLOSING\](.*?)\[/CLOSING\]", text, re.DOTALL)
    if closing_match:
        result.closing = closing_match.group(1).strip()

    result.is_structured = bool(result.intro and result.wines)
    return result


def strip_markdown(text: str) -> str:
    """Strip Markdown formatting for plain-text contexts (e.g. photo captions)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return text
