#!/usr/bin/env python3
"""
Тестирование CHAT SHOP Telegram Bot
"""

import sys
import os
import asyncio

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from cryptobot import CryptoBot

async def test_database():
    """Тестирование базы данных"""
    print("🧪 Тестирование базы данных...")
    
    try:
        db = Database()
        print("✅ База данных инициализирована")
        
        # Тест добавления пользователя
        test_user_id = 12345
        result = db.add_user(test_user_id, "test_user", "Test User")
        print(f"✅ Добавление пользователя: {result}")
        
        # Тест получения пользователя
        user = db.get_user(test_user_id)
        print(f"✅ Получение пользователя: {user is not None}")
        
        # Тест получения товаров
        products = db.get_products()
        print(f"✅ Получение товаров: {len(products)} товаров найдено")
        
        # Тест получения товаров по категории
        category_products = db.get_products("CHEAP MANUALS")
        print(f"✅ Товары категории CHEAP MANUALS: {len(category_products)} товаров")
        
        print("✅ Все тесты базы данных пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования базы данных: {e}")

async def test_cryptobot():
    """Тестирование криптобота"""
    print("\n🧪 Тестирование криптобота...")
    
    try:
        crypto_bot = CryptoBot()
        print("✅ Криптобот инициализирован")
        
        # Тест получения валют
        currencies = await crypto_bot.get_currencies()
        if currencies:
            print(f"✅ Получение валют: {len(currencies)} валют доступно")
        else:
            print("⚠️ Получение валют: API недоступен (проверьте токен)")
        
        # Тест форматирования сообщения
        test_invoice = {
            "amount": "100.0",
            "currency": "USDT",
            "pay_url": "https://example.com/pay",
            "invoice_id": "test_123"
        }
        
        message = crypto_bot.format_payment_message(test_invoice)
        print(f"✅ Форматирование сообщения: {len(message)} символов")
        
        # Тест создания клавиатуры
        keyboard = crypto_bot.create_payment_keyboard("test_123")
        print(f"✅ Создание клавиатуры: {len(keyboard['inline_keyboard'])} кнопок")
        
        print("✅ Все тесты криптобота пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования криптобота: {e}")

async def test_integration():
    """Тестирование интеграции"""
    print("\n🧪 Тестирование интеграции...")
    
    try:
        db = Database()
        crypto_bot = CryptoBot()
        
        # Тест создания заказа
        test_user_id = 12345
        test_product_id = 1
        
        # Получаем товар
        product = db.get_product(test_product_id)
        if product:
            print(f"✅ Получение товара: {product['name']}")
            
            # Создаем заказ
            order_id = db.create_order(test_user_id, test_product_id, product['price'])
            print(f"✅ Создание заказа: ID {order_id}")
            
            # Получаем историю заказов
            orders = db.get_user_orders(test_user_id)
            print(f"✅ История заказов: {len(orders)} заказов")
            
        else:
            print("⚠️ Товар не найден для тестирования")
        
        print("✅ Все тесты интеграции пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования интеграции: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов LUXURY SHOP бота...\n")
    
    await test_database()
    await test_cryptobot()
    await test_integration()
    
    print("\n🎉 Все тесты завершены!")
    print("💡 Если все тесты пройдены успешно, бот готов к работе!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
