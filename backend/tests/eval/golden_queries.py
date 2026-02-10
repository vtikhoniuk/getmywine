"""Golden query definitions for eval tests."""

from dataclasses import dataclass, field


@dataclass
class GoldenQuery:
    """A single golden query for evaluation."""

    id: str
    query_ru: str
    expected_tool: str  # "search_wines" | "semantic_search" | "any"
    expected_filters: dict = field(default_factory=dict)
    min_results: int = 1
    description: str = ""


# --- Tool selection queries ---
# Verify LLM picks the correct tool based on query type.

TOOL_SELECTION_QUERIES = [
    GoldenQuery(
        id="red_dry_under_2000",
        query_ru="красное сухое до 2000 рублей",
        expected_tool="search_wines",
        expected_filters={"wine_type": "red", "sweetness": "dry"},
        description="Explicit type + sweetness + price -> search_wines",
    ),
    GoldenQuery(
        id="elegant_light",
        query_ru="что-то элегантное и лёгкое",
        expected_tool="semantic_search",
        description="Abstract mood -> semantic_search",
    ),
    GoldenQuery(
        id="pinot_noir",
        query_ru="пино нуар",
        expected_tool="search_wines",
        description="Grape variety -> search_wines",
    ),
    GoldenQuery(
        id="wine_for_steak",
        query_ru="вино к стейку",
        expected_tool="search_wines",
        description="Food pairing -> search_wines",
    ),
    GoldenQuery(
        id="sparkling_celebration",
        query_ru="игристое вино",
        expected_tool="search_wines",
        expected_filters={"wine_type": "sparkling"},
        description="Explicit type -> search_wines",
    ),
    GoldenQuery(
        id="refreshing_summer",
        query_ru="что-то освежающее на лето",
        expected_tool="semantic_search",
        description="Mood/season description -> semantic_search",
    ),
    GoldenQuery(
        id="white_france",
        query_ru="белое из Франции",
        expected_tool="search_wines",
        expected_filters={"wine_type": "white"},
        description="Type + country -> search_wines",
    ),
    GoldenQuery(
        id="expensive_premium",
        query_ru="вино дороже 5000 рублей",
        expected_tool="search_wines",
        description="Explicit price -> search_wines",
    ),
]


# --- Filter accuracy queries ---
# Verify LLM extracts correct filter values from natural language.

FILTER_ACCURACY_QUERIES = [
    GoldenQuery(
        id="filter_red_dry_budget",
        query_ru="красное сухое до 2000 рублей",
        expected_tool="search_wines",
        expected_filters={"wine_type": "red", "sweetness": "dry", "price_max": 2000},
        description="Full extraction: type + sweetness + price_max",
    ),
    GoldenQuery(
        id="filter_grape_malbec",
        query_ru="хочу попробовать мальбек",
        expected_tool="search_wines",
        expected_filters={"grape_variety": "мальбек"},
        description="Single grape variety filter",
    ),
    GoldenQuery(
        id="filter_country_type",
        query_ru="итальянское красное",
        expected_tool="search_wines",
        expected_filters={"wine_type": "red"},
        description="Country + type extraction",
    ),
]


# --- Semantic search quality queries ---
# Verify semantic search returns relevant results with decent similarity.

SEMANTIC_QUERIES = [
    GoldenQuery(
        id="semantic_romantic",
        query_ru="вино для романтического ужина",
        expected_tool="semantic_search",
        min_results=1,
        description="Romantic dinner -> elegant wines",
    ),
    GoldenQuery(
        id="semantic_unusual",
        query_ru="что-нибудь необычное и интересное",
        expected_tool="semantic_search",
        min_results=1,
        description="Unusual -> diverse results",
    ),
    GoldenQuery(
        id="semantic_berry_notes",
        query_ru="вино с ягодными нотами",
        expected_tool="semantic_search",
        min_results=1,
        description="Berry notes -> fruity wines",
    ),
]
