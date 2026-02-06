# Quickstart: Chat Welcome & AI Greeting

**Feature**: 002-chat-welcome
**Branch**: `002-chat-welcome`

## Prerequisites

- Docker и Docker Compose установлены
- Проект из US-001 развёрнут и работает
- `make up` запускает приложение

## Быстрый старт

### 1. Применить миграции

```bash
# Создать миграцию (если нужно сгенерировать)
docker exec getmywine-backend alembic revision --autogenerate -m "create_chat_tables"

# Применить миграции
docker exec getmywine-backend alembic upgrade head
```

### 2. Проверить API

```bash
# Зарегистрироваться (если нет пользователя)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test1234", "is_age_verified": true}' \
  -c cookies.txt

# Получить/создать диалог
curl http://localhost:8000/api/v1/chat/conversation \
  -b cookies.txt

# Отправить сообщение
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Привет! Что ты умеешь?"}' \
  -b cookies.txt
```

### 3. Открыть чат в браузере

```
http://localhost:8000/chat
```

## Тестирование

### Запуск всех тестов

```bash
make test
```

### Запуск только тестов чата

```bash
docker exec getmywine-backend python -m pytest tests/ -k chat -v
```

### Тестовые сценарии

| Сценарий | Команда |
|----------|---------|
| Contract тесты | `pytest tests/contract/test_chat.py` |
| Integration тесты | `pytest tests/integration/test_chat_flow.py` |
| Unit тесты | `pytest tests/unit/test_chat_service.py` |

## Структура файлов

```
backend/app/
├── models/
│   ├── conversation.py    # Модель Conversation
│   └── message.py         # Модель Message + enum MessageRole
├── repositories/
│   ├── conversation.py    # CRUD для диалогов
│   └── message.py         # CRUD для сообщений
├── services/
│   ├── chat.py            # Бизнес-логика чата
│   └── ai_mock.py         # Mock AI сервис
├── routers/
│   └── chat.py            # API endpoints
├── schemas/
│   └── chat.py            # Pydantic модели
└── templates/
    └── chat.html          # Страница чата
```

## Основные эндпоинты

| Method | Path | Description |
|--------|------|-------------|
| GET | `/chat` | HTML страница чата |
| GET | `/api/v1/chat/conversation` | Получить/создать диалог |
| POST | `/api/v1/chat/messages` | Отправить сообщение |
| GET | `/api/v1/chat/messages/history` | История с пагинацией |

## Конфигурация

Новые переменные окружения (опционально):

```env
# .env
AI_RESPONSE_DELAY=0.5     # Задержка mock AI (секунды)
CHAT_MESSAGE_MAX_LENGTH=2000  # Макс. длина сообщения
```

## Troubleshooting

### "401 Unauthorized" при доступе к чату
- Убедитесь, что вы авторизованы (есть cookie `access_token`)
- Проверьте, что cookie не истёк (7 дней)

### Сообщения не сохраняются
- Проверьте логи: `make logs`
- Убедитесь, что миграции применены: `alembic current`

### AI не отвечает
- Mock AI всегда должен отвечать
- Проверьте таймауты в логах

## Следующие шаги

После реализации этой фичи:
1. `/speckit.tasks` — создать tasks.md с конкретными задачами
2. `/speckit.implement` — начать разработку по TDD
