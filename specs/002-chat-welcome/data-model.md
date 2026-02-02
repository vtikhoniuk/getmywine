# Data Model: Chat Welcome & AI Greeting

**Feature**: 002-chat-welcome
**Date**: 2026-02-02

## Entity Relationship Diagram

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│     users       │       │  conversations   │       │    messages     │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)          │──┐    │ id (PK)         │
│ email           │  │    │ user_id (FK)     │  │    │ conversation_id │
│ password_hash   │  └───>│ created_at       │  └───>│ role            │
│ is_age_verified │       │ updated_at       │       │ content         │
│ created_at      │       └──────────────────┘       │ created_at      │
└─────────────────┘              1:1                 │ is_welcome      │
      (existing)                                     └─────────────────┘
                                                            1:N
```

## Entities

### Conversation

Диалог пользователя с AI-сомелье. Один пользователь имеет один диалог (для MVP).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Уникальный идентификатор |
| user_id | UUID | FK → users.id, UNIQUE | Владелец диалога |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Время создания |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Время последнего сообщения |

**Indexes**:
- `ix_conversations_user_id` (user_id) — UNIQUE

**Relationships**:
- `user`: Many-to-One → User
- `messages`: One-to-Many → Message

### Message

Сообщение в диалоге. Может быть от пользователя, AI или системы.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Уникальный идентификатор |
| conversation_id | UUID | FK → conversations.id | Диалог |
| role | ENUM | NOT NULL | Отправитель: user, assistant, system |
| content | TEXT | NOT NULL, MAX 2000 | Текст сообщения |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Время отправки |
| is_welcome | BOOLEAN | DEFAULT FALSE | Приветственное сообщение |

**Indexes**:
- `ix_messages_conversation_id` (conversation_id)
- `ix_messages_created_at` (created_at) — для сортировки

**Relationships**:
- `conversation`: Many-to-One → Conversation

### MessageRole (Enum)

| Value | Description |
|-------|-------------|
| user | Сообщение от пользователя |
| assistant | Ответ AI-сомелье |
| system | Системное сообщение (приветствие) |

## Validation Rules

### Message Content
- Минимальная длина: 1 символ
- Максимальная длина: 2000 символов
- Не может быть пустым или только пробелами

### Conversation
- Один пользователь = один диалог (UNIQUE constraint на user_id)
- Диалог создаётся автоматически при первом входе в чат

## State Transitions

### Conversation Lifecycle

```
[User enters chat]
       │
       ▼
┌──────────────────┐
│ Check existing   │
│ conversation     │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ Exists? │
    └────┬────┘
    No   │   Yes
    │    │    │
    ▼    │    ▼
┌────────┴────────┐
│ Create new      │──────────────────┐
│ conversation    │                  │
└────────┬────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Add welcome     │                  │
│ message         │                  │
└────────┬────────┘                  │
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Load message │
              │ history      │
              └──────────────┘
```

### Message Flow

```
[User sends message]
       │
       ▼
┌──────────────────┐
│ Validate content │
│ (1-2000 chars)   │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ Valid?  │
    └────┬────┘
    No   │   Yes
    │    │    │
    ▼    │    ▼
 Error   │  ┌─────────────────┐
         │  │ Save user       │
         │  │ message         │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Call AI service │
         │  │ (mock)          │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Save AI         │
         │  │ response        │
         │  └────────┬────────┘
         │           │
         │           ▼
         │  ┌─────────────────┐
         │  │ Update          │
         │  │ conversation    │
         │  │ updated_at      │
         │  └─────────────────┘
```

## Migration Plan

### Migration 004: Create Chat Tables

```sql
-- Create enum type
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- Create conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_conversations_user_id ON conversations(user_id);

-- Create messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL CHECK (char_length(content) <= 2000),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_welcome BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX ix_messages_created_at ON messages(created_at);
```

## Welcome Message Content

```
Привет! Я AI-сомелье, и я помогу вам разобраться в мире вина. 🍷

Я могу:
• Подобрать вино под ваши предпочтения
• Рекомендовать вино к блюду или случаю
• Рассказать о сортах винограда и регионах
• Помочь понять винную терминологию

Хотите начать с определения ваших вкусовых предпочтений? Просто напишите мне!
```
