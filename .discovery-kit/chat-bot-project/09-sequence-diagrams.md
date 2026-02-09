# Sequence Diagrams: NutriBot

> **Основано на:** USM v1.0, C4 v1.0, API v1.0
> **Версия:** 1.0

---

## Обзор

| # | Сценарий | Сложность | Участники |
|---|----------|-----------|-----------|
| 1 | Онбординг клиента | Средняя | Client, Telegram, Bot, API, DB |
| 2 | Загрузка и обработка анализов | Высокая | Client, Bot, API, Queue, Worker, OCR, LLM, DB |
| 3 | Генерация отчёта | Высокая | Nutritionist, Web, API, Worker, LLM, DB |
| 4 | Отправка отчёта клиенту | Средняя | Nutritionist, Web, API, Bot, Telegram, Client |

---

## 1. Онбординг клиента

### Контекст

**User Story:** US-001, US-002, SS-001
**Участники:** Client, Telegram, Bot, API, Database

### Диаграмма

```mermaid
sequenceDiagram
    participant C as Client
    participant T as Telegram
    participant B as Bot
    participant A as API
    participant D as Database

    C->>T: Переходит по реферальной ссылке
    T->>B: /start {referral_code}

    activate B
    B->>A: POST /bot/clients {referral_code, telegram_id}
    activate A
    A->>D: Проверить referral_code
    D-->>A: Nutritionist found
    A->>D: INSERT client
    D-->>A: Client created
    A->>D: INSERT conversation {state: "onboarding"}
    D-->>A: Conversation created
    A-->>B: {client_id, nutritionist_name}
    deactivate A

    B-->>T: Приветствие + Disclaimer
    deactivate B
    T-->>C: "Привет! Я бот нутрициолога Марины..."

    C->>T: Нажимает "Согласен"
    T->>B: callback: consent_accepted

    activate B
    B->>A: PATCH /bot/clients/{id}/state {consent: true}
    A->>D: UPDATE conversation
    A-->>B: OK
    B-->>T: "Как вас зовут?"
    deactivate B
    T-->>C: Запрос имени

    C->>T: "Анна"
    T->>B: message: "Анна"

    activate B
    B->>A: PATCH /bot/clients/{id}/profile {name: "Анна"}
    A->>D: UPDATE client_profiles
    A-->>B: OK
    B-->>T: "Сколько вам лет?"
    deactivate B
    T-->>C: Запрос возраста

    Note over C,D: Цикл продолжается для остальных вопросов...
```

### Примечания

- Referral code извлекается из deep link (`t.me/nutribot?start=REF123`)
- Согласие на обработку данных сохраняется как юридический факт
- State machine: onboarding → questionnaire → lab_upload → completed

---

## 2. Загрузка и обработка анализов

### Контекст

**User Story:** US-010, US-011, SS-004
**Участники:** Client, Bot, API, Queue, Worker, OCR Service, LLM, Database

### Диаграмма

```mermaid
sequenceDiagram
    participant C as Client
    participant B as Bot
    participant A as API
    participant S as Storage
    participant Q as Queue
    participant W as Worker
    participant OCR as OCR Service
    participant LLM as LLM API
    participant D as Database

    C->>B: Отправляет фото анализа
    activate B
    B->>A: POST /bot/clients/{id}/lab-tests (file)
    activate A

    A->>S: Upload file
    S-->>A: file_url

    A->>D: INSERT lab_tests {status: "pending"}
    D-->>A: lab_test_id

    A-)Q: Enqueue: process_lab_results(lab_test_id)
    A-->>B: {status: "processing", message: "Обрабатываю..."}
    deactivate A

    B-->>C: "Анализ загружен. Обработка займёт ~30 сек..."
    deactivate B

    activate W
    Q->>W: Dequeue: process_lab_results

    W->>D: UPDATE lab_tests {status: "processing"}

    W->>S: Download file
    S-->>W: file_content

    W->>OCR: POST /recognize {image}
    activate OCR
    OCR-->>W: {text, confidence}
    deactivate OCR

    W->>LLM: POST /analyze {text, prompt: "extract lab values"}
    activate LLM
    LLM-->>W: {values: [{name, value, unit}...]}
    deactivate LLM

    loop For each value
        W->>D: SELECT analysis_types WHERE name LIKE...
        D-->>W: analysis_type
        W->>D: INSERT lab_values {value, status, confidence}
    end

    W->>D: UPDATE lab_tests {status: "completed"}
    W-)B: Notify: lab_results_ready(client_telegram_id)
    deactivate W

    activate B
    B->>D: SELECT lab_values
    D-->>B: values[]
    B-->>C: "Распознаны результаты:\n- Гемоглобин: 135 g/L ✓\n- Ферритин: 8 ng/mL ⚠️ (ниже нормы)"
    B-->>C: "Всё верно? [Да] [Исправить]"
    deactivate B

    alt Клиент подтверждает
        C->>B: [Да]
        B->>A: POST /lab-tests/{id}/verify
        A->>D: UPDATE lab_values SET is_verified = true
    else Клиент исправляет
        C->>B: [Исправить]
        B-->>C: "Какой показатель исправить?"
        C->>B: "Ферритин 10"
        B->>A: PATCH /lab-tests/{id}/values/{id} {value: 10}
    end
```

### Примечания

- OCR + LLM работают последовательно: сначала распознавание текста, затем извлечение структурированных данных
- Confidence score показывает уверенность OCR, низкий score → запрос подтверждения
- При ошибке OCR предлагается ручной ввод
- Показатели со статусом "low" или "high" помечаются как red flags

---

## 3. Генерация отчёта

### Контекст

