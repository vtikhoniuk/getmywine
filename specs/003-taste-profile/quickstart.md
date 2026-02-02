# Quickstart: Taste Profile Discovery

**Feature**: 003-taste-profile
**Date**: 2026-02-02

## Prerequisites

- Docker и Docker Compose установлены
- Фича US-001 (auth) реализована и работает
- Фича US-002 (chat) реализована и работает

## Setup

```bash
# 1. Перейти в ветку фичи
git checkout 003-taste-profile

# 2. Запустить окружение
docker compose up -d

# 3. Применить миграции
docker compose exec backend alembic upgrade head

# 4. Проверить миграцию
docker compose exec db psql -U ai_sommelier -c "\dt" | grep -E "(taste_profiles|wine_memories)"
# Ожидаемый вывод:
#  public | taste_profiles | table | ai_sommelier
#  public | wine_memories  | table | ai_sommelier
```

## Validation Scenarios

### Scenario 1: Skip Onboarding (US1)

**Цель**: Проверить пропуск опроса и создание пустого профиля

```bash
# 1. Зарегистрировать нового пользователя (если нет)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!", "is_age_verified": true}'

# 2. Войти и получить cookie
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!"}' \
  -c cookies.txt

# 3. Пропустить онбординг
curl -X POST http://localhost:8000/api/profile/onboarding/skip \
  -b cookies.txt

# Ожидаемый ответ:
# {
#   "id": "...",
#   "onboarding_status": "skipped",
#   "sweetness": null,
#   "acidity": null,
#   ...
# }

# 4. Получить профиль
curl http://localhost:8000/api/profile \
  -b cookies.txt

# Ожидаемый ответ: профиль с onboarding_status = "skipped", все параметры null
```

### Scenario 2: Complete Onboarding (US2)

**Цель**: Пройти онбординг полностью

```bash
# 1. Создать нового пользователя (другой email)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test2@example.com", "password": "Test123!", "is_age_verified": true}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test2@example.com", "password": "Test123!"}' \
  -c cookies2.txt

# 2. Начать онбординг
curl -X POST http://localhost:8000/api/profile/onboarding/start \
  -b cookies2.txt

# Ожидаемый ответ:
# {
#   "step": 1,
#   "total_steps": 5,
#   "question": "Какое вино вам больше нравится: сухое или сладкое?",
#   "question_type": "sweetness",
#   "suggested_options": ["Сухое", "Полусухое", "Полусладкое", "Сладкое", "Не знаю"],
#   "allows_free_text": true
# }

# 3. Ответить на вопросы (пройти все 5 шагов)
curl -X POST http://localhost:8000/api/profile/onboarding/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "Предпочитаю сухое"}' \
  -b cookies2.txt

# Повторить для шагов 2-5...

# 4. Проверить финальный профиль
curl http://localhost:8000/api/profile \
  -b cookies2.txt

# Ожидаемый ответ: профиль с onboarding_status = "completed",
# параметры заполнены с confidence > 0
```

### Scenario 3: Add Wine Memory (US3)

**Цель**: Добавить описание запомнившегося вина

```bash
# Добавить вино
curl -X POST http://localhost:8000/api/profile/wine-memories \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Красное вино из Тосканы, пили на отпуске в Италии. Было насыщенным с нотами вишни.",
    "sentiment": "liked",
    "context": "Романтический ужин в ресторане"
  }' \
  -b cookies.txt

# Ожидаемый ответ:
# {
#   "id": "...",
#   "raw_description": "Красное вино из Тосканы...",
#   "extracted_type": "red",
#   "extracted_region": "Тоскана",
#   "extracted_notes": ["вишня"],
#   "sentiment": "liked",
#   ...
# }

# Получить список вин
curl http://localhost:8000/api/profile/wine-memories \
  -b cookies.txt
```

### Scenario 4: Set Budget (US4)

**Цель**: Установить и изменить бюджет

```bash
# Установить бюджет
curl -X PUT http://localhost:8000/api/profile/budget \
  -H "Content-Type: application/json" \
  -d '{"budget_range": "budget_3"}' \
  -b cookies.txt

# Ожидаемый ответ: профиль с budget_range = "budget_3"

# Изменить бюджет
curl -X PUT http://localhost:8000/api/profile/budget \
  -H "Content-Type: application/json" \
  -d '{"budget_range": "budget_4"}' \
  -b cookies.txt

# Ожидаемый ответ: профиль с budget_range = "budget_4"
```

### Scenario 5: Profile Auto-Update (US5)

**Цель**: Проверить обновление профиля из чата

```bash
# Отправить сообщение в чат с предпочтением
curl -X POST http://localhost:8000/api/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Мне очень нравятся лёгкие белые вина с цитрусовыми нотами"}' \
  -b cookies.txt

# Получить профиль
curl http://localhost:8000/api/profile \
  -b cookies.txt

# Ожидаемый результат:
# - body должен быть близок к 1-2 (лёгкое)
# - preferred_aromas должен содержать "citrus"
# - confidence для этих параметров > 0
```

## Running Tests

```bash
# Запустить все тесты
docker compose exec backend pytest tests/ -v

# Только contract tests для profile
docker compose exec backend pytest tests/contract/test_profile.py -v

# Только integration tests
docker compose exec backend pytest tests/integration/test_onboarding_flow.py -v

# С покрытием
docker compose exec backend pytest tests/ --cov=app/services/profile --cov-report=term-missing
```

## Common Issues

### Миграция не применяется

```bash
# Проверить статус миграций
docker compose exec backend alembic current
docker compose exec backend alembic history

# Применить все миграции
docker compose exec backend alembic upgrade head
```

### Профиль не создаётся автоматически

Профиль создаётся при первом обращении к `/api/profile` или при старте онбординга.
Убедитесь, что пользователь авторизован (cookie присутствует).

### Extraction не работает

Mock extractor работает по ключевым словам. Проверьте, что сообщение содержит
узнаваемые слова: "сухое", "сладкое", "лёгкое", "насыщенное", "красное", "белое".

## Cleanup

```bash
# Удалить тестовые данные
docker compose exec db psql -U ai_sommelier -c "DELETE FROM wine_memories; DELETE FROM taste_profiles;"

# Остановить окружение
docker compose down
```
