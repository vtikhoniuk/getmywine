# Quickstart: Langfuse Monitoring

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-10

## Prerequisites

- Docker и Docker Compose установлены
- `.env` файл с `OPENROUTER_API_KEY` и `TELEGRAM_BOT_TOKEN`

## Запуск

```bash
# Запустить все сервисы (включая Langfuse)
docker compose up -d

# Проверить статус
docker compose ps

# Ожидаемые контейнеры (9 штук):
# - getmywine-db           (PostgreSQL приложения)
# - getmywine-backend      (FastAPI)
# - getmywine-telegram-bot (Telegram polling)
# - langfuse-web           (Langfuse UI, порт 3000)
# - langfuse-worker        (фоновая обработка)
# - langfuse-postgres      (PostgreSQL Langfuse, порт 5433)
# - langfuse-clickhouse    (аналитика трейсов)
# - langfuse-redis         (кэш/очередь)
# - langfuse-minio         (blob storage)
```

## Первый доступ

1. Открыть **http://localhost:3000** в браузере
2. При auto-provisioning: войти с предзаданными credentials из `.env`:
   - Email: значение `LANGFUSE_INIT_USER_EMAIL` (default: `dev@getmywine.local`)
   - Password: значение `LANGFUSE_INIT_USER_PASSWORD` (default: `devpassword123`)
3. Проект `GetMyWine` уже создан, API-ключи настроены

## Проверка трейсинга

1. Отправить сообщение Telegram-боту (например, "красное сухое до 2000 рублей")
2. Открыть Langfuse UI → Traces
3. Найти свежий трейс — должен содержать:
   - Root span: `generate_agentic_response`
   - Child: LLM generation с токенами и стоимостью
   - Child: `execute_search_wines` с фильтрами и результатами

## Отключение трейсинга

```bash
# В .env добавить:
LANGFUSE_TRACING_ENABLED=false

# Перезапустить backend:
docker compose restart backend telegram-bot
```

## Запуск без Langfuse

Если Langfuse-контейнеры не запущены или недоступны:
- Backend и Telegram-бот работают нормально
- Langfuse SDK логирует предупреждение, но не блокирует ответы
- Трейсы не записываются

## Полезные команды

```bash
# Логи Langfuse
docker compose logs langfuse-web -f
docker compose logs langfuse-worker -f

# Остановить только Langfuse (бот продолжит работать)
docker compose stop langfuse-web langfuse-worker langfuse-postgres langfuse-clickhouse langfuse-redis langfuse-minio

# Сбросить данные Langfuse (удалить volumes)
docker compose down -v --remove-orphans
# Предупреждение: это удалит ВСЕ volumes, включая основную БД!
# Для удаления только Langfuse volumes:
docker volume rm getmywine_langfuse_postgres_data getmywine_langfuse_clickhouse_data getmywine_langfuse_clickhouse_logs getmywine_langfuse_minio_data
```

## Порты

| Сервис | Порт | Доступ |
|--------|------|--------|
| Langfuse UI | 3000 | http://localhost:3000 |
| Langfuse PostgreSQL | 5433 | localhost only |
| ClickHouse HTTP | 8123 | localhost only |
| Redis | 6379 | localhost only |
| MinIO API | 9090 | localhost |
| MinIO Console | 9091 | localhost only |