**User Story:** SS-005, SS-006, US-015
**Участники:** Nutritionist, Web App, API, Queue, Worker, LLM, Database

### Диаграмма

```mermaid
sequenceDiagram
    participant N as Nutritionist
    participant W as Web App
    participant A as API
    participant Q as Queue
    participant WK as Worker
    participant LLM as LLM API
    participant D as Database
    participant S as Storage

    N->>W: Открывает карточку клиента
    W->>A: GET /clients/{id}
    A->>D: SELECT client, profile, health, lab_tests
    D-->>A: client_data
    A-->>W: {client, profile, health, lab_tests}
    W-->>N: Отображает карточку

    N->>W: Нажимает "Создать отчёт"
    W->>A: POST /clients/{id}/reports
    activate A

    A->>D: INSERT reports {status: "draft"}
    D-->>A: report_id

    A-)Q: Enqueue: generate_report(report_id)
    A-->>W: {report_id, status: "generating"}
    deactivate A

    W-->>N: "Отчёт генерируется..."

    activate WK
    Q->>WK: Dequeue: generate_report

    WK->>D: SELECT client, profile, health, lab_values
    D-->>WK: all_client_data

    Note over WK,LLM: Формируем промпт с контекстом

    WK->>LLM: POST /messages {prompt: generate_report}
    activate LLM
    LLM-->>WK: {summary, sections, recommendations}
    deactivate LLM

    WK->>D: UPDATE reports {summary, status: "ready"}
    WK->>D: INSERT report_sections
    D-->>WK: OK

    WK-)W: WebSocket: report_ready(report_id)
    deactivate WK

    W->>A: GET /reports/{id}
    A->>D: SELECT report, sections
    D-->>A: report_data
    A-->>W: {report}

    W-->>N: Отображает готовый отчёт
```

### Примечания

- Генерация асинхронная, нутрициолог получает уведомление через WebSocket
- Промпт для LLM включает: профиль, анамнез, все показатели анализов с интерпретацией
- Отчёт структурирован по секциям: резюме, анализ показателей, рекомендации, вопросы
- Нутрициолог может редактировать любую секцию перед отправкой

---

## 4. Отправка отчёта клиенту

### Контекст

**User Story:** US-016, US-017
**Участники:** Nutritionist, Web App, API, Worker, Storage, Bot, Telegram, Client

### Диаграмма

```mermaid
sequenceDiagram
    participant N as Nutritionist
    participant W as Web App
    participant A as API
    participant Q as Queue
    participant WK as Worker
    participant S as Storage
    participant B as Bot
    participant T as Telegram
    participant C as Client

    N->>W: Редактирует отчёт
    W->>A: PATCH /reports/{id} {sections, recommendations}
    A->>D: UPDATE reports, report_sections
    A-->>W: OK

    N->>W: Нажимает "Сгенерировать PDF"
    W->>A: POST /reports/{id}/generate-pdf
    activate A
    A-)Q: Enqueue: generate_pdf(report_id)
    A-->>W: {status: "generating_pdf"}
    deactivate A

    activate WK
    Q->>WK: Dequeue: generate_pdf
    WK->>D: SELECT report, sections
    D-->>WK: report_data
    Note over WK: Генерация PDF с брендингом
    WK->>S: Upload PDF
    S-->>WK: pdf_url
    WK->>D: UPDATE reports {pdf_url}
    WK-)W: WebSocket: pdf_ready(report_id, pdf_url)
    deactivate WK

    W-->>N: Показывает превью PDF

    N->>W: Нажимает "Отправить клиенту"
    W->>A: POST /reports/{id}/send
    activate A

    A->>D: SELECT client.telegram_id
    D-->>A: telegram_id

    A->>B: POST /send-document {telegram_id, pdf_url}
    activate B
    B->>S: Download PDF
    S-->>B: pdf_file
    B->>T: sendDocument(chat_id, pdf)
    T-->>B: OK
    B-->>A: {sent: true}
    deactivate B

    A->>D: UPDATE reports {status: "sent", sent_at: now()}
    A-->>W: {status: "sent"}
    deactivate A

    T-->>C: Получает PDF-отчёт

    activate B
    B->>T: sendMessage: "Готов обсудить рекомендации? Запишитесь на консультацию!"
    deactivate B
    T-->>C: CTA на запись
```

### Примечания

- PDF генерируется с брендингом нутрициолога (логотип, контакты)
- После отправки статус отчёта меняется на "sent"
- Бот предлагает клиенту записаться на консультацию (CTA)
- История отправок сохраняется для аналитики

---

## Приложения

### Участники (из C4)

| ID | Название | Тип | Описание |
|----|----------|-----|----------|
| C | Client | Person | Клиент нутрициолога |
| N | Nutritionist | Person | Нутрициолог |
| T | Telegram | External System | Мессенджер |
| B | Bot | Container | Telegram Bot (aiogram) |
| W | Web App | Container | SPA для нутрициолога |
| A | API | Container | REST API (FastAPI) |
| D | Database | Container | PostgreSQL |
| S | Storage | Container | Object Storage (S3) |
| Q | Queue | Container | Redis Queue |
| WK | Worker | Container | Celery Worker |
| OCR | OCR Service | External System | Yandex Vision |
| LLM | LLM API | External System | Claude/OpenAI |

### Соглашения

| Символ | Значение |
|--------|----------|
| `->>` | Синхронный запрос |
| `-->>` | Синхронный ответ |
| `-)` | Асинхронный запрос (enqueue) |
| `--)` | Асинхронное уведомление |
| `-x` | Ошибка |
| `activate/deactivate` | Время выполнения |
| `Note over` | Комментарий |
| `alt/else/end` | Условное ветвление |
| `loop` | Цикл |
