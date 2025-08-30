#!/usr/bin/env python3
"""
Система авторизации администраторов для LUXURY SHOP
"""

from config import ADMIN_USERNAMES, ADMIN_IDS
from typing import Union

class AdminAuth:
    """Класс для проверки прав администратора"""
    
    @staticmethod
    def is_admin(user_id: int, username: str = None) -> bool:
        """
        Проверяет, является ли пользователь администратором
        
        Args:
            user_id: ID пользователя в Telegram
            username: Username пользователя (опционально)
            
        Returns:
            bool: True если пользователь администратор
        """
        # Проверка по ID
        if user_id in ADMIN_IDS:
            return True
            
        # Проверка по username
        if username and username in ADMIN_USERNAMES:
            return True
            
        return False
    
    @staticmethod
    def get_admin_list() -> dict:
        """
        Возвращает список всех администраторов
        
        Returns:
            dict: Словарь с администраторами
        """
        return {
            "usernames": ADMIN_USERNAMES,
            "ids": ADMIN_IDS,
            "total": len(ADMIN_USERNAMES) + len(ADMIN_IDS)
        }
    
    @staticmethod
    def add_admin(user_id: int = None, username: str = None) -> bool:
        """
        Добавляет нового администратора (только для суперадминов)
        
        Args:
            user_id: ID пользователя
            username: Username пользователя
            
        Returns:
            bool: True если администратор добавлен
        """
        # Здесь можно добавить логику добавления администраторов
        # Например, через базу данных или конфигурационный файл
        return False
    
    @staticmethod
    def remove_admin(user_id: int = None, username: str = None) -> bool:
        """
        Удаляет администратора (только для суперадминов)
        
        Args:
            user_id: ID пользователя
            username: Username пользователя
            
        Returns:
            bool: True если администратор удален
        """
        # Здесь можно добавить логику удаления администраторов
        return False

def require_admin(func):
    """
    Декоратор для проверки прав администратора
    
    Usage:
        @require_admin
        def admin_only_function(update, context):
            # Только для администраторов
            pass
    """
    def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if not AdminAuth.is_admin(user.id, user.username):
            update.message.reply_text("❌ У вас нет прав администратора!")
            return
        return func(update, context, *args, **kwargs)
    return wrapper
