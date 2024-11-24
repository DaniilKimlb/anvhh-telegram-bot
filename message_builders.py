from telegram import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from user_models import UserModel
from hh import HHApi

def build_main_menu(auth_token_exists: bool) -> InlineKeyboardMarkup:
    """Создает главное меню."""
    if auth_token_exists:
        keyboard = [
            [InlineKeyboardButton("🚀 Начать отклики на вакансии", callback_data='start_vacancy_responses')],
            [InlineKeyboardButton("⚙️ Настройка отклика", callback_data='settings')],
            [InlineKeyboardButton("ℹ️ О нас", callback_data='about_us')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🔑 Авторизоваться", callback_data='authorize')],
            [InlineKeyboardButton("ℹ️ О нас", callback_data='about_us')],
        ]
    return InlineKeyboardMarkup(keyboard)


def build_settings_menu() -> InlineKeyboardMarkup:
    """Создает меню настроек."""
    keyboard = [
        [InlineKeyboardButton("📝 Выбрать резюме для откликов", callback_data='select_resume')],
        [InlineKeyboardButton("🔍 Обновить ключевые слова для поиска вакансий", callback_data='set_keywords')],
        [InlineKeyboardButton("💌 Обновить сопроводительное письмо", callback_data='set_cover_letter')],
        [InlineKeyboardButton("🔧 Текущие настройки", callback_data='view_settings')],
        [InlineKeyboardButton("🔙 Назад в главное меню", callback_data='main_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_main_menu_back_button() -> InlineKeyboardMarkup:
    """Создает меню с кнопкой 'Назад' в главное меню."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в главное меню", callback_data='main_menu')]])

def build_settings_back_button() -> InlineKeyboardMarkup:
    """Создает меню с кнопкой 'Назад' в настройки."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='settings')]])


def build_owner_payment_status_menu(chat_id: int, subscription_level: str) -> InlineKeyboardMarkup:
    """Создает меню статуса оплаты для владельца."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Выставил счет", callback_data=f'issue_invoice_{chat_id}')],
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f'confirm_payment_{chat_id}_{subscription_level}')],
    ])

def display_about_message():
    """Возвращает текст и клавиатуру для раздела 'О нас'."""
    about_message = (
        "👋 Добро пожаловать в ANVHH!\n\n"
        "Мы – бот, который помогает вам легко и быстро откликаться на вакансии в HeadHunter. "
        "Воспользуйтесь нашими услугами для автоматизации процесса подачи откликов, экономьте ваше время и сосредоточьтесь на важных задачах!\n\n"
        "🎯 *Основные преимущества:*\n"
        "— 📄 Автоматический отклик на вакансии\n"
        "— 🔍 Возможность задать ключевые слова для поиска вакансий\n"
        "— 💌 Генерация персонализированных сопроводительных писем\n"
        "— 🗓 Контроль лимита откликов и времени следующей возможности подать отклик\n"
        "— 🔄 Автоматизация рутинных процессов и повышение шансов на трудоустройство\n\n"
        "Мы ценим вашу конфиденциальность и сохраняем ваши данные исключительно для работы бота. "
        "Мы не передаем ваши данные третьим лицам и не используем их в других целях.\n\n"
        "Этот бот является *открытым исходным кодом* (open-source), и вы можете принять участие в его развитии. "
        "Если у вас есть идеи или вы хотите внести свой вклад, посетите наш репозиторий на GitHub: "
        "[anvhh-telegram-bot](https://github.com/DaniilKimlb/anvhh-telegram-bot/issues).\n\n"
        "Если у вас возникли вопросы или предложения, свяжитесь с нами через контакт: @scrscrq."
    )
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в главное меню", callback_data='main_menu')]])
    return about_message, reply_markup


def display_current_settings_message(user: UserModel):
    """Возвращает текст и клавиатуру с текущими настройками пользователя."""
    settings_message = "🔧 *Текущие настройки для отклика*:\n\n"
    settings_message += f"📄 *ID резюме*: {user.get('resume_id', '❌ Не установлено')}\n"
    settings_message += f"🔍 *Ключевые слова*: {user.get('keywords', '❌ Не установлены')}\n"
    settings_message += f"💌 *Сопроводительное письмо*: {'✅ Установлено' if user.get('cover_letter_template') else '❌ Не установлено'}\n"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='settings')]])
    return settings_message, reply_markup

async def display_resume_selection_message(query: CallbackQuery, user: UserModel):
    """Позволяет пользователю выбрать резюме для откликов."""
    auth_token = user.get("auth_token")
    hh_api = HHApi(auth_token)
    resume_list = await hh_api.get_resumes()

    if not resume_list:
        await query.edit_message_text("Резюме не найдены.")
        return

    message_text = "Ваши резюме:\n\n"
    buttons = []

    for index, resume in enumerate(resume_list):
        title = resume['title']
        resume_id = resume['id']
        message_text += f"{index + 1}. [{title}](https://hh.kz/resume/{resume_id})\n"
        buttons.append([InlineKeyboardButton(f"Выбрать резюме {index + 1}", callback_data=f"select_resume_{resume_id}")])

    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='settings')])

    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=reply_markup)

def generate_cover_letter(company_name, vacancy_name, template):
    """Генерирует сопроводительное письмо на основе шаблона."""
    return template.format(company_name=company_name, vacancy_name=vacancy_name).replace('\\n', '\n').strip()
