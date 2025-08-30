import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')  # ID администратора для уведомлений

# Настройки логирования в канал
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')  # ID канала для логов (например: -1001234567890)
LOGS_CHANNEL_USERNAME = os.getenv('LOGS_CHANNEL_USERNAME')  # Username канала (опционально, для публичных каналов)

# Поддержка/оператор
SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@luxurydelivery')

# Настройки базы данных
DATABASE_PATH = 'orders.db'

# Настройки товаров
PRODUCTS = {
    'mef_premium_vhq': 'Меф premium VHQ 💎',
    'alpha_big': 'Альфа крупные крисы❄️',
    'cocaine_colymbia': 'Cocaine  COLYMBIA 🥥',
    'hashish_afghani': 'Гашиш  Afghani 🍫',
    'hashish_first_lady': 'Гашиш First Lady 🥫',
    'og_kush': 'Шишки OG KUSH 🌴',
    'mdma_vhq': 'Мдма VHQ 🍥'
}

# Варианты фасовки
PACKAGING_OPTIONS = ['1 г', '2 г', '3 г', 'Другое количество (обсуждается с @luxurydelivery)']

# Время доставки (в минутах)
MIN_DELIVERY_TIME = 30
MAX_DELIVERY_TIME = 200

# Ссылки
REVIEWS_LINK = "https://t.me/luxrydelivery"  # Ссылка на канал с отзывами
ABOUT_TEXT = """
🏪 **О нашем сервисе доставки**

Мы предоставляем быструю и надежную доставку качественных товаров по всему городу.

✨ **Наши преимущества:**
• Быстрая доставка (30-200 минут)
• Конфиденциальность
• Качественные товары
• Удобное оформление заказа

📞 **Поддержка:** @luxurydelivery
⭐ **Отзывы:** @luxrydelivery

*Работаем 24/7 для вашего удобства!*
""" 