"""Shared fixtures for bot unit tests."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.wine import Sweetness, Wine, WineType


@pytest.fixture
def mock_wine() -> Wine:
    """Wine with image_url set."""
    wine = MagicMock(spec=Wine)
    wine.id = uuid.uuid4()
    wine.name = "Château Margaux 2018"
    wine.region = "Bordeaux"
    wine.country = "France"
    wine.grape_varieties = ["Cabernet Sauvignon", "Merlot"]
    wine.sweetness = Sweetness.DRY
    wine.acidity = 3
    wine.tannins = 4
    wine.body = 5
    wine.price_rub = 36000.0
    wine.wine_type = WineType.RED
    wine.image_url = "/static/images/wines/abc123.png"
    return wine


@pytest.fixture
def mock_wine_no_image() -> Wine:
    """Wine without image_url."""
    wine = MagicMock(spec=Wine)
    wine.id = uuid.uuid4()
    wine.name = "Cloudy Bay Sauvignon Blanc 2023"
    wine.region = "Marlborough"
    wine.country = "New Zealand"
    wine.grape_varieties = ["Sauvignon Blanc"]
    wine.sweetness = Sweetness.DRY
    wine.acidity = 4
    wine.tannins = 1
    wine.body = 2
    wine.price_rub = 2240.0
    wine.wine_type = WineType.WHITE
    wine.image_url = None
    return wine


@pytest.fixture
def mock_update() -> MagicMock:
    """Mocked telegram.Update with message and user."""
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.username = "testuser"
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.language_code = "ru"

    mock_message = MagicMock()
    mock_message.reply_text = AsyncMock()
    mock_message.reply_photo = AsyncMock()
    mock_message.text = "Порекомендуй вино"

    mock_update = MagicMock()
    mock_update.effective_user = mock_user
    mock_update.message = mock_message

    return mock_update
