# Research: Agentic RAG для рекомендаций вин

**Feature**: 015-agentic-rag | **Date**: 2026-02-10

## R-001: Tool Use API через OpenRouter

**Вопрос**: Поддерживает ли OpenRouter tool use / function calling через OpenAI SDK?

**Decision**: OpenRouter полностью поддерживает tool calling через стандартный OpenAI SDK с параметром `tools`.

**Rationale**:
- API формат: стандартный OpenAI `tools` параметр с JSON Schema для каждого инструмента
- Ответ: `response.choices[0].message.tool_calls` — массив вызовов с `function.name`, `function.arguments`
- Результат: отправляется сообщением с `role: "tool"` и `tool_call_id`
- Поддержка: `anthropic/claude-sonnet-4` (текущая модель проекта) поддерживает tool calling
- Параллельные вызовы: `parallel_tool_calls=false` для последовательного выполнения
- SDK: `openai.AsyncOpenAI` — тот же клиент, что уже используется в проекте

**Alternatives considered**:
- Anthropic native API (client.messages.create с tools) — работает, но OpenRouter даёт единый интерфейс для всех провайдеров
- LangChain/LangGraph — избыточно для 2 инструментов и 50 вин

**Implementation pattern**:
```python
# 1. Определение tools
tools = [{"type": "function", "function": {"name": "search_wines", ...}}]

# 2. Первый вызов — LLM решает, какие tools вызвать
response = await client.chat.completions.create(
    model=model, messages=messages, tools=tools
)

# 3. Если tool_calls в ответе — выполнить и отправить результат
if response.choices[0].message.tool_calls:
    messages.append(response.choices[0].message)  # assistant message
    for tool_call in response.choices[0].message.tool_calls:
        result = execute_tool(tool_call)
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    # 4. Второй вызов — LLM формирует ответ с результатами
    response = await client.chat.completions.create(
        model=model, messages=messages, tools=tools
    )
```

