import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# CryptoBot @send integration
CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN')
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Bot settings
BOT_USERNAME = "@your_bot_username"
OWNER_USERNAME = "@luxury_sup"
BOT_NAME = "LUXURY SHOP"

# Admin settings
ADMIN_USERNAMES = os.getenv('ADMIN_USERNAMES', '@omens2').split(',')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]

# ID админского канала для уведомлений о платежах
ADMIN_CHANNEL_ID = int(os.getenv('ADMIN_CHANNEL_ID', '-1001234567890'))  # Замените на ID вашего админского канала

# Database settings (можно использовать SQLite для простоты)
DATABASE_URL = "sqlite:///shop_bot.db"

# Payment settings
MIN_PAYMENT_AMOUNT = 1.0  # минимальная сумма в USD

# TON USDT wallet for manual transfers
TON_USDT_WALLET = os.getenv('TON_USDT_WALLET', '').strip()

# TRX wallet for manual transfers
TRX_USDT_WALLET = os.getenv('TRX_USDT_WALLET', 'TW2sEyrgWyHsxWs2T6S867Tq1g8fnj5xUk').strip()

# Webhook settings
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
RELAY_TOKEN = os.getenv('RELAY_TOKEN')  # общий секрет для ретрансляции с Netlify