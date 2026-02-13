.PHONY: help build up down restart logs logs-bot test lint shell db-shell clean db-reset db-reseed

# Default target
help:
	@echo "GetMyWine - Доступные команды:"
	@echo ""
	@echo "  make build      - Собрать Docker-образы"
	@echo "  make up         - Запустить приложение"
	@echo "  make down       - Остановить приложение"
	@echo "  make restart    - Перезапустить приложение"
	@echo "  make logs       - Показать логи backend"
	@echo "  make logs-bot   - Показать логи Telegram-бота"
	@echo "  make logs-all   - Показать логи всех сервисов"
	@echo ""
	@echo "  make test       - Запустить все тесты"
	@echo "  make test-v     - Запустить тесты (verbose)"
	@echo "  make test-cov   - Запустить тесты с покрытием"
	@echo "  make lint       - Проверить код линтером"
	@echo ""
	@echo "  make shell      - Открыть shell в backend контейнере"
	@echo "  make db-shell   - Открыть psql в базе данных"
	@echo "  make db-reset   - Пересоздать БД с нуля (удаляет все данные!)"
	@echo "  make db-reseed  - Перезаполнить вина (downgrade + upgrade)"
	@echo "  make clean      - Удалить контейнеры и volumes"

# Docker commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart backend

logs-backend:
	docker logs -f getmywine-backend

logs-bot:
	docker logs -f getmywine-telegram-bot

logs-all:
	docker compose logs -f

# Testing (local)
test:
	cd backend && python3 -m pytest tests/unit/

test-v:
	cd backend && python3 -m pytest tests/unit/ -v

test-cov:
	cd backend && python3 -m pytest tests/unit/ --cov=app --cov-report=term-missing

# Linting
lint:
	docker exec getmywine-backend ruff check app/ tests/

lint-fix:
	docker exec getmywine-backend ruff check app/ tests/ --fix

# Shell access
shell:
	docker exec -it getmywine-backend /bin/bash

db-shell:
	docker exec -it getmywine-db psql -U getmywine -d getmywine

# Database reset - полное пересоздание БД
db-reset:
	@echo "⚠️  Удаляем все данные и пересоздаём БД..."
	docker compose down
	docker volume rm aiwine-hub_postgres_data 2>/dev/null || true
	docker compose up -d
	@echo "✅ БД пересоздана, миграции применены"

# Reseed wines - только перезаполнение вин
db-reseed:
	@echo "🍷 Перезаполняем вина..."
	docker compose exec backend alembic downgrade 005
	docker compose exec backend alembic upgrade head
	@echo "✅ Вина перезаполнены"

# Cleanup
clean:
	docker compose down -v --remove-orphans

# Rebuild and restart
rebuild: down build up

