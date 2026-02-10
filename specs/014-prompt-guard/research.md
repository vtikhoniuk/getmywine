# Research: 014-prompt-guard

**Date**: 2026-02-10
**Branch**: `014-prompt-guard`

## Decision 1: Куда добавлять защитные инструкции в системном промпте

**Decision**: Добавить секцию ЗАЩИТА в `SYSTEM_PROMPT_BASE` — все варианты (cold start, personalized, continuation) наследуют её автоматически.

**Rationale**: `SYSTEM_PROMPT_BASE` — корень всех промптов. `SYSTEM_PROMPT_COLD_START` и `SYSTEM_PROMPT_PERSONALIZED` строятся как `BASE + дополнение`. `SYSTEM_PROMPT_CONTINUATION` — единственный, который не наследует BASE, но он всегда конкатенируется к одному из первых двух. Таким образом, добавление в BASE покрывает 100% сценариев.

**Alternatives considered**:
- Дублировать в каждом варианте → Нарушает DRY, риск рассинхронизации
- Отдельная переменная GUARD_PROMPT, конкатенируемая в коде → Избыточная абстракция для одного блока текста

## Decision 2: Формат маркера [GUARD]

**Decision**: `[GUARD:тип]` в начале ответа (перед `[INTRO]`), без закрывающего тега. Тип — одно из: `off_topic`, `prompt_injection`, `social_engineering`.

**Rationale**: Маркер должен быть: (1) легко парсим regex-ом, (2) не конфликтует с существующими маркерами, (3) содержит тип для классификации. Формат `[GUARD:type]` аналогичен `[WINE:N]` — единообразие с существующим стилем.

**Alternatives considered**:
- JSON-объект в начале ответа → Усложняет парсинг, ломает текстовый формат
- Маркер в конце ответа → Менее надёжен (LLM может обрезать конец)
- Отдельное поле в ответе (structured output) → Требует изменения API LLM-сервиса

## Decision 3: Где парсить и стрипать [GUARD]

**Decision**: Расширить `ParsedResponse` dataclass и `parse_structured_response()` в `sommelier_prompts.py`. Добавить поле `guard_type: Optional[str]`. Парсинг `[GUARD:type]` — первый шаг при разборе ответа. Логирование — в `ChatService.send_message()` после получения ответа от SommelierService.

**Rationale**: `parse_structured_response()` — единая точка парсинга, используемая и web, и Telegram. Расширение этой функции гарантирует, что [GUARD] будет обработан во всех каналах. Стрип маркера происходит неявно — `parsed.intro` уже не содержит текст перед `[INTRO]`.

**Alternatives considered**:
- Отдельная функция парсинга → Два прохода по тексту, дублирование
- Парсинг в SommelierService → Telegram бот не использует SommelierService напрямую для парсинга

## Decision 4: Стратегия логирования

**Decision**: Python `logging.warning()` с structured prefix `GUARD_ALERT` в `ChatService.send_message()`. Формат: `GUARD_ALERT type={type} user_id={user_id} message="{first_100_chars}"`.

**Rationale**: Использует существующую инфраструктуру логирования. WARNING level — достаточно для мониторинга, не требует отдельной таблицы БД. Формат с prefix позволяет grep/filter по логам. User ID включён для возможного последующего анализа, но не включает PII.

**Alternatives considered**:
- Отдельная таблица в БД → Overkill для MVP, можно добавить позднее
- INFO level → Слишком тихо, GUARD-события должны быть заметны
- ERROR level → Завышает severity, это не ошибка системы

## Decision 5: Тестирование prompt guard

**Decision**: Юнит-тесты для парсинга `[GUARD]` маркера + набор тестовых промптов для ручного/полуавтоматического тестирования LLM-ответов. Интеграционные тесты с мок-LLM для проверки полного потока (запрос → парсинг → логирование).

**Rationale**: LLM-ответы недетерминистичны — 100% автоматизация тестов промпт-защиты невозможна. Юнит-тесты покрывают парсер (детерминистичная часть). Тестовые наборы промптов — для ручной валидации при изменениях промпта.

**Alternatives considered**:
- Только юнит-тесты → Не покрывает реальное поведение LLM
- Полная интеграция с LLM в CI → Дорого, недетерминистично, медленно
