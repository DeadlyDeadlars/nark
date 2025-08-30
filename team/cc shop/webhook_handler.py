#!/usr/bin/env python3
"""
Обработчик вебхуков для автоматической проверки платежей LUXURY SHOP
"""

import json
import hashlib
import hmac
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from database import Database
from cryptobot import CryptoBot
from config import WEBHOOK_SECRET, RELAY_TOKEN

class WebhookHandler:
    """Класс для обработки вебхуков от CryptoBot"""
    
    def __init__(self):
        self.db = Database()
        self.crypto_bot = CryptoBot()
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Проверяет подпись вебхука для безопасности
        
        Args:
            payload: Тело вебхука
            signature: Подпись от CryptoBot
            
        Returns:
            bool: True если подпись верна
        """
        if not WEBHOOK_SECRET:
            return True  # Если секрет не настроен, пропускаем проверку
            
        expected_signature = hmac.new(
            WEBHOOK_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

    def verify_relay_token(self, token: str) -> bool:
        """
        Проверяет ретрансляционный токен от Netlify функции
        """
        if not RELAY_TOKEN:
            return False
        return hmac.compare_digest(token or "", RELAY_TOKEN)
    
    async def process_payment_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает вебхук о платеже
        
        Args:
            webhook_data: Данные вебхука от CryptoBot
            
        Returns:
            dict: Результат обработки
        """
        try:
            # Проверяем статус платежа
            status = webhook_data.get('status')
            invoice_id = webhook_data.get('invoice_id')
            
            if not invoice_id:
                return {"success": False, "error": "Invoice ID not found"}
            
            # Получаем информацию о платеже
            payment_info = await self.crypto_bot.get_invoice_status(invoice_id)
            
            if not payment_info:
                return {"success": False, "error": "Payment info not found"}
            
            # Обрабатываем различные статусы
            if status == "paid":
                return await self.handle_paid_payment(webhook_data, payment_info)
            elif status == "expired":
                return await self.handle_expired_payment(webhook_data)
            elif status == "cancelled":
                return await self.handle_cancelled_payment(webhook_data)
            else:
                return {"success": False, "error": f"Unknown status: {status}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_paid_payment(self, webhook_data: Dict[str, Any], payment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает успешно оплаченный платеж
        
        Args:
            webhook_data: Данные вебхука
            payment_info: Информация о платеже
            
        Returns:
            dict: Результат обработки
        """
        try:
            invoice_id = webhook_data.get('invoice_id')
            amount = webhook_data.get('amount')
            currency = webhook_data.get('currency')
            
            # Находим заказ по invoice_id
            order = self.db.get_order_by_payment_id(invoice_id)
            
            if not order:
                return {"success": False, "error": "Order not found"}
            
            # Обновляем статус заказа
            if self.db.update_order_status(order['id'], 'completed'):
                # Выдаем товар пользователю
                await self.deliver_product(order)
                
                # Обновляем баланс пользователя если нужно
                if currency == "USDT":
                    self.db.update_balance(order['user_id'], amount)
                
                return {
                    "success": True,
                    "message": f"Payment processed successfully. Order {order['id']} completed.",
                    "order_id": order['id'],
                    "user_id": order['user_id']
                }
            else:
                return {"success": False, "error": "Failed to update order status"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_expired_payment(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает истекший платеж
        
        Args:
            webhook_data: Данные вебхука
            
        Returns:
            dict: Результат обработки
        """
        try:
            invoice_id = webhook_data.get('invoice_id')
            
            # Находим заказ и обновляем статус
            order = self.db.get_order_by_payment_id(invoice_id)
            
            if order:
                self.db.update_order_status(order['id'], 'expired')
                return {
                    "success": True,
                    "message": f"Payment expired. Order {order['id']} marked as expired.",
                    "order_id": order['id']
                }
            else:
                return {"success": False, "error": "Order not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_cancelled_payment(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает отмененный платеж
        
        Args:
            webhook_data: Данные вебхука
            
        Returns:
            dict: Результат обработки
        """
        try:
            invoice_id = webhook_data.get('invoice_id')
            
            # Находим заказ и обновляем статус
            order = self.db.get_order_by_payment_id(invoice_id)
            
            if order:
                self.db.update_order_status(order['id'], 'cancelled')
                return {
                    "success": True,
                    "message": f"Payment cancelled. Order {order['id']} marked as cancelled.",
                    "order_id": order['id']
                }
            else:
                return {"success": False, "error": "Order not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def deliver_product(self, order: Dict[str, Any]) -> bool:
        """
        Выдает товар пользователю
        
        Args:
            order: Информация о заказе
            
        Returns:
            bool: True если товар выдан
        """
        try:
            # Здесь можно добавить логику выдачи товара
            # Например, отправка файла, ссылки или другого контента
            
            # Логируем выдачу товара
            self.db.log_product_delivery(
                order_id=order['id'],
                user_id=order['user_id'],
                product_id=order['product_id'],
                delivered_at=datetime.now()
            )
            
            return True
            
        except Exception as e:
            print(f"Error delivering product: {e}")
            return False
    
    def get_webhook_status(self) -> Dict[str, Any]:
        """
        Возвращает статус вебхуков
        
        Returns:
            dict: Статус вебхуков
        """
        return {
            "webhooks_enabled": bool(WEBHOOK_SECRET),
            "last_webhook": self.db.get_last_webhook_time(),
            "total_webhooks": self.db.get_total_webhooks(),
            "successful_webhooks": self.db.get_successful_webhooks()
        }

class WebhookServer:
    """Простой HTTP сервер для приема вебхуков"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.handler = WebhookHandler()
    
    async def start_server(self):
        """Запускает HTTP сервер для вебхуков"""
        try:
            import aiohttp
            from aiohttp import web
            
            async def webhook_handler(request):
                """Обработчик вебхуков"""
                try:
                    # Получаем данные вебхука
                    payload = await request.text()
                    signature = request.headers.get('X-Crypto-Pay-API-Signature', '')
                    relay_token = request.headers.get('X-Relay-Token', '')
                    
                    # Проверяем ретрансляционный токен или подпись от CryptoBot
                    if self.handler.verify_relay_token(relay_token):
                        pass  # доверяем Netlify функции
                    elif self.handler.verify_webhook_signature(payload, signature):
                        pass
                    else:
                        return web.Response(status=401, text="Invalid signature or relay token")
                    
                    # Парсим JSON
                    webhook_data = json.loads(payload)
                    
                    # Обрабатываем вебхук
                    result = await self.handler.process_payment_webhook(webhook_data)
                    
                    if result.get('success'):
                        return web.Response(status=200, text="Webhook processed successfully")
                    else:
                        return web.Response(status=400, text=f"Error: {result.get('error')}")
                        
                except Exception as e:
                    return web.Response(status=500, text=f"Internal error: {str(e)}")
            
            # Создаем приложение
            app = web.Application()
            app.router.add_post('/webhook', webhook_handler)
            
            # Запускаем сервер
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            
            print(f"🌐 Webhook server started on {self.host}:{self.port}")
            print(f"📡 Webhook URL: http://{self.host}:{self.port}/webhook")
            
            # Держим сервер запущенным
            while True:
                await asyncio.sleep(1)
                
        except ImportError:
            print("❌ aiohttp not installed. Install with: pip install aiohttp")
        except Exception as e:
            print(f"❌ Error starting webhook server: {e}")

# Функция для запуска вебхук сервера
async def start_webhook_server(host: str = '0.0.0.0', port: int = 8080):
    """Запускает вебхук сервер"""
    server = WebhookServer(host, port)
    await server.start_server()

if __name__ == "__main__":
    # Тестовый запуск вебхук сервера
    asyncio.run(start_webhook_server())
