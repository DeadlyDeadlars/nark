import asyncio
import os
import time
import random
import secrets
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, ADMIN_ID, PACKAGING_OPTIONS, MIN_DELIVERY_TIME, MAX_DELIVERY_TIME, ABOUT_TEXT
from catalog import get_variant
from database import Database
from keyboards import (
    get_main_keyboard, get_products_keyboard, get_packaging_keyboard,
    get_cancel_keyboard, get_admin_keyboard, get_confirm_keyboard,
    get_payment_method_keyboard, get_payment_confirm_keyboard
)
from states import OrderStates, AdminStates
from logger import setup_logging, log_order, log_admin_action, log_error, log_payment_event, log_user_action

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database()

# Словарь для хранения данных заказов пользователей
user_orders = {}

# Инициализация логирования
logger = None

async def safe_edit_text(message: types.Message, text: str, reply_markup=None):
    """Безопасное редактирование текста сообщения: игнорирует ошибку 'message is not modified'."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            try:
                await message.edit_reply_markup(reply_markup=reply_markup)
            except TelegramBadRequest:
                pass
        else:
            raise

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Учитываем пользователя в БД
    try:
        db.track_user(message.from_user.id, message.from_user.username)
    except Exception as e:
        if logger:
            await log_error(logger, f"Ошибка трекинга пользователя: {e}")
    await message.answer(
        "👋 Добро пожаловать в бот доставки!\n\n"
        "Выберите нужный раздел:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin для администратора"""
    if str(message.from_user.id) == ADMIN_ID:
        await message.answer(
            "🔧 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ У вас нет доступа к панели администратора.")

@dp.callback_query(F.data == "about")
async def about_handler(callback: CallbackQuery):
    """Обработчик кнопки 'О нас'"""
    await safe_edit_text(callback.message, ABOUT_TEXT, reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "order")
async def order_handler(callback: CallbackQuery):
    """Обработчик кнопки 'Заказать доставку'"""
    await safe_edit_text(callback.message, "🛒 Выберите товар:", reply_markup=get_products_keyboard())

@dp.callback_query(F.data.startswith("product:"))
async def product_handler(callback: CallbackQuery):
    """Обработчик выбора товара"""
    product_name = callback.data.split(":", 1)[1]
    
    # Сохраняем выбранный товар
    user_id = callback.from_user.id
    if user_id not in user_orders:
        user_orders[user_id] = {}
    user_orders[user_id]['product'] = product_name
    if logger:
        await log_user_action(logger, user_id, callback.from_user.username, "select_product", product=product_name)
    
    await safe_edit_text(callback.message, f"📦 Выбран товар: {product_name}\n\nТеперь выберите фасовку:", reply_markup=get_packaging_keyboard(product_name))

