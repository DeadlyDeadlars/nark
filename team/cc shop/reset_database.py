#!/usr/bin/env python3
"""
Скрипт для сброса базы данных
Используйте только если нужно полностью пересоздать БД
"""

import os
import sqlite3

def reset_database():
    """Сброс базы данных"""
    db_path = "shop_bot.db"
    
    print("⚠️ ВНИМАНИЕ! Это удалит все данные из базы!")
    print(f"База данных: {db_path}")
    
    # Проверяем, существует ли файл
    if os.path.exists(db_path):
        print(f"📁 Найден файл базы данных: {db_path}")
        
        # Удаляем файл
        try:
            os.remove(db_path)
            print("✅ Файл базы данных удален")
        except Exception as e:
            print(f"❌ Ошибка удаления файла: {e}")
            return False
    else:
        print("📁 Файл базы данных не найден")
    
    print("🔄 База данных будет пересоздана при следующем запуске бота")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("СБРОС БАЗЫ ДАННЫХ LUXURY SHOP")
    print("=" * 50)
    
    confirm = input("Вы уверены, что хотите удалить все данные? (yes/no): ")
    
    if confirm.lower() in ['yes', 'y', 'да', 'д']:
        if reset_database():
            print("✅ База данных успешно сброшена!")
            print("🚀 Запустите бота заново для создания новой БД")
        else:
            print("❌ Ошибка при сбросе базы данных")
    else:
        print("❌ Операция отменена")
