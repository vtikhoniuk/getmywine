# Research: Taste Profile Discovery

**Feature**: 003-taste-profile
**Date**: 2026-02-02

## R1: Profile Extraction Approach

**Decision**: Mock-based extraction с подготовкой к LLM

**Rationale**:
- MVP использует mock AI (из spec.md: "Интеграция с реальным LLM — используется mock")
- Структура сервиса должна позволять лёгкую замену на реальный LLM
- Mock возвращает предопределённые ответы на ключевые слова

**Alternatives considered**:
- Rule-based extraction: Отвергнуто — слишком ограничено для естественного языка
- Immediate LLM integration: Отвергнуто — MVP scope, фокус на структуре данных

**Implementation notes**:
- `ProfileExtractorService` с интерфейсом `extract_preferences(text: str) -> ProfileUpdate`
- Mock реализация: словарь keyword → параметр
- Пример: "сухое" → sweetness: 1, "сладкое" → sweetness: 5

## R2: Profile Parameters & Scales

**Decision**: 5 основных параметров на шкале 1-5 + список ароматов

**Parameters**:
| Параметр | Шкала | Описание |
|----------|-------|----------|
| sweetness | 1-5 | 1=сухое, 5=сладкое |
| acidity | 1-5 | 1=мягкое, 5=кислое |
| tannins | 1-5 | 1=мягкие, 5=терпкие (для красных) |
| body | 1-5 | 1=лёгкое, 5=насыщенное |
| preferred_aromas | list[str] | фрукты, специи, цветы, etc. |

**Rationale**:
- 5-балльная шкала интуитивно понятна пользователям
- Параметры соответствуют стандартной винной терминологии
- Ароматы — свободный список, т.к. их слишком много для enum

**Alternatives considered**:
- 10-балльная шкала: Отвергнуто — избыточная точность для MVP
- Binary preferences: Отвергнуто — теряется нюанс

## R3: Confidence Scoring

**Decision**: Confidence 0.0-1.0 на каждый параметр

**Algorithm**:
```
initial_confidence = 0.0 (unknown)
after_explicit_answer = 0.8 (direct statement like "я люблю сухое")
after_implicit_signal = 0.3 (indirect signal like "мне понравилось то белое")
after_confirmation = min(current + 0.2, 1.0) (repeated preference)
after_contradiction = max(current - 0.3, 0.0) (conflicting statement)
```

**Rationale**:
- Позволяет AI понимать, насколько он уверен в предпочтениях
- Низкая уверенность → больше вопросов или disclaimers
- Высокая уверенность → точные рекомендации

**Alternatives considered**:
- Boolean known/unknown: Отвергнуто — теряется градация
- Bayesian approach: Отвергнуто — overkill для MVP

## R4: Budget Ranges

**Decision**: 5 фиксированных диапазонов в рублях

**Ranges**:
| ID | Label | Min (₽) | Max (₽) |
|----|-------|---------|---------|
| budget_1 | До 500₽ | 0 | 500 |
| budget_2 | 500-1000₽ | 500 | 1000 |
| budget_3 | 1000-2000₽ | 1000 | 2000 |
| budget_4 | 2000-5000₽ | 2000 | 5000 |
| budget_5 | 5000₽+ | 5000 | null |

**Rationale**:
- Диапазоны из spec.md (FR-014)
- Покрывают массовый и премиум сегменты
- null для верхней границы = без ограничения

**Alternatives considered**:
- Произвольная сумма: Отвергнуто — сложнее для UX и matching
- Относительные категории (cheap/medium/expensive): Отвергнуто — субъективно

## R5: Onboarding Flow Pattern

**Decision**: Inline onboarding в чате с возможностью пропуска

**Flow**:
```
1. User enters chat for first time
2. AI: Welcome message + "Давайте узнаем ваши предпочтения" + [Пропустить]
3. If skip: Create empty profile, show disclaimer, continue to chat
4. If continue:
   a. AI asks about sweetness preference
   b. AI asks about wine experience
   c. AI asks about favorite foods/flavors
   d. AI asks about budget
   e. AI confirms profile summary
5. Profile created, user can chat freely
```

**Rationale**:
- Не прерывает пользователя отдельным модальным окном
- Диалоговый формат соответствует концепции AI-сомелье
- Пропуск снижает барьер входа (из spec.md US-004)

**Alternatives considered**:
- Separate onboarding page: Отвергнуто — создаёт friction
- Form-based survey: Отвергнуто — противоречит "диалог, не анкета"

## R6: Wine Memory Structure

**Decision**: Свободное описание + извлечённые характеристики + sentiment

**Structure**:
```
WineMemory:
  - raw_description: str (user input as-is)
  - extracted_type: enum (red, white, rose, sparkling, null)
  - extracted_region: str | null
  - extracted_notes: list[str]
  - sentiment: enum (liked, disliked, neutral)
  - context: str | null (occasion, food pairing)
  - created_at: datetime
```

**Rationale**:
- Сохраняем оригинал для future LLM analysis
- Извлекаем структурированные данные для matching
- Sentiment влияет на профиль

**Alternatives considered**:
- Only structured data: Отвергнуто — теряем context
- Only raw text: Отвергнуто — не можем использовать для recommendations

## R7: Profile Update Triggers

**Decision**: Автоматическое обновление после каждого релевантного сообщения

**Triggers**:
1. Explicit onboarding answers → high confidence update
2. Wine memory creation → medium confidence update
3. Chat messages with preference signals → low confidence update
4. Feedback on recommendations (future) → high confidence update

**Rationale**:
- Профиль "учится" с каждым взаимодействием (SC-005)
- Разные источники имеют разный weight

**Implementation**:
- `ProfileService.process_message(user_id, message)` вызывается после каждого сообщения
- Возвращает `ProfileUpdateResult` с изменениями или None
