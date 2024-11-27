import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ContextTypes
from user_models import UserModel
from hh import HHApi
from config import base_config
from message_builders import (
    build_main_menu,
    build_settings_menu,
    build_main_menu_back_button,
    build_settings_back_button,
    display_about_message,
    display_current_settings_message,
    display_resume_selection_message,
    generate_cover_letter,
)

# Константы состояний
STATE_SET_KEYWORDS = 1
STATE_SET_COVER_LETTER = 2
STATE_ENTERING_PHONE = 3

async def update_message_in_task(query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode=None, disable_web_page_preview=None) -> None:
    """Асинхронно редактирует сообщение без блокировки основного цикла событий."""
    asyncio.create_task(query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview
    ))
    await asyncio.sleep(0)


async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    chat_id = update.message.chat_id
    user = UserModel(chat_id)
    await user.load()
    auth_token_exists = "auth_token" in user.config
    reply_markup = build_main_menu(auth_token_exists)
    await update.message.reply_text(
        "🏠 Добро пожаловать в главное меню!\n\n"
        "Для использования всех функций бота вам нужно авторизоваться на HH. "
        "Пожалуйста, нажмите кнопку *🔑 Авторизоваться* ниже, чтобы получить доступ к вакансиям и начать отклики.",
        reply_markup=reply_markup
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок в встроенных клавиатурах."""
    query = update.callback_query
    chat_id = query.message.chat_id
    user = UserModel(chat_id)
    await user.load()
    auth_token = user.get("auth_token")

    data = query.data

    if data == 'about_us':
        await update_message_in_task(query, *display_about_message(), disable_web_page_preview=True, parse_mode="Markdown")
    elif data == 'authorize':
        await handle_authorization_process(query, user)
    elif data == 'check_authorization':
        await check_authorization_status(query, user)
    elif data == 'start_vacancy_responses':
        asyncio.create_task(process_vacancy_responses(query, context, user))
        await asyncio.sleep(0)
    elif data == 'view_settings':
        await update_message_in_task(query, *display_current_settings_message(user))
    elif data == 'settings':
        await update_message_in_task(query, "⚙️ Настройка отклика:", build_settings_menu())
    elif data == 'select_resume':
        asyncio.create_task(display_resume_selection_message(query, user))
        await asyncio.sleep(0)
    elif data.startswith('select_resume_'):
        await select_resume(query, data, user)
    elif data == 'set_keywords':
        await set_keywords(query, context)
    elif data == 'set_cover_letter':
        await set_cover_letter(query, context)
    elif data == 'main_menu':
        await go_to_main_menu(query, auth_token)
    await query.answer()

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает входящие текстовые сообщения."""
    chat_id = update.message.chat_id
    state = context.user_data.get('state')
    user = UserModel(chat_id)
    await user.load()

    if state == STATE_SET_KEYWORDS:
        keywords = update.message.text
        user.set('keywords', keywords)
        await user.save()
        await reset_state_with_message(update, context, "✅ Ключевые слова обновлены.")
    elif state == STATE_SET_COVER_LETTER:
        cover_letter = update.message.text
        user.set('cover_letter_template', cover_letter)
        await user.save()
        await reset_state_with_message(update, context, "✅ Сопроводительное письмо обновлено.")
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки для взаимодействия с ботом.")

# Дополнительные функции для обработки логики

async def handle_authorization_process(query: CallbackQuery, user: UserModel):
    """Начинает процесс авторизации."""
    auth_url = base_config.getAuthUrl(user.chat_id)
    await update_message_in_task(
        query,
        '🔐 Для продолжения, пожалуйста, нажмите кнопку ниже, чтобы авторизоваться и вернитесь обратно.',
        InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Перейти к авторизации", url=auth_url)],
            [InlineKeyboardButton("✅ Авторизировались?", callback_data='check_authorization')],
        ])
    )

