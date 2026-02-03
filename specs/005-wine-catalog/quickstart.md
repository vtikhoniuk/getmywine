# Quickstart: Wine Catalog

**Date**: 2026-02-03
**Feature**: 005-wine-catalog

## Prerequisites

- Docker & Docker Compose
- PostgreSQL 16 с pgvector extension
- Python 3.12+
- OpenAI API key (для embeddings)

## Setup

### 1. Переменные окружения

Добавить в `.env`:

```bash
OPENAI_API_KEY=sk-...  # Для генерации embeddings
```

### 2. Применить миграции

```bash
# Из корня проекта
docker-compose exec backend alembic upgrade head
```

Это создаст:
- Таблицу `wines` со всеми полями
- Enum типы: `wine_type`, `sweetness`, `price_range`
- pgvector extension и HNSW индекс
- Seed data: 50 вин

### 3. Проверить каталог

```bash
# Количество вин
docker-compose exec db psql -U postgres -d aiwine -c "SELECT COUNT(*) FROM wines;"
# Ожидается: 50

# Распределение по типам
docker-compose exec db psql -U postgres -d aiwine -c "
SELECT wine_type, COUNT(*)
FROM wines
GROUP BY wine_type;
"
# Ожидается: red ~20, white ~15, rose ~8, sparkling ~7
```

## API Endpoints

### List wines

```bash
# Все вина
curl http://localhost:8000/api/v1/wines

# Только красные
curl "http://localhost:8000/api/v1/wines?wine_type=red"

# Бюджетные вина
curl "http://localhost:8000/api/v1/wines?price_max=70"

# Комбинированный фильтр
curl "http://localhost:8000/api/v1/wines?wine_type=white&sweetness=dry&price_max=80"
```

### Get wine by ID

```bash
curl http://localhost:8000/api/v1/wines/{wine_id}
```

### Semantic search

```bash
curl -X POST http://localhost:8000/api/v1/wines/search \
  -H "Content-Type: application/json" \
  -d '{"query": "лёгкое вино к рыбе", "limit": 5}'
```

## Testing

### Unit tests

```bash
docker-compose exec backend pytest tests/unit/test_wine_service.py -v
```

### Integration tests

```bash
docker-compose exec backend pytest tests/integration/test_wine_api.py -v
```

### Test semantic search

```bash
docker-compose exec backend pytest tests/integration/test_wine_search.py -v
```

## Troubleshooting

### pgvector not found

```bash
docker-compose exec db psql -U postgres -d aiwine -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Embeddings not generated

Проверить OpenAI API key и запустить:

```bash
docker-compose exec backend python -c "
from app.services.wine import WineService
from app.core.database import get_db

async def regenerate():
    async for db in get_db():
        service = WineService(db)
        await service.regenerate_embeddings()

import asyncio
asyncio.run(regenerate())
"
```

### Seed data missing

```bash
# Откатить и применить заново
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

## Performance Check

```bash
# Проверить время поиска по типу
docker-compose exec db psql -U postgres -d aiwine -c "
EXPLAIN ANALYZE
SELECT * FROM wines WHERE wine_type = 'red' LIMIT 20;
"
# Ожидается: < 10ms

# Проверить семантический поиск
docker-compose exec db psql -U postgres -d aiwine -c "
EXPLAIN ANALYZE
SELECT * FROM wines
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
"
# Ожидается: < 50ms (с HNSW индексом)
```
