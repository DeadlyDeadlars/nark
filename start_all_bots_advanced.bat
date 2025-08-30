@echo off
chcp 65001 >nul
title Запуск всех ботов (улучшенная версия)

echo.
echo ========================================
echo  ЗАПУСК ВСЕХ БОТОВ (УЛУЧШЕННАЯ ВЕРСИЯ)
echo ========================================
echo.
echo Папки: dost, griffin, team
echo Логи: all_bots_advanced.log
echo.
echo Особенности:
echo - Автоматический перезапуск при сбоях
echo - Мониторинг состояния ботов
echo - Лучшая обработка ошибок
echo.
echo Для остановки нажмите Ctrl+C
echo ========================================
echo.

python run_all_bots_advanced.py

echo.
echo Боты остановлены. Нажмите любую клавишу для выхода...
pause >nul
