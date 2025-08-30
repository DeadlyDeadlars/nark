#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации BIN'ов
"""

from database import Database

def test_bins_generation():
    print("🧪 Тестирование генерации BIN'ов...")
    
    # Создаем экземпляр базы данных
    db = Database()
    
    # Проверяем количество стран
    countries = db.get_countries()
    print(f"🌍 Найдено стран: {len(countries)}")
    
    # Проверяем количество BIN'ов
    total_bins = 0
    for country in countries[:5]:  # Проверяем первые 5 стран
        bins = db.get_bins_by_country(country['code'])
        print(f"  {country['flag']} {country['name']}: {len(bins)} BIN'ов")
        total_bins += len(bins)
    
    print(f"📊 Всего BIN'ов: {total_bins}")
    
    # Проверяем, что BIN'ы действительно сгенерированы
    if total_bins > 0:
        print("✅ BIN'ы успешно сгенерированы!")
    else:
        print("❌ BIN'ы не сгенерированы!")
        
        # Попробуем сгенерировать заново
        print("🔄 Пробуем сгенерировать BIN'ы заново...")
        db.generate_random_bins_for_all_countries()
        
        # Проверяем снова
        total_bins = 0
        for country in countries[:5]:
            bins = db.get_bins_by_country(country['code'])
            print(f"  {country['flag']} {country['name']}: {len(bins)} BIN'ов")
            total_bins += len(bins)
        
        if total_bins > 0:
            print("✅ BIN'ы успешно сгенерированы после повторной попытки!")
        else:
            print("❌ Не удалось сгенерировать BIN'ы!")

if __name__ == "__main__":
    test_bins_generation()
