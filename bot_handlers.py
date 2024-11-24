from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from api_services import (
    handle_start_command,
    handle_callback_query,
    handle_text_message,
)

def register_handlers(application: Application) -> None:
    """Регистрирует обработчики команд и сообщений."""
    application.add_handler(CommandHandler("start", handle_start_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
