@echo off
chcp 65001 >nul
title Запуск всех ботов

echo.
echo ========================================
echo    ЗАПУСК ВСЕХ БОТОВ
echo ========================================
echo.
echo Папки: dost, griffin, team
echo Логи: all_bots.log
echo.
echo Для остановки нажмите Ctrl+C
echo ========================================
echo.

python run_all_bots.py

echo.
echo Боты остановлены. Нажмите любую клавишу для выхода...
pause >nul
