"""Wine card formatters for Telegram bot.

Formats wine information for mobile-friendly Telegram display.
Per contracts/bot-commands.md formatting specifications.
"""

from typing import Optional

from app.models.wine import Wine, Sweetness


def format_characteristic_bar(value: int, max_value: int = 5) -> str:
    """Create a visual bar for wine characteristics.

    Args:
        value: Characteristic value (0-5)
        max_value: Maximum value for the bar

    Returns:
        String of filled (⬛) and empty (⬜) blocks

    Example:
        >>> format_characteristic_bar(3)
        '⬛⬛⬛⬜⬜'
    """
    filled = min(max(value, 0), max_value)
    empty = max_value - filled
    return "\u2B1B" * filled + "\u2B1C" * empty


def get_sweetness_label(sweetness: Sweetness, language: str = "ru") -> str:
    """Get localized sweetness label.

    Args:
        sweetness: Sweetness enum value
        language: Target language ('ru' or 'en')

    Returns:
        Localized sweetness string
    """
    labels = {
        "ru": {
            Sweetness.DRY: "сухое",
            Sweetness.SEMI_DRY: "полусухое",
            Sweetness.SEMI_SWEET: "полусладкое",
            Sweetness.SWEET: "сладкое",
        },
        "en": {
            Sweetness.DRY: "dry",
            Sweetness.SEMI_DRY: "semi-dry",
            Sweetness.SEMI_SWEET: "semi-sweet",
            Sweetness.SWEET: "sweet",
        },
    }
    lang_labels = labels.get(language, labels["en"])
    return lang_labels.get(sweetness, sweetness.value)


def format_wine_card(
    wine: Wine,
    reason: Optional[str] = None,
    language: str = "ru",
) -> str:
    """Format a wine as a Telegram card.

    Creates a mobile-friendly wine card with:
    - Wine name (bold)
    - Region and country
    - Grape varieties
    - Characteristics (visual bars)
    - Price
    - Optional recommendation reason

    Args:
        wine: Wine model instance
        reason: Optional recommendation reason from AI
        language: Response language ('ru' or 'en')

    Returns:
        Formatted Markdown string for Telegram

    Example output (Russian):
        🍷 *Château Margaux 2015*
        📍 Бордо, Франция
        🍇 Каберне Совиньон, Мерло

        *Характеристики:*
        • Сладость: сухое
        • Кислотность: ⬛⬛⬛⬜⬜
        • Танины: ⬛⬛⬛⬛⬜
        • Тело: ⬛⬛⬛⬛⬜

        💰 ~$350

        *Почему это вино:*
        Классическое бордо с элегантными танинами...
    """
    # Labels based on language
    if language == "ru":
        labels = {
            "characteristics": "Характеристики",
            "sweetness": "Сладость",
            "acidity": "Кислотность",
            "tannins": "Танины",
            "body": "Тело",
            "why": "Почему это вино",
        }
    else:
        labels = {
            "characteristics": "Characteristics",
            "sweetness": "Sweetness",
            "acidity": "Acidity",
            "tannins": "Tannins",
            "body": "Body",
            "why": "Why this wine",
        }

    # Sweetness label
    sweetness_label = get_sweetness_label(wine.sweetness, language)

    # Grape varieties (limit to 3)
    grapes = ", ".join(wine.grape_varieties[:3]) if wine.grape_varieties else "N/A"

    # Build card
    card = f"""\U0001F377 *{wine.name}*
\U0001F4CD {wine.region}, {wine.country}
\U0001F347 {grapes}

*{labels['characteristics']}:*
• {labels['sweetness']}: {sweetness_label}
• {labels['acidity']}: {format_characteristic_bar(wine.acidity)}
• {labels['tannins']}: {format_characteristic_bar(wine.tannins)}
• {labels['body']}: {format_characteristic_bar(wine.body)}

\U0001F4B0 ~{wine.price_rub:.0f}₽"""

    # Add recommendation reason if provided
    if reason and reason.strip():
        card += f"\n\n*{labels['why']}:*\n{reason}"

    return card


def format_wine_card_simple(wine: Wine, language: str = "ru") -> str:
    """Format a wine as a simple card (for welcome message).

    Shorter format without characteristics bars.

    Args:
        wine: Wine model instance
        language: Response language ('ru' or 'en')

    Returns:
        Formatted simple card string
    """
    return f"""\U0001F377 *{wine.name}*
\U0001F4CD {wine.region}, {wine.country}
\U0001F4B0 ~{wine.price_rub:.0f}₽"""


def format_wine_photo_caption(wine: Wine, language: str = "ru") -> str:
    """Format a plain-text caption for a wine photo.

    No Markdown — Telegram shows it as-is under the image.
    """
    sweetness_label = get_sweetness_label(wine.sweetness, language)
    grapes = ", ".join(wine.grape_varieties[:3]) if wine.grape_varieties else ""
    lines = [
        wine.name,
        f"{wine.region}, {wine.country}",
    ]
    if grapes:
        lines.append(grapes)
    lines.append(f"{sweetness_label}, ~{wine.price_rub:.0f}\u20bd")
    return "\n".join(lines)


def format_welcome_message(
    first_name: Optional[str],
    wines: list[Wine],
    language: str = "ru",
) -> str:
    """Format welcome message with wine suggestions.

    Per contracts/bot-commands.md /start response format.

    Args:
        first_name: User's first name for personalization
        wines: List of suggested wines
        language: Response language ('ru' or 'en')

    Returns:
        Formatted welcome message
    """
    if language == "ru":
        greeting = f"Привет, {first_name}!" if first_name else "Привет!"
        message = f"""{greeting} \U0001F44B Я GetMyWine, и я помогу вам разобраться в мире вина.

Вот что я подобрал для вас сегодня:

"""
        for wine in wines:
            message += format_wine_card_simple(wine, language) + "\n\n"

        message += """Напишите мне, что вы ищете! Например:
• "Вино к стейку"
• "Лёгкое белое на вечер"
• "Подарок для друга\""""
    else:
        greeting = f"Hello, {first_name}!" if first_name else "Hello!"
        message = f"""{greeting} \U0001F44B I'm GetMyWine, and I'll help you navigate the world of wine.

Here's what I've selected for you today:

"""
        for wine in wines:
            message += format_wine_card_simple(wine, language) + "\n\n"

        message += """Tell me what you're looking for! For example:
• "Wine for steak"
• "Light white for the evening"
• "Gift for a friend\""""

    return message