@dp.callback_query(F.data.startswith("packaging:"))
async def packaging_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора фасовки"""
    packaging_index = int(callback.data.split(":", 1)[1])
    product_name = user_orders.get(callback.from_user.id, {}).get('product')
    variant = get_variant(product_name, packaging_index)
    packaging = variant.weight if variant else (PACKAGING_OPTIONS[packaging_index] if 0 <= packaging_index < len(PACKAGING_OPTIONS) else "")
    
    # Сохраняем выбранную фасовку
    user_id = callback.from_user.id
    if user_id not in user_orders:
        user_orders[user_id] = {}
    user_orders[user_id]['packaging'] = packaging
    if variant:
        user_orders[user_id]['price'] = variant.price
    if logger:
        await log_user_action(logger, user_id, callback.from_user.username, "select_packaging", product=product_name, packaging=packaging)
    
    await safe_edit_text(callback.message, f"📦 Выбрана фасовка: {packaging}\n\nУкажите адрес доставки:", reply_markup=get_cancel_keyboard())
    
    # Переводим в состояние ожидания адреса (без дублирующего сообщения)
    await state.set_state(OrderStates.waiting_for_address)
    await callback.answer()

@dp.message(OrderStates.waiting_for_address)
async def address_handler(message: Message, state: FSMContext):
    """Обработчик ввода адреса"""
    address = message.text.strip()
    
    if len(address) < 10:
        await message.answer("❌ Адрес слишком короткий. Пожалуйста, укажите полный адрес.")
        return
    
    user_id = message.from_user.id
    if user_id not in user_orders:
        await message.answer("❌ Ошибка. Начните заказ заново.", reply_markup=get_main_keyboard())
        return
    
    user_orders[user_id]['address'] = address
    if logger:
        await log_user_action(logger, user_id, message.from_user.username, "enter_address", product=user_orders[user_id].get('product'), packaging=user_orders[user_id].get('packaging'), address=address)
    
    # Генерируем случайное время доставки
    delivery_time = random.randint(MIN_DELIVERY_TIME, MAX_DELIVERY_TIME)
    user_orders[user_id]['delivery_time'] = delivery_time
    
    # Показываем подтверждение заказа
    price_part = f"\n💵 *Цена:* {int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders[user_id].get('price') is not None else ""
    order_text = (
        f"📋 *Подтверждение заказа:*\n\n"
        f"🛒 *Товар:* {user_orders[user_id]['product']}\n"
        f"📦 *Кол-во:* {user_orders[user_id]['packaging']}\n"
        f"🏠 *Адрес:* {address}\n"
        f"{price_part}\n"
        f"⏳ *Время доставки:* {delivery_time} минут\n\n"
        f"Подтвердите заказ:"
    )
    
    await message.answer(order_text, reply_markup=get_confirm_keyboard())
    await state.clear()

@dp.callback_query(F.data == "confirm_order")
async def confirm_order_handler(callback: CallbackQuery):
    """Обработчик подтверждения заказа"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "Без username"
    
    if user_id not in user_orders:
        await callback.answer("❌ Ошибка. Начните заказ заново.")
        return
    
    order_data = user_orders[user_id]
    
    # Сохраняем заказ в базу данных
    order_id = db.add_order(
        user_id=user_id,
        username=username,
        product=order_data['product'],
        packaging=order_data['packaging'],
        address=order_data['address'],
        delivery_time=order_data['delivery_time']
    )
    
    # Переходим к выбору способа оплаты
    price_part = f"{int(order_data['price']) if isinstance(order_data.get('price'), (int, float)) and float(order_data['price']).is_integer() else order_data.get('price')} ₽" if order_data.get('price') is not None else "—"
    # Генерируем номер заказа (псевдослучайный)
    order_number = secrets.randbelow(900000) + 100000  # шестизначный
    user_orders[user_id]['order_number'] = order_number
    payment_text = (
        f"🧾 *Ваш заказ создан!*\n\n"
        f"#️⃣ *Номер заказа:* {order_number}\n"
        f"🛒 *Товар:* {order_data['product']} ({order_data['packaging']})\n"
        f"💵 *Стоимость:* {price_part}\n"
        f"⏳ *Доставка:* {order_data['delivery_time']} мин.\n\n"
        f"Выберите способ оплаты:" 
    )
    await safe_edit_text(callback.message, payment_text, reply_markup=get_payment_method_keyboard())
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "show_payment_methods",
            details=f"order_id={order_id}",
            username=username,
            product=order_data['product'],
            packaging=order_data['packaging'],
            amount=price_part,
            order_number=order_number,
        )
@dp.callback_query(F.data == "pay_card")
async def pay_card_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_orders:
        # Допустим, данные могли очиститься; просто покажем инструкции без суммы
        amount_text = "—"
        product_text = "—"
    else:
        data = user_orders[user_id]
        amount_text = f"{int(data['price']) if isinstance(data.get('price'), (int, float)) and float(data['price']).is_integer() else data.get('price')} ₽" if data.get('price') is not None else "—"
        product_text = f"{data['product']} ({data['packaging']})"

    # Реквизиты карты можно хранить в .env (например, CARD_NUMBER). Пока покажем плейсхолдер.
    card_number = os.getenv("CARD_NUMBER", "2200 0000 0000 0000")
    # Запускаем таймер на оплату: 10 минут
    user_orders.setdefault(user_id, {})
    user_orders[user_id]['payment_deadline'] = time.time() + 10 * 60
    payment_details = (
        f"📇 *Реквизиты для оплаты:*\n`{card_number}`\n\n"
        f"#️⃣ *Номер заказа:* {user_orders.get(user_id, {}).get('order_number', '—')}\n"
        f"💰 *Сумма к оплате:* {amount_text}\n"
        f"🎁 *Товар:* {product_text}\n\n"
        f"⚠️ *Важно:* после оплаты нажмите 'Подтвердить оплату'\n"
        f"⏳ *Время на оплату:* 10 минут"
    )
    await safe_edit_text(callback.message, payment_details, reply_markup=get_payment_confirm_keyboard())
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "pay_method_selected",
            method="card",
            username=callback.from_user.username,
            product=data.get('product') if user_id in user_orders else None,
            packaging=data.get('packaging') if user_id in user_orders else None,
            amount=amount_text,
            order_number=user_orders.get(user_id, {}).get('order_number'),
        )

