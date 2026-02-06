"""Error and system messages for Telegram bot."""

# Error messages (per contracts/bot-commands.md)
ERROR_LLM_UNAVAILABLE = (
    "К сожалению, сервис рекомендаций временно недоступен. "
    "Попробуйте через несколько минут \U0001F504"
)

ERROR_NO_WINES_FOUND = (
    "К сожалению, не нашёл подходящих вин по вашим критериям. "
    "Попробуйте изменить запрос или расширить критерии."
)

ERROR_UNKNOWN_INTENT = (
    "Не совсем понял ваш запрос \U0001F914 "
    "Попробуйте переформулировать или отправьте /help для списка команд."
)

ERROR_SESSION_EXPIRED = "Начинаю новый диалог! Что вас интересует сегодня?"

ERROR_DATABASE = (
    "Произошла техническая ошибка. Мы уже работаем над решением."
)

# Account linking errors
ERROR_EMAIL_NOT_FOUND = (
    "❌ Аккаунт с таким email не найден. "
    "Проверьте адрес или зарегистрируйтесь на сайте."
)

ERROR_INVALID_CODE = (
    "❌ Неверный код. Попробуйте ещё раз или запросите новый командой /link"
)

ERROR_EMAIL_ALREADY_LINKED = (
    "ℹ️ Этот email уже связан с другим Telegram-аккаунтом."
)

# Success messages
SUCCESS_ACCOUNTS_LINKED = (
    "✅ Аккаунты успешно связаны! Теперь ваш профиль синхронизирован."
)

SUCCESS_FEEDBACK_LIKE = "✅ Спасибо!"
SUCCESS_FEEDBACK_DISLIKE = "Учтём!"
