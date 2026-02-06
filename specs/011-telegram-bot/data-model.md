# Data Model: Telegram-бот для GetMyWine

**Feature**: 011-telegram-bot
**Date**: 2026-02-05

## Entity Overview

```
┌─────────────────┐         ┌─────────────────┐
│  TelegramUser   │ 1 ──? 1 │      User       │
│  (NEW)          │         │  (existing)     │
└────────┬────────┘         └─────────────────┘
         │
         │ 1
         │
         ▼ *
┌─────────────────┐         ┌─────────────────┐
│  Conversation   │ 1 ── * │    Message      │
│  (extended)     │         │  (existing)     │
└─────────────────┘         └─────────────────┘
```

## New Entity: TelegramUser

Связывает Telegram ID с профилем пользователя. Может существовать без привязки к User (standalone Telegram user).

### Table: `telegram_users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | Внутренний ID |
| `telegram_id` | BIGINT | UNIQUE, NOT NULL, INDEX | Telegram user ID |
| `user_id` | UUID | FK → users.id, NULLABLE | Связь с web-аккаунтом (optional) |
| `username` | VARCHAR(255) | NULLABLE | Telegram username (@example) |
| `first_name` | VARCHAR(255) | NULLABLE | Имя из Telegram |
| `last_name` | VARCHAR(255) | NULLABLE | Фамилия из Telegram |
| `language_code` | VARCHAR(10) | DEFAULT 'ru' | Предпочитаемый язык (из Telegram locale) |
| `is_age_verified` | BOOLEAN | DEFAULT FALSE, NOT NULL | Согласие с 18+ (выполнен /start) |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW(), NOT NULL | Дата создания |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW(), NOT NULL | Дата обновления |

### Indexes

```sql
CREATE UNIQUE INDEX ix_telegram_users_telegram_id ON telegram_users(telegram_id);
CREATE INDEX ix_telegram_users_user_id ON telegram_users(user_id);
```

### SQLAlchemy Model

```python
class TelegramUser(Base):
    """Telegram user profile linked to main user account."""

    __tablename__ = "telegram_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="ru",
    )
    is_age_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", lazy="joined")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="telegram_user",
        foreign_keys="[Conversation.telegram_user_id]",
    )
```

## Extended Entity: Conversation

Добавляется поддержка канала (web/telegram) и связь с TelegramUser.

### New Columns for `conversations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `channel` | VARCHAR(20) | DEFAULT 'web', NOT NULL | Канал: 'web' \| 'telegram' |
| `telegram_user_id` | UUID | FK → telegram_users.id, NULLABLE | Для Telegram-сессий |

### Migration Changes

```python
# Add channel column
op.add_column('conversations', sa.Column(
    'channel',
    sa.String(20),
    nullable=False,
    server_default='web',
))

# Add telegram_user_id column
op.add_column('conversations', sa.Column(
    'telegram_user_id',
    sa.UUID(as_uuid=True),
    sa.ForeignKey('telegram_users.id', ondelete='CASCADE'),
    nullable=True,
))

# Index for Telegram queries
op.create_index(
    'ix_conversations_telegram_user_id',
    'conversations',
    ['telegram_user_id'],
)
```

### Updated SQLAlchemy Model (additions)

```python
class Conversation(Base):
    # ... existing fields ...

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="web",
    )
    telegram_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationship
    telegram_user: Mapped[Optional["TelegramUser"]] = relationship(
        "TelegramUser",
        back_populates="conversations",
    )

    @property
    def session_timeout_minutes(self) -> int:
        """Session timeout based on channel."""
        if self.channel == "telegram":
            return 24 * 60  # 24 hours for Telegram
        return 30  # 30 minutes for web
```

## Existing Entities (No Changes)

### User

Остаётся без изменений. TelegramUser ссылается на User через `user_id`.

### Message

Остаётся без изменений. Сообщения привязаны к Conversation.

### Wine

Остаётся без изменений. Используется для рекомендаций через SommelierService.

## Entity Relationships

| Relationship | Type | Description |
|--------------|------|-------------|
| TelegramUser → User | 1:0..1 | Optional link to web account |
| TelegramUser → Conversation | 1:* | Telegram user's chat sessions |
| Conversation → User | *:1 | Web user sessions (existing) |
| Conversation → TelegramUser | *:0..1 | Telegram user sessions (new) |
| Conversation → Message | 1:* | Chat messages (existing) |

## State Transitions

### TelegramUser Lifecycle

```
                    ┌──────────────────┐
                    │   Not Exists     │
                    └────────┬─────────┘
                             │ /start (first time)
                             ▼
                    ┌──────────────────┐
                    │   Created        │
                    │ is_age_verified  │
                    │     = true       │
                    └────────┬─────────┘
                             │ /link <email>
                             ▼
                    ┌──────────────────┐
                    │   Linked         │
                    │ user_id != null  │
                    └──────────────────┘
```

### Conversation (Telegram) Lifecycle

```
                    ┌──────────────────┐
                    │     Active       │
                    │  closed_at=null  │
                    │  channel=telegram│
                    └────────┬─────────┘
                             │ 24h inactivity OR /start
                             ▼
                    ┌──────────────────┐
                    │     Closed       │
                    │  closed_at=now   │
                    └──────────────────┘
```

## Validation Rules

### TelegramUser

| Field | Rule | Error Message |
|-------|------|---------------|
| telegram_id | > 0 | "Invalid Telegram ID" |
| language_code | 2-10 chars | "Invalid language code" |
| username | @-prefixed or null | "Invalid username format" |

### Conversation (extended)

| Field | Rule | Error Message |
|-------|------|---------------|
| channel | 'web' \| 'telegram' | "Invalid channel" |
| telegram_user_id | Required if channel='telegram' | "Telegram user required" |
| user_id | Required if channel='web' | "User required for web channel" |

## Alembic Migration

**File**: `migrations/versions/xxx_add_telegram_support.py`

```python
"""Add Telegram bot support

Revision ID: xxx
Revises: [previous]
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'xxx'
down_revision = '[previous]'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create telegram_users table
    op.create_table(
        'telegram_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('language_code', sa.String(10), nullable=False, server_default='ru'),
        sa.Column('is_age_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_telegram_users_telegram_id', 'telegram_users', ['telegram_id'], unique=True)
    op.create_index('ix_telegram_users_user_id', 'telegram_users', ['user_id'])

    # Extend conversations table
    op.add_column('conversations', sa.Column('channel', sa.String(20), nullable=False, server_default='web'))
    op.add_column('conversations', sa.Column(
        'telegram_user_id',
        postgresql.UUID(as_uuid=True),
        nullable=True,
    ))
    op.create_foreign_key(
        'fk_conversations_telegram_user_id',
        'conversations',
        'telegram_users',
        ['telegram_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_conversations_telegram_user_id', 'conversations', ['telegram_user_id'])


def downgrade() -> None:
    op.drop_index('ix_conversations_telegram_user_id', table_name='conversations')
    op.drop_constraint('fk_conversations_telegram_user_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'telegram_user_id')
    op.drop_column('conversations', 'channel')

    op.drop_index('ix_telegram_users_user_id', table_name='telegram_users')
    op.drop_index('ix_telegram_users_telegram_id', table_name='telegram_users')
    op.drop_table('telegram_users')
```
