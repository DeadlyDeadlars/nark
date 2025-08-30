#!/usr/bin/env python3
"""
Тестовый скрипт для проверки конфигурации
"""

from config import ADMIN_CHANNEL_ID, ADMIN_IDS, BOT_TOKEN, CRYPTOBOT_TOKEN

def test_config():
    print("🔧 Тестирование конфигурации...")
    
    print(f"BOT_TOKEN: {'✅ Установлен' if BOT_TOKEN else '❌ Не установлен'}")
    print(f"CRYPTOBOT_TOKEN: {'✅ Установлен' if CRYPTOBOT_TOKEN else '❌ Не установлен'}")
    print(f"ADMIN_CHANNEL_ID: {ADMIN_CHANNEL_ID}")
    print(f"ADMIN_IDS: {ADMIN_IDS}")
    
    # Проверяем ADMIN_CHANNEL_ID
    if ADMIN_CHANNEL_ID == -1001234567890:
        print("⚠️ ADMIN_CHANNEL_ID равен значению по умолчанию!")
        print("   Установите правильный ID канала в файле .env")
    else:
        print("✅ ADMIN_CHANNEL_ID настроен правильно")
    
    # Проверяем ADMIN_IDS
    if not ADMIN_IDS:
        print("⚠️ ADMIN_IDS не настроены!")
        print("   Установите ID администраторов в файле .env")
    else:
        print(f"✅ ADMIN_IDS настроены: {ADMIN_IDS}")

if __name__ == "__main__":
    test_config()
