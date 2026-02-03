# Research: Wine Catalog

**Date**: 2026-02-03
**Feature**: 005-wine-catalog

## 1. Источники данных для Seed

### Decision: X-Wines Dataset + ручная курация

### Rationale
- [X-Wines](https://github.com/rogerioxavier/X-Wines) — 100K+ вин с рейтингами, открытая лицензия
- Данные структурированы: название, регион, сорт, рейтинг
- Можно отфильтровать 50 вин по критериям разнообразия

### Alternatives Considered

| Источник | Плюсы | Минусы | Решение |
|----------|-------|--------|---------|
| [LWIN Database](https://www.liv-ex.com/lwin/) | 200K+ вин, открытый | Нет цен, нет описаний | Отклонён |
| [WineVybe API](https://winevybe.com/wine-api/) | Полные данные, API | Платный для production | Отклонён |
| [Wine-Searcher API](https://www.wine-searcher.com/trade/ws-api) | Цены, магазины | Требует membership | Отклонён |
| [Kaggle Wine Reviews](https://github.com/gleivas/wine_api) | 130K отзывов | Только отзывы, нет структуры | Частично |
| Manual curation | Полный контроль | Трудоёмко | Выбран как дополнение |

### Implementation

1. Скачать X-Wines dataset
2. Отфильтровать по критериям:
   - Тип: 20 красных, 15 белых, 8 розовых, 7 игристых
   - Цена: 45 в диапазоне $50-100, 5 премиум ($100+)
   - Регионы: минимум 6 стран
3. Дополнить описаниями из Kaggle Wine Reviews
4. Добавить изображения с Unsplash (Creative Commons)
5. Создать JSON fixture для seed миграции

---

## 2. pgvector Setup

### Decision: HNSW index + OpenAI text-embedding-3-small

### Rationale
- [pgvector](https://github.com/pgvector/pgvector) уже в стеке (constitution)
- HNSW даёт лучший recall без дополнительной настройки
- text-embedding-3-small: 1536 dimensions, дешёвый, достаточно точный

### Best Practices (из [Instaclustr Guide](https://www.instaclustr.com/education/vector-database/pgvector-key-features-tutorial-and-pros-and-cons-2026-guide/))

1. **Index**: HNSW для <1M векторов (у нас 50)
2. **Dimensions**: 1536 (OpenAI) или 384 (sentence-transformers)
3. **Distance**: cosine для текстовых embeddings
4. **Maintenance**: VACUUM ANALYZE после bulk insert

### Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE wines ADD COLUMN embedding vector(1536);

CREATE INDEX ON wines
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Embedding Pipeline

```
Wine description → Claude/OpenAI API → embedding vector → PostgreSQL
```

---

## 3. Embedding Model

### Decision: Claude API (уже в стеке) или fallback на OpenAI

### Rationale
- Claude уже используется для чата
- Можно использовать для генерации embeddings через промпт
- Альтернатива: OpenAI text-embedding-3-small ($0.02/1M tokens)

### Alternatives Considered

| Модель | Размерность | Цена | Качество |
|--------|-------------|------|----------|
| OpenAI text-embedding-3-small | 1536 | $0.02/1M | Хорошее |
| OpenAI text-embedding-3-large | 3072 | $0.13/1M | Отличное |
| sentence-transformers (local) | 384-768 | Бесплатно | Среднее |
| Cohere embed-v3 | 1024 | $0.10/1M | Хорошее |

### Implementation

Для 50 вин с описаниями ~200 слов каждое:
- ~10K tokens total
- Стоимость: ~$0.0002 (negligible)
- Выбор: OpenAI text-embedding-3-small (проще интеграция)

---

## 4. Цены вин

### Decision: Фиксированные цены в seed, без live updates

### Rationale
- MVP не требует актуальных цен
- Показываем "ориентировочная цена" с disclaimer
- Упрощает реализацию

### Data Source
- Средние цены из Wine-Searcher (ручной сбор для 50 вин)
- Округление до $5

---

## 5. Изображения

### Decision: Unsplash + fallback placeholder

### Rationale
- Unsplash: бесплатные изображения под лицензией
- Не требует хостинга (direct links)
- Placeholder для недоступных изображений

### Implementation

1. Поиск generic wine bottle images на Unsplash по типу:
   - "red wine bottle" → для красных
   - "white wine bottle" → для белых
   - "rose wine" → для розовых
   - "champagne bottle" → для игристых
2. Хранить URL в БД
3. Fallback: `/static/images/wine-placeholder.svg`

---

## Open Questions (Resolved)

| Вопрос | Решение |
|--------|---------|
| Откуда брать данные? | X-Wines + ручная курация |
| Какой embedding model? | OpenAI text-embedding-3-small |
| Как хранить embeddings? | pgvector с HNSW index |
| Откуда изображения? | Unsplash (generic by type) |
| Как обновлять цены? | Фиксированные в MVP |

---

## References

- [X-Wines Dataset](https://github.com/rogerioxavier/X-Wines)
- [LWIN Database](https://www.liv-ex.com/lwin/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector Tutorial](https://www.instaclustr.com/education/vector-database/pgvector-key-features-tutorial-and-pros-and-cons-2026-guide/)
- [Hybrid Search with pgvector](https://www.tigerdata.com/blog/combining-semantic-search-and-full-text-search-in-postgresql-with-cohere-pgvector-and-pgai)
