"""Wine name normalization utility."""

PREFIXES = ["Игристое вино ", "Шампанское ", "Вино "]


def normalize_wine_name(
    name: str, producer: str, vintage_year: int | None
) -> str:
    """Normalize wine name by removing category prefix, producer, and year.

    Algorithm (see research.md R-001):
    1. Strip category prefix (longest first): "Игристое вино " > "Шампанское " > "Вино "
    2. Strip trailing ", {vintage_year}" if vintage_year is not None
    3. Strip trailing ", {producer}" if it matches
    4. Trim whitespace
    """
    result = name

    for prefix in PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix) :]
            break

    if vintage_year is not None:
        year_str = str(vintage_year)
        if result.rstrip().endswith(year_str):
            idx = result.rfind(year_str)
            i = idx - 1
            while i >= 0 and result[i] in " ,":
                i -= 1
            result = result[: i + 1]

    suffix_producer = f", {producer}"
    if result.endswith(suffix_producer):
        result = result[: -len(suffix_producer)]

    return result.strip()
