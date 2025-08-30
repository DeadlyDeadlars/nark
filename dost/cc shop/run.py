#!/usr/bin/env python3
"""
Запуск CHAT SHOP Telegram Bot
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from bot import ShopBot
    print("🚀 Запуск LUXURY SHOP бота...")
    print("📱 Бот готов к работе!")
    print("💡 Для остановки нажмите Ctrl+C")
    
    bot = ShopBot()
    bot.run()
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("💡 Убедитесь, что все зависимости установлены:")
    print("   pip install -r requirements.txt")
    
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")
    print("💡 Проверьте настройки в config.py и .env файлах")
