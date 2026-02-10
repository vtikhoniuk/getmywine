# Data Model: Agentic RAG для рекомендаций вин

**Feature**: 015-agentic-rag | **Date**: 2026-02-10

## Изменения схемы БД

**Схема таблицы `wines` НЕ МЕНЯЕТСЯ.** Все поля, типы, constraints и индексы остаются прежними. Новые миграции не требуются.

## Изменения в Repository (новые фильтры)

### WineRepository.get_list() — новые параметры

| Параметр | Тип | Описание | SQL |
|----------|-----|----------|-----|
| grape_variety | Optional[str] | Сорт винограда | `Wine.grape_varieties.contains([value])` |
| food_pairing | Optional[str] | Сочетаемость с блюдом | `Wine.food_pairings.overlap([value])` |
| region | Optional[str] | Регион производства | `Wine.region.ilike(f'%{value}%')` |

**Примечание**: grape_variety — поиск по точному вхождению в ARRAY (например, "Мальбек" → `["Мальбек"]`). food_pairing — поиск по пересечению (overlap), т.к. пользователь может указать одно блюдо из нескольких в массиве.

### WineRepository.semantic_search() — без изменений

Существующий метод принимает `embedding: list[float]` и опциональные фильтры (wine_type, sweetness, price_min, price_max). Используется как есть.

## Tool Definitions (JSON Schema)

Инструменты определяются для LLM API в формате OpenAI function calling.

### Tool 1: search_wines

```json
{
  "type": "function",
  "function": {
    "name": "search_wines",
    "description": "Поиск вин по структурированным критериям: тип, сладость, сорт винограда, цена, страна, регион, сочетаемость с блюдами. Используй когда пользователь указывает конкретные характеристики вина.",
    "parameters": {
      "type": "object",
      "properties": {
        "wine_type": {
          "type": "string",
          "enum": ["red", "white", "rose", "sparkling"],
          "description": "Тип вина"
        },
        "sweetness": {
          "type": "string",
          "enum": ["dry", "semi_dry", "semi_sweet", "sweet"],
          "description": "Сладость вина"
        },
        "grape_variety": {
          "type": "string",
          "description": "Сорт винограда (например: Мальбек, Каберне Совиньон, Рислинг)"
        },
        "price_min": {
          "type": "number",
          "description": "Минимальная цена в рублях"
        },
        "price_max": {
          "type": "number",
          "description": "Максимальная цена в рублях"
        },
        "country": {
          "type": "string",
          "description": "Страна производства (например: Аргентина, Италия, Россия)"
        },
        "region": {
          "type": "string",
          "description": "Регион производства (например: Тоскана, Мендоса)"
        },
        "food_pairing": {
          "type": "string",
          "description": "Блюдо для сочетания (например: стейк, рыба, сыр)"
        }
      },
      "required": []
    }
  }
}
```

### Tool 2: semantic_search

```json
{
  "type": "function",
  "function": {
    "name": "semantic_search",
    "description": "Семантический поиск вин по описанию, настроению или вкусовым предпочтениям. Используй когда пользователь описывает вино абстрактно: 'лёгкое и освежающее', 'с нотами ванили', 'элегантное для ужина'.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Текстовое описание желаемого вина на естественном языке"
        },
        "wine_type": {
          "type": "string",
          "enum": ["red", "white", "rose", "sparkling"],
          "description": "Дополнительный фильтр по типу вина (опционально)"
        },
        "price_max": {
          "type": "number",
          "description": "Дополнительный фильтр по максимальной цене (опционально)"
        }
      },
      "required": ["query"]
    }
  }
}
```

## Tool Response Format

Оба инструмента возвращают JSON с найденными винами в формате, пригодном для формирования рекомендации:

```json
{
  "found": 5,
  "wines": [
    {
      "name": "Malbec",
      "producer": "Luigi Bosca",
      "region": "Мендоса, Аргентина",
      "vintage_year": 2024,
      "grape_varieties": ["Мальбек"],
      "wine_type": "red",
      "sweetness": "dry",
      "body": 4,
      "tannins": 3,
      "acidity": 3,
      "price_rub": 1799,
      "description": "...",
      "tasting_notes": "...",
      "food_pairings": ["стейк", "ягнятина", "зрелые сыры"]
    }
  ],
  "filters_applied": {
    "wine_type": "red",
    "price_max": 2000
  }
}
```

Для semantic_search дополнительно включается `similarity_score` (0.0-1.0) для каждого вина.

## Agent Loop — State Model

Состояние agent loop не персистится. Существует только в рамках обработки одного запроса.

```
AgentState:
  messages: list[dict]       # Аккумулированные сообщения (system + user + assistant + tool)
  tools: list[dict]          # Определения инструментов (константа)
  iteration: int             # Текущая итерация (0-2)
  max_iterations: int        # Лимит (2)
  found_wines: list[Wine]    # Накопленные результаты поиска
```

### State Transitions

```
START → [LLM call with tools]
  ├─ Response has tool_calls → EXECUTE_TOOLS → increment iteration
  │   ├─ iteration < max_iterations → [LLM call with tools + results]
  │   └─ iteration >= max_iterations → GENERATE_FINAL
  ├─ Response has content (no tool_calls) → DONE
  └─ Error → FALLBACK (get_list + standard prompt)
```

## Validation Rules

1. **Tool parameters**: Все параметры опциональны для search_wines. query обязателен для semantic_search
2. **Enum values**: wine_type и sweetness валидируются перед SQL-запросом; невалидные значения игнорируются
3. **Price range**: price_min < price_max; если нарушено — price_min игнорируется
4. **Iteration limit**: Максимум 2 итерации tool calls; после — финальный LLM call без tools
5. **Empty results**: 0 вин от инструмента → LLM получает `{"found": 0, "wines": []}` и решает сам (расширить поиск или сообщить пользователю)
