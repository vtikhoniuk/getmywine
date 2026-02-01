# API Inventory: AI-Sommelier

> **Дата:** 2026-02-01
> **Версия:** 1.0

---

## Обзор

| Категория | Endpoints |
|-----------|-----------|
| Auth | 4 |
| Chat | 3 |
| Profile | 3 |
| Catalog | 2 |
| Feedback | 2 |
| **Всего** | **14** |

---

## Auth

### POST /auth/register
Регистрация нового пользователя.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| email | string | да |
| password | string | да |
| name | string | нет |
| age_confirmed | boolean | да |

**Response:** 201 Created + Set-Cookie (JWT)

---

### POST /auth/login
Вход в систему.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| email | string | да |
| password | string | да |

**Response:** 200 OK + Set-Cookie (JWT)

---

### POST /auth/logout
Выход из системы.

**Response:** 200 OK + Clear-Cookie

---

### POST /auth/password-reset
Запрос сброса пароля.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| email | string | да |

**Response:** 200 OK (email отправлен)

---

## Chat

### GET /chat
Главная страница чата (HTML).

**Response:** HTML страница с историей и формой ввода

---

### POST /chat/message
Отправка сообщения.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| content | string | да |

**Response:** HTML partial (сообщение пользователя + ответ AI)

---

### GET /chat/suggestions
Персонализированные подсказки.

**Response:** HTML partial (1-3 кнопки-подсказки)

---

## Profile

### GET /profile
Страница профиля (HTML).

**Response:** HTML страница

---

### POST /profile/update
Обновление профиля.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| name | string | нет |
| budget_range | string | нет |

**Response:** HTML partial или redirect

---

### DELETE /profile
Удаление аккаунта.

**Response:** 200 OK + redirect на landing

---

## Onboarding

### GET /onboarding
Страница онбординга (HTML).

**Response:** HTML страница с вопросами

---

### POST /onboarding/answer
Ответ на вопрос онбординга.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| question_id | string | да |
| answer | string | да |

**Response:** HTML partial (следующий вопрос или redirect)

---

### POST /onboarding/skip
Пропуск онбординга.

**Response:** Redirect → /chat

---

## Catalog (Admin)

### GET /admin/wines
Список вин в каталоге.

**Response:** HTML страница

---

### POST /admin/wines
Добавление вина.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| name | string | да |
| type | string | да |
| ... | ... | ... |

**Response:** Redirect или HTML partial

---

## Feedback

### POST /feedback
Отправка feedback на рекомендацию.

| Параметр | Тип | Обязательный |
|----------|-----|--------------|
| wine_id | uuid | да |
| rating | string | да |
| comment | string | нет |

**Response:** HTML partial ("Спасибо!")

---

### GET /feedback/history
История feedback пользователя.

**Response:** HTML partial (список)

---

## Коды ответов

| Код | Описание |
|-----|----------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Server Error |

---

## Аутентификация

- **Метод:** JWT в HttpOnly cookie
- **Срок жизни:** 7 дней
- **Refresh:** При каждом запросе (sliding expiration)

```python
# Пример middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY)
            request.state.user_id = payload["sub"]
        except JWTError:
            pass
    return await call_next(request)
```

---

## HTMX Headers

| Header | Описание |
|--------|----------|
| HX-Request | Запрос от HTMX |
| HX-Trigger | Событие после ответа |
| HX-Redirect | Redirect на стороне клиента |

```python
# Пример ответа с HTMX redirect
return Response(
    status_code=200,
    headers={"HX-Redirect": "/chat"}
)
```
