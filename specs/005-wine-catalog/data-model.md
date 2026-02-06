# Data Model: Wine Catalog

**Date**: 2026-02-03
**Feature**: 005-wine-catalog

## Entities

### Wine

Основная сущность каталога вин.

```
┌─────────────────────────────────────────────────────────────┐
│                          Wine                                │
├─────────────────────────────────────────────────────────────┤
│ id              : UUID          [PK, auto]                  │
│ name            : VARCHAR(255)  [NOT NULL, indexed]         │
│ producer        : VARCHAR(255)  [NOT NULL]                  │
│ vintage_year    : INTEGER       [NULL, 1900-2030]           │
│ country         : VARCHAR(100)  [NOT NULL]                  │
│ region          : VARCHAR(255)  [NOT NULL]                  │
│ appellation     : VARCHAR(255)  [NULL]                      │
│ grape_varieties : VARCHAR[]     [NOT NULL, array]           │
│ wine_type       : wine_type     [NOT NULL, enum]            │
│ sweetness       : sweetness     [NOT NULL, enum]            │
│ acidity         : INTEGER       [NOT NULL, 1-5]             │
│ tannins         : INTEGER       [NOT NULL, 1-5]             │
│ body            : INTEGER       [NOT NULL, 1-5]             │
│ description     : TEXT          [NOT NULL]                  │
│ tasting_notes   : TEXT          [NULL]                      │
│ food_pairings   : VARCHAR[]     [NULL, array]               │
│ price_rub       : DECIMAL(10,2) [NOT NULL]                  │
│ price_range     : price_range   [NOT NULL, enum]            │
│ image_url       : VARCHAR(500)  [NULL]                      │
│ embedding       : VECTOR(1536)  [NULL, pgvector]            │
│ created_at      : TIMESTAMPTZ   [NOT NULL, auto]            │
│ updated_at      : TIMESTAMPTZ   [NOT NULL, auto]            │
└─────────────────────────────────────────────────────────────┘
```

## Enums

### wine_type

```sql
CREATE TYPE wine_type AS ENUM (
    'red',       -- Красное
    'white',     -- Белое
    'rose',      -- Розовое
    'sparkling'  -- Игристое
);
```

### sweetness

```sql
CREATE TYPE sweetness AS ENUM (
    'dry',        -- Сухое
    'semi_dry',   -- Полусухое
    'semi_sweet', -- Полусладкое
    'sweet'       -- Сладкое
);
```

### price_range

```sql
CREATE TYPE price_range AS ENUM (
    'budget',   -- < 2400₽
    'mid',      -- 2400₽-8000₽
    'premium'   -- > 8000₽
);
```

## Indexes

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| wines_pkey | PRIMARY | id | Уникальный идентификатор |
| ix_wines_name | BTREE | name | Поиск по названию |
| ix_wines_wine_type | BTREE | wine_type | Фильтр по типу |
| ix_wines_price_rub | BTREE | price_rub | Сортировка/фильтр по цене |
| ix_wines_country | BTREE | country | Фильтр по стране |
| ix_wines_embedding | HNSW | embedding | Семантический поиск |

## Constraints

| Constraint | Type | Rule |
|------------|------|------|
| ck_wines_vintage_year | CHECK | vintage_year IS NULL OR (vintage_year >= 1900 AND vintage_year <= 2030) |
| ck_wines_acidity | CHECK | acidity >= 1 AND acidity <= 5 |
| ck_wines_tannins | CHECK | tannins >= 1 AND tannins <= 5 |
| ck_wines_body | CHECK | body >= 1 AND body <= 5 |
| ck_wines_price_rub | CHECK | price_rub > 0 |

## Relationships

```
┌─────────────────┐
│      Wine       │
└─────────────────┘
        │
        │ (future: favorites, ratings)
        ▼
┌─────────────────┐
│      User       │
└─────────────────┘
```

**Note**: В MVP нет связи Wine ↔ User. Добавится в Release 1.1 (US-015 Избранное).

## Validation Rules

### Name
- Required
- 1-255 characters
- Trimmed whitespace

### Vintage Year
- Optional (NV wines)
- If present: 1900-2030

### Grape Varieties
- Required
- At least 1 variety
- Each: 1-100 characters

### Acidity / Tannins / Body
- Required
- Integer 1-5

### Description
- Required
- 10-2000 characters

### Price RUB
- Required
- Positive decimal
- Max 2 decimal places

### Image URL
- Optional
- If present: valid URL format, max 500 chars

## Migration SQL

```sql
-- 005_create_wines_table.py

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE wine_type AS ENUM ('red', 'white', 'rose', 'sparkling');
CREATE TYPE sweetness AS ENUM ('dry', 'semi_dry', 'semi_sweet', 'sweet');
CREATE TYPE price_range AS ENUM ('budget', 'mid', 'premium');

CREATE TABLE wines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    producer VARCHAR(255) NOT NULL,
    vintage_year INTEGER,
    country VARCHAR(100) NOT NULL,
    region VARCHAR(255) NOT NULL,
    appellation VARCHAR(255),
    grape_varieties VARCHAR[] NOT NULL,
    wine_type wine_type NOT NULL,
    sweetness sweetness NOT NULL,
    acidity INTEGER NOT NULL,
    tannins INTEGER NOT NULL,
    body INTEGER NOT NULL,
    description TEXT NOT NULL,
    tasting_notes TEXT,
    food_pairings VARCHAR[],
    price_rub DECIMAL(10,2) NOT NULL,
    price_range price_range NOT NULL,
    image_url VARCHAR(500),
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_wines_vintage_year
        CHECK (vintage_year IS NULL OR (vintage_year >= 1900 AND vintage_year <= 2030)),
    CONSTRAINT ck_wines_acidity CHECK (acidity >= 1 AND acidity <= 5),
    CONSTRAINT ck_wines_tannins CHECK (tannins >= 1 AND tannins <= 5),
    CONSTRAINT ck_wines_body CHECK (body >= 1 AND body <= 5),
    CONSTRAINT ck_wines_price_rub CHECK (price_rub > 0)
);

CREATE INDEX ix_wines_name ON wines(name);
CREATE INDEX ix_wines_wine_type ON wines(wine_type);
CREATE INDEX ix_wines_price_rub ON wines(price_rub);
CREATE INDEX ix_wines_country ON wines(country);
CREATE INDEX ix_wines_embedding ON wines
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```
