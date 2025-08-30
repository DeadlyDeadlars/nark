#!/usr/bin/env python3
"""
Дополнительная панель администратора для управления ботом
"""

import sqlite3
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH

class AdminPanel:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    def get_detailed_stats(self):
        """Получение детальной статистики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        # Статистика по дням
        cursor.execute('''
            SELECT DATE(order_date), COUNT(*) 
            FROM orders 
            WHERE order_date >= datetime('now', '-7 days')
            GROUP BY DATE(order_date)
            ORDER BY DATE(order_date) DESC
        ''')
        daily_stats = cursor.fetchall()
        
        # Статистика по товарам
        cursor.execute('''
            SELECT product, COUNT(*) 
            FROM orders 
            GROUP BY product 
            ORDER BY COUNT(*) DESC
        ''')
        product_stats = cursor.fetchall()
        
        # Статистика по фасовке
        cursor.execute('''
            SELECT packaging, COUNT(*) 
            FROM orders 
            GROUP BY packaging 
            ORDER BY COUNT(*) DESC
        ''')
        packaging_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_orders': total_orders,
            'daily_stats': daily_stats,
            'product_stats': product_stats,
            'packaging_stats': packaging_stats
        }
    
    def export_orders_to_json(self, filename='orders_export.json'):
        """Экспорт заказов в JSON файл"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, username, product, packaging, address, 
                   delivery_time, order_date, status
            FROM orders 
            ORDER BY order_date DESC
        ''')
        
        orders = cursor.fetchall()
        conn.close()
        
        # Преобразуем в список словарей
        orders_list = []
        for order in orders:
            orders_list.append({
                'id': order[0],
                'user_id': order[1],
                'username': order[2],
                'product': order[3],
                'packaging': order[4],
                'address': order[5],
                'delivery_time': order[6],
                'order_date': order[7],
                'status': order[8]
            })
        
        # Сохраняем в файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(orders_list, f, ensure_ascii=False, indent=2)
        
        return len(orders_list)
    
    def get_user_activity(self, days=7):
        """Получение активности пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, COUNT(*) as order_count, 
                   MAX(order_date) as last_order
            FROM orders 
            WHERE order_date >= datetime('now', '-{} days')
            GROUP BY user_id, username
            ORDER BY order_count DESC
        '''.format(days))
        
        user_activity = cursor.fetchall()
        conn.close()
        
        return user_activity
    
    def search_orders(self, query):
        """Поиск заказов по различным критериям"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Поиск по адресу
        cursor.execute('''
            SELECT * FROM orders 
            WHERE address LIKE ? OR product LIKE ? OR username LIKE ?
            ORDER BY order_date DESC
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def delete_order(self, order_id):
        """Удаление заказа по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count > 0
    
    def update_order_status(self, order_id, status):
        """Обновление статуса заказа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders 
            SET status = ? 
            WHERE id = ?
        ''', (status, order_id))
        
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return updated_count > 0

def main():
    """Главная функция для тестирования панели администратора"""
    admin = AdminPanel()
    
    print("🔧 Панель администратора")
    print("=" * 50)
    
    while True:
        print("\nВыберите действие:")
        print("1. Детальная статистика")
        print("2. Экспорт заказов в JSON")
        print("3. Активность пользователей")
        print("4. Поиск заказов")
        print("5. Удалить заказ")
        print("6. Обновить статус заказа")
        print("0. Выход")
        
        choice = input("\nВведите номер: ")
        
        if choice == "1":
            stats = admin.get_detailed_stats()
            print(f"\n📊 Детальная статистика:")
            print(f"Всего заказов: {stats['total_orders']}")
            
            print("\n📅 Статистика по дням:")
            for date, count in stats['daily_stats']:
                print(f"  {date}: {count} заказов")
            
            print("\n🛒 Статистика по товарам:")
            for product, count in stats['product_stats']:
                print(f"  {product}: {count} заказов")
        
        elif choice == "2":
            count = admin.export_orders_to_json()
            print(f"\n✅ Экспортировано {count} заказов в orders_export.json")
        
        elif choice == "3":
            days = input("Введите количество дней (по умолчанию 7): ")
            days = int(days) if days.isdigit() else 7
            
            activity = admin.get_user_activity(days)
            print(f"\n👥 Активность пользователей за {days} дней:")
            for username, count, last_order in activity:
                print(f"  @{username}: {count} заказов, последний: {last_order}")
        
        elif choice == "4":
            query = input("Введите поисковый запрос: ")
            results = admin.search_orders(query)
            print(f"\n🔍 Найдено {len(results)} заказов:")
            for order in results[:5]:  # Показываем первые 5
                print(f"  ID: {order[0]}, @{order[2]}, {order[3]} - {order[4]}")
        
        elif choice == "5":
            order_id = input("Введите ID заказа для удаления: ")
            if order_id.isdigit():
                success = admin.delete_order(int(order_id))
                print("✅ Заказ удален" if success else "❌ Заказ не найден")
            else:
                print("❌ Неверный ID")
        
        elif choice == "6":
            order_id = input("Введите ID заказа: ")
            status = input("Введите новый статус: ")
            if order_id.isdigit():
                success = admin.update_order_status(int(order_id), status)
                print("✅ Статус обновлен" if success else "❌ Заказ не найден")
            else:
                print("❌ Неверный ID")
        
        elif choice == "0":
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main() 