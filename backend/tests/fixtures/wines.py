"""Test fixtures for wine catalog tests."""
import uuid
from datetime import datetime, timezone

# Sample wine data for testing
SAMPLE_WINES = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Château Margaux 2018",
        "producer": "Château Margaux",
        "vintage_year": 2018,
        "country": "France",
        "region": "Bordeaux",
        "appellation": "Margaux",
        "grape_varieties": ["Cabernet Sauvignon", "Merlot", "Petit Verdot"],
        "wine_type": "red",
        "sweetness": "dry",
        "acidity": 3,
        "tannins": 4,
        "body": 5,
        "description": "Элегантное вино с нотами чёрной смородины, фиалки и кедра. Шелковистые танины и долгое послевкусие.",
        "tasting_notes": "Чёрная смородина, фиалка, кедр, графит",
        "food_pairings": ["стейк", "баранина", "выдержанные сыры"],
        "price_rub": 36000.00,
        "price_range": "premium",
        "image_url": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "name": "Cloudy Bay Sauvignon Blanc 2023",
        "producer": "Cloudy Bay",
        "vintage_year": 2023,
        "country": "New Zealand",
        "region": "Marlborough",
        "appellation": None,
        "grape_varieties": ["Sauvignon Blanc"],
        "wine_type": "white",
        "sweetness": "dry",
        "acidity": 4,
        "tannins": 1,
        "body": 2,
        "description": "Освежающее вино с яркой кислотностью и нотами цитрусовых, крыжовника и свежескошенной травы.",
        "tasting_notes": "Лайм, грейпфрут, крыжовник, трава",
        "food_pairings": ["морепродукты", "салаты", "козий сыр"],
        "price_rub": 2240.00,
        "price_range": "budget",
        "image_url": "https://images.unsplash.com/photo-1558001373-7b93ee48ffa0",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "name": "Moët & Chandon Brut Impérial",
        "producer": "Moët & Chandon",
        "vintage_year": None,  # NV
        "country": "France",
        "region": "Champagne",
        "appellation": "Champagne",
        "grape_varieties": ["Chardonnay", "Pinot Noir", "Pinot Meunier"],
        "wine_type": "sparkling",
        "sweetness": "dry",
        "acidity": 4,
        "tannins": 1,
        "body": 2,
        "description": "Классическое шампанское с тонким перляжем и нотами зелёного яблока, цитрусовых и бриоши.",
        "tasting_notes": "Яблоко, цитрус, бриошь, миндаль",
        "food_pairings": ["устрицы", "канапе", "белая рыба"],
        "price_rub": 4400.00,
        "price_range": "mid",
        "image_url": "https://images.unsplash.com/photo-1549934151-05c1d7cfaa07",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "name": "Whispering Angel Rosé 2023",
        "producer": "Château d'Esclans",
        "vintage_year": 2023,
        "country": "France",
        "region": "Provence",
        "appellation": "Côtes de Provence",
        "grape_varieties": ["Grenache", "Cinsault", "Rolle"],
        "wine_type": "rose",
        "sweetness": "dry",
        "acidity": 3,
        "tannins": 1,
        "body": 2,
        "description": "Бледно-розовое вино с ароматами клубники, персика и лёгкими цветочными нотами.",
        "tasting_notes": "Клубника, персик, цветы, минералы",
        "food_pairings": ["салаты", "гриль", "средиземноморская кухня"],
        "price_rub": 1920.00,
        "price_range": "budget",
        "image_url": "https://images.unsplash.com/photo-1558001373-7b93ee48ffa0",
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "name": "Masseto 2019",
        "producer": "Tenuta dell'Ornellaia",
        "vintage_year": 2019,
        "country": "Italy",
        "region": "Tuscany",
        "appellation": "Toscana IGT",
        "grape_varieties": ["Merlot"],
        "wine_type": "red",
        "sweetness": "dry",
        "acidity": 3,
        "tannins": 4,
        "body": 5,
        "description": "Культовое итальянское Мерло с глубоким рубиновым цветом, нотами спелых ягод, специй и шоколада.",
        "tasting_notes": "Ежевика, слива, специи, шоколад, ваниль",
        "food_pairings": ["дичь", "трюфели", "ризотто с грибами"],
        "price_rub": 60000.00,
        "price_range": "premium",
        "image_url": "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3",
    },
]


def get_sample_wine(index: int = 0) -> dict:
    """Get a sample wine by index."""
    return SAMPLE_WINES[index % len(SAMPLE_WINES)]


def get_red_wines() -> list[dict]:
    """Get all red wines from samples."""
    return [w for w in SAMPLE_WINES if w["wine_type"] == "red"]


def get_white_wines() -> list[dict]:
    """Get all white wines from samples."""
    return [w for w in SAMPLE_WINES if w["wine_type"] == "white"]


def get_wines_by_price_range(min_price: float, max_price: float) -> list[dict]:
    """Get wines within a price range."""
    return [w for w in SAMPLE_WINES if min_price <= w["price_rub"] <= max_price]


def get_premium_wines() -> list[dict]:
    """Get premium wines (>8000₽)."""
    return [w for w in SAMPLE_WINES if w["price_range"] == "premium"]


def create_wine_dict(**overrides) -> dict:
    """Create a wine dict with optional overrides for testing."""
    base = get_sample_wine(0).copy()
    base["id"] = uuid.uuid4()
    base.update(overrides)
    return base
