"""Inline keyboards for Telegram bot.

Per contracts/bot-commands.md keyboard specifications.
"""

import uuid
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_feedback_keyboard(wine_id: uuid.UUID) -> InlineKeyboardMarkup:
    """Create feedback keyboard for wine recommendations.

    Shows thumbs up/down buttons for user feedback.

    Args:
        wine_id: UUID of the wine being rated

    Returns:
        InlineKeyboardMarkup with like/dislike buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("\U0001F44D", callback_data=f"like:{wine_id}"),
            InlineKeyboardButton("\U0001F44E", callback_data=f"dislike:{wine_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_sweetness_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Create sweetness selection keyboard for profile editing.

    Args:
        language: Display language ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with sweetness options
    """
    if language == "ru":
        labels = {
            "dry": "Сухое",
            "semi_dry": "Полусухое",
            "semi_sweet": "Полусладкое",
            "sweet": "Сладкое",
        }
    else:
        labels = {
            "dry": "Dry",
            "semi_dry": "Semi-dry",
            "semi_sweet": "Semi-sweet",
            "sweet": "Sweet",
        }

    keyboard = [
        [InlineKeyboardButton(labels["dry"], callback_data="pref:sweetness:dry")],
        [InlineKeyboardButton(labels["semi_dry"], callback_data="pref:sweetness:semi_dry")],
        [InlineKeyboardButton(labels["semi_sweet"], callback_data="pref:sweetness:semi_sweet")],
        [InlineKeyboardButton(labels["sweet"], callback_data="pref:sweetness:sweet")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_budget_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Create budget selection keyboard for profile editing.

    Args:
        language: Display language ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with budget options
    """
    if language == "ru":
        labels = {
            "30": "До $30",
            "100": "$30-100",
            "999": "$100+",
        }
    else:
        labels = {
            "30": "Up to $30",
            "100": "$30-100",
            "999": "$100+",
        }

    keyboard = [
        [InlineKeyboardButton(labels["30"], callback_data="pref:budget:30")],
        [InlineKeyboardButton(labels["100"], callback_data="pref:budget:100")],
        [InlineKeyboardButton(labels["999"], callback_data="pref:budget:999")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_profile_action_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Create keyboard for profile actions.

    Args:
        language: Display language ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with profile action buttons
    """
    if language == "ru":
        update_label = "Обновить профиль"
    else:
        update_label = "Update profile"

    keyboard = [
        [InlineKeyboardButton(update_label, callback_data="profile:update")],
    ]
    return InlineKeyboardMarkup(keyboard)


def create_fill_profile_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Create keyboard for filling empty profile.

    Args:
        language: Display language ('ru' or 'en')

    Returns:
        InlineKeyboardMarkup with fill profile button
    """
    if language == "ru":
        fill_label = "Заполнить профиль"
    else:
        fill_label = "Fill profile"

    keyboard = [
        [InlineKeyboardButton(fill_label, callback_data="profile:fill")],
    ]
    return InlineKeyboardMarkup(keyboard)
