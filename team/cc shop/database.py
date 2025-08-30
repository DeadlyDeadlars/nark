import sqlite3
import json
import random
from datetime import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = "shop_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                language TEXT DEFAULT 'ru'
            )
        ''')
        
        # Таблица товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                emoji TEXT,
                quantity INTEGER DEFAULT -1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unit_price REAL,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Таблица избранных товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (product_id),
                UNIQUE(user_id, product_id)
            )
        ''')
        
        # Таблица для логов вебхуков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_type TEXT NOT NULL,
                payload TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')
        
        # Таблица для выдачи товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                product_id INTEGER,
                delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivery_method TEXT DEFAULT 'manual',
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Таблица стран
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                flag TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Таблица BIN'ов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER,
                bin_number TEXT NOT NULL,
                bank_name TEXT,
                card_type TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (country_id) REFERENCES countries (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Проверяем и добавляем недостающие колонки
        self.migrate_database()
        
        # Добавляем начальные товары
        self.add_initial_products()
        
        # Добавляем страны и BIN'ы
        self.add_countries_and_bins()
        
        # Запускаем автоматическое обновление BIN'ов
        self.refresh_bins_daily()
    
    def initialize_bins_if_empty(self):
        """Инициализация BIN'ов если таблица пуста"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже BIN'ы
            cursor.execute('SELECT COUNT(*) FROM bins')
            bins_count = cursor.fetchone()[0]
            
            if bins_count == 0:
                print("🔄 Инициализация BIN'ов...")
                self.generate_random_bins_for_all_countries()
                print("✅ BIN'ы инициализированы!")
            else:
                print(f"✅ BIN'ы уже существуют: {bins_count} записей")
            
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка инициализации BIN'ов: {e}")
    
    def add_initial_products(self):
        """Добавление начальных товаров в магазин"""
        products = [
            # CHEAP MANUALS
            ("Мануал по работе с ба", "Подробное руководство по работе с ба - обучение до профита", 300.0, "CHEAP MANUALS", "📖", -1),
            ("Мануал по работе с Crypto.com + бины", "Руководство по Crypto.com с бинами - обучение до профита", 200.0, "CHEAP MANUALS", "💵", -1),
            ("Мануал по работе с Coinbase", "Руководство по Coinbase - обучение до профита", 200.0, "CHEAP MANUALS", "🏧", -1),
            ("Мануал по работе с goat.com", "Руководство по goat.com - обучение до профита", 100.0, "CHEAP MANUALS", "👟", -1),
            ("Мануал по работе с гифтами", "Руководство по работе с гифтами - обучение до профита", 90.0, "CHEAP MANUALS", "🎁", -1),
            ("Мануал по работе с Enroll", "Руководство по Enroll - обучение до профита", 90.0, "CHEAP MANUALS", "📝", -1),
            
            # CHEAP MERCHANT
            ("2d shop electric USA/CA", "2d магазин электрики США/Канада", 200.0, "CHEAP MERCHANT", "⚡", -1),
            ("2d merch casino KYC CRYPTO", "2d мерч казино с KYC", 100.0, "CHEAP MERCHANT", "🎰", -1),
            ("3d btc merch", "3d мерч для Bitcoin", 220.0, "CHEAP MERCHANT", "₿", -1),
            ("2d shop jewelry", "2d магазин ювелирных изделий", 100.0, "CHEAP MERCHANT", "💎", -1),
            ("2d merchant for Apple", "2d мерчант для Apple", 100.0, "CHEAP MERCHANT", "🍎", -1),
            
            # Обучение
            ("Обучение (Минимальный вариант)", "Базовое обучение до профита", 299.0, "Обучение", "📚", -1),
            ("Обучение (Полный вариант)", "Полное обучение до профита", 1666.0, "Обучение", "🎓", -1),
            ("Обучение (LUXURY VERSION)", "Luxury версия обучения до профита", 4999.0, "Обучение", "👑", -1),
            
            # MANUALS
            ("Статья/мануал под заказ", "Индивидуальный мануал - обучение до профита", 500.0, "MANUALS", "📋", -1),
            ("Мануал по Tax Refund", "Руководство по налоговому возврату - обучение до профита", 200.0, "MANUALS", "💰", -1),
            ("Мануал по работе с Interac и канадскими банками", "Руководство по Interac и банкам Канады - обучение до профита", 999.0, "MANUALS", "🏦", -1),
            ("Мануал как заливать в самореги ба", "Руководство по пополнению саморегов - обучение до профита", 400.0, "MANUALS", "💳", -1),
            ("Мануал по открытию кредитки на фуллки US/Канады", "Руководство по кредитным картам - обучение до профита", 400.0, "MANUALS", "💳", -1),
            ("Мануал по работе с чеками США", "Руководство по чекам США - обучение до профита", 600.0, "MANUALS", "🧾", -1),
            ("Мануал по работе с банковскими логами США", "Руководство по банковским логам - обучение до профита", 600.0, "MANUALS", "🏛️", -1),
            ("Мануал по открытию саморегов ба", "Руководство по открытию саморегов - обучение до профита", 500.0, "MANUALS", "🏦", -1),
            ("Мануал по работе с дампами", "Руководство по дампам - обучение до профита", 650.0, "MANUALS", "💾", -1),
            
            # MERCHANT
            ("2d merch casino NO KYC CRYPTO", "2d мерч казино без KYC", 333.0, "MERCHANT", "🎰", -1),
            ("POS Terminal на iPhone под заказ", "POS терминал для iPhone", 777.0, "MERCHANT", "📱", -1),
            ("Контора под Apple Pay и дебетки", "Контора для Apple Pay и дебетовых карт", 390.0, "MERCHANT", "🍎", -1),
            
            # CC
            ("GOOD QUALITY SPAM CC`s", "Качественные спам CC", 25.0, "CC", "📱", -1),
            ("VHQ SNIFFER CC`s", "VHQ сниффер CC", 30.0, "CC", "✅", -1),
            ("VHQ BASE RICH", "VHQ база богатых", 35.0, "CC", "🔥", -1),
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сначала удаляем все существующие товары
        cursor.execute('DELETE FROM products')
        
        for product in products:
            cursor.execute('''
                INSERT OR IGNORE INTO products (name, description, price, category, emoji, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', product)
        
        conn.commit()
        conn.close()
    
    def add_countries_and_bins(self):
        """Добавление стран и BIN'ов"""
        countries = [
            ("UNITED STATES", "US", "🇺🇸"),
            ("UNITED ARAB EMIRATES", "AE", "🇦🇪"),
            ("ALBANIA", "AL", "🇦🇱"),
            ("AUSTRIA", "AT", "🇦🇹"),
            ("BANGLADESH", "BD", "🇧🇩"),
            ("BULGARIA", "BG", "🇧🇬"),
            ("BENIN", "BJ", "🇧🇯"),
            ("BRAZIL", "BR", "🇧🇷"),
            ("CANADA", "CA", "🇨🇦"),
            ("CONGO", "CG", "🇨🇬"),
            ("CÔTE D'IVOIRE", "CI", "🇨🇮"),
            ("ANTIGUA AND BARBUDA", "AG", "🇦🇬"),
            ("ARGENTINA", "AR", "🇦🇷"),
            ("AUSTRALIA", "AU", "🇦🇺"),
            ("BELGIUM", "BE", "🇧🇪"),
            ("BAHRAIN", "BH", "🇧🇭"),
            ("BOLIVIA", "BO", "🇧🇴"),
            ("BOTSWANA", "BW", "🇧🇼"),
            ("CONGO, DEMOCRATIC REPUBLIC", "CD", "🇨🇩"),
            ("SWITZERLAND", "CH", "🇨🇭"),
            ("CHILE", "CL", "🇨🇱"),
            ("CHINA", "CN", "🇨🇳"),
            ("COLOMBIA", "CO", "🇨🇴"),
            ("COSTA RICA", "CR", "🇨🇷"),
            ("CUBA", "CU", "🇨🇺"),
            ("CYPRUS", "CY", "🇨🇾"),
            ("CZECH REPUBLIC", "CZ", "🇨🇿"),
            ("GERMANY", "DE", "🇩🇪"),
            ("DENMARK", "DK", "🇩🇰"),
            ("DOMINICAN REPUBLIC", "DO", "🇩🇴"),
            ("ALGERIA", "DZ", "🇩🇿"),
            ("ECUADOR", "EC", "🇪🇨"),
            ("ESTONIA", "EE", "🇪🇪"),
            ("EGYPT", "EG", "🇪🇬"),
            ("SPAIN", "ES", "🇪🇸"),
            ("FINLAND", "FI", "🇫🇮"),
            ("FRANCE", "FR", "🇫🇷"),
            ("UNITED KINGDOM", "GB", "🇬🇧"),
            ("GEORGIA", "GE", "🇬🇪"),
            ("GHANA", "GH", "🇬🇭"),
            ("GREECE", "GR", "🇬🇷"),
            ("HONG KONG", "HK", "🇭🇰"),
            ("CROATIA", "HR", "🇭🇷"),
            ("HUNGARY", "HU", "🇭🇺"),
            ("INDONESIA", "ID", "🇮🇩"),
            ("IRELAND", "IE", "🇮🇪"),
            ("ISRAEL", "IL", "🇮🇱"),
            ("INDIA", "IN", "🇮🇳"),
            ("IRAQ", "IQ", "🇮🇶"),
            ("IRAN", "IR", "🇮🇷"),
            ("ICELAND", "IS", "🇮🇸"),
            ("ITALY", "IT", "🇮🇹"),
            ("JAMAICA", "JM", "🇯🇲"),
            ("JORDAN", "JO", "🇯🇴"),
            ("JAPAN", "JP", "🇯🇵"),
            ("KENYA", "KE", "🇰🇪"),
            ("KYRGYZSTAN", "KG", "🇰🇬"),
            ("CAMBODIA", "KH", "🇰🇭"),
            ("SOUTH KOREA", "KR", "🇰🇷"),
            ("KAZAKHSTAN", "KZ", "🇰🇿"),
            ("LEBANON", "LB", "🇱🇧"),
            ("LIBYA", "LY", "🇱🇾"),
            ("MOROCCO", "MA", "🇲🇦"),
            ("MOLDOVA", "MD", "🇲🇩"),
            ("MONTENEGRO", "ME", "🇲🇪"),
            ("MADAGASCAR", "MG", "🇲🇬"),
            ("MACEDONIA", "MK", "🇲🇰"),
            ("MALI", "ML", "🇲🇱"),
            ("MONGOLIA", "MN", "🇲🇳"),
            ("MEXICO", "MX", "🇲🇽"),
            ("MALAYSIA", "MY", "🇲🇾"),
            ("NIGERIA", "NG", "🇳🇬"),
            ("NETHERLANDS", "NL", "🇳🇱"),
            ("NORWAY", "NO", "🇳🇴"),
            ("NEPAL", "NP", "🇳🇵"),
            ("NEW ZEALAND", "NZ", "🇳🇿"),
            ("OMAN", "OM", "🇴🇲"),
            ("PANAMA", "PA", "🇵🇦"),
            ("PERU", "PE", "🇵🇪"),
            ("PHILIPPINES", "PH", "🇵🇭"),
            ("PAKISTAN", "PK", "🇵🇰"),
            ("POLAND", "PL", "🇵🇱"),
            ("PORTUGAL", "PT", "🇵🇹"),
            ("PARAGUAY", "PY", "🇵🇾"),
            ("QATAR", "QA", "🇶🇦"),
            ("ROMANIA", "RO", "🇷🇴"),
            ("SERBIA", "RS", "🇷🇸"),
            ("RUSSIA", "RU", "🇷🇺"),
            ("RWANDA", "RW", "🇷🇼"),
            ("SAUDI ARABIA", "SA", "🇸🇦"),
            ("SINGAPORE", "SG", "🇸🇬"),
            ("SLOVAKIA", "SK", "🇸🇰"),
            ("SLOVENIA", "SI", "🇸🇮"),
            ("SOMALIA", "SO", "🇸🇴"),
            ("SOUTH AFRICA", "ZA", "🇿🇦"),
            ("SWEDEN", "SE", "🇸🇪"),
            ("SYRIA", "SY", "🇸🇾"),
            ("THAILAND", "TH", "🇹🇭"),
            ("TUNISIA", "TN", "🇹🇳"),
            ("TURKEY", "TR", "🇹🇷"),
            ("UKRAINE", "UA", "🇺🇦"),
            ("UGANDA", "UG", "🇺🇬"),
            ("URUGUAY", "UY", "🇺🇾"),
            ("UZBEKISTAN", "UZ", "🇺🇿"),
            ("VENEZUELA", "VE", "🇻🇪"),
            ("VIETNAM", "VN", "🇻🇳"),
            ("YEMEN", "YE", "🇾🇪"),
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Добавляем страны
        for country in countries:
            cursor.execute('''
                INSERT OR IGNORE INTO countries (name, code, flag)
                VALUES (?, ?, ?)
            ''', country)
        
        conn.commit()
        conn.close()
        
        # Генерируем рандомные BIN'ы для всех стран
        print("🔄 Генерируем BIN'ы для всех стран...")
        self.generate_random_bins_for_all_countries()
        print("✅ BIN'ы сгенерированы!")
    
    def generate_random_bins_for_all_countries(self):
        """Генерируем рандомные BIN'ы для всех стран"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Очищаем существующие BIN'ы
            cursor.execute('DELETE FROM bins')
            
            # Получаем все активные страны
            cursor.execute('SELECT id, code FROM countries WHERE is_active = 1')
            countries = cursor.fetchall()
            
            # Список типов карт
            card_types = ["Visa", "MasterCard", "American Express", "Discover", "JCB", "UnionPay"]
            
            for country_id, country_code in countries:
                # Генерируем от 5 до 8 BIN'ов для каждой страны
                num_bins = random.randint(5, 8)
                
                for _ in range(num_bins):
                    # Генерируем случайный 6-значный BIN
                    bin_number = str(random.randint(100000, 999999))
                    
                    # Случайный тип карты
                    card_type = random.choice(card_types)
                    
                    cursor.execute('''
                        INSERT INTO bins (country_id, bin_number, bank_name, card_type, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (country_id, bin_number, None, card_type))
            
            conn.commit()
            conn.close()
            print(f"✅ Сгенерировано BIN'ов для {len(countries)} стран")
            
        except Exception as e:
            print(f"❌ Ошибка генерации BIN'ов: {e}")
            if 'conn' in locals():
                conn.close()
    
    def add_country_if_missing(self, name: str, code: str, flag: str) -> bool:
        """Добавляет страну, если её нет, и активирует если выключена. Возвращает True, если была добавлена."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM countries WHERE code = ?', (code,))
            row = cursor.fetchone()
            if row:
                cursor.execute('UPDATE countries SET is_active = 1, name = ?, flag = ? WHERE code = ?', (name, flag, code))
                conn.commit()
                conn.close()
                return False
            cursor.execute('INSERT INTO countries (name, code, flag, is_active) VALUES (?, ?, ?, 1)', (name, code, flag))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error ensuring country {code}: {e}")
            try:
                conn.close()
            except Exception:
                pass
            return False
    
    def generate_bins_for_country(self, country_code: str) -> int:
        """Генерирует BIN'ы только для указанной страны. Возвращает количество созданных BIN'ов."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM countries WHERE code = ? AND is_active = 1', (country_code,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return 0
            country_id = row[0]
            # Удаляем старые BIN'ы страны
            cursor.execute('DELETE FROM bins WHERE country_id = ?', (country_id,))
            card_types = ["Visa", "MasterCard", "American Express", "Discover", "JCB", "UnionPay"]
            created = 0
            num_bins = random.randint(5, 8)
            for _ in range(num_bins):
                bin_number = str(random.randint(100000, 999999))
                bank_name = f"Bank {random.randint(100, 999)}"
                card_type = random.choice(card_types)
                cursor.execute('INSERT INTO bins (country_id, bin_number, bank_name, card_type, is_active) VALUES (?, ?, ?, ?, 1)', (country_id, bin_number, bank_name, card_type))
                created += 1
            conn.commit()
            conn.close()
            return created
        except Exception as e:
            print(f"Error generating bins for {country_code}: {e}")
            try:
                conn.close()
            except Exception:
                pass
            return 0
    
    def refresh_bins_daily(self):
        """Обновление BIN'ов каждые 24 часа"""
        import threading
        import time
        
        def refresh_loop():
            while True:
                try:
                    # Ждем 24 часа (86400 секунд)
                    time.sleep(86400)
                    print("🔄 Обновление BIN'ов...")
                    self.generate_random_bins_for_all_countries()
                    print("✅ BIN'ы обновлены!")
                except Exception as e:
                    print(f"❌ Ошибка обновления BIN'ов: {e}")
        
        # Запускаем обновление в отдельном потоке
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
        print("🔄 Автоматическое обновление BIN'ов запущено (каждые 24 часа)")
    
    def get_countries(self) -> List[Dict[str, Any]]:
        """Получение списка стран"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM countries WHERE is_active = 1 ORDER BY id')
            countries = cursor.fetchall()
            conn.close()
            
            if countries:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, country)) for country in countries]
            return []
        except Exception as e:
            print(f"Error getting countries: {e}")
            return []
    
    def get_bins_by_country(self, country_code: str) -> List[Dict[str, Any]]:
        """Получение BIN'ов по коду страны"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.* FROM bins b
                JOIN countries c ON b.country_id = c.id
                WHERE c.code = ? AND b.is_active = 1
                ORDER BY b.bin_number
            ''', (country_code,))
            bins = cursor.fetchall()
            conn.close()
            
            if bins:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, bin_data)) for bin_data in bins]
            return []
        except Exception as e:
            print(f"Error getting bins by country: {e}")
            return []
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Добавление нового пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, first_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, user))
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_balance(self, user_id: int, amount: float) -> bool:
        """Обновление баланса пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET balance = balance + ? WHERE user_id = ?
            ''', (amount, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating balance: {e}")
            return False
    
    def add_balance(self, user_id: int, amount: float) -> bool:
        """Добавление баланса пользователю (алиас для update_balance)"""
        return self.update_balance(user_id, amount)
    
    def get_order_by_payment_id(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Получение заказа по ID платежа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.*, p.name, p.emoji, p.category, o.unit_price
                FROM orders o 
                LEFT JOIN products p ON o.product_id = p.id 
                WHERE o.payment_id = ?
            ''', (payment_id,))
            order = cursor.fetchone()
            conn.close()
            
            if order:
                columns = [description[0] for description in cursor.description]
                order_dict = dict(zip(columns, order))
                
                # Добавляем product_price для совместимости
                order_dict['product_price'] = order_dict.get('unit_price')
                
                return order_dict
            return None
        except Exception as e:
            print(f"Error getting order by payment ID: {e}")
            return None
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получение заказа по ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.*, p.name, p.emoji, p.category, o.unit_price
                FROM orders o 
                LEFT JOIN products p ON o.product_id = p.id 
                WHERE o.id = ?
            ''', (order_id,))
            order = cursor.fetchone()
            conn.close()
            
            if order:
                columns = [description[0] for description in cursor.description]
                order_dict = dict(zip(columns, order))
                
                # Добавляем product_price для совместимости
                order_dict['product_price'] = order_dict.get('unit_price')
                
                return order_dict
            return None
        except Exception as e:
            print(f"Error getting order by ID: {e}")
            return None
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновление статуса заказа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (status, order_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_affected > 0:
                print(f"✅ Статус заказа {order_id} обновлен на '{status}'")
                return True
            else:
                print(f"❌ Заказ {order_id} не найден")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обновления статуса заказа: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def log_webhook(self, webhook_type: str, payload: str, success: bool, error_message: str = None) -> bool:
        """Логирование вебхука"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO webhook_logs (webhook_type, payload, success, error_message)
                VALUES (?, ?, ?, ?)
            ''', (webhook_type, payload, 1 if success else 0, error_message))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging webhook: {e}")
            return False
    
    def log_product_delivery(self, order_id: int, user_id: int, product_id: int, delivered_at: datetime) -> bool:
        """Логирование выдачи товара"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO product_deliveries (order_id, user_id, product_id, delivered_at)
                VALUES (?, ?, ?, ?)
            ''', (order_id, user_id, product_id, delivered_at))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging product delivery: {e}")
            return False
    
    def get_last_webhook_time(self) -> Optional[str]:
        """Получение времени последнего вебхука"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT processed_at FROM webhook_logs ORDER BY processed_at DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting last webhook time: {e}")
            return None
    
    def get_total_webhooks(self) -> int:
        """Получение общего количества вебхуков"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM webhook_logs')
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting total webhooks: {e}")
            return 0
    
    def get_successful_webhooks(self) -> int:
        """Получение количества успешных вебхуков"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM webhook_logs WHERE success = 1')
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            print(f"Error getting successful webhooks: {e}")
            return 0
    
    def get_products(self, category: str = None) -> List[Dict[str, Any]]:
        """Получение списка товаров"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT * FROM products WHERE category = ? AND is_active = 1
                    ORDER BY price ASC
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT * FROM products WHERE is_active = 1 ORDER BY price ASC
                ''')
            
            products = cursor.fetchall()
            conn.close()
            
            if products:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, product)) for product in products]
            return []
        except Exception as e:
            print(f"Error getting products: {e}")
            return []
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о товаре"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,))
            product = cursor.fetchone()
            conn.close()
            
            if product:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, product))
            return None
        except Exception as e:
            print(f"Error getting product: {e}")
            return None
    
    def create_order(self, user_id: int, product_id: int, amount: float, payment_id: str = None) -> int:
        """Создание заказа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем информацию о продукте для сохранения цены за единицу
            product = None
            if product_id > 0:  # Не пополнение баланса
                cursor.execute('SELECT name, price, emoji, category FROM products WHERE id = ?', (product_id,))
                product = cursor.fetchone()
            
            # Создаем заказ
            unit_price = product[1] if product else None
            cursor.execute('''
                INSERT INTO orders (user_id, product_id, amount, payment_id, status, created_at, unit_price)
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
            ''', (user_id, product_id, amount, payment_id, 'pending', unit_price))
            
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Заказ создан: ID={order_id}, user_id={user_id}, amount={amount}")
            return order_id
            
        except Exception as e:
            print(f"❌ Ошибка создания заказа: {e}")
            if 'conn' in locals():
                conn.close()
            return -1
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновление статуса заказа"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (status, order_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_affected > 0:
                print(f"✅ Статус заказа {order_id} обновлен на '{status}'")
                return True
            else:
                print(f"❌ Заказ {order_id} не найден")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка обновления статуса заказа: {e}")
            if 'conn' in locals():
                conn.close()
            return False
    
    def get_user_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение заказов пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.*, p.name, p.emoji, p.category, o.unit_price
                FROM orders o 
                LEFT JOIN products p ON o.product_id = p.id 
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
            ''', (user_id,))
            orders = cursor.fetchall()
            conn.close()
            
            if orders:
                columns = [description[0] for description in cursor.description]
                result = []
                for order in orders:
                    order_dict = dict(zip(columns, order))
                    # Добавляем product_price для совместимости
                    order_dict['product_price'] = order_dict.get('unit_price')
                    result.append(order_dict)
                return result
            return []
        except Exception as e:
            print(f"Error getting user orders: {e}")
            return []
    
    def add_to_favorites(self, user_id: int, product_id: int) -> bool:
        """Добавление товара в избранное"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO favorites (user_id, product_id)
                VALUES (?, ?)
            ''', (user_id, product_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding to favorites: {e}")
            return False
    
    def get_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение избранных товаров пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* FROM products p
                JOIN favorites f ON p.id = f.product_id
                WHERE f.user_id = ? AND p.is_active = 1
                ORDER BY p.price ASC
            ''', (user_id,))
            products = cursor.fetchall()
            conn.close()
            
            if products:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, product)) for product in products]
            return []
        except Exception as e:
            print(f"Error getting favorites: {e}")
            return []

    def migrate_database(self):
        """Миграция базы данных - добавление недостающих колонок"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существующие колонки в таблице orders
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Если нужных колонок нет, пересоздаем таблицу
            missing_columns = []
            if 'unit_price' not in columns:
                missing_columns.append('unit_price')
            if 'updated_at' not in columns:
                missing_columns.append('updated_at')
            if 'status' not in columns:
                missing_columns.append('status')
            if 'created_at' not in columns:
                missing_columns.append('created_at')
            
            if missing_columns:
                print(f"🔄 Добавляем недостающие колонки: {', '.join(missing_columns)}")
                
                # Создаем временную таблицу с правильной схемой
                cursor.execute('''
                    CREATE TABLE orders_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        payment_id TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        unit_price REAL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (product_id) REFERENCES products (product_id)
                    )
                ''')
                
                # Копируем данные из старой таблицы
                cursor.execute('''
                    INSERT INTO orders_new (id, user_id, product_id, amount, payment_id, status, created_at, updated_at, unit_price)
                    SELECT id, user_id, product_id, amount, payment_id, 
                           COALESCE(status, 'pending') as status,
                           COALESCE(created_at, CURRENT_TIMESTAMP) as created_at,
                           COALESCE(updated_at, CURRENT_TIMESTAMP) as updated_at,
                           unit_price
                    FROM orders
                ''')
                
                # Удаляем старую таблицу и переименовываем новую
                cursor.execute('DROP TABLE orders')
                cursor.execute('ALTER TABLE orders_new RENAME TO orders')
                
                print("✅ Таблица orders обновлена")
            
            conn.commit()
            conn.close()
            print("✅ Миграция базы данных завершена")
            
        except Exception as e:
            print(f"❌ Ошибка миграции базы данных: {e}")
            if 'conn' in locals():
                conn.close()

