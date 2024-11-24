from telegram.ext import Application
from config import base_config
from bot_handlers import register_handlers

def main() -> None:
    """Основная функция для запуска бота."""
    TOKEN = base_config.getBotToken()
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков из контроллеров
    register_handlers(application)

    application.run_polling()

if __name__ == '__main__':
    main()
