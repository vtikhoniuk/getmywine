.PHONY: help build up down restart logs test lint shell db-shell clean

# Default target
help:
	@echo "AI-Sommelier - Доступные команды:"
	@echo ""
	@echo "  make build      - Собрать Docker-образы"
	@echo "  make up         - Запустить приложение"
	@echo "  make down       - Остановить приложение"
	@echo "  make restart    - Перезапустить приложение"
	@echo "  make logs       - Показать логи backend"
	@echo "  make logs-all   - Показать логи всех сервисов"
	@echo ""
	@echo "  make test       - Запустить все тесты"
	@echo "  make test-v     - Запустить тесты (verbose)"
	@echo "  make test-cov   - Запустить тесты с покрытием"
	@echo "  make lint       - Проверить код линтером"
	@echo ""
	@echo "  make shell      - Открыть shell в backend контейнере"
	@echo "  make db-shell   - Открыть psql в базе данных"
	@echo "  make clean      - Удалить контейнеры и volumes"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart backend

logs:
	docker logs -f ai-sommelier-backend

logs-all:
	docker-compose logs -f

# Testing
test:
	docker exec ai-sommelier-backend python -m pytest tests/

test-v:
	docker exec ai-sommelier-backend python -m pytest tests/ -v

test-cov:
	docker exec ai-sommelier-backend python -m pytest tests/ --cov=app --cov-report=term-missing

# Linting
lint:
	docker exec ai-sommelier-backend ruff check app/ tests/

lint-fix:
	docker exec ai-sommelier-backend ruff check app/ tests/ --fix

# Shell access
shell:
	docker exec -it ai-sommelier-backend /bin/bash

db-shell:
	docker exec -it ai-sommelier-db psql -U postgres -d ai_sommelier

# Cleanup
clean:
	docker-compose down -v --remove-orphans

# Rebuild and restart
rebuild: build up
