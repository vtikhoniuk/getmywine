# API Inventory: NutriBot

> **Основано на:** USM v1.0, ER v1.0
> **Базовый URL:** `https://api.nutribot.ru/v1`
> **Версия:** 1.0

---

## Обзор

**Всего endpoints:** 32
**API Style:** REST
**Формат:** JSON
**Авторизация:** Bearer JWT

### Сводка по доменам

| Домен | Endpoints | Описание |
|-------|-----------|----------|
| Auth | 4 | Аутентификация нутрициологов |
| Nutritionists | 3 | Профиль нутрициолога |
| Clients | 7 | Управление клиентами |
| Lab Tests | 5 | Анализы клиентов |
| Reports | 5 | Отчёты |
| Bot Internal | 5 | Внутренние эндпоинты для бота |
| System | 3 | Служебные эндпоинты |

---

## 1. Auth

| Method | Path | Auth | User Story | Description |
|--------|------|------|------------|-------------|
| POST | `/auth/register` | Public | US-018 | Регистрация нутрициолога |
| POST | `/auth/login` | Public | US-018 | Вход в систему |
| POST | `/auth/refresh` | Refresh Token | — | Обновление токена |
| POST | `/auth/logout` | Auth | — | Выход из системы |

### `POST /auth/register`

**Назначение:** Регистрация нутрициолога
**User Story:** US-018

**Request Body:**
```json
{
  "email": "marina@example.com",
  "password": "SecurePass123",
  "name": "Марина Ковалёва",
  "phone": "+79161234567"
}
```

**Responses:**
- `201` — Успешная регистрация
- `400` — Невалидные данные
- `409` — Email уже занят

---

### `POST /auth/login`

**Назначение:** Вход в систему
**User Story:** US-018

**Request Body:**
```json
{
  "email": "marina@example.com",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "marina@example.com",
    "name": "Марина Ковалёва"
  }
}
```

**Responses:**
- `200` — Успешный вход
- `401` — Неверные учётные данные
- `429` — Превышен лимит попыток

---

## 2. Nutritionists

| Method | Path | Auth | User Story | Description |
|--------|------|------|------------|-------------|
| GET | `/nutritionists/me` | Auth | US-019 | Получить профиль |
| PATCH | `/nutritionists/me` | Auth | US-019 | Обновить профиль |
| GET | `/nutritionists/me/referral-link` | Auth | US-001 | Получить реферальную ссылку |

### `GET /nutritionists/me`

**Response:**
```json
{
  "id": "uuid",
  "email": "marina@example.com",
  "name": "Марина Ковалёва",
  "phone": "+79161234567",
  "specialization": "Нутрициология, спортивное питание",
  "avatar_url": "https://...",
  "settings": {
    "notifications": { "email": true, "telegram": true },
    "branding": { "logo_url": null }
  },
  "created_at": "2026-01-15T10:00:00Z"
}
```

---

## 3. Clients

| Method | Path | Auth | User Story | Description |
|--------|------|------|------------|-------------|
| GET | `/clients` | Auth | US-013 | Список клиентов |
| GET | `/clients/{id}` | Auth | US-014 | Карточка клиента |
| GET | `/clients/{id}/profile` | Auth | US-014 | Профиль клиента |
| GET | `/clients/{id}/health` | Auth | US-014 | Данные о здоровье |
| GET | `/clients/{id}/lab-tests` | Auth | US-014 | Анализы клиента |
| GET | `/clients/{id}/reports` | Auth | US-014 | Отчёты клиента |
| DELETE | `/clients/{id}` | Auth | — | Удалить клиента (soft) |

### `GET /clients`

**Query Parameters:**
- `status` — Фильтр по статусу (new, active, completed, archived)
- `search` — Поиск по имени
- `page`, `limit` — Пагинация

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Анна Петрова",
      "status": "active",
      "telegram_username": "@anna_p",
      "profile_completeness": 0.85,
      "last_activity_at": "2026-01-29T14:30:00Z",
      "has_new_data": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

---

### `GET /clients/{id}`

**Response:**
```json
{
  "id": "uuid",
  "name": "Анна Петрова",
  "telegram_id": 123456789,
  "telegram_username": "@anna_p",
  "phone": "+79167654321",
  "status": "active",
  "profile": { ... },
  "health": { ... },
  "lab_tests_count": 2,
  "reports_count": 1,
  "created_at": "2026-01-20T10:00:00Z"
}
```

---

## 4. Lab Tests

