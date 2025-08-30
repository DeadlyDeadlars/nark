import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokens
MAIN_BOT_TOKEN = os.getenv('MAIN_BOT_TOKEN')
INFO_BOT_TOKEN = os.getenv('INFO_BOT_TOKEN')

# Admin IDs (comma-separated in .env)
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
SUPER_ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else None  # Первый админ в списке - супер-админ

# Database
DATABASE_URL = "sqlite:///bot_database.db"

# Info bot chat ID for logs
# ВАЖНО: INFO_BOT_CHAT_ID должен быть user_id (ваш личный id) или id группы/канала, куда добавлен инфо-бот как админ.
# НЕЛЬЗЯ указывать id другого бота! Если хотите получать логи в личку — используйте свой user_id (например, 123456789).
# Для группы/канала используйте отрицательный id (например, -1001234567890) и добавьте инфо-бота как администратора.
INFO_BOT_CHAT_ID = os.getenv('INFO_BOT_CHAT_ID')

# Available cities
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Омск", "Самара", "Ростов-на-Дону",
    "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"
]

# Default bot settings
DEFAULT_SETTINGS = {
    "welcome_message": "Добро пожаловать!",
    "worker_panel_message": "Панель воркера",
    "admin_panel_message": "Панель администратора",
    "payment_instructions": "Инструкции по оплате",
    "referral_bonus": "10",  # Процент от реферальных платежей
    "min_payment": "100",    # Минимальная сумма платежа
    "max_payment": "10000"   # Максимальная сумма платежа
} 