async def check_authorization_status(query: CallbackQuery, user: UserModel):
    """Проверяет статус авторизации."""
    auth_token = user.get("auth_token")
    if not auth_token:
        await user.load(use_cache=False)  # Перезагрузка конфигурации без кэша
        auth_token = user.get("auth_token")
    if auth_token:
        await query.answer("✅ Вы успешно авторизовались!")
        reply_markup = build_main_menu(auth_token_exists=True)
        await update_message_in_task(
            query,
            "🏠 Добро пожаловать в главное меню! Используйте кнопки ниже для работы с ботом.",
            reply_markup
        )
    else:
        auth_url = base_config.getAuthUrl(user.chat_id)
        await update_message_in_task(
            query,
            "❌ Вы еще не авторизованы. Пожалуйста, перейдите по ссылке и авторизуйтесь.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Перейти к авторизации", url=auth_url)],
                [InlineKeyboardButton("🔄 Авторизировались?", callback_data='check_authorization')],
            ])
        )

async def process_vacancy_responses(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, user: UserModel):
    """Обрабатывает процесс отклика на вакансии."""


    auth_token = user.get("auth_token")
    resume_id = user.get("resume_id")
    keywords = user.get('keywords')
    cover_letter_template = user.get('cover_letter_template')
    subscription_level = user.get('subscription_level')

    # Запускаем процесс отклика в отдельной задаче
    asyncio.create_task(
        begin_vacancy_responses(
            query,
            context,
            auth_token=auth_token,
            resume_id=resume_id,
            keywords=keywords,
            cover_letter_template=cover_letter_template,
        )
    )
    await asyncio.sleep(0)


async def select_resume(query: CallbackQuery, data: str, user: UserModel):
    """Позволяет выбрать резюме для отклика."""
    resume_id = data.split('_')[-1]
    user.set('resume_id', resume_id)
    await user.save()
    await update_message_in_task(
        query,
        "✅ Резюме успешно установлено для откликов.\n\n⚙️ Настройка отклика:",
        build_settings_menu()
    )

