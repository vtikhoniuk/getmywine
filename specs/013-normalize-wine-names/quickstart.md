# Quickstart: Нормализация названий вин

**Feature**: 013-normalize-wine-names | **Date**: 2026-02-10

## Prerequisites

- Python 3.12+
- PostgreSQL 16 с pgvector
- Docker Compose (для запуска окружения)
- OpenRouter или OpenAI API key (для пересчёта эмбеддингов)

## Порядок внедрения

### Шаг 1: Создать функцию normalize_wine_name()

Переиспользуемая функция в утилитах (например, `backend/app/utils/wine_normalization.py`):

```python
PREFIXES = ["Игристое вино ", "Шампанское ", "Вино "]

def normalize_wine_name(name: str, producer: str, vintage_year: int | None) -> str:
    result = name
    for prefix in PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    if vintage_year is not None:
        year_str = str(vintage_year)
        if result.rstrip().endswith(year_str):
            idx = result.rfind(year_str)
            i = idx - 1
            while i >= 0 and result[i] in " ,":
                i -= 1
            result = result[:i+1]
    suffix_producer = f", {producer}"
    if result.endswith(suffix_producer):
        result = result[:-len(suffix_producer)]
    return result.strip()
```

### Шаг 2: Обновить wines_seed.json

Применить `normalize_wine_name()` к каждому вину в seed-файле (скриптом или в миграции).

### Шаг 3: Создать Alembic-миграцию

```bash
cd backend
alembic revision -m "normalize_wine_names"
```

Миграция: SELECT id, name, producer, vintage_year → `normalize_wine_name()` → UPDATE name для каждой записи.

### Шаг 3: Упростить _extract_wines_from_response()

В `backend/app/services/telegram_bot.py`:
- Удалить 3-уровневый matching (strip «Вино», strip year)
- Оставить прямой `response_text.find(wine.name)`

### Шаг 4: Запустить миграцию

```bash
docker compose up -d
# Миграция запускается автоматически при старте (alembic upgrade head)
```

### Шаг 5: Пересчитать эмбеддинги (отдельный шаг)

```bash
docker compose exec backend python -m app.scripts.generate_embeddings
```

Скрипт может потребовать доработки для обновления эмбеддингов в БД (текущая версия сохраняет в файл).

## Проверка

### Автоматическая

```bash
cd backend
pytest tests/unit/test_wine_name_normalization.py -v
pytest tests/unit/test_extract_wines.py -v
pytest tests/unit/test_bot_sender.py -v
```

### Ручная

1. Открыть БД: `docker compose exec db psql -U getmywine -d getmywine`
2. Проверить: `SELECT name FROM wines WHERE name LIKE 'Вино%' OR name LIKE 'Игристое%' OR name LIKE 'Шампанское%';` → 0 строк
3. Проверить: `SELECT COUNT(DISTINCT name) FROM wines;` → 50
4. Отправить боту запрос в Telegram → убедиться, что рекомендации приходят с фотографиями

## Конфигурация

Переменные окружения (уже добавлены):

| Переменная | Default | Описание |
|-----------|---------|----------|
| TELEGRAM_WINE_PHOTO_HEIGHT | 460 | Высота фото бутылки (px) |
