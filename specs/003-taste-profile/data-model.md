# Data Model: Taste Profile Discovery

**Feature**: 003-taste-profile
**Date**: 2026-02-02

## Entity Relationship Diagram

```
┌─────────────────┐       1:1        ┌─────────────────────┐
│      User       │─────────────────▶│    TasteProfile     │
│  (from US-001)  │                  │                     │
└─────────────────┘                  └─────────────────────┘
        │                                      │
        │ 1:N                                  │ contains
        ▼                                      ▼
┌─────────────────┐                  ┌─────────────────────┐
│   WineMemory    │                  │  ProfileParameter   │
│                 │                  │   (embedded/JSON)   │
└─────────────────┘                  └─────────────────────┘
```

## Entities

### TasteProfile

Вкусовой профиль пользователя. Один профиль на пользователя.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK → users.id, UNIQUE | Связь с пользователем |
| sweetness | JSONB | nullable | Параметр сладости {value: 1-5, confidence: 0-1} |
| acidity | JSONB | nullable | Параметр кислотности {value: 1-5, confidence: 0-1} |
| tannins | JSONB | nullable | Параметр танинов {value: 1-5, confidence: 0-1} |
| body | JSONB | nullable | Параметр тела {value: 1-5, confidence: 0-1} |
| preferred_aromas | JSONB | default [] | Список предпочитаемых ароматов |
| budget_range | VARCHAR(20) | nullable | ID диапазона бюджета (budget_1..budget_5) |
| experience_level | VARCHAR(20) | nullable | Уровень опыта (novice, amateur, expert) |
| onboarding_status | VARCHAR(20) | NOT NULL, default 'pending' | pending, skipped, completed |
| onboarding_step | INTEGER | nullable | Текущий шаг онбординга (1-5) |
| created_at | TIMESTAMP | NOT NULL, default now() | Дата создания |
| updated_at | TIMESTAMP | NOT NULL, default now() | Дата последнего обновления |

**Indexes**:
- `idx_taste_profile_user_id` on user_id (UNIQUE)

**Validation Rules**:
- `sweetness.value`, `acidity.value`, `tannins.value`, `body.value` ∈ [1, 5]
- `*.confidence` ∈ [0.0, 1.0]
- `budget_range` ∈ {null, 'budget_1', 'budget_2', 'budget_3', 'budget_4', 'budget_5'}
- `experience_level` ∈ {null, 'novice', 'amateur', 'expert'}
- `onboarding_status` ∈ {'pending', 'skipped', 'in_progress', 'completed'}

### WineMemory

Запомнившееся вино, описанное пользователем.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK → users.id, NOT NULL | Связь с пользователем |
| raw_description | TEXT | NOT NULL | Оригинальное описание пользователя |
| extracted_type | VARCHAR(20) | nullable | Тип вина (red, white, rose, sparkling) |
| extracted_region | VARCHAR(100) | nullable | Извлечённый регион |
| extracted_notes | JSONB | default [] | Извлечённые вкусовые ноты |
| sentiment | VARCHAR(20) | NOT NULL | Впечатление (liked, disliked, neutral) |
| context | TEXT | nullable | Контекст (где/когда пили, с чем) |
| created_at | TIMESTAMP | NOT NULL, default now() | Дата создания |

**Indexes**:
- `idx_wine_memory_user_id` on user_id
- `idx_wine_memory_created_at` on created_at DESC

**Validation Rules**:
- `raw_description` length ≤ 2000 characters
- `extracted_type` ∈ {null, 'red', 'white', 'rose', 'sparkling'}
- `sentiment` ∈ {'liked', 'disliked', 'neutral'}

## JSONB Structures

### ProfileParameter (embedded in TasteProfile)

```json
{
  "value": 3,           // 1-5 scale
  "confidence": 0.7,    // 0.0-1.0
  "updated_at": "2026-02-02T10:30:00Z"
}
```

### PreferredAromas (embedded in TasteProfile)

```json
[
  {"aroma": "citrus", "confidence": 0.8},
  {"aroma": "oak", "confidence": 0.5},
  {"aroma": "berry", "confidence": 0.9}
]
```

## State Transitions

### OnboardingStatus

```
                    ┌──────────────┐
                    │   pending    │ ◀── initial state (profile created)
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │    skipped      │       │  in_progress    │
    └─────────────────┘       └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   completed     │
                              └─────────────────┘
```

**Transitions**:
- `pending` → `skipped`: User clicks "Пропустить"
- `pending` → `in_progress`: User starts onboarding
- `in_progress` → `completed`: User finishes all questions
- `skipped` → `in_progress`: User decides to take survey later

## Migration Script (reference)

```sql
-- Migration: 005_create_taste_profile_tables.py

CREATE TABLE taste_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    sweetness JSONB,
    acidity JSONB,
    tannins JSONB,
    body JSONB,
    preferred_aromas JSONB DEFAULT '[]'::jsonb,
    budget_range VARCHAR(20),
    experience_level VARCHAR(20),
    onboarding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    onboarding_step INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_taste_profile_user_id ON taste_profiles(user_id);

CREATE TABLE wine_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    raw_description TEXT NOT NULL,
    extracted_type VARCHAR(20),
    extracted_region VARCHAR(100),
    extracted_notes JSONB DEFAULT '[]'::jsonb,
    sentiment VARCHAR(20) NOT NULL,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_wine_memory_user_id ON wine_memories(user_id);
CREATE INDEX idx_wine_memory_created_at ON wine_memories(created_at DESC);

-- Check constraints
ALTER TABLE taste_profiles ADD CONSTRAINT chk_onboarding_status
    CHECK (onboarding_status IN ('pending', 'skipped', 'in_progress', 'completed'));

ALTER TABLE taste_profiles ADD CONSTRAINT chk_budget_range
    CHECK (budget_range IS NULL OR budget_range IN ('budget_1', 'budget_2', 'budget_3', 'budget_4', 'budget_5'));

ALTER TABLE taste_profiles ADD CONSTRAINT chk_experience_level
    CHECK (experience_level IS NULL OR experience_level IN ('novice', 'amateur', 'expert'));

ALTER TABLE wine_memories ADD CONSTRAINT chk_extracted_type
    CHECK (extracted_type IS NULL OR extracted_type IN ('red', 'white', 'rose', 'sparkling'));

ALTER TABLE wine_memories ADD CONSTRAINT chk_sentiment
    CHECK (sentiment IN ('liked', 'disliked', 'neutral'));
```

## Dependencies

- **User** (from US-001): TasteProfile и WineMemory связаны с User через FK
- **Conversation/Message** (from US-002): ProfileService читает сообщения для извлечения предпочтений