async def set_keywords(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс установки ключевых слов."""
    await update_message_in_task(
        query,
        "🔍 Введите ключевые слова для поиска вакансий, на которые хотите откликаться (например, 'Python разработчик Казахстан').\n\n"
        "📖 [Описание языка поисковых запросов](https://hh.kz/article/1175)",
        build_settings_back_button(),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    context.user_data['state'] = STATE_SET_KEYWORDS

async def set_cover_letter(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс установки сопроводительного письма."""
    await update_message_in_task(
        query,
        "Введите текст письма.\n\n"
        "Используйте следующие шаблоны:\n"
        "{company_name} — название компании\n"
        "{vacancy_name} — название вакансии\n\n"
        "Пример:\n"
        "Ввод: 'Здравствуйте, {company_name}! Я заинтересован в вашей вакансии {vacancy_name}.'\n"
        "Вывод: 'Здравствуйте, Google! Я заинтересован в вашей вакансии Разработчик.'",
        build_settings_back_button()
    )
    context.user_data['state'] = STATE_SET_COVER_LETTER

async def go_to_main_menu(query: CallbackQuery, auth_token):
    """Возвращает пользователя в главное меню."""
    reply_markup = build_main_menu(auth_token_exists=auth_token is not None)
    await update_message_in_task(
        query,
        "🏠 Главное меню! Используйте кнопки ниже для работы с ботом.",
        reply_markup
    )



async def reset_state_with_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Сбрасывает состояние и отправляет сообщение."""
    reply_markup = build_settings_menu()
    await update.message.reply_text(f"{text}\n\n⚙️ Настройка отклика:", reply_markup=reply_markup)
    context.user_data['state'] = None



async def begin_vacancy_responses(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    auth_token,
    resume_id,
    keywords,
    cover_letter_template,
) -> bool:
    """Запускает процесс отклика на вакансии."""
    missing_parameters = []
    if not resume_id:
        missing_parameters.append("📄 Установить резюме")
    if not keywords:
        missing_parameters.append("🔍 Обновить ключевые слова для поиска")
    if not cover_letter_template:
        missing_parameters.append("✉️ Обновить сопроводительное письмо")

    if missing_parameters:
        buttons = []
        if not resume_id:
            buttons.append([InlineKeyboardButton("📄 Установить резюме", callback_data='select_resume')])
        if not keywords:
            buttons.append([InlineKeyboardButton("🔍 Обновить ключевые слова для поиска", callback_data='set_keywords')])
        if not cover_letter_template:
            buttons.append([InlineKeyboardButton("✉️ Обновить сопроводительное письмо", callback_data='set_cover_letter')])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update_message_in_task(
            query,
            "⚠️ Для начала откликов необходимо задать все обязательные параметры:\n" +
            "\n".join(missing_parameters) +
            "\n\nПожалуйста, установите недостающие параметры с помощью кнопок ниже:",
            reply_markup
        )
        return False

    hhApi = HHApi(auth_token)
    success_counter = 0
    is_vacancies_ended = False
    total_counter = 0
    successful_responses_counter = 0
    try:
        await update_message_in_task(query, "🔄 Получаем вакансии...")
        remaining_responses, next_available_time = await hhApi.count_remaining_responses()
        is_today_limit = remaining_responses <= 0
        if is_today_limit:
            await update_message_in_task(
                query,
                f"⛔ На сегодня вы достигли лимита откликов 🙁\n\nСледующий отклик станет доступен: {next_available_time}.",
                build_main_menu_back_button()
            )
            return False
        await update_message_in_task(
            query,
            f"⏳ Доступно {remaining_responses} откликов. Начинаем откликаться..."
        )
        page = 0
        while not is_today_limit and not is_vacancies_ended:
            try:
                vacancies_list = await hhApi.get_vacancies(keywords, page=page)
                if not vacancies_list:
                    is_vacancies_ended = True
                    break
                page += 1
                for vacancy in vacancies_list:
                    try:
                        if vacancy.get('has_test', False):
                            await hhApi.add_vacancy_to_blacklist(vacancy['id'])
                            continue
                        if vacancy.get('relations') and len(vacancy['relations']) > 0:
                            continue
                        total_counter += 1
                        cover_letter = generate_cover_letter(vacancy['employer']['name'], vacancy['name'], cover_letter_template)
                        status = await hhApi.respond_to_vacancy(
                            vacancy_id=vacancy['id'],
                            resume_id=resume_id,
                            cover_letter=cover_letter
                        )
                        if status == 'today_limit':
                            is_today_limit = True
                            break
                        elif status == 'success':
                            success_counter += 1
                            successful_responses_counter += 1
                        new_status_text = f"⏳ Обработка вакансий...\nОткликов: {success_counter} / {remaining_responses}"
                        if successful_responses_counter >= 4:
                            try:
                                await update_message_in_task(query, new_status_text)
                                successful_responses_counter = 0
                            except Exception as edit_error:
                                print(f"Ошибка редактирования текста сообщения: {edit_error}")
                                continue
                        if success_counter >= remaining_responses:
                            is_today_limit = True
                            break
                    except Exception as edit_error:
                        print(f"Ошибка откликов: {edit_error}")
                        continue
            except Exception as edit_error:
                print(edit_error, 'error in vacancies processing')
        if success_counter >= 1:
            base_message = f"✅ Успешно отправлено {success_counter} откликов из {remaining_responses}."
            reply_markup = build_main_menu_back_button()
            if is_vacancies_ended:
                base_message = (
                    f"🔍❌ Упс... Вакансии по ключевым словам: *{keywords}* закончились. "
                    "Попробуйте изменить ключевые слова или повторить попытку позже.\n\n"
                    f"✅ Однако удалось успешно отправить {success_counter} откликов из {remaining_responses}."
                )
            await update_message_in_task(
                query,
                base_message,
                reply_markup
            )
            return True
        elif is_vacancies_ended:
            await update_message_in_task(
                query,
                f"🔍❌ Упс... Вакансии по ключевым словам: *{keywords}* закончились, или ничего не нашлось. Попробуйте изменить ключевые слова или повторить попытку позже.",
                build_main_menu_back_button()
            )
            return False
    except Exception as e:
        print(e, 'error in begin_vacancy_responses')
        await update_message_in_task(
            query,
            "❌ Извините, что-то пошло не так. Повторите попытку позже",
            build_main_menu_back_button()
        )
