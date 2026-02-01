# Data Model: NutriBot

> **Версия:** 1.0
> **Основано на:** Brief v1.0, USM v1.0, C4 v1.0
> **Тип БД:** PostgreSQL 15

---

## 1. Обзор

**Всего сущностей:** 12

### Группы

| Группа | Сущности | Описание |
|--------|----------|----------|
| **Core** | nutritionists, clients | Основные пользователи |
| **Profile** | client_profiles, health_data | Данные анкет |
| **Lab** | lab_tests, lab_results, lab_values | Анализы и результаты |
| **Reports** | reports, report_sections | Отчёты |
| **Reference** | goals, analysis_types | Справочники |
| **System** | conversations, messages | Логи диалогов |

---

## 2. ER-диаграмма (полная)

```mermaid
erDiagram
    nutritionists {
        uuid id PK
        string email UK
        string password_hash
        string name
        string phone
        string specialization
        string avatar_url
        jsonb settings
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    clients {
        uuid id PK
        uuid nutritionist_id FK
        bigint telegram_id UK
        string telegram_username
        string name
        string phone
        string referral_code UK
        enum status "new, active, completed, archived"
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    client_profiles {
        uuid id PK
        uuid client_id FK "UK"
        int age
        enum gender "male, female, other"
        int height_cm
        decimal weight_kg
        jsonb goals
        jsonb dietary_preferences
        jsonb allergies
        jsonb restrictions
        jsonb lifestyle
        decimal completeness_score
        timestamp created_at
        timestamp updated_at
    }

    health_data {
        uuid id PK
        uuid client_id FK
        jsonb chronic_conditions
        jsonb symptoms
        jsonb medications
        jsonb supplements
        jsonb red_flags
        text notes
        timestamp created_at
        timestamp updated_at
    }

    goals {
        uuid id PK
        string code UK
        string name
        string description
        jsonb related_analyses
        int sort_order
        bool is_active
    }

    lab_tests {
        uuid id PK
        uuid client_id FK
        enum source "ocr, manual"
        string original_file_url
        enum status "pending, processing, completed, failed"
        timestamp test_date
        string laboratory
        jsonb raw_ocr_data
        timestamp created_at
        timestamp updated_at
    }

    analysis_types {
        uuid id PK
        string code UK
        string name
        string category
        string unit
        decimal ref_min
        decimal ref_max
        string description
        bool is_active
    }

    lab_values {
        uuid id PK
        uuid lab_test_id FK
        uuid analysis_type_id FK
        decimal value
        string unit
        enum status "normal, low, high, critical"
        decimal confidence
        bool is_verified
        timestamp created_at
    }

    reports {
        uuid id PK
        uuid client_id FK
        uuid nutritionist_id FK
        enum status "draft, ready, sent"
        string title
        text summary
        jsonb recommendations
        jsonb llm_metadata
        string pdf_url
        timestamp sent_at
        timestamp created_at
        timestamp updated_at
    }

    report_sections {
        uuid id PK
        uuid report_id FK
        string section_type
        text content
        jsonb data
        int sort_order
        timestamp created_at
        timestamp updated_at
    }

    conversations {
        uuid id PK
        uuid client_id FK
        enum state "onboarding, questionnaire, lab_upload, completed"
        jsonb context
        timestamp last_message_at
        timestamp created_at
        timestamp updated_at
    }

    messages {
        uuid id PK
        uuid conversation_id FK
        enum direction "inbound, outbound"
        string content_type
        text content
        jsonb metadata
        timestamp created_at
    }

    nutritionists ||--o{ clients : "has"
    clients ||--|| client_profiles : "has"
    clients ||--o{ health_data : "has"
    clients ||--o{ lab_tests : "uploads"
    clients ||--o{ reports : "receives"
    clients ||--|| conversations : "has"

    lab_tests ||--o{ lab_values : "contains"
    lab_values }o--|| analysis_types : "references"

    reports ||--o{ report_sections : "contains"
    reports }o--|| nutritionists : "created_by"

    conversations ||--o{ messages : "contains"

    client_profiles }o--o{ goals : "selects"
```

---

## 3. Описание сущностей

### nutritionists

**Назначение:** Нутрициологи — основные пользователи системы (B2B)

```mermaid
erDiagram
    nutritionists {
        uuid id PK
        string email UK
        string password_hash
        string name
        string phone
        string specialization
        string avatar_url
        jsonb settings
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }
```

**Бизнес-правила:**
- Email уникален (case-insensitive)
- Soft delete через deleted_at
- Settings содержит: notification_preferences, branding, questionnaire_config

---

### clients

**Назначение:** Клиенты нутрициологов (пользователи Telegram-бота)

```mermaid
erDiagram
    clients {
        uuid id PK
        uuid nutritionist_id FK
        bigint telegram_id UK
        string telegram_username
        string name
        string phone
        string referral_code UK
        enum status
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }
```

**Бизнес-правила:**
- Один клиент — один нутрициолог (для MVP)
- Referral code генерируется для приглашения
- Status: new → active → completed → archived

---

### client_profiles

**Назначение:** Профиль клиента — демография и предпочтения

