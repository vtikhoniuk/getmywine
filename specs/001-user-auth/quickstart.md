# Быстрый старт: Регистрация и авторизация

## Предварительные требования

- Docker 24+
- Docker Compose 2.20+

## Структура Docker

```text
/
├── docker-compose.yml       # Оркестрация сервисов
├── backend/
│   ├── Dockerfile           # Python/FastAPI образ
│   ├── app/
│   └── requirements.txt
└── .env                     # Переменные окружения
```

## Настройка окружения

### 1. Создание .env файла

Создайте файл `.env` в корне проекта:

```env
# Database
POSTGRES_USER=ai_sommelier
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=ai_sommelier

# Backend
DATABASE_URL=postgresql+asyncpg://ai_sommelier:change-me-in-production@db:5432/ai_sommelier

# JWT
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# Email (для password reset)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=smtp-password
SMTP_FROM=AI-Sommelier <noreply@example.com>

# Rate limiting
RATE_LIMIT_LOGIN=5/15minutes
RATE_LIMIT_REGISTER=3/hour
RATE_LIMIT_PASSWORD_RESET=3/hour
```

### 2. Docker Compose конфигурация

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    container_name: ai-sommelier-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-sommelier-backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: ${JWT_ALGORITHM}
      JWT_EXPIRE_DAYS: ${JWT_EXPIRE_DAYS}
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      SMTP_FROM: ${SMTP_FROM}
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app:ro  # Для hot reload в dev
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
```

### 3. Backend Dockerfile

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Порт приложения
EXPOSE 8000

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Запуск

### Development (с hot reload)

```bash
docker compose up --build
```

### Production

```bash
docker compose up -d --build
```

### Просмотр логов

```bash
docker compose logs -f backend
```

### Остановка

```bash
docker compose down
```

### Полная очистка (включая данные)

```bash
docker compose down -v
```

## Проверка работоспособности

### Документация API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Тестовые запросы

#### Регистрация

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "is_age_verified": true
  }'
```

#### Вход

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

#### Проверка авторизации

```bash
curl http://localhost:8000/api/v1/auth/me \
  -b cookies.txt
```

## Запуск тестов

```bash
docker compose exec backend pytest tests/ -v
```

### С покрытием

```bash
docker compose exec backend pytest tests/ --cov=app --cov-report=html
```

## Деплой на VPS

### 1. Клонирование репозитория

```bash
ssh user@your-vps
git clone https://github.com/your-repo/ai-sommelier.git
cd ai-sommelier
```

### 2. Настройка .env для production

```bash
cp .env.example .env
nano .env  # Заполнить реальные значения
```

**Важно**: Измените `JWT_SECRET` и `POSTGRES_PASSWORD` на безопасные значения.

### 3. Запуск

```bash
docker compose up -d --build
```

### 4. Настройка Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. SSL с Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com
```

## Типичные проблемы

### Container не запускается

```bash
docker compose logs backend
```

Частые причины:
- БД ещё не готова (healthcheck должен помочь)
- Неверный DATABASE_URL

### Миграции не применились

```bash
docker compose exec backend alembic upgrade head
```

### Нужно пересоздать БД

```bash
docker compose down -v
docker compose up -d
```
