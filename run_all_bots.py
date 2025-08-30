#!/usr/bin/env python3
"""
Единый запуск всех трех ботов
Запускает боты из папок: dost, griffin, team
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('all_bots.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def run_dost_bot():
    """Запуск бота из папки dost"""
    try:
        logger.info("🚀 Запуск бота DOST...")
        
        # Добавляем путь к модулям dost
        dost_path = Path("dost")
        if dost_path.exists():
            sys.path.insert(0, str(dost_path))
            
            # Импортируем и запускаем бота
            from bot import main as dost_main
            await dost_main()
        else:
            logger.error("❌ Папка dost не найдена")
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота DOST: {e}")

async def run_griffin_bot():
    """Запуск бота из папки griffin"""
    try:
        logger.info("🚀 Запуск бота GRIFFIN...")
        
        # Добавляем путь к модулям griffin
        griffin_path = Path("griffin")
        if griffin_path.exists():
            sys.path.insert(0, str(griffin_path))
            
            # Импортируем и запускаем бота
            from main_bot import main as griffin_main
            await griffin_main()
        else:
            logger.error("❌ Папка griffin не найдена")
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота GRIFFIN: {e}")

async def run_team_bot():
    """Запуск бота из папки team"""
    try:
        logger.info("🚀 Запуск бота TEAM...")
        
        # Добавляем путь к модулям team
        team_path = Path("team")
        if team_path.exists():
            sys.path.insert(0, str(team_path))
            
            # Импортируем и запускаем бота
            from main_bot import main as team_main
            await team_main()
        else:
            logger.error("❌ Папка team не найдена")
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота TEAM: {e}")

async def run_all_bots():
    """Запуск всех ботов одновременно"""
    logger.info("🎯 Запуск всех ботов...")
    
    # Создаем задачи для каждого бота
    tasks = [
        asyncio.create_task(run_dost_bot(), name="DOST"),
        asyncio.create_task(run_griffin_bot(), name="GRIFFIN"),
        asyncio.create_task(run_team_bot(), name="TEAM")
    ]
    
    try:
        # Запускаем все боты одновременно
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("👋 Все боты остановлены")

def main():
    """Главная функция"""
    print("🤖 Запуск всех ботов...")
    print("📁 Папки: dost, griffin, team")
    print("📝 Логи сохраняются в all_bots.log")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    try:
        asyncio.run(run_all_bots())
    except KeyboardInterrupt:
        print("\n🛑 Остановка всех ботов...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