```mermaid
erDiagram
    client_profiles {
        uuid id PK
        uuid client_id FK "UK"
        int age
        enum gender
        int height_cm
        decimal weight_kg
        jsonb goals
        jsonb dietary_preferences
        jsonb allergies
        jsonb restrictions
        jsonb lifestyle
        decimal completeness_score
        timestamp created_at
        timestamp updated_at
    }
```

**JSONB структуры:**

```json
// goals
["weight_loss", "energy", "health"]

// dietary_preferences
{
  "meals_per_day": 3,
  "typical_breakfast": "Овсянка с фруктами",
  "typical_lunch": "Суп и салат",
  "typical_dinner": "Куриная грудка с овощами",
  "snacks": ["орехи", "фрукты"],
  "water_intake_liters": 1.5
}

// allergies
["lactose", "nuts"]

// restrictions
{
  "vegetarian": false,
  "vegan": false,
  "gluten_free": true,
  "religious": null,
  "disliked_foods": ["печень", "морепродукты"]
}

// lifestyle
{
  "activity_level": "moderate",
  "sleep_quality": "poor",
  "stress_level": "high",
  "work_schedule": "office_9_to_6"
}
```

---

### health_data

**Назначение:** Медицинские данные клиента

**Бизнес-правила:**
- Red flags требуют немедленного внимания нутрициолога
- Может быть несколько записей (история)

**JSONB структуры:**

```json
// chronic_conditions
["diabetes_type_2", "hypertension"]

// symptoms
["fatigue", "digestive_issues", "skin_problems"]

// medications
[
  {"name": "Метформин", "dosage": "500mg", "frequency": "twice_daily"}
]

// supplements
[
  {"name": "Витамин D", "dosage": "2000 IU", "frequency": "daily"}
]

// red_flags
["diabetes", "pregnancy", "kidney_disease"]
```

---

### lab_tests

**Назначение:** Загруженные результаты анализов

**Бизнес-правила:**
- Source: ocr (автоматическое распознавание) или manual (ручной ввод)
- Status workflow: pending → processing → completed/failed
- raw_ocr_data хранит сырой результат OCR для дебага

---

### analysis_types (справочник)

**Назначение:** Типы лабораторных показателей с референсными значениями

**Примеры записей:**

| code | name | category | unit | ref_min | ref_max |
|------|------|----------|------|---------|---------|
| HGB | Гемоглобин | ОАК | g/L | 120 | 160 |
| GLU | Глюкоза | Биохимия | mmol/L | 3.9 | 6.1 |
| TSH | ТТГ | Гормоны | mIU/L | 0.4 | 4.0 |
| FERR | Ферритин | Железо | ng/mL | 12 | 150 |
| VIT_D | Витамин D | Витамины | ng/mL | 30 | 100 |

---

### lab_values

**Назначение:** Конкретные значения показателей из анализов

**Бизнес-правила:**
- Связывает lab_test с analysis_type
- Status определяется автоматически по ref_min/ref_max
- Confidence (0-1) показывает уверенность OCR
- is_verified — подтверждено пользователем

---

### reports

**Назначение:** Отчёты для клиентов

**Бизнес-правила:**
- Генерируются автоматически (draft), редактируются нутрициологом (ready), отправляются клиенту (sent)
- llm_metadata содержит промпты и параметры генерации
- pdf_url — ссылка на сгенерированный PDF

---

### conversations / messages

**Назначение:** Логи диалогов в Telegram-боте

**Бизнес-правила:**
- Один активный conversation на клиента
- State машина: onboarding → questionnaire → lab_upload → completed
- Context содержит текущий прогресс заполнения

---

## 4. Связи

| Связь | Тип | Описание | Каскад |
|-------|-----|----------|--------|
| nutritionists → clients | 1:N | Нутрициолог имеет много клиентов | SET NULL on delete |
| clients → client_profiles | 1:1 | Один профиль на клиента | CASCADE |
| clients → health_data | 1:N | Может быть история | CASCADE |
| clients → lab_tests | 1:N | Много анализов | CASCADE |
| clients → reports | 1:N | Много отчётов | CASCADE |
| clients → conversations | 1:1 | Один активный диалог | CASCADE |
| lab_tests → lab_values | 1:N | Анализ содержит показатели | CASCADE |
| lab_values → analysis_types | N:1 | Справочник типов | RESTRICT |
| reports → report_sections | 1:N | Секции отчёта | CASCADE |
| conversations → messages | 1:N | История сообщений | CASCADE |

---

## 5. Индексы

```sql
-- Поиск клиентов нутрициолога
CREATE INDEX idx_clients_nutritionist ON clients(nutritionist_id) WHERE deleted_at IS NULL;

-- Поиск по Telegram ID
CREATE UNIQUE INDEX idx_clients_telegram ON clients(telegram_id);

-- Анализы клиента
CREATE INDEX idx_lab_tests_client ON lab_tests(client_id, created_at DESC);

-- Показатели анализа
CREATE INDEX idx_lab_values_test ON lab_values(lab_test_id);

-- Отчёты клиента
CREATE INDEX idx_reports_client ON reports(client_id, created_at DESC);

-- Сообщения диалога
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

---

## 6. Миграции (порядок)

1. **Reference tables:** goals, analysis_types
2. **Core tables:** nutritionists
3. **Client tables:** clients, client_profiles, health_data
4. **Lab tables:** lab_tests, lab_values
5. **Report tables:** reports, report_sections
6. **Dialog tables:** conversations, messages
