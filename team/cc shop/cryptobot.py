import aiohttp
import json
from typing import Optional, Dict, Any
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL

class CryptoBot:
    def __init__(self):
        self.token = CRYPTOBOT_TOKEN
        self.api_url = CRYPTOBOT_API_URL
        self.headers = {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json"
        }
    
    async def create_invoice(self, amount: float, currency: str = "USDT", description: str = None) -> Optional[Dict[str, Any]]:
        """Создание счета на оплату"""
        try:
            if not self.token:
                print("Error creating invoice: CRYPTOBOT_TOKEN is not set")
                return None
            payload = {
                "amount": str(amount),
                # Crypto Pay API expects 'asset' (e.g., 'USDT', 'TON', 'BTC')
                "asset": currency,
                "description": description or f"Оплата товара на сумму {amount} {currency}",
                "paid_btn_name": "callback",
                "paid_btn_url": "https://t.me/your_bot_username",
                "payload": "shop_payment"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/createInvoice",
                    headers=self.headers,
                    json=payload
                ) as response:
                    text = await response.text()
                    if response.status == 200:
                        try:
                            result = await response.json()
                        except Exception:
                            print(f"Error creating invoice: invalid JSON: {text}")
                            return None
                        if result.get("ok"):
                            return result.get("result")
                        print(f"Error creating invoice: API responded not ok: {result}")
                        return None
                    print(f"Error creating invoice: HTTP {response.status}: {text}")
                    return None
        except Exception as e:
            print(f"Error creating invoice: {e}")
            return None
    
    async def get_invoice_status(self, invoice_id: str) -> Optional[str]:
        """Получение статуса счета"""
        try:
            payload = {"invoice_id": invoice_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/getInvoice",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result", {}).get("status")
                    return None
        except Exception as e:
            print(f"Error getting invoice status: {e}")
            return None
    
    async def get_exchange_rates(self) -> Optional[Dict[str, Any]]:
        """Получение курсов валют"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/getExchangeRates",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result")
                    return None
        except Exception as e:
            print(f"Error getting exchange rates: {e}")
            return None
    
    async def get_currencies(self) -> Optional[Dict[str, Any]]:
        """Получение доступных валют"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/getCurrencies",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result")
                    return None
        except Exception as e:
            print(f"Error getting currencies: {e}")
            return None
    
    def format_payment_message(self, invoice_data: Dict[str, Any]) -> str:
        """Форматирование сообщения для оплаты"""
        if not invoice_data:
            return "Ошибка создания счета на оплату"
        
        amount = invoice_data.get("amount", 0)
        currency = invoice_data.get("asset", "USDT")
        pay_url = invoice_data.get("pay_url", "")
        invoice_id = invoice_data.get("invoice_id", "")
        
        # Убираем потенциально проблемные символы для Markdown
        # Используем bot_invoice_url, если есть (это правильный deep-link ?start=invoice-<ID>)
        bot_invoice_url = invoice_data.get("bot_invoice_url") or ""
        preferred_url = bot_invoice_url or pay_url or ""
        safe_pay_url = preferred_url.replace("(", "%28").replace(")", "%29") if isinstance(preferred_url, str) else ""
        message = (
            "💳 *Счет на оплату создан*\n\n"
            f"💰 Сумма: `{amount} {currency}`\n"
            f"🆔 ID счета: `{invoice_id}`\n\n"
            f"🔗 [Оплатить в CryptoBot]({safe_pay_url})\n\n"
            "⚠️ *Внимание:* Оплатите счет в течение 30 минут"
        )
        
        return message
    
    def create_payment_keyboard(self, invoice_id: str) -> Dict[str, Any]:
        """Создание клавиатуры для оплаты"""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "💳 Оплатить",
                        "url": f"https://t.me/CryptoBot?start=pay-{invoice_id}"
                    }
                ],
                [
                    {
                        "text": "🔄 Проверить статус",
                        "callback_data": f"check_payment_{invoice_id}"
                    }
                ],
                [
                    {
                        "text": "❌ Отменить",
                        "callback_data": f"cancel_payment_{invoice_id}"
                    }
                ]
            ]
        }
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обработка webhook от криптобота"""
        try:
            if webhook_data.get("status") == "paid":
                return {
                    "invoice_id": webhook_data.get("invoice_id"),
                    "amount": webhook_data.get("amount"),
                    "currency": webhook_data.get("currency"),
                    "status": "paid",
                    "payload": webhook_data.get("payload")
                }
            return None
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return None
