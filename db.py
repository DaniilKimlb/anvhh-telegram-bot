import asyncpg
from datetime import datetime, timedelta
from config import base_config

DATABASE_URL = base_config.getDatabaseUrl()
user_config_cache = {}
CACHE_TTL = timedelta(minutes=10)

async def load_user_config(chat_id, use_cache=True):
    chat_id = int(chat_id)

    if use_cache and chat_id in user_config_cache:
        cached_data, timestamp = user_config_cache[chat_id]
        if datetime.now() - timestamp < CACHE_TTL:
            return cached_data

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchrow("SELECT * FROM user_settings WHERE chat_id = $1", chat_id)
        if result:
            config_data = dict(result)
            # Кэшируем результат
            user_config_cache[chat_id] = (config_data, datetime.now())
            return config_data
        else:
            return {}
    finally:
        await conn.close()

async def save_user_config(chat_id, config_data):
    chat_id = int(chat_id)
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchrow("SELECT chat_id FROM user_settings WHERE chat_id = $1", chat_id)
        if result:
            # Обновляем запись
            set_clause = ', '.join([f"{key} = ${idx+1}" for idx, key in enumerate(config_data.keys())])
            values = list(config_data.values())
            await conn.execute(
                f"UPDATE user_settings SET {set_clause} WHERE chat_id = ${len(values)+1}",
                *values, chat_id
            )
        else:
            # Вставляем новую запись
            columns = ', '.join(config_data.keys())
            placeholders = ', '.join([f"${idx+1}" for idx in range(len(config_data))])
            values = list(config_data.values())
            await conn.execute(
                f"INSERT INTO user_settings (chat_id, {columns}) VALUES (${len(values)+1}, {placeholders})",
                *values, chat_id
            )
        # Инвалидируем кэш
        if chat_id in user_config_cache:
            del user_config_cache[chat_id]
    finally:
        await conn.close()

async def find_resume_owner(resume_id):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.fetchrow("SELECT chat_id FROM user_settings WHERE resume_id = $1", resume_id)
        if result:
            return result['chat_id']
        return None
    finally:
        await conn.close()
