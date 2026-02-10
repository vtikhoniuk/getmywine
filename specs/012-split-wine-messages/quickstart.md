# Quickstart: 012-split-wine-messages

## Обзор

Фича формализует существующий формат 5 сообщений в Telegram-боте: вступление → 3 вина с фото → завершающий вопрос. Основная работа — рефакторинг дублирования и добавление тестов.

## Предусловия

- Python 3.12+
- PostgreSQL 16 с данными (wines_seed загружен)
- Telegram Bot Token (для ручного тестирования)
- Изображения вин в `backend/app/static/images/wines/`

## Быстрый старт

```bash
# 1. Установить зависимости
cd backend && pip install -r requirements.txt

# 2. Запустить тесты (после их создания)
cd backend && python -m pytest tests/unit/test_structured_response.py -v
cd backend && python -m pytest tests/unit/test_bot_utils.py -v
cd backend && python -m pytest tests/unit/test_bot_formatters.py -v

# 3. Запустить бота для ручного тестирования
cd backend && python -m app.bot.main
```

## Ключевые файлы

| Файл | Роль |
|------|------|
| `backend/app/bot/handlers/start.py` | Обработчик /start |
| `backend/app/bot/handlers/message.py` | Обработчик текстовых сообщений |
| `backend/app/bot/utils.py` | Утилиты (markdown, image path, language) |
| `backend/app/bot/formatters.py` | Форматирование карточек вин |
| `backend/app/services/sommelier_prompts.py` | Промпты LLM, парсинг ответа |

## Архитектура отправки сообщений

```
User Message → Handler → TelegramBotService → SommelierService (LLM)
                                                       ↓
                                              Structured Response
                                                       ↓
                                          parse_structured_response()
                                                       ↓
                                              is_structured?
                                              /            \
                                           Yes              No
                                            ↓                ↓
                                    5 messages          1 text + photos
                                    (intro,             (fallback)
                                     wine1+photo,
                                     wine2+photo,
                                     wine3+photo,
                                     closing)
```

## Чеклист проверки

- [ ] /start от нового пользователя → 5 сообщений (приветствие + 3 фото + вопрос)
- [ ] Текстовый запрос → 5 сообщений (контекст + 3 фото + вопрос)
- [ ] Каждое фото содержит подпись с названием и ценой
- [ ] При отсутствии изображения — текст вместо фото
- [ ] При ошибке парсинга — fallback на единое сообщение