**Source**: [OpenRouter Tool Calling Docs](https://openrouter.ai/docs/guides/features/tool-calling)

---

## R-002: Текущее состояние LLM-сервиса

**Вопрос**: Что нужно изменить в `llm.py` для поддержки tool use?

**Decision**: Добавить новый метод `generate_with_tools()` в `BaseLLMService` и реализации. Не менять существующий `generate()`.

**Rationale**:
- Текущий `generate()` возвращает `str` — чистый текст ответа
- Tool use требует возврат полного `ChatCompletionMessage` (может содержать и `content`, и `tool_calls`)
- Новый метод нужен для обработки `tool_calls` в ответе
- Существующий `generate()` используется в welcome-потоке (вне scope) — не трогаем
- `generate_wine_recommendation()` — обёртка над `generate()` с `temperature=0.6`; заменяется на `generate_with_tools()` в sommelier

**Current code gap** (llm.py:111):
```python
return response.choices[0].message.content  # Только текст, tool_calls игнорируются
```

**Required change**:
```python
async def generate_with_tools(
    self, system_prompt, user_prompt, tools, messages=None, temperature=None, max_tokens=None
) -> ChatCompletionMessage:
    # Возвращает полный message object (content + tool_calls)
```

**Alternatives considered**:
- Модификация существующего `generate()` — нарушит обратную совместимость с welcome-потоком
- Отдельный класс `AgentLLMService` — избыточно, один новый метод достаточен

---

## R-003: Wine Repository — недостающие фильтры

**Вопрос**: Какие фильтры необходимо добавить в `WineRepository.get_list()`?

**Decision**: Добавить 2 фильтра: `grape_variety` и `food_pairing`. Оба работают через PostgreSQL ARRAY contains.

**Rationale**:
- `grape_varieties` (ARRAY текст): хранится как `["Мальбек"]` или `["Каберне Совиньон", "Мерло"]`
- `food_pairings` (ARRAY текст): хранится как `["стейк", "ягнятина", "зрелые сыры"]`
- Язык значений: русский (проверено в wines_seed.json)
- SQLAlchemy ARRAY contains: `Wine.grape_varieties.contains([value])`
- Для food_pairings: поиск по вхождению любого элемента — `Wine.food_pairings.overlap([value])`

**Current `get_list()` parameters** (wine.py:36-49):
- wine_type, sweetness, price_min, price_max, country, body_min, body_max, with_image

**New parameters**:
- `grape_variety: Optional[str]` — поиск вин, содержащих указанный сорт
- `food_pairing: Optional[str]` — поиск вин, подходящих к указанному блюду
- `region: Optional[str]` — уже доступно как поле Wine, но не как фильтр в get_list()

**Alternatives considered**:
- Фильтрация в Python после SQL-запроса — неэффективно для масштабирования
- Full-text search по grape_varieties — избыточно для ARRAY с точными значениями

---

## R-004: Архитектура Agent Loop

**Вопрос**: Где разместить agent loop и как структурировать?

**Decision**: Agent loop в новом методе `SommelierService.generate_agentic_response()`. Вызывается из `generate_response()` вместо текущей 4-path логики.

**Rationale**:
- SommelierService уже оркестрирует LLM-вызовы — логичное место для agent loop
- `generate_response()` остаётся точкой входа, внутри маршрутизация меняется
- Welcome-поток (`generate_welcome_with_suggestions()`) не затрагивается
- Agent loop: простой цикл (max 2 итерации), не требует отдельного класса

**Flow**:
```
generate_response()
├─ build_unified_system_prompt(user_profile, events_context)
├─ generate_agentic_response(system_prompt, user_message, history, tools)
│  ├─ Iteration 1: LLM → tool_calls? → execute tools → add results
│  ├─ Iteration 2: LLM → tool_calls? → execute tools → add results
│  └─ Final: LLM → text response with [INTRO][WINE:1-3][CLOSING]
└─ return response_text
```

**Tool definitions** (2 инструмента):

1. `search_wines` — структурированный SQL поиск:
   - Parameters: wine_type?, sweetness?, grape_variety?, price_min?, price_max?, country?, region?, food_pairing?
   - Returns: JSON list вин в формате каталога

2. `semantic_search` — векторный поиск по описанию:
   - Parameters: query (text description)
   - Returns: JSON list вин с similarity score

**Alternatives considered**:
- Отдельный AgentService — добавляет слой без пользы (50 вин, 2 инструмента)
- Tool execution в LLMService — нарушает Clean Architecture (LLM не должен знать о Wine)

---

## R-005: Единый системный промпт

**Вопрос**: Как объединить 4 промпта (cold_start, personalized, event, food) в один?

**Decision**: Единый `SYSTEM_PROMPT_AGENTIC` с описанием инструментов и контекстными блоками.

**Rationale**:
- 4 текущих промпта содержат ~80% общего контента (SYSTEM_PROMPT_BASE)
- Различия: hint для холодного старта, профиль пользователя, event-контекст, food pairing hints
- С tool use LLM сам определяет контекст — не нужна keyword-маршрутизация
- Пользовательский профиль и event-контекст передаются как user prompt context (не system prompt)

**Structure единого промпта**:
```
SYSTEM_PROMPT_AGENTIC = SYSTEM_PROMPT_BASE + """

## Доступные инструменты
- search_wines: поиск по структурированным критериям (тип, сладость, сорт, цена, страна, блюдо)
- semantic_search: поиск по описанию и настроению

## Порядок работы
1. Проанализируй запрос пользователя
2. Вызови подходящий инструмент (или оба)
3. Из результатов выбери 3 лучших вина
4. Сформируй ответ в формате [INTRO][WINE:1-3][CLOSING]

## Если инструменты не нужны
- Для общих вопросов о вине отвечай без инструментов
- Для smalltalk отвечай без инструментов

## Fallback
- 0 результатов → расширь фильтры (убери наименее важные)
- Нет подходящих вин → скажи честно и предложи альтернативу
"""
```

**User prompt включает** (динамически):
- Пользовательский профиль (если есть)
- Контекст дня (праздники, сезон, время)
- Историю переписки (через messages)

**Alternatives considered**:
- Сохранить 4 промпта + добавить tools к каждому — дублирование контента, сложнее поддерживать
- System prompt per-request — можно, но единый промпт проще

---

## R-006: Семантический поиск — генерация эмбеддинга запроса

**Вопрос**: Как генерировать эмбеддинг для пользовательского запроса в runtime?

**Decision**: Вызов OpenAI Embeddings API (через OpenRouter или OpenAI напрямую) для текста пользовательского запроса.

**Rationale**:
- Вина уже имеют эмбеддинги (1536 dims, text-embedding-3-small)
- Для cosine similarity нужен эмбеддинг запроса той же модели
- OpenRouter поддерживает embeddings API: `POST /api/v1/embeddings`
- OpenAI SDK: `client.embeddings.create(model="text-embedding-3-small", input=query)`
- Текущий `generate_embeddings.py` использует тот же API — консистентно

**Implementation**:
```python
async def get_query_embedding(self, query: str) -> list[float]:
    response = await self.client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return response.data[0].embedding
```

**Where**: Новый метод в `LLMService` или отдельный `EmbeddingService`.

**Alternatives considered**:
- Локальная модель (sentence-transformers) — несовместима с text-embedding-3-small эмбеддингами в БД
- OpenRouter embeddings — не все модели доступны; OpenAI напрямую надёжнее для embeddings

---

## R-007: Обработка ошибок и fallback

**Вопрос**: Что происходит, когда tool use не работает (ошибка API, неподдерживаемая модель)?

**Decision**: Graceful degradation — при ошибке tool use переключаемся на текущее поведение (get_list + промпт с каталогом).

**Rationale**:
- Tool use может не работать: модель не поддерживает, API error, rate limit
- Текущий flow (20 случайных вин в промпт) — рабочий fallback
- Пользователь не должен видеть ошибку — просто менее точные рекомендации
- Логирование ошибки для диагностики

**Fallback chain**:
1. Tool use → success → agentic response
2. Tool use → error → log error → fallback to get_list(limit=20) + standard prompt
3. LLM → error → mock AI response (уже реализовано)

**Alternatives considered**:
- Показывать ошибку пользователю — плохой UX
- Retry tool use — увеличивает латентность, 1 retry достаточно в рамках 2 итераций
