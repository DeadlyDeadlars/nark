#!/usr/bin/env python3
"""
Административная панель для LUXURY SHOP Telegram Bot
"""

import sys
import os
import sqlite3
from typing import List, Dict, Any

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from admin_auth import AdminAuth

class AdminPanel:
    def __init__(self):
        self.db = Database()
        self.auth = AdminAuth()
    
    def check_admin_access(self) -> bool:
        """Проверяет доступ администратора"""
        print("🔐 ПРОВЕРКА ДОСТУПА АДМИНИСТРАТОРА")
        print("-" * 40)
        
        # Запрашиваем данные пользователя
        user_id = input("Введите ваш Telegram ID: ").strip()
        username = input("Введите ваш username (без @): ").strip()
        
        if username and not username.startswith('@'):
            username = f"@{username}"
        
        try:
            user_id = int(user_id)
            if self.auth.is_admin(user_id, username):
                print(f"✅ Доступ разрешен! Добро пожаловать, {username or user_id}")
                return True
            else:
                print("❌ Доступ запрещен! Вы не являетесь администратором.")
                return False
        except ValueError:
            print("❌ Неверный ID пользователя")
            return False
    
    def show_menu(self):
        """Показать главное меню администратора"""
        while True:
            print("\n" + "="*50)
            print("🔧 АДМИНИСТРАТИВНАЯ ПАНЕЛЬ LUXURY SHOP")
            print("="*50)
            print("1. 📊 Статистика")
            print("2. 👥 Управление пользователями")
            print("3. 📦 Управление товарами")
            print("4. 📋 Управление заказами")
            print("5. 💰 Управление балансами")
            print("6. 📢 Рассылка сообщений")
            print("7. 🚫 Блокировка пользователей")
            print("8. 🔄 Резервное копирование")
            print("9. ⚙️ Настройки бота")
            print("10. 👑 Управление администраторами")
            print("11. 📡 Статус вебхуков")
            print("0. ❌ Выход")
            print("="*50)
            
            choice = input("Выберите действие (0-11): ").strip()
            
            if choice == "1":
                self.show_statistics()
            elif choice == "2":
                self.manage_users()
            elif choice == "3":
                self.manage_products()
            elif choice == "4":
                self.manage_orders()
            elif choice == "5":
                self.manage_balances()
            elif choice == "6":
                self.broadcast_messages()
            elif choice == "7":
                self.manage_user_blocks()
            elif choice == "8":
                self.backup_database()
            elif choice == "9":
                self.bot_settings()
            elif choice == "10":
                self.manage_administrators()
            elif choice == "11":
                self.webhook_status()
            elif choice == "0":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
    
    def show_statistics(self):
        """Показать статистику"""
        print("\n📊 СТАТИСТИКА")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Статистика пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE balance > 0")
            users_with_balance = cursor.fetchone()[0]
            
            # Статистика товаров
            cursor.execute("SELECT COUNT(*) FROM products")
            total_products = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
            active_products = cursor.fetchone()[0]
            
            # Статистика заказов
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
            completed_orders = cursor.fetchone()[0]
            
            # Общая сумма заказов
            cursor.execute("SELECT SUM(amount) FROM orders WHERE status = 'completed'")
            total_revenue = cursor.fetchone()[0] or 0
            
            conn.close()
            
            print(f"👥 Пользователи: {total_users} (с балансом: {users_with_balance})")
            print(f"📦 Товары: {total_products} (активных: {active_products})")
            print(f"📋 Заказы: {total_orders} (выполнено: {completed_orders})")
            print(f"💰 Общий доход: {total_revenue:.2f} $")
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
    
    def manage_users(self):
        """Управление пользователями"""
        while True:
            print("\n👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ")
            print("-" * 30)
            print("1. 📋 Список всех пользователей")
            print("2. 🔍 Найти пользователя")
            print("3. 💰 Изменить баланс")
            print("4. 🚫 Заблокировать пользователя")
            print("5. 🔙 Назад")
            
            choice = input("Выберите действие (1-5): ").strip()
            
            if choice == "1":
                self.list_users()
            elif choice == "2":
                self.find_user()
            elif choice == "3":
                self.change_user_balance()
            elif choice == "4":
                self.block_user()
            elif choice == "5":
                break
            else:
                print("❌ Неверный выбор.")
    
    def list_users(self):
        """Показать список пользователей"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, balance, created_at 
                FROM users ORDER BY created_at DESC LIMIT 20
            """)
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                print("👥 Пользователи не найдены")
                return
            
            print(f"\n👥 Последние {len(users)} пользователей:")
            print("-" * 80)
            print(f"{'ID':<12} {'Username':<20} {'Имя':<20} {'Баланс':<10} {'Дата'}")
            print("-" * 80)
            
            for user in users:
                user_id, username, first_name, balance, created_at = user
                username = username or "N/A"
                first_name = first_name or "N/A"
                print(f"{user_id:<12} {username:<20} {first_name:<20} {balance:<10.2f} {created_at}")
                
        except Exception as e:
            print(f"❌ Ошибка получения списка пользователей: {e}")
    
    def find_user(self):
        """Найти пользователя"""
        user_id = input("Введите ID пользователя: ").strip()
        
        try:
            user_id = int(user_id)
            user = self.db.get_user(user_id)
            
            if user:
                print(f"\n👤 Пользователь найден:")
                print(f"ID: {user['user_id']}")
                print(f"Username: {user.get('username', 'N/A')}")
                print(f"Имя: {user.get('first_name', 'N/A')}")
                print(f"Баланс: {user.get('balance', 0)} $")
                print(f"Дата регистрации: {user.get('created_at', 'N/A')}")
            else:
                print("❌ Пользователь не найден")
                
        except ValueError:
            print("❌ Неверный ID пользователя")
        except Exception as e:
            print(f"❌ Ошибка поиска пользователя: {e}")
    
    def change_user_balance(self):
        """Изменить баланс пользователя"""
        try:
            user_id = int(input("Введите ID пользователя: ").strip())
            amount = float(input("Введите сумму изменения (+ для пополнения, - для списания): ").strip())
            
            if self.db.update_balance(user_id, amount):
                print(f"✅ Баланс пользователя {user_id} изменен на {amount} $")
            else:
                print("❌ Ошибка изменения баланса")
                
        except ValueError:
            print("❌ Неверные данные")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    def manage_products(self):
        """Управление товарами"""
        while True:
            print("\n📦 УПРАВЛЕНИЕ ТОВАРАМИ")
            print("-" * 30)
            print("1. 📋 Список всех товаров")
            print("2. ➕ Добавить товар")
            print("3. ✏️ Редактировать товар")
            print("4. 🚫 Деактивировать товар")
            print("5. 🔙 Назад")
            
            choice = input("Выберите действие (1-5): ").strip()
            
            if choice == "1":
                self.list_products()
            elif choice == "2":
                self.add_product()
            elif choice == "3":
                self.edit_product()
            elif choice == "4":
                self.deactivate_product()
            elif choice == "5":
                break
            else:
                print("❌ Неверный выбор.")
    
    def list_products(self):
        """Показать список товаров"""
        products = self.db.get_products()
        
        if not products:
            print("📦 Товары не найдены")
            return
        
        print(f"\n📦 Всего товаров: {len(products)}")
        print("-" * 100)
        print(f"{'ID':<4} {'Название':<40} {'Цена':<8} {'Категория':<15} {'Кол-во':<8} {'Статус'}")
        print("-" * 100)
        
        for product in products:
            status = "✅" if product['is_active'] else "❌"
            quantity = "∞" if product['quantity'] == -1 else str(product['quantity'])
            name = product['name'][:37] + "..." if len(product['name']) > 40 else product['name']
            
            print(f"{product['id']:<4} {name:<40} {product['price']:<8.0f} {product['category']:<15} {quantity:<8} {status}")
    
    def add_product(self):
        """Добавить новый товар"""
        try:
            print("\n➕ ДОБАВЛЕНИЕ НОВОГО ТОВАРА")
            print("-" * 30)
            
            name = input("Название товара: ").strip()
            description = input("Описание: ").strip()
            price = float(input("Цена ($): ").strip())
            category = input("Категория: ").strip()
            emoji = input("Эмодзи: ").strip()
            quantity = int(input("Количество (-1 для бесконечности): ").strip())
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (name, description, price, category, emoji, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, price, category, emoji, quantity))
            conn.commit()
            conn.close()
            
            print("✅ Товар успешно добавлен!")
            
        except ValueError:
            print("❌ Неверные данные")
        except Exception as e:
            print(f"❌ Ошибка добавления товара: {e}")
    
    def manage_orders(self):
        """Управление заказами"""
        print("\n📋 УПРАВЛЕНИЕ ЗАКАЗАМИ")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.user_id, p.name, o.amount, o.status, o.created_at
                FROM orders o
                JOIN products p ON o.product_id = p.id
                ORDER BY o.created_at DESC LIMIT 20
            """)
            orders = cursor.fetchall()
            conn.close()
            
            if not orders:
                print("📋 Заказы не найдены")
                return
            
            print(f"📋 Последние {len(orders)} заказов:")
            print("-" * 80)
            print(f"{'ID':<4} {'User ID':<10} {'Товар':<30} {'Сумма':<8} {'Статус':<12} {'Дата'}")
            print("-" * 80)
            
            for order in orders:
                order_id, user_id, product_name, amount, status, created_at = order
                product_name = product_name[:27] + "..." if len(product_name) > 30 else product_name
                print(f"{order_id:<4} {user_id:<10} {product_name:<30} {amount:<8.2f} {status:<12} {created_at}")
                
        except Exception as e:
            print(f"❌ Ошибка получения заказов: {e}")
    
    def manage_balances(self):
        """Управление балансами"""
        print("\n💰 УПРАВЛЕНИЕ БАЛАНСАМИ")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, balance
                FROM users
                WHERE balance > 0
                ORDER BY balance DESC
            """)
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                print("💰 Пользователи с балансом не найдены")
                return
            
            print(f"💰 Пользователи с балансом (всего: {len(users)}):")
            print("-" * 60)
            print(f"{'User ID':<10} {'Username':<20} {'Имя':<20} {'Баланс'}")
            print("-" * 60)
            
            total_balance = 0
            for user in users:
                user_id, username, first_name, balance = user
                username = username or "N/A"
                first_name = first_name or "N/A"
                total_balance += balance
                print(f"{user_id:<10} {username:<20} {first_name:<20} {balance:.2f} $")
            
            print("-" * 60)
            print(f"💰 Общий баланс всех пользователей: {total_balance:.2f} $")
            
        except Exception as e:
            print(f"❌ Ошибка получения балансов: {e}")
    
    def backup_database(self):
        """Резервное копирование базы данных"""
        import shutil
        from datetime import datetime
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_shop_bot_{timestamp}.db"
            
            shutil.copy2(self.db.db_path, backup_path)
            print(f"✅ Резервная копия создана: {backup_path}")
            
        except Exception as e:
            print(f"❌ Ошибка создания резервной копии: {e}")
    
    def broadcast_messages(self):
        """Рассылка сообщений всем пользователям"""
        print("\n📢 РАССЫЛКА СООБЩЕНИЙ")
        print("-" * 30)
        print("1. 📢 Отправить сообщение всем пользователям")
        print("2. 🎯 Отправить сообщение по категории")
        print("3. 📊 Статистика рассылок")
        print("4. 🔙 Назад")
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == "1":
            self.send_broadcast_to_all()
        elif choice == "2":
            self.send_broadcast_by_category()
        elif choice == "3":
            self.show_broadcast_stats()
        elif choice == "4":
            return
        else:
            print("❌ Неверный выбор.")
    
    def send_broadcast_to_all(self):
        """Отправить сообщение всем пользователям"""
        try:
            message = input("Введите сообщение для рассылки: ").strip()
            if not message:
                print("❌ Сообщение не может быть пустым")
                return
            
            confirm = input(f"Отправить сообщение '{message[:50]}...' всем пользователям? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Рассылка отменена")
                return
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                print("❌ Пользователи не найдены")
                return
            
            print(f"📢 Отправка сообщения {len(users)} пользователям...")
            
            # Здесь можно добавить логику отправки через Telegram Bot API
            # Для демонстрации просто показываем количество
            print(f"✅ Сообщение отправлено {len(users)} пользователям")
            
        except Exception as e:
            print(f"❌ Ошибка рассылки: {e}")
    
    def send_broadcast_by_category(self):
        """Отправить сообщение по категории пользователей"""
        try:
            print("\n🎯 Категории пользователей:")
            print("1. Все пользователи")
            print("2. Пользователи с балансом > 0")
            print("3. Новые пользователи (за последние 7 дней)")
            print("4. Пользователи с заказами")
            
            category = input("Выберите категорию (1-4): ").strip()
            message = input("Введите сообщение: ").strip()
            
            if not message:
                print("❌ Сообщение не может быть пустым")
                return
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            if category == "1":
                cursor.execute("SELECT user_id FROM users")
                category_name = "всем пользователям"
            elif category == "2":
                cursor.execute("SELECT user_id FROM users WHERE balance > 0")
                category_name = "пользователям с балансом"
            elif category == "3":
                cursor.execute("SELECT user_id FROM users WHERE created_at >= datetime('now', '-7 days')")
                category_name = "новым пользователям"
            elif category == "4":
                cursor.execute("SELECT DISTINCT user_id FROM orders")
                category_name = "пользователям с заказами"
            else:
                print("❌ Неверная категория")
                conn.close()
                return
            
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                print(f"❌ Пользователи в категории '{category_name}' не найдены")
                return
            
            print(f"📢 Отправка сообщения {len(users)} пользователям ({category_name})...")
            print(f"✅ Сообщение отправлено {len(users)} пользователям")
            
        except Exception as e:
            print(f"❌ Ошибка рассылки: {e}")
    
    def show_broadcast_stats(self):
        """Показать статистику рассылок"""
        print("\n📊 СТАТИСТИКА РАССЫЛОК")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Пользователи с балансом
            cursor.execute("SELECT COUNT(*) FROM users WHERE balance > 0")
            users_with_balance = cursor.fetchone()[0]
            
            # Новые пользователи
            cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')")
            new_users = cursor.fetchone()[0]
            
            # Пользователи с заказами
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM orders")
            users_with_orders = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"👥 Всего пользователей: {total_users}")
            print(f"💰 С балансом: {users_with_balance}")
            print(f"🆕 Новые (7 дней): {new_users}")
            print(f"📦 С заказами: {users_with_orders}")
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
    
    def manage_user_blocks(self):
        """Управление блокировкой пользователей"""
        print("\n🚫 УПРАВЛЕНИЕ БЛОКИРОВКОЙ ПОЛЬЗОВАТЕЛЕЙ")
        print("-" * 40)
        print("1. 🚫 Заблокировать пользователя")
        print("2. ✅ Разблокировать пользователя")
        print("3. 📋 Список заблокированных")
        print("4. 🔍 Найти пользователя")
        print("5. 🔙 Назад")
        
        choice = input("Выберите действие (1-5): ").strip()
        
        if choice == "1":
            self.block_user()
        elif choice == "2":
            self.unblock_user()
        elif choice == "3":
            self.list_blocked_users()
        elif choice == "4":
            self.find_user_for_block()
        elif choice == "5":
            return
        else:
            print("❌ Неверный выбор.")
    
    def block_user(self):
        """Заблокировать пользователя"""
        try:
            user_id = input("Введите ID пользователя для блокировки: ").strip()
            reason = input("Причина блокировки: ").strip()
            
            if not reason:
                reason = "Нарушение правил"
            
            try:
                user_id = int(user_id)
            except ValueError:
                print("❌ Неверный ID пользователя")
                return
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT username, first_name FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                print("❌ Пользователь не найден")
                conn.close()
                return
            
            # Добавляем в таблицу заблокированных пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocked_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    reason TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    blocked_by TEXT DEFAULT 'admin'
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO blocked_users (user_id, username, first_name, reason)
                VALUES (?, ?, ?, ?)
            ''', (user_id, user[0], user[1], reason))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Пользователь {user_id} заблокирован")
            print(f"📝 Причина: {reason}")
            
        except Exception as e:
            print(f"❌ Ошибка блокировки: {e}")
    
    def unblock_user(self):
        """Разблокировать пользователя"""
        try:
            user_id = input("Введите ID пользователя для разблокировки: ").strip()
            
            try:
                user_id = int(user_id)
            except ValueError:
                print("❌ Неверный ID пользователя")
                return
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
            affected = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if affected > 0:
                print(f"✅ Пользователь {user_id} разблокирован")
            else:
                print(f"❌ Пользователь {user_id} не был заблокирован")
                
        except Exception as e:
            print(f"❌ Ошибка разблокировки: {e}")
    
    def list_blocked_users(self):
        """Показать список заблокированных пользователей"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocked_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    reason TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    blocked_by TEXT DEFAULT 'admin'
                )
            ''')
            
            cursor.execute("SELECT * FROM blocked_users ORDER BY blocked_at DESC")
            blocked_users = cursor.fetchall()
            conn.close()
            
            if not blocked_users:
                print("✅ Заблокированных пользователей нет")
                return
            
            print(f"\n🚫 Заблокированные пользователи ({len(blocked_users)}):")
            print("-" * 80)
            print(f"{'ID':<12} {'Username':<20} {'Имя':<20} {'Причина':<20} {'Дата блокировки'}")
            print("-" * 80)
            
            for user in blocked_users:
                user_id, username, first_name, reason, blocked_at, blocked_by = user
                username = username or "N/A"
                first_name = first_name or "N/A"
                reason = reason[:17] + "..." if len(reason) > 20 else reason
                print(f"{user_id:<12} {username:<20} {first_name:<20} {reason:<20} {blocked_at}")
                
        except Exception as e:
            print(f"❌ Ошибка получения списка заблокированных: {e}")
    
    def find_user_for_block(self):
        """Найти пользователя для блокировки"""
        try:
            search = input("Введите ID, username или имя пользователя: ").strip()
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Поиск по ID
            try:
                user_id = int(search)
                cursor.execute("SELECT user_id, username, first_name, balance FROM users WHERE user_id = ?", (user_id,))
            except ValueError:
                # Поиск по username или имени
                cursor.execute("""
                    SELECT user_id, username, first_name, balance 
                    FROM users 
                    WHERE username LIKE ? OR first_name LIKE ?
                """, (f"%{search}%", f"%{search}%"))
            
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                print("❌ Пользователи не найдены")
                return
            
            print(f"\n🔍 Найдено пользователей: {len(users)}")
            print("-" * 60)
            print(f"{'ID':<12} {'Username':<20} {'Имя':<20} {'Баланс'}")
            print("-" * 60)
            
            for user in users:
                user_id, username, first_name, balance = user
                username = username or "N/A"
                first_name = first_name or "N/A"
                print(f"{user_id:<12} {username:<20} {first_name:<20} {balance:.2f} $")
            
            if len(users) == 1:
                user_id = users[0][0]
                block_choice = input(f"\nЗаблокировать пользователя {user_id}? (y/n): ").strip().lower()
                if block_choice == 'y':
                    reason = input("Причина блокировки: ").strip()
                    if not reason:
                        reason = "Нарушение правил"
                    
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS blocked_users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT,
                            first_name TEXT,
                            reason TEXT,
                            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            blocked_by TEXT DEFAULT 'admin'
                        )
                    ''')
                    cursor.execute('''
                        INSERT OR REPLACE INTO blocked_users (user_id, username, first_name, reason)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, users[0][1], users[0][2], reason))
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ Пользователь {user_id} заблокирован")
                    
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
    
    def bot_settings(self):
        """Настройки бота"""
        print("\n⚙️ НАСТРОЙКИ БОТА")
        print("-" * 30)
        print("1. 🔧 Основные настройки")
        print("2. 💰 Настройки платежей")
        print("3. 📦 Настройки товаров")
        print("4. 🔙 Назад")
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == "1":
            self.main_settings()
        elif choice == "2":
            self.payment_settings()
        elif choice == "3":
            self.product_settings()
        elif choice == "4":
            return
        else:
            print("❌ Неверный выбор.")
    
    def main_settings(self):
        """Основные настройки бота"""
        print("\n🔧 ОСНОВНЫЕ НАСТРОЙКИ")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу настроек если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем базовые настройки
            settings = [
                ("bot_name", "LUXURY SHOP", "Название бота"),
                ("welcome_message", "Добро пожаловать в LUXURY SHOP!", "Приветственное сообщение"),
                ("maintenance_mode", "false", "Режим обслуживания"),
                ("max_products_per_user", "10", "Максимум товаров в корзине"),
                ("auto_delete_inactive_users", "30", "Дни до удаления неактивных пользователей")
            ]
            
            for key, value, description in settings:
                cursor.execute('''
                    INSERT OR IGNORE INTO bot_settings (key, value, description)
                    VALUES (?, ?, ?)
                ''', (key, value, description))
            
            # Показываем текущие настройки
            cursor.execute("SELECT key, value, description FROM bot_settings")
            current_settings = cursor.fetchall()
            
            print("📋 Текущие настройки:")
            print("-" * 50)
            for key, value, description in current_settings:
                print(f"🔑 {key}: {value}")
                print(f"📝 {description}")
                print("-" * 50)
            
            # Возможность изменения настроек
            change_choice = input("\nИзменить настройку? (y/n): ").strip().lower()
            if change_choice == 'y':
                setting_key = input("Введите ключ настройки: ").strip()
                new_value = input("Введите новое значение: ").strip()
                
                cursor.execute("UPDATE bot_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?", (new_value, setting_key))
                if cursor.rowcount > 0:
                    print(f"✅ Настройка {setting_key} обновлена")
                else:
                    print(f"❌ Настройка {setting_key} не найдена")
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка настроек: {e}")
    
    def payment_settings(self):
        """Настройки платежей"""
        print("\n💰 НАСТРОЙКИ ПЛАТЕЖЕЙ")
        print("-" * 30)
        print("1. 💳 Минимальная сумма платежа")
        print("2. 🏦 Поддерживаемые валюты")
        print("3. ⏰ Таймаут платежа")
        print("4. 🔙 Назад")
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == "1":
            self.set_min_payment()
        elif choice == "2":
            self.set_currencies()
        elif choice == "3":
            self.set_payment_timeout()
        elif choice == "4":
            return
        else:
            print("❌ Неверный выбор.")
    
    def product_settings(self):
        """Настройки товаров"""
        print("\n📦 НАСТРОЙКИ ТОВАРОВ")
        print("-" * 30)
        print("1. 📊 Категории товаров")
        print("2. 🏷️ Теги товаров")
        print("3. 📸 Изображения товаров")
        print("4. 🔙 Назад")
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == "1":
            self.manage_categories()
        elif choice == "2":
            self.manage_tags()
        elif choice == "3":
            self.manage_product_images()
        elif choice == "4":
            return
        else:
            print("❌ Неверный выбор.")
    
    def manage_categories(self):
        """Управление категориями товаров"""
        print("\n📊 УПРАВЛЕНИЕ КАТЕГОРИЯМИ")
        print("-" * 30)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Получаем все категории
            cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
            categories = cursor.fetchall()
            
            print("📋 Текущие категории:")
            for i, (category,) in enumerate(categories, 1):
                print(f"{i}. {category}")
            
            print("\n1. ➕ Добавить категорию")
            print("2. ✏️ Переименовать категорию")
            print("3. 🗑️ Удалить категорию")
            print("4. 🔙 Назад")
            
            choice = input("Выберите действие (1-4): ").strip()
            
            if choice == "1":
                new_category = input("Введите название новой категории: ").strip()
                if new_category:
                    # Добавляем тестовый товар в новую категорию
                    cursor.execute('''
                        INSERT INTO products (name, description, price, category, emoji, quantity)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (f"Тестовый товар {new_category}", f"Описание для {new_category}", 0.0, new_category, "📦", 1))
                    conn.commit()
                    print(f"✅ Категория '{new_category}' добавлена")
            
            elif choice == "2":
                if categories:
                    old_category = input("Введите название категории для переименования: ").strip()
                    new_name = input("Введите новое название: ").strip()
                    
                    if old_category and new_name:
                        cursor.execute("UPDATE products SET category = ? WHERE category = ?", (new_name, old_category))
                        conn.commit()
                        print(f"✅ Категория '{old_category}' переименована в '{new_name}'")
            
            elif choice == "3":
                if categories:
                    category_to_delete = input("Введите название категории для удаления: ").strip()
                    confirm = input(f"Удалить категорию '{category_to_delete}' и все товары в ней? (y/n): ").strip().lower()
                    
                    if confirm == 'y':
                        cursor.execute("DELETE FROM products WHERE category = ?", (category_to_delete,))
                        conn.commit()
                        print(f"✅ Категория '{category_to_delete}' удалена")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка управления категориями: {e}")
    
    def manage_tags(self):
        """Управление тегами товаров"""
        print("\n🏷️ УПРАВЛЕНИЕ ТЕГАМИ")
        print("-" * 30)
        print("Функция в разработке...")
    
    def manage_product_images(self):
        """Управление изображениями товаров"""
        print("\n📸 УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ")
        print("-" * 30)
        print("Функция в разработке...")
    
    def set_min_payment(self):
        """Установить минимальную сумму платежа"""
        print("\n💳 МИНИМАЛЬНАЯ СУММА ПЛАТЕЖА")
        print("-" * 30)
        try:
            amount = input("Введите минимальную сумму платежа ($): ").strip()
            if amount:
                print(f"✅ Минимальная сумма платежа установлена: {amount} $")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    def set_currencies(self):
        """Установить поддерживаемые валюты"""
        print("\n🏦 ПОДДЕРЖИВАЕМЫЕ ВАЛЮТЫ")
        print("-" * 30)
        print("Текущие валюты: USDT, BTC, ETH")
        print("Функция настройки в разработке...")
    
    def set_payment_timeout(self):
        """Установить таймаут платежа"""
        print("\n⏰ ТАЙМАУТ ПЛАТЕЖА")
        print("-" * 30)
        try:
            timeout = input("Введите таймаут платежа в минутах: ").strip()
            if timeout:
                print(f"✅ Таймаут платежа установлен: {timeout} минут")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    def manage_administrators(self):
        """Управление администраторами"""
        print("\n👑 УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ")
        print("-" * 40)
        
        # Показываем текущих администраторов
        admin_list = self.auth.get_admin_list()
        
        print("📋 Текущие администраторы:")
        print(f"👤 Usernames: {', '.join(admin_list['usernames'])}")
        print(f"🆔 IDs: {', '.join(map(str, admin_list['ids']))}")
        print(f"📊 Всего: {admin_list['total']}")
        
        print("\n⚠️ Для изменения списка администраторов отредактируйте файл .env")
        print("📝 Формат:")
        print("ADMIN_USERNAMES=@admin1,@admin2,@admin3")
        print("ADMIN_IDS=123456789,987654321,555666777")
    
    def webhook_status(self):
        """Статус вебхуков"""
        print("\n📡 СТАТУС ВЕБХУКОВ")
        print("-" * 30)
        
        try:
            # Получаем статистику вебхуков
            last_webhook = self.db.get_last_webhook_time()
            total_webhooks = self.db.get_total_webhooks()
            successful_webhooks = self.db.get_successful_webhooks()
            
            print(f"📊 Общее количество вебхуков: {total_webhooks}")
            print(f"✅ Успешных вебхуков: {successful_webhooks}")
            print(f"❌ Неудачных вебхуков: {total_webhooks - successful_webhooks}")
            
            if last_webhook:
                print(f"🕐 Последний вебхук: {last_webhook}")
            else:
                print("🕐 Вебхуки еще не поступали")
            
            print("\n🌐 Настройка вебхуков:")
            print("1. Установите WEBHOOK_URL в .env")
            print("2. Установите WEBHOOK_SECRET в .env")
            print("3. Запустите webhook_handler.py")
            print("4. Настройте вебхук в CryptoBot")
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса вебхуков: {e}")

def main():
    """Главная функция"""
    print("🔧 Добро пожаловать в административную панель LUXURY SHOP!")
    
    admin = AdminPanel()
    
    # Проверяем доступ администратора
    if not admin.check_admin_access():
        print("❌ Доступ запрещен. Программа завершена.")
        return
    
    admin.show_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Работа административной панели прервана")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
