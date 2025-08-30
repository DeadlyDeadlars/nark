#!/usr/bin/env python3
"""
Улучшенный запуск всех трех ботов
Запускает боты из папок: dost, griffin, team
с лучшей обработкой ошибок и изоляцией
"""

import asyncio
import sys
import os
import logging
import subprocess
import signal
import time
from pathlib import Path
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('all_bots_advanced.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BotRunner:
    """Класс для управления запуском ботов"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.bot_configs = {
            'dost': {
                'path': 'dost',
                'script': 'bot.py',
                'name': 'DOST',
                'color': '🟢'
            },
            'griffin': {
                'path': 'griffin', 
                'script': 'main_bot.py',
                'name': 'GRIFFIN',
                'color': '🔵'
            },
            'team': {
                'path': 'team',
                'script': 'main_bot.py', 
                'name': 'TEAM',
                'color': '🟡'
            }
        }
    
    def check_dependencies(self) -> bool:
        """Проверка наличия всех необходимых папок и файлов"""
        logger.info("🔍 Проверка зависимостей...")
        
        for bot_id, config in self.bot_configs.items():
            bot_path = Path(config['path'])
            script_path = bot_path / config['script']
            
            if not bot_path.exists():
                logger.error(f"❌ Папка {config['path']} не найдена")
                return False
                
            if not script_path.exists():
                logger.error(f"❌ Файл {config['script']} не найден в папке {config['path']}")
                return False
                
            logger.info(f"✅ {config['color']} {config['name']}: {config['path']}/{config['script']}")
        
        return True
    
    def start_bot(self, bot_id: str) -> bool:
        """Запуск отдельного бота в отдельном процессе"""
        config = self.bot_configs[bot_id]
        bot_path = Path(config['path'])
        script_path = bot_path / config['script']
        
        try:
            logger.info(f"🚀 Запуск {config['color']} {config['name']}...")
            
            # Запускаем бота в отдельном процессе
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(bot_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes[bot_id] = process
            logger.info(f"✅ {config['color']} {config['name']} запущен (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска {config['color']} {config['name']}: {e}")
            return False
    
    def stop_bot(self, bot_id: str):
        """Остановка отдельного бота"""
        if bot_id in self.processes:
            config = self.bot_configs[bot_id]
            process = self.processes[bot_id]
            
            try:
                logger.info(f"🛑 Остановка {config['color']} {config['name']}...")
                process.terminate()
                
                # Ждем завершения процесса
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️ Принудительная остановка {config['color']} {config['name']}")
                    process.kill()
                    process.wait()
                
                logger.info(f"✅ {config['color']} {config['name']} остановлен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка остановки {config['color']} {config['name']}: {e}")
    
    def start_all_bots(self) -> bool:
        """Запуск всех ботов"""
        logger.info("🎯 Запуск всех ботов...")
        
        success_count = 0
        for bot_id in self.bot_configs.keys():
            if self.start_bot(bot_id):
                success_count += 1
            time.sleep(1)  # Небольшая задержка между запусками
        
        logger.info(f"📊 Запущено ботов: {success_count}/{len(self.bot_configs)}")
        return success_count > 0
    
    def stop_all_bots(self):
        """Остановка всех ботов"""
        logger.info("🛑 Остановка всех ботов...")
        
        for bot_id in list(self.processes.keys()):
            self.stop_bot(bot_id)
        
        self.processes.clear()
        logger.info("👋 Все боты остановлены")
    
    def monitor_bots(self):
        """Мониторинг состояния ботов"""
        while True:
            try:
                time.sleep(30)  # Проверяем каждые 30 секунд
                
                for bot_id, process in list(self.processes.items()):
                    config = self.bot_configs[bot_id]
                    
                    # Проверяем, что процесс еще работает
                    if process.poll() is not None:
                        logger.warning(f"⚠️ {config['color']} {config['name']} завершился неожиданно")
                        
                        # Перезапускаем бота
                        logger.info(f"🔄 Перезапуск {config['color']} {config['name']}...")
                        self.stop_bot(bot_id)
                        time.sleep(2)
                        self.start_bot(bot_id)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("🛑 Получен сигнал остановки...")
    if hasattr(signal_handler, 'runner'):
        signal_handler.runner.stop_all_bots()
    sys.exit(0)

def main():
    """Главная функция"""
    print("🤖 Запуск всех ботов (улучшенная версия)...")
    print("📁 Папки: dost, griffin, team")
    print("📝 Логи: all_bots_advanced.log")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    # Создаем экземпляр BotRunner
    runner = BotRunner()
    signal_handler.runner = runner
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Проверяем зависимости
        if not runner.check_dependencies():
            logger.error("❌ Проверка зависимостей не пройдена")
            return
        
        # Запускаем все боты
        if not runner.start_all_bots():
            logger.error("❌ Не удалось запустить ни одного бота")
            return
        
        # Запускаем мониторинг
        logger.info("📊 Мониторинг ботов запущен...")
        runner.monitor_bots()
        
    except KeyboardInterrupt:
        print("\n🛑 Остановка всех ботов...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        runner.stop_all_bots()

if __name__ == "__main__":
    main()
