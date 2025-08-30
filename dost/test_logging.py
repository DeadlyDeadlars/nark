#!/usr/bin/env python3
"""
Тест системы логирования в канал
"""

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from logger import setup_logging, log_order, log_admin_action, log_error

# Загружаем переменные окружения
load_dotenv()

async def test_logging():
    """Тестирование системы логирования"""
    
    # Получаем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не найден в .env файле")
        return
    
    # Создаем экземпляр бота
    bot = Bot(token=bot_token)
    
    try:
        # Настраиваем логирование
        print("🔧 Настройка логирования...")
        logger = setup_logging(bot)
        
        # Ждем немного для инициализации
        await asyncio.sleep(1)
        
        # Тестируем логирование заказа
        print("📦 Тестирование логирования заказа...")
        await log_order(
            logger=logger,
            user_id=123456789,
            username="test_user",
            product="Тестовый товар",
            packaging="1 г",
            address="Тестовый адрес",
            delivery_time=60
        )
        
        await asyncio.sleep(1)
        
        # Тестируем логирование действия администратора
        print("👨‍💼 Тестирование логирования действия администратора...")
        await log_admin_action(
            logger=logger,
            admin_id=987654321,
            action="Тестовое действие",
            details="Тестовые детали действия"
        )
        
        await asyncio.sleep(1)
        
        # Тестируем логирование ошибки
        print("❌ Тестирование логирования ошибки...")
        await log_error(
            logger=logger,
            error="Тестовая ошибка",
            context="Тестовый контекст"
        )
        
        await asyncio.sleep(1)
        
        # Тестируем обычное логирование
        print("ℹ️ Тестирование обычного логирования...")
        logger.info("Тестовое информационное сообщение")
        logger.warning("Тестовое предупреждение")
        
        await asyncio.sleep(2)
        
        print("✅ Тестирование завершено!")
        print("📢 Проверьте канал логов для подтверждения")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
    
    finally:
        # Закрываем бота
        await bot.session.close()

def main():
    """Главная функция"""
    print("🧪 Запуск тестирования системы логирования...")
    print("=" * 50)
    
    # Проверяем наличие переменных окружения
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    logs_channel_id = os.getenv('LOGS_CHANNEL_ID')
    logs_channel_username = os.getenv('LOGS_CHANNEL_USERNAME')
    
    print(f"🤖 Токен бота: {'✅' if bot_token else '❌'}")
    print(f"📢 ID канала логов: {'✅' if logs_channel_id else '❌'}")
    print(f"📢 Username канала логов: {'✅' if logs_channel_username else '❌'}")
    
    if not bot_token:
        print("\n❌ Ошибка: BOT_TOKEN не найден!")
        print("Создайте файл .env и добавьте BOT_TOKEN")
        return
    
    if not logs_channel_id:
        print("\n⚠️ Предупреждение: Канал логов не настроен!")
        print("Логи будут выводиться только в консоль")
        print("Для настройки канала добавьте LOGS_CHANNEL_ID в .env")
        print("💡 Для приватных каналов используйте только LOGS_CHANNEL_ID")
    
    print("\n🚀 Запуск тестов...")
    asyncio.run(test_logging())

if __name__ == "__main__":
    main() 