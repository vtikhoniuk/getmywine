"""Unit tests for Telegram inline keyboards.

T029 [US3]: Tests for inline keyboards per TDD requirement.
"""

import uuid

import pytest

# Check if telegram module is available
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not TELEGRAM_AVAILABLE,
    reason="telegram module not available"
)


class TestFeedbackKeyboard:
    """Tests for wine feedback keyboard."""

    def test_creates_like_dislike_buttons(self):
        """Should create keyboard with like and dislike buttons."""
        from app.bot.keyboards import create_feedback_keyboard

        wine_id = uuid.uuid4()
        keyboard = create_feedback_keyboard(wine_id)

        # Should have one row
        assert len(keyboard.inline_keyboard) == 1

        # Row should have 2 buttons
        row = keyboard.inline_keyboard[0]
        assert len(row) == 2

    def test_like_button_callback_data(self):
        """Like button should have correct callback data."""
        from app.bot.keyboards import create_feedback_keyboard

        wine_id = uuid.uuid4()
        keyboard = create_feedback_keyboard(wine_id)

        like_button = keyboard.inline_keyboard[0][0]
        assert like_button.callback_data == f"like:{wine_id}"

    def test_dislike_button_callback_data(self):
        """Dislike button should have correct callback data."""
        from app.bot.keyboards import create_feedback_keyboard

        wine_id = uuid.uuid4()
        keyboard = create_feedback_keyboard(wine_id)

        dislike_button = keyboard.inline_keyboard[0][1]
        assert dislike_button.callback_data == f"dislike:{wine_id}"

    def test_button_emojis(self):
        """Buttons should have thumbs up/down emojis."""
        from app.bot.keyboards import create_feedback_keyboard

        wine_id = uuid.uuid4()
        keyboard = create_feedback_keyboard(wine_id)

        like_button = keyboard.inline_keyboard[0][0]
        dislike_button = keyboard.inline_keyboard[0][1]

        assert "\U0001F44D" in like_button.text  # 👍
        assert "\U0001F44E" in dislike_button.text  # 👎


class TestProfileKeyboard:
    """Tests for profile edit keyboard."""

    def test_sweetness_selection_keyboard(self):
        """Should create keyboard for sweetness selection."""
        from app.bot.keyboards import create_sweetness_keyboard

        keyboard = create_sweetness_keyboard()

        # Should have 4 options (dry, semi-dry, semi-sweet, sweet)
        assert len(keyboard.inline_keyboard) == 4

        # Each row should have one button
        for row in keyboard.inline_keyboard:
            assert len(row) == 1

    def test_sweetness_callback_data(self):
        """Sweetness buttons should have correct callback data."""
        from app.bot.keyboards import create_sweetness_keyboard

        keyboard = create_sweetness_keyboard()

        callbacks = [row[0].callback_data for row in keyboard.inline_keyboard]
        assert "pref:sweetness:dry" in callbacks
        assert "pref:sweetness:semi_dry" in callbacks
        assert "pref:sweetness:semi_sweet" in callbacks
        assert "pref:sweetness:sweet" in callbacks

    def test_budget_selection_keyboard(self):
        """Should create keyboard for budget selection."""
        from app.bot.keyboards import create_budget_keyboard

        keyboard = create_budget_keyboard()

        # Should have 3 options
        assert len(keyboard.inline_keyboard) == 3

    def test_budget_callback_data(self):
        """Budget buttons should have correct callback data."""
        from app.bot.keyboards import create_budget_keyboard

        keyboard = create_budget_keyboard()

        callbacks = [row[0].callback_data for row in keyboard.inline_keyboard]
        assert "pref:budget:30" in callbacks
        assert "pref:budget:100" in callbacks
        assert "pref:budget:999" in callbacks


class TestKeyboardLabels:
    """Tests for keyboard label localization."""

    def test_sweetness_russian_labels(self):
        """Sweetness keyboard should have Russian labels."""
        from app.bot.keyboards import create_sweetness_keyboard

        keyboard = create_sweetness_keyboard(language="ru")

        labels = [row[0].text for row in keyboard.inline_keyboard]
        assert "Сухое" in labels
        assert "Полусухое" in labels
        assert "Полусладкое" in labels
        assert "Сладкое" in labels

    def test_budget_russian_labels(self):
        """Budget keyboard should have labels with dollar amounts."""
        from app.bot.keyboards import create_budget_keyboard

        keyboard = create_budget_keyboard(language="ru")

        labels = [row[0].text for row in keyboard.inline_keyboard]
        assert any("$30" in label for label in labels)
        assert any("$100" in label for label in labels)