@dp.callback_query(F.data == "confirm_payment")
async def confirm_payment_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Проверка таймера оплаты
    deadline = user_orders.get(user_id, {}).get('payment_deadline')
    if deadline is None or time.time() > deadline:
        from config import SUPPORT_USERNAME
        from keyboards import get_payment_retry_keyboard
        expired_text = (
            f"⏰ *Время на оплату истекло.*\n\n"
            f"Если вы уже оплатили — отправьте чек оператору: {SUPPORT_USERNAME}.\n"
            f"Нажмите 'Попробовать ещё раз', чтобы получить новые реквизиты."
        )
        await safe_edit_text(callback.message, expired_text, reply_markup=get_payment_retry_keyboard())
        if logger:
            await log_payment_event(
                logger,
                user_id,
                "payment_time_expired",
                username=callback.from_user.username,
                product=user_orders.get(user_id, {}).get('product'),
                packaging=user_orders.get(user_id, {}).get('packaging'),
                amount=(f"{int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders.get(user_id, {}).get('price') is not None else None),
                order_number=user_orders.get(user_id, {}).get('order_number'),
                method="card",
            )
        return
    searching_text = "🔎 *Ищем ваш платёж в системе…*"
    await safe_edit_text(callback.message, searching_text)
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "confirm_payment_clicked",
            username=callback.from_user.username,
            product=user_orders.get(user_id, {}).get('product'),
            packaging=user_orders.get(user_id, {}).get('packaging'),
            amount=(f"{int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders.get(user_id, {}).get('price') is not None else None),
            order_number=user_orders.get(user_id, {}).get('order_number'),
        )
    await asyncio.sleep(10)
    from config import SUPPORT_USERNAME
    from keyboards import get_payment_retry_keyboard
    fail_text = (
        f"❌ *Платёж не найден.*\n\n"
        f"Если вы уже оплатили — отправьте чек оператору: {SUPPORT_USERNAME}.\n"
        f"Или попробуйте позже."
    )
    await safe_edit_text(callback.message, fail_text, reply_markup=get_payment_retry_keyboard())
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "payment_not_found",
            username=callback.from_user.username,
            product=user_orders.get(user_id, {}).get('product'),
            packaging=user_orders.get(user_id, {}).get('packaging'),
            amount=(f"{int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders.get(user_id, {}).get('price') is not None else None),
            order_number=user_orders.get(user_id, {}).get('order_number'),
            method="card",
        )

@dp.callback_query(F.data == "retry_payment")
async def retry_payment_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    searching_text = "🔎 *Ищем ваш платёж в системе…*"
    await safe_edit_text(callback.message, searching_text)
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "retry_payment_clicked",
            username=callback.from_user.username,
            product=user_orders.get(user_id, {}).get('product'),
            packaging=user_orders.get(user_id, {}).get('packaging'),
            amount=(f"{int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders.get(user_id, {}).get('price') is not None else None),
            order_number=user_orders.get(user_id, {}).get('order_number'),
            method="card",
        )
    await asyncio.sleep(10)
    from config import SUPPORT_USERNAME
    from keyboards import get_payment_retry_keyboard
    fail_text = (
        f"❌ *Платёж не найден.*\n\n"
        f"Если вы уже оплатили — отправьте чек оператору: {SUPPORT_USERNAME}.\n"
        f"Или попробуйте позже."
    )
    await safe_edit_text(callback.message, fail_text, reply_markup=get_payment_retry_keyboard())
    if logger:
        await log_payment_event(
            logger,
            user_id,
            "payment_not_found",
            username=callback.from_user.username,
            product=user_orders.get(user_id, {}).get('product'),
            packaging=user_orders.get(user_id, {}).get('packaging'),
            amount=(f"{int(user_orders[user_id]['price']) if isinstance(user_orders[user_id].get('price'), (int, float)) and float(user_orders[user_id]['price']).is_integer() else user_orders[user_id].get('price')} ₽" if user_orders.get(user_id, {}).get('price') is not None else None),
            order_number=user_orders.get(user_id, {}).get('order_number'),
            method="card",
        )

@dp.callback_query(F.data == "copy_card")
async def copy_card_handler(callback: CallbackQuery):
    card_number = os.getenv("CARD_NUMBER", "2200 0000 0000 0000")
    # Показываем всплывающее окно без отправки нового сообщения в чат
    await callback.answer(f"Номер карты:\n{card_number}", show_alert=True)
    # Дополнительно логируем событие копирования
    if logger:
        await log_payment_event(logger, callback.from_user.id, "copy_card_clicked")

@dp.callback_query(F.data == "cancel_order")
async def cancel_order_handler(callback: CallbackQuery):
    """Обработчик отмены заказа"""
    user_id = callback.from_user.id
    
    # Очищаем данные заказа
    if user_id in user_orders:
        del user_orders[user_id]
    
    await safe_edit_text(callback.message, "❌ Заказ отменен.\n\nВыберите нужный раздел:", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    """Обработчик возврата в главное меню"""
    await safe_edit_text(callback.message, "👋 Главное меню\n\nВыберите нужный раздел:", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "back_to_products")
async def back_to_products_handler(callback: CallbackQuery):
    """Обработчик возврата к выбору товаров"""
    await safe_edit_text(callback.message, "🛒 Выберите товар:", reply_markup=get_products_keyboard())

# Административные функции
@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Обработчик статистики для администратора"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    stats = db.get_order_stats()
    user_count = db.get_user_count()
    stats_text = (
        f"📊 *Статистика:*\n\n"
        f"👥 *Пользователей:* {user_count}\n"
        f"📈 *Всего заказов:* {stats['total']}\n"
        f"📅 *За сегодня:* {stats['today']}\n"
        f"📊 *За неделю:* {stats['week']}"
    )
    
    await safe_edit_text(callback.message, stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_orders")
async def admin_orders_handler(callback: CallbackQuery):
    """Обработчик просмотра заказов для администратора"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    orders = db.get_orders(limit=10)
    
    if not orders:
        orders_text = "📋 Заказов пока нет."
    else:
        orders_text = "📋 **Последние заказы:**\n\n"
        for order in orders:
            orders_text += (
                f"🆔 **ID:** {order[0]}\n"
                f"👤 **Клиент:** @{order[2]}\n"
                f"🛒 **Товар:** {order[3]}\n"
                f"📦 **Фасовка:** {order[4]}\n"
                f"🏠 **Адрес:** {order[5]}\n"
                f"📅 **Дата:** {order[7]}\n\n"
            )
    
    await safe_edit_text(callback.message, orders_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Нет доступа")
        return
    await safe_edit_text(callback.message, "📢 *Рассылка*\n\nОтправьте текст сообщения для рассылки всем пользователям:")
    await state.set_state(AdminStates.waiting_for_broadcast_text)

@dp.message(AdminStates.waiting_for_broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ Нет доступа")
        return
    text = message.text
    user_ids = db.get_all_user_ids()
    ok, fail = 0, 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
            continue
    await message.answer(f"📢 Готово. Успешно: {ok}, ошибок: {fail}", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_reply")
async def admin_reply_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответа пользователю для администратора"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    await safe_edit_text(callback.message, "💬 **Ответ пользователю**\n\nВведите ID пользователя:")
    await state.set_state(AdminStates.waiting_for_user_id)

@dp.message(AdminStates.waiting_for_user_id)
async def admin_user_id_handler(message: Message, state: FSMContext):
    """Обработчик ввода ID пользователя"""
    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        
        await message.answer("Введите сообщение для пользователя:")
        await state.set_state(AdminStates.waiting_for_admin_message)
    except ValueError:
        await message.answer("❌ Неверный ID пользователя. Попробуйте снова.")

@dp.message(AdminStates.waiting_for_admin_message)
async def admin_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода сообщения администратора"""
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    admin_message = message.text
    
    try:
        # Отправляем сообщение пользователю
        await bot.send_message(
            target_user_id,
            f"💬 **Сообщение от администратора:**\n\n{admin_message}"
        )
        
        # Сохраняем ответ в базу данных
        db.add_admin_response(target_user_id, admin_message)
        
        # Логируем действие администратора
        if logger:
            try:
                await log_admin_action(
                    logger=logger,
                    admin_id=message.from_user.id,
                    action="Отправка сообщения пользователю",
                    details=f"Пользователь ID: {target_user_id}, Сообщение: {admin_message[:50]}..."
                )
            except Exception as e:
                await log_error(logger, f"Ошибка логирования действия администратора: {e}")
        
        await message.answer(
            f"✅ Сообщение отправлено пользователю {target_user_id}",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        if logger:
            await log_error(logger, f"Ошибка отправки сообщения администратора: {e}")
        await message.answer(
            f"❌ Ошибка отправки сообщения: {e}",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data == "admin_main")
async def admin_main_handler(callback: CallbackQuery):
    """Обработчик возврата в главное меню администратора"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    await safe_edit_text(callback.message, "🔧 Панель администратора\n\nВыберите действие:", reply_markup=get_admin_keyboard())

async def main():
    """Главная функция запуска бота"""
    global logger
    
    # Инициализируем логирование после запуска event loop
    logger = setup_logging(bot)
    
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 