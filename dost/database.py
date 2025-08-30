import sqlite3
import datetime
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                product TEXT NOT NULL,
                packaging TEXT NOT NULL,
                address TEXT NOT NULL,
                delivery_time INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new'
            )
        ''')
        
        # Создаем таблицу для ручных ответов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_message TEXT NOT NULL,
                response_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Автовосстановление таблицы users из заказов, если она пуста
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        if users_count == 0:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username)
                    SELECT DISTINCT user_id, username
                    FROM orders
                    WHERE user_id IS NOT NULL
                ''')
            except Exception:
                pass

        conn.commit()
        conn.close()
    
    def add_order(self, user_id, username, product, packaging, address, delivery_time):
        """Добавление нового заказа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (user_id, username, product, packaging, address, delivery_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, product, packaging, address, delivery_time))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return order_id
    
    def get_orders(self, limit=50):
        """Получение списка заказов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders ORDER BY order_date DESC LIMIT ?
        ''', (limit,))
        
        orders = cursor.fetchall()
        conn.close()
        
        return orders
    
    def get_user_orders(self, user_id):
        """Получение заказов конкретного пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC
        ''', (user_id,))
        
        orders = cursor.fetchall()
        conn.close()
        
        return orders
    
    def add_admin_response(self, user_id, admin_message):
        """Добавление ответа администратора"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO admin_responses (user_id, admin_message)
            VALUES (?, ?)
        ''', (user_id, admin_message))
        
        conn.commit()
        conn.close()
    
    def get_order_stats(self):
        """Получение статистики заказов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество заказов
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        # Заказы за сегодня
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE DATE(order_date) = DATE('now')
        ''')
        today_orders = cursor.fetchone()[0]
        
        # Заказы за неделю
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE order_date >= datetime('now', '-7 days')
        ''')
        week_orders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_orders,
            'today': today_orders,
            'week': week_orders
        } 

    def track_user(self, user_id: int, username: str | None):
        """Добавление/обновление пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_seen=CURRENT_TIMESTAMP
        ''', (user_id, username))
        conn.commit()
        conn.close()

    def get_user_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_user_ids(self) -> list[int]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]