| Method | Path | Auth | User Story | Description |
|--------|------|------|------------|-------------|
| GET | `/lab-tests/{id}` | Auth | US-014 | Детали анализа |
| GET | `/lab-tests/{id}/values` | Auth | US-014 | Показатели анализа |
| PATCH | `/lab-tests/{id}/values/{value_id}` | Auth | US-011 | Исправить показатель |
| POST | `/lab-tests/{id}/verify` | Auth | US-011 | Подтвердить все показатели |
| DELETE | `/lab-tests/{id}` | Auth | — | Удалить анализ |

### `GET /lab-tests/{id}/values`

**Response:**
```json
{
  "lab_test_id": "uuid",
  "test_date": "2026-01-25",
  "laboratory": "Инвитро",
  "values": [
    {
      "id": "uuid",
      "analysis_type": {
        "code": "HGB",
        "name": "Гемоглобин",
        "category": "ОАК"
      },
      "value": 135,
      "unit": "g/L",
      "status": "normal",
      "reference": { "min": 120, "max": 160 },
      "confidence": 0.95,
      "is_verified": true
    },
    {
      "id": "uuid",
      "analysis_type": {
        "code": "FERR",
        "name": "Ферритин",
        "category": "Железо"
      },
      "value": 8,
      "unit": "ng/mL",
      "status": "low",
      "reference": { "min": 12, "max": 150 },
      "confidence": 0.88,
      "is_verified": false
    }
  ]
}
```

---

## 5. Reports

| Method | Path | Auth | User Story | Description |
|--------|------|------|------------|-------------|
| GET | `/reports/{id}` | Auth | US-015 | Получить отчёт |
| PATCH | `/reports/{id}` | Auth | US-015 | Редактировать отчёт |
| POST | `/reports/{id}/generate-pdf` | Auth | US-016 | Сгенерировать PDF |
| POST | `/reports/{id}/send` | Auth | US-017 | Отправить клиенту |
| POST | `/clients/{id}/reports` | Auth | SS-005 | Создать отчёт |

### `POST /clients/{id}/reports`

**Назначение:** Запустить генерацию отчёта по клиенту (LLM)

**Response:**
```json
{
  "id": "uuid",
  "status": "draft",
  "created_at": "2026-01-30T12:00:00Z"
}
```

*Генерация асинхронная, статус меняется на "ready" по завершении*

---

### `PATCH /reports/{id}`

**Request Body:**
```json
{
  "summary": "Обновлённое резюме...",
  "sections": [
    {
      "id": "uuid",
      "content": "Редактированный текст секции"
    }
  ],
  "recommendations": [
    "Увеличить потребление железа",
    "Добавить ферментированные продукты"
  ]
}
```

---

### `POST /reports/{id}/send`

**Назначение:** Отправить готовый отчёт клиенту в Telegram

**Response:**
```json
{
  "status": "sent",
  "sent_at": "2026-01-30T14:30:00Z"
}
```

---

## 6. Bot Internal

*Эндпоинты для внутреннего использования Telegram-ботом*

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/bot/clients` | Bot Secret | Создать клиента по referral |
| PATCH | `/bot/clients/{telegram_id}/profile` | Bot Secret | Обновить профиль |
| PATCH | `/bot/clients/{telegram_id}/health` | Bot Secret | Обновить health data |
| POST | `/bot/clients/{telegram_id}/lab-tests` | Bot Secret | Загрузить анализ |
| GET | `/bot/clients/{telegram_id}/state` | Bot Secret | Получить состояние диалога |

### `POST /bot/clients/{telegram_id}/lab-tests`

**Request:**
```
Content-Type: multipart/form-data

file: [binary]
source: "ocr" | "manual"
```

**Response:**
```json
{
  "lab_test_id": "uuid",
  "status": "processing",
  "message": "Анализ обрабатывается, это займёт около 30 секунд"
}
```

---

## 7. System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | Public | Health check |
| GET | `/reference/analysis-types` | Auth | Справочник типов анализов |
| GET | `/reference/goals` | Auth | Справочник целей |

---

## Приложения

### Коды ошибок

| Code | Description |
|------|-------------|
| 400 | Bad Request — невалидные данные |
| 401 | Unauthorized — требуется авторизация |
| 403 | Forbidden — нет доступа к ресурсу |
| 404 | Not Found — ресурс не найден |
| 409 | Conflict — конфликт (дубликат) |
| 422 | Unprocessable Entity — бизнес-ошибка |
| 429 | Too Many Requests — rate limit |
| 500 | Internal Server Error |

### Формат ошибки

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Поле email обязательно",
    "details": [
      {
        "field": "email",
        "message": "Это поле обязательно"
      }
    ]
  }
}
```

### Пагинация

**Query:**
```
?page=1&limit=20
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

### Авторизация

**Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Payload:**
```json
{
  "sub": "nutritionist-uuid",
  "email": "marina@example.com",
  "iat": 1706600000,
  "exp": 1706603600
}
```
