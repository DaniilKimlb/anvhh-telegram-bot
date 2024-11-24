import httpx
from datetime import datetime, timedelta, timezone
import pytz
from cryptography.fernet import Fernet
from config import base_config

class HHApi:
    """Класс для взаимодействия с API HeadHunter."""
    base_url = base_config.getBaseUrl()

    def __init__(self, encrypted_auth_token):
        """Инициализация с расшифровкой токена."""
        self.encryption_key = base_config.getEncryptionKey()
        self.cipher = Fernet(self.encryption_key)
        self.auth_token = self.decrypt_token(encrypted_auth_token)
        self.headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'User-Agent': base_config.getUserAgent()
        }

    def decrypt_token(self, encrypted_token):
        """Расшифровывает токен авторизации."""
        return self.cipher.decrypt(encrypted_token.encode()).decode()

    async def get(self, endpoint, params=None):
        """Выполняет GET-запрос к API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url + endpoint,
                headers=self.headers,
                params=params
            )
        return response

    async def post(self, endpoint, data=None, json=None):
        """Выполняет POST-запрос к API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url + endpoint,
                headers=self.headers,
                data=data,
                json=json
            )
        return response

    async def put(self, endpoint, data=None):
        """Выполняет PUT-запрос к API."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                self.base_url + endpoint,
                headers=self.headers,
                data=data
            )
        return response

    async def delete(self, endpoint):
        """Выполняет DELETE-запрос к API."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                self.base_url + endpoint,
                headers=self.headers
            )
        return response

    async def patch(self, endpoint, data=None):
        """Выполняет PATCH-запрос к API."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                self.base_url + endpoint,
                headers=self.headers,
                data=data
            )
        return response

    async def respond_to_vacancy(self, vacancy_id, resume_id, cover_letter):
        """Откликается на вакансию."""
        data = {
            "message": cover_letter,
            "resume_id": resume_id,
            "vacancy_id": vacancy_id,
        }
        response = await self.post('/negotiations', data=data)
        if response.status_code == 201:
            return 'success'
        elif response.status_code == 400:
            return 'today_limit'
        elif response.status_code == 403:
            response_data = response.json()
            if self.is_error_present(response_data, "test_required"):
                return 'test_required'
            elif self.is_error_present(response_data, "already_applied"):
                return 'already_applied'
            return 'forbidden'
        else:
            print(f"Failed to respond to vacancy: {response.status_code}")
            return 'error'

    def is_error_present(self, data, error_value):
        """Проверяет наличие определенной ошибки в ответе API."""
        for error in data.get("errors", []):
            if error.get("value") == error_value:
                return True
        return False

    async def add_vacancy_to_blacklist(self, vacancy_id):
        """Добавляет вакансию в черный список."""
        response = await self.put(f'/vacancies/blacklisted/{vacancy_id}')
        if response.status_code == 204:
            return 'blacklisted'
        else:
            print(f"Failed to add vacancy to blacklist: {response.status_code}")
            return 'error'

    async def get_resumes(self):
        """Получает список резюме пользователя."""
        response = await self.get('/resumes/mine')
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            print(f"Failed to retrieve resumes: {response.status_code}")
            return []

    async def get_negotiations(self, per_page):
        """Получает список откликов пользователя."""
        params = {'per_page': per_page, 'order_by': 'created_at', 'order': 'desc'}
        response = await self.get('/negotiations', params=params)
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            print(f"Failed to get negotiations: {response.status_code}")
            return None

    async def get_vacancies(self, keywords, page=0):
        """Получает список вакансий по ключевым словам."""
        params = {
            'text': keywords,
            'per_page': 50,
            'page': page,
        }
        response = await self.get('/vacancies', params=params)
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            print(f"Failed to retrieve vacancies: {response.status_code}")
            return []

    async def count_remaining_responses(self):
        """Считает оставшиеся отклики пользователя."""
        current_time = datetime.now(timezone.utc)
        max_daily_responses = 200
        negotiations = await self.get_negotiations(per_page=max_daily_responses)
        if negotiations is None:
            return 0, current_time.strftime('%d.%m.%Y %H:%M (%Z)')
        if len(negotiations) == 0:
            return max_daily_responses, current_time.strftime('%d.%m.%Y %H:%M (%Z)')

        response_times = sorted(
            [datetime.fromisoformat(response["created_at"]).astimezone(timezone.utc) for response in negotiations]
        )

        time_24_hours_ago = current_time - timedelta(hours=24)
        responses_last_24_hours = [
            response_time for response_time in response_times
            if time_24_hours_ago <= response_time <= current_time
        ]

        used_responses = len(responses_last_24_hours)
        remaining_responses = max(0, max_daily_responses - used_responses)

        if remaining_responses <= 0:
            next_available_time = responses_last_24_hours[-1] + timedelta(hours=24)
        else:
            next_available_time = current_time

        almaty_tz = pytz.timezone('Asia/Almaty')
        next_available_time_almaty = next_available_time.astimezone(almaty_tz)
        formatted_next_available_time = next_available_time_almaty.strftime('%d.%m.%Y %H:%M (%Z)')

        return remaining_responses, formatted_next_available_time

