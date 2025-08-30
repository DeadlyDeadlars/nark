@echo off
chcp 65001 >nul
title CHAT SHOP Admin Panel

echo.
echo ========================================
echo    LUXURY SHOP Admin Panel
echo ========================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

echo Запуск административной панели...
python admin.py

echo.
echo Административная панель закрыта
pause
