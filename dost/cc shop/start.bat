@echo off
chcp 65001 >nul
title CHAT SHOP Telegram Bot

echo.
echo ========================================
echo    LUXURY SHOP Telegram Bot Launcher
echo ========================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    echo Скачать: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

echo Проверка зависимостей...
if not exist "requirements.txt" (
    echo ❌ Файл requirements.txt не найден!
    pause
    exit /b 1
)

echo Установка зависимостей...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей!
    pause
    exit /b 1
)

echo ✅ Зависимости установлены
echo.

echo Проверка конфигурации...
if not exist ".env" (
    echo ⚠️  Файл .env не найден!
    echo Создайте файл .env на основе env_example.txt
    echo.
    echo Содержимое .env должно быть:
    echo BOT_TOKEN=your_telegram_bot_token
    echo CRYPTOBOT_TOKEN=your_cryptobot_api_token
    echo.
    pause
    exit /b 1
)

echo ✅ Конфигурация найдена
echo.

echo 🚀 Запуск CHAT SHOP бота...
echo 💡 Для остановки нажмите Ctrl+C
echo.

python bot.py

echo.
echo Бот остановлен
pause
