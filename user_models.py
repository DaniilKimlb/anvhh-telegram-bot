from db import load_user_config, save_user_config, find_resume_owner

class UserModel:
    """Модель пользователя для работы с настройками."""

    def __init__(self, chat_id: int):
        self.chat_id = int(chat_id)
        self.config = {}

    async def load(self, use_cache=True):
        """Загружает конфигурацию пользователя из базы данных."""
        self.config = await load_user_config(self.chat_id, use_cache=use_cache)

    async def save(self):
        """Сохраняет конфигурацию пользователя в базу данных."""
        await save_user_config(self.chat_id, self.config)

    def get(self, key, default=None):
        """Получает значение из конфигурации пользователя."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Устанавливает значение в конфигурации пользователя."""
        self.config[key] = value


    async def is_resume_owner(self, resume_id):
        """Проверяет, принадлежит ли резюме данному пользователю."""
        resume_owner = await find_resume_owner(resume_id)
        return resume_owner == self.chat_id
