# Sequence Диаграммы: GetMyWine

> **Дата:** 2026-02-01
> **Версия:** 1.0

---

## 1. Регистрация пользователя

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL

    U->>F: Заполняет форму регистрации
    F->>B: POST /auth/register
    B->>B: Валидация email, пароль
    B->>B: Hash password (bcrypt)
    B->>DB: INSERT INTO users
    DB-->>B: OK
    B->>DB: INSERT INTO taste_profiles (пустой)
    DB-->>B: OK
    B-->>F: 201 Created + JWT
    F-->>U: Redirect → Онбординг
```

---

## 2. Вход в систему

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL

    U->>F: Email + пароль
    F->>B: POST /auth/login
    B->>DB: SELECT user WHERE email
    DB-->>B: User row
    B->>B: Verify password hash
    alt Пароль верный
        B->>B: Generate JWT
        B-->>F: 200 OK + JWT
        F-->>U: Redirect → Чат
    else Пароль неверный
        B-->>F: 401 Unauthorized
        F-->>U: Ошибка
    end
```

---

## 3. Онбординг (изучение вкуса)

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL

    U->>F: Открывает онбординг
    F->>B: GET /onboarding/questions
    B-->>F: Список вопросов

    loop Каждый вопрос
        F-->>U: Показать вопрос
        U->>F: Ответ
        F->>B: POST /onboarding/answer
        B->>DB: UPDATE taste_profiles
        DB-->>B: OK
    end

    B-->>F: Онбординг завершён
    F-->>U: Redirect → Чат

    Note over U,F: Или "Пропустить" → сразу в чат
```

---

## 4. Отправка сообщения и получение рекомендации

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL
    participant LLM as Claude API

    U->>F: Вводит сообщение
    F->>B: POST /chat/message

    B->>DB: SELECT taste_profile WHERE user_id
    DB-->>B: Профиль пользователя

    B->>DB: SELECT messages WHERE user_id LIMIT 10
    DB-->>B: История чата

    B->>DB: Vector search: похожие вина
    DB-->>B: Top-5 вин из каталога

    B->>LLM: Chat completion (профиль + история + вина + запрос)
    LLM-->>B: Ответ с рекомендацией

    B->>DB: INSERT INTO messages (user)
    B->>DB: INSERT INTO messages (assistant)
    DB-->>B: OK

    B-->>F: HTML partial (HTMX)
    F-->>U: Показать ответ
```

---

## 5. Обратная связь на рекомендацию

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL

    U->>F: Клик "Понравилось" / "Не понравилось"
    F->>B: POST /feedback

    B->>DB: INSERT INTO feedback
    DB-->>B: OK

    B->>DB: SELECT wine characteristics
    DB-->>B: Характеристики вина

    B->>DB: UPDATE taste_profiles (усилить/ослабить)
    DB-->>B: OK

    B-->>F: 200 OK
    F-->>U: "Спасибо за отзыв!"
```

---

## 6. Генерация персонализированных подсказок

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant DB as PostgreSQL
    participant LLM as Claude API

    F->>B: GET /suggestions

    B->>DB: SELECT taste_profile
    DB-->>B: Профиль

    B->>DB: SELECT recent feedback
    DB-->>B: Последние отзывы

    B->>LLM: Generate 3 suggestions
    LLM-->>B: Подсказки

    B-->>F: ["Лучший пино нуар", "Вино к пасте", ...]
    F-->>F: Отобразить подсказки
```

---

## Примечания

### HTMX интеграция
- Backend возвращает HTML partials вместо JSON
- `hx-post`, `hx-get` для AJAX-запросов
- `hx-swap="beforeend"` для добавления сообщений в чат

### Пример HTMX endpoint

```python
@app.post("/chat/message")
async def send_message(request: Request, content: str = Form(...)):
    # ... логика ...
    return templates.TemplateResponse(
        "partials/message.html",
        {"request": request, "message": response}
    )
```
