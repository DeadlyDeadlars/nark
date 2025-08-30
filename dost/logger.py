import logging
import asyncio
from datetime import datetime
from typing import Optional
from aiogram import Bot
from config import BOT_TOKEN, LOGS_CHANNEL_ID, LOGS_CHANNEL_USERNAME

class TelegramChannelHandler(logging.Handler):
    """Обработчик логов для отправки в Telegram канал"""
    
    def __init__(self, bot: Bot, channel_id: Optional[str] = None, channel_username: Optional[str] = None):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.channel_username = channel_username
        self.queue = asyncio.Queue()
        self.running = True
        self._processor_task = None
    
    def emit(self, record):
        """Отправка лога в очередь для обработки"""
        if self.running:
            try:
                # Форматируем сообщение
                message = self.format(record)
                # Проверяем, запущен ли event loop
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(self.queue.put((record.levelname, message)))
                except RuntimeError:
                    # Event loop не запущен, просто выводим в консоль
                    print(f"[{record.levelname}] {message}")
            except Exception as e:
                # Избегаем рекурсии при ошибках логирования
                print(f"Ошибка логирования: {e}")
    
    async def _message_processor(self):
        """Обработчик очереди сообщений"""
        while self.running:
            try:
                level, message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._send_to_channel(level, message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Ошибка обработки лога: {e}")
    
    def start_processor(self):
        """Запуск обработчика сообщений"""
        if self._processor_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._processor_task = asyncio.create_task(self._message_processor())
            except RuntimeError:
                # Event loop не запущен, обработчик запустится позже
                pass
    
    async def _send_to_channel(self, level: str, message: str):
        """Отправка сообщения в канал"""
        if not self.channel_id:
            return
        
        try:
            # Эмодзи для разных уровней логирования
            level_emojis = {
                'DEBUG': '🔍',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            
            emoji = level_emojis.get(level, '📝')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Форматируем сообщение для канала (без Markdown для избежания ошибок)
            channel_message = f"{emoji} {level}\n"
            channel_message += f"🕐 {timestamp}\n"
            channel_message += f"📄 {message}\n"
            channel_message += "─" * 30
            
            # Отправляем в канал (ID работает для всех типов каналов)
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=channel_message,
                parse_mode=None,  # отключаем Markdown/HTML для логов
                disable_web_page_preview=True
            )
                
        except Exception as e:
            print(f"Ошибка отправки в канал: {e}")
    
    def stop(self):
        """Остановка обработчика"""
        self.running = False
        if self._processor_task:
            self._processor_task.cancel()

def setup_logging(bot: Bot) -> logging.Logger:
    """Настройка логирования только бизнес-событий (без стартовых сообщений)."""
    logger = logging.getLogger('delivery_bot')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(message)s')

    # Не добавляем консольный handler, чтобы не засорять терминал

    if LOGS_CHANNEL_ID:
        try:
            channel_handler = TelegramChannelHandler(
                bot=bot,
                channel_id=LOGS_CHANNEL_ID,
                channel_username=LOGS_CHANNEL_USERNAME
            )
            channel_handler.setLevel(logging.INFO)
            channel_handler.setFormatter(formatter)
            logger.addHandler(channel_handler)
            channel_handler.start_processor()
        except Exception as e:
            print(f"Ошибка настройки логирования в канал: {e}")
    return logger

async def _send_startup_message(bot: Bot, logger: logging.Logger):
    # Отключено по требованию: стартовые логи не отправляем
    return

async def log_order(logger: logging.Logger, user_id: int, username: str, product: str, packaging: str, address: str, delivery_time: int):
    """Логирование нового заказа"""
    order_message = f"🛒 Новый заказ!\n\n"
    order_message += f"👤 Пользователь: @{username} (ID: {user_id})\n"
    order_message += f"📦 Товар: {product}\n"
    order_message += f"⚖️ Фасовка: {packaging}\n"
    order_message += f"🏠 Адрес: {address}\n"
    order_message += f"⏰ Время доставки: {delivery_time} мин."
    
    logger.info(order_message)

async def log_admin_action(logger: logging.Logger, admin_id: int, action: str, details: str = ""):
    """Логирование действий администратора"""
    admin_message = f"👨‍💼 Действие администратора\n\n"
    admin_message += f"🆔 Админ ID: {admin_id}\n"
    admin_message += f"🔧 Действие: {action}\n"
    if details:
        admin_message += f"📋 Детали: {details}"
    
    logger.info(admin_message)

async def log_error(logger: logging.Logger, error: str, context: str = ""):
    """Логирование ошибок"""
    error_message = f"❌ Ошибка в боте\n\n"
    error_message += f"🚨 Ошибка: {error}\n"
    if context:
        error_message += f"📍 Контекст: {context}"
    
    logger.error(error_message) 

async def log_payment_event(
    logger: logging.Logger,
    user_id: int,
    event: str,
    details: str = "",
    *,
    username: str | None = None,
    product: str | None = None,
    packaging: str | None = None,
    address: str | None = None,
    amount: str | None = None,
    order_number: int | None = None,
    method: str | None = None,
):
    """Логирование событий оплаты с расширенным контекстом."""
    uname = f"@{username}" if username else "—"
    lines = [
        "💳 Событие оплаты",
        f"🆔 Пользователь: {user_id}",
        f"👤 Username: {uname}",
        f"📌 Событие: {event}",
    ]
    if method:
        lines.append(f"💼 Метод: {method}")
    if order_number is not None:
        lines.append(f"#️⃣ Заказ: {order_number}")
    if product is not None:
        lines.append(f"🛒 Товар: {product}")
    if packaging is not None:
        lines.append(f"⚖️ Фасовка: {packaging}")
    if amount is not None:
        lines.append(f"💵 Сумма: {amount}")
    if address is not None:
        lines.append(f"🏠 Адрес: {address}")
    if details:
        lines.append(f"📋 Детали: {details}")
    logger.info("\n".join(lines))

async def log_user_action(
    logger: logging.Logger,
    user_id: int,
    username: str | None,
    action: str,
    *,
    product: str | None = None,
    packaging: str | None = None,
    address: str | None = None,
):
    """Логи с понятным снапшотом выбора пользователя."""
    uname = f"@{username}" if username else "—"
    lines = [
        "🧭 Действие пользователя",
        f"🆔 ID: {user_id}",
        f"👤 Username: {uname}",
        f"📌 Событие: {action}",
    ]
    if product is not None:
        lines.append(f"🛒 Товар: {product}")
    if packaging is not None:
        lines.append(f"⚖️ Фасовка: {packaging}")
    if address is not None:
        lines.append(f"🏠 Адрес: {address}")
    logger.info("\n".join(lines))