#!/usr/bin/env python3
"""
Скрипт для тестирования функциональности бота
"""

import asyncio
import random
from database import Database
from config import PRODUCTS, PACKAGING_OPTIONS, MIN_DELIVERY_TIME, MAX_DELIVERY_TIME

class BotTester:
    def __init__(self):
        self.db = Database()
    
    def test_database_connection(self):
        """Тестирование подключения к базе данных"""
        print("🔍 Тестирование подключения к базе данных...")
        try:
            # Пробуем создать тестовый заказ
            order_id = self.db.add_order(
                user_id=123456789,
                username="test_user",
                product="Тестовый товар",
                packaging="1 г",
                address="Тестовый адрес",
                delivery_time=60
            )
            print(f"✅ Подключение к БД успешно. Создан тестовый заказ ID: {order_id}")
            
            # Получаем статистику
            stats = self.db.get_order_stats()
            print(f"📊 Статистика: всего заказов - {stats['total']}")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    def test_config(self):
        """Тестирование конфигурации"""
        print("\n🔍 Тестирование конфигурации...")
        
        # Проверяем товары
        print(f"📦 Товары: {list(PRODUCTS.keys())}")
        
        # Проверяем фасовку
        print(f"📋 Фасовка: {PACKAGING_OPTIONS}")
        
        # Проверяем время доставки
        print(f"⏰ Время доставки: {MIN_DELIVERY_TIME}-{MAX_DELIVERY_TIME} минут")
        
        return True
    
    def generate_test_orders(self, count=5):
        """Генерация тестовых заказов"""
        print(f"\n🔍 Генерация {count} тестовых заказов...")
        
        test_users = [
            {"id": 111111111, "username": "user1"},
            {"id": 222222222, "username": "user2"},
            {"id": 333333333, "username": "user3"},
            {"id": 444444444, "username": "user4"},
            {"id": 555555555, "username": "user5"}
        ]
        
        test_addresses = [
            "ул. Ленина, д. 1, кв. 5",
            "пр. Мира, д. 15, кв. 12",
            "ул. Гагарина, д. 8, кв. 3",
            "пр. Победы, д. 25, кв. 7",
            "ул. Советская, д. 10, кв. 15"
        ]
        
        for i in range(count):
            user = test_users[i % len(test_users)]
            product_key = random.choice(list(PRODUCTS.keys()))
            product = PRODUCTS[product_key]
            packaging = random.choice(PACKAGING_OPTIONS)
            address = random.choice(test_addresses)
            delivery_time = random.randint(MIN_DELIVERY_TIME, MAX_DELIVERY_TIME)
            
            order_id = self.db.add_order(
                user_id=user["id"],
                username=user["username"],
                product=product,
                packaging=packaging,
                address=address,
                delivery_time=delivery_time
            )
            
            print(f"✅ Создан заказ ID: {order_id} - {product} {packaging}")
        
        return True
    
    def test_admin_responses(self):
        """Тестирование ответов администратора"""
        print("\n🔍 Тестирование ответов администратора...")
        
        test_user_id = 123456789
        test_message = "Это тестовое сообщение от администратора"
        
        try:
            self.db.add_admin_response(test_user_id, test_message)
            print("✅ Ответ администратора добавлен в БД")
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления ответа администратора: {e}")
            return False
    
    def display_test_results(self):
        """Отображение результатов тестирования"""
        print("\n📊 Результаты тестирования:")
        
        # Получаем статистику
        stats = self.db.get_order_stats()
        print(f"📈 Всего заказов: {stats['total']}")
        print(f"📅 За сегодня: {stats['today']}")
        print(f"📊 За неделю: {stats['week']}")
        
        # Получаем последние заказы
        orders = self.db.get_orders(limit=3)
        if orders:
            print("\n📋 Последние заказы:")
            for order in orders:
                print(f"  ID: {order[0]}, @{order[2]}, {order[3]} - {order[4]}")
    
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        print("\n🧹 Очистка тестовых данных...")
        
        # Удаляем тестовые заказы
        conn = self.db.db_path
        import sqlite3
        db_conn = sqlite3.connect(conn)
        cursor = db_conn.cursor()
        
        # Удаляем заказы с тестовыми адресами
        cursor.execute('''
            DELETE FROM orders 
            WHERE address LIKE '%Тестовый%' OR address LIKE '%Ленина%'
        ''')
        deleted_count = cursor.rowcount
        
        # Удаляем тестовые ответы администратора
        cursor.execute('''
            DELETE FROM admin_responses 
            WHERE admin_message LIKE '%тестовое%'
        ''')
        
        db_conn.commit()
        db_conn.close()
        
        print(f"✅ Удалено {deleted_count} тестовых заказов")

def main():
    """Главная функция тестирования"""
    print("🧪 Тестирование Telegram-бота для доставки")
    print("=" * 50)
    
    tester = BotTester()
    
    # Запускаем тесты
    tests = [
        ("Подключение к БД", tester.test_database_connection),
        ("Конфигурация", tester.test_config),
        ("Генерация тестовых заказов", lambda: tester.generate_test_orders(3)),
        ("Ответы администратора", tester.test_admin_responses)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Тест: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} - ПРОЙДЕН")
                passed_tests += 1
            else:
                print(f"❌ {test_name} - ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ {test_name} - ОШИБКА: {e}")
    
    # Отображаем результаты
    tester.display_test_results()
    
    # Итоги
    print(f"\n📊 Итоги тестирования:")
    print(f"✅ Пройдено тестов: {passed_tests}/{total_tests}")
    print(f"📈 Процент успешности: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️ Некоторые тесты не пройдены")
    
    # Спрашиваем об очистке
    cleanup = input("\n🧹 Очистить тестовые данные? (y/n): ").lower()
    if cleanup == 'y':
        tester.cleanup_test_data()
    
    print("\n👋 Тестирование завершено!")

if __name__ == "__main__":
    main() 