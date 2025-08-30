import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, text, inspect
from models import Base, User, Payment, UserAction, BotSettings, AdminLevel, PromoCode, Order, OrderStatus, StashType, UserAddress, Product, PaymentMethod
import config
import json
from datetime import datetime, timedelta
import random
import requests
import signal
import sys
import os
import time
from typing import List
from aiogram.exceptions import TelegramBadRequest  # Добавляем импорт TelegramBadRequest

# Constants for commissions
CARD_COMMISSION = 0.05  # 5%
CRYPTO_COMMISSION = 0.005  # 0.5%

# --- NEW: TXT FILES READING ---
# Кэш для товаров по городам
products_cache = {}  # ключ: (city, district)
CACHE_TTL = 24 * 60 * 60  # 24 часа в секундах

def get_products_for_district(city: str, district: str) -> List[dict]:
    """Получение случайных продуктов для района с кэшированием на 24 часа"""
    now = time.time()
    cache_key = (city, district)
    cache_entry = products_cache.get(cache_key)
    if cache_entry:
        products, timestamp = cache_entry
        if now - timestamp < CACHE_TTL:
            return products
    try:
        products = []
        with open('products.txt', 'r', encoding='utf-8') as file:
            for line in file:
                parts = line.strip().split(';')
                if len(parts) >= 3:
                    name, weight, price = parts[:3]
                    stash_emoji = random.choice(['🧲', '💎'])
                    stash_type = 'магнит' if stash_emoji == '🧲' else 'клад'
                    products.append({
                        'id': len(products),
                        'name': f"{stash_emoji} {name}",
                        'weight': weight,
                        'price': float(price),
                        'stash_type': stash_type,
                        'stash_emoji': stash_emoji
                    })
        num_products = random.randint(3, 7)
        selected_products = random.sample(products, min(num_products, len(products)))
        products_cache[cache_key] = (selected_products, now)
        return selected_products
    except Exception as e:
        logger.error(f"Error in get_products_for_district: {e}")
        return []

# Добавляем проверку на бан для всех действий пользователя
async def check_user_banned(message: types.Message) -> bool:
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if user and user.is_banned:
            await message.answer("🚫 Вы забанены в боте. Обратитесь к администратору.")
            return True
    return False

def get_districts_for_city(city: str) -> List[str]:
    """Получение списка районов для города из файла districts.txt"""
    logger.info(f"Attempting to get districts for city: {city}")
    districts = []
    try:
        with open('districts.txt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(';')
                logger.info(f"Processing line: {line.strip()}")
                logger.info(f"Split parts: {parts}")
                if len(parts) > 1:
                    current_city = parts[0].strip()
                    district = parts[1].strip()
                    logger.info(f"Comparing cities: '{current_city}' with '{city}'")
                    if current_city.lower() == city.lower():  # Сравниваем без учета регистра
                        logger.info(f"Found matching district: {district}")
                        districts.append(district)
        
        logger.info(f"Found {len(districts)} districts for city {city}: {districts}")
        return districts
    except FileNotFoundError:
        logger.error("districts.txt not found during district retrieval.")
    except Exception as e:
        logger.error(f"Error reading districts.txt for districts for city {city}: {e}")
    return districts

# --- END TXT FILES READING ---

# --- NEW: CITIES AND DISTRICTS READING ---
def get_unique_cities():
    cities = set()
    try:
        with open('districts.txt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(';')
                if len(parts) > 0:
                    cities.add(parts[0])
    except Exception as e:
        logging.error(f"Error reading districts.txt for cities: {e}")
    return list(cities)

def get_all_products():
    products = []
    try:
        with open('products.txt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(';')
                # Ensure at least 4 parts (name, weight, price, quantity)
                if len(parts) >= 4:
                    product = {
                        'name': parts[0],
                        'weight': parts[1],
                        'price': float(parts[2]),  # Convert price to float
                        'quantity': int(parts[3]), # Read quantity as integer
                        'description': parts[4] if len(parts) > 4 else "", # Get description if available
                        'photo': parts[5] if len(parts) > 5 else None # Get photo if available
                    }
                    products.append(product)
                else:
                    logging.warning(f"Skipping invalid line in products.txt (less than 4 fields): {line.strip()}")
    except FileNotFoundError:
        logging.error("products.txt not found.")
        return []
    except ValueError as e:
        logging.error(f"Error converting values in products.txt: {e}")
        return []
    except Exception as e:
        logging.error(f"Error reading products.txt: {e}")
    return products

# --- END CITIES AND DISTRICTS READING ---

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(config.DATABASE_URL)

# Add migration for created_at column
with Session(engine) as session:
    try:
        # Check if created_at column exists using SQLAlchemy text()
        result = session.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result]
        
        if 'created_at' not in columns:
            # Add created_at column with default value
            session.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            session.commit()
            logger.info("Successfully added created_at column to users table")
        
        # Check if is_blocked column exists in users table
        if 'is_blocked' not in columns:
            session.execute(text("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE"))
            session.commit()
            logger.info("Added is_blocked column to users table")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        session.rollback()

# Create all tables
Base.metadata.create_all(engine)

# Initialize bots and dispatcher
bot = Bot(token=config.MAIN_BOT_TOKEN)
info_bot = Bot(token=config.INFO_BOT_TOKEN)  # Initialize info_bot
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States
class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_city = State()
    waiting_for_payment = State()
    waiting_for_user_id = State()
    waiting_for_setting_value = State()
    waiting_for_topup_amount = State()
    waiting_for_withdraw_amount = State()
    waiting_for_broadcast_message = State()
    waiting_for_promo_code = State()
    waiting_for_promo_amount = State()
    waiting_for_promo_percent = State()  # Добавляем новое состояние
    waiting_for_promo_limit = State()    # Добавляем новое состояние
    waiting_for_city_selection = State()
    waiting_for_district_selection = State()
    waiting_for_product_selection = State()
    waiting_for_buy_confirmation = State()
    waiting_for_payment_confirmation = State()
    waiting_for_order_note = State()
    waiting_for_address = State()
    waiting_for_address_description = State()
    waiting_for_order_amount = State()  # Новое состояние для ввода суммы заказа
    waiting_for_payment_details = State()  # New state for payment details
    in_admin_panel = State()
    in_settings = State()

# Получить главное меню (ReplyKeyboardMarkup)
def get_main_keyboard(is_admin=False, is_worker=False, balance=0.0):
    keyboard = [
        [KeyboardButton(text="Города")],
        [KeyboardButton(text="Доставка 🏎")],
        [KeyboardButton(text="👽 Оператор"), KeyboardButton(text="🛠️ Поддержка")],
        [KeyboardButton(text="💬 MATRAS чат")],
        [KeyboardButton(text="📍 Мои адреса")],
        [KeyboardButton(text="📦 Мои заказы")],
        [KeyboardButton(text=f"Баланс ({balance} руб.)")],
        [KeyboardButton(text="🎟️ Ввести промокод")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Админ-панель")])
    if is_worker:
        keyboard.append([KeyboardButton(text="Воркер-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Показывать главное меню
async def show_main_menu(message, user=None):
    if user is None:
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    is_admin = user.is_admin if user else False
    is_worker = user.is_worker if user else False
    balance = user.balance if user else 0.0
    reply_markup = get_main_keyboard(is_admin, is_worker, balance)
    await message.answer("Вы в главном меню", reply_markup=reply_markup)

# Капча: после прохождения всегда показывать главное меню
@dp.message(UserStates.waiting_for_captcha)
async def check_captcha(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answer = data.get("captcha_answer")
    try:
        if int(message.text) == answer:
            await message.answer("Капча пройдена!")
            await state.clear()
            # Получаем приветствие из настроек
            with Session(engine) as session:
                setting = session.query(BotSettings).filter_by(key="welcome_message").first()
                if setting and setting.value:
                    welcome_text = setting.value
                else:
                    welcome_text = "💎ТОПОВОЕ КАЧЕСТВО, СОБСТВЕНОГО ПРОИЗВОДСТВА 💎\n\n🪐Адреса только город, не лес! 70% адресов на магнитах, \nне какой грязи , и  больших трат на такси🪐\n\n👽Наш товар высшего качества\n👽Мы работаем круглосуточно \n👽Удобный способ оплаты\n👽Качественные\n👽Проверенные клады"
            await message.answer(welcome_text)
            await show_main_menu(message)
        else:
            await message.answer("Неверно. Попробуйте снова.")
    except Exception:
        await message.answer("Введите число.")

# Обработка /start с параметром worker
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext = None):
    user = message.from_user
    args = message.text.split()
    with Session(engine) as session:
        db_user = session.query(User).filter_by(telegram_id=user.id).first()
        if not db_user:
            is_worker = len(args) > 1 and args[1] == "worker"
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_worker=is_worker,
                balance=0.0,
                is_admin=user.id in config.ADMIN_IDS,
                admin_level=AdminLevel.SUPER_ADMIN if user.id == config.SUPER_ADMIN_ID else AdminLevel.ADMIN if user.id in config.ADMIN_IDS else None
            )
            session.add(db_user)
            session.commit()
        else:
            # Если пользователь зашел по ссылке воркера, обновить статус
            if len(args) > 1 and args[1] == "worker" and not db_user.is_worker:
                db_user.is_worker = True
                session.commit()
    # Капча
    a, b = random.randint(1, 9), random.randint(1, 9)
    await message.answer(f"Капча: сколько будет {a} + {b}?")
    await state.update_data(captcha_answer=a + b)
    await state.set_state(UserStates.waiting_for_captcha)

# Обработка кнопок главного меню
@dp.message(F.text == "Города")
async def menu_cities(message: types.Message, state: FSMContext):
    if await check_user_banned(message):
        return
    await log_user_action(message.from_user.id, "button_click", {"button": "Города"})
    cities = get_unique_cities()
    if not cities:
        await message.answer("Список городов пуст.")
        return
    
    # Создаем кнопки по 2 в ряд
    keyboard = []
    cities_list = sorted(cities)  # Сортируем города по алфавиту
    for i in range(0, len(cities_list), 2):
        row = []
        row.append(InlineKeyboardButton(text=cities_list[i], callback_data=f"city_{cities_list[i]}"))
        if i + 1 < len(cities_list):
            row.append(InlineKeyboardButton(text=cities_list[i+1], callback_data=f"city_{cities_list[i+1]}"))
        keyboard.append(row)
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите город:", reply_markup=markup)
    await state.set_state(UserStates.waiting_for_city_selection)

@dp.callback_query(F.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    try:
        city = callback.data.split('_')[1]
        await state.update_data(selected_city=city)
        await show_districts(callback.message, city)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in select_city: {e}")
        await callback.answer("Произошла ошибка при выборе города")

@dp.callback_query(F.data == "back_to_cities")
async def back_to_cities(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Логируем возврат к выбору города
        await log_user_action(
            info_bot,
            callback.from_user.id,
            "back_to_cities",
            {
                "button": callback.data
            }
        )
        
        await state.set_state(UserStates.waiting_for_city_selection)
        await callback.message.edit_text(
            "Выберите город:",
            reply_markup=get_cities_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in back_to_cities: {e}")
        await callback.answer("Произошла ошибка при возврате к выбору города")
        await state.clear()
        await show_main_menu(callback.message)

@dp.callback_query(F.data.startswith("dist_"))
async def select_district(callback: types.CallbackQuery, state: FSMContext):
    try:
        district = callback.data.split('_')[1]
        data = await state.get_data()
        city = data.get("selected_city")
        
        if not city:
            await callback.answer("Ошибка: город не выбран")
            return
            
        await state.update_data(selected_district=district)
        await state.set_state(UserStates.waiting_for_product_selection)
        
        # Логируем выбор района
        await log_user_action(
            info_bot,
            callback.from_user.id,
            "district_selected",
            {
                "city": city,
                "district": district,
                "button": callback.data
            }
        )
        
        # Было:
        # products = get_products_for_city(city)
        # Стало:
        products = get_products_for_district(city, district)
        if not products:
            await callback.answer("Нет доступных товаров", show_alert=True)
            return
            
        # Создаем клавиатуру с товарами
        keyboard = []
        for i, product in enumerate(products):
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{product['name']} ({product['weight']}) - {product['price']} руб.",
                    callback_data=f"prod_{i}"
                )
            ])
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_cities")])
        
        # Сохраняем список товаров в state для последующего использования
        await state.update_data(products=products)
        
        await callback.message.edit_text(
            f"Выберите товар в районе {district}:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    except Exception as e:
        logger.error(f"Error in select_district: {e}")
        await callback.answer("Произошла ошибка при выборе района")
        await state.clear()
        await show_main_menu(callback.message)

@dp.callback_query(F.data.startswith("prod_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    try:
        product_index = int(callback.data.split('_')[1])
        data = await state.get_data()
        products = data.get("products")
        city = data.get("selected_city")
        district = data.get("selected_district")
        
        if not all([products, city, district]):
            await callback.answer("Ошибка: данные не найдены")
            return
            
        if product_index >= len(products):
            await callback.answer("Ошибка: товар не найден")
            return
            
        product = products[product_index]
        await state.update_data(selected_product=product)
        await state.set_state(UserStates.waiting_for_buy_confirmation)
        
        # Логируем выбор товара
        await log_user_action(
            info_bot,
            callback.from_user.id,
            "product_selected",
            {
                "city": city,
                "district": district,
                "product": product,
                "button": callback.data
            }
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Купить", callback_data=f"buy_product_{product_index}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
        ])
        
        await callback.message.edit_text(
            f"Подтвердите покупку:\n\n"
            f"Город: {city}\n"
            f"Район: {district}\n"
            f"Товар: {product['name']} ({product['weight']})\n"
            f"Цена: {product['price']} руб.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in select_product: {e}")
        await callback.answer("Произошла ошибка при выборе товара")
        await state.clear()
        await show_main_menu(callback.message)

@dp.callback_query(F.data.startswith("buy_product_"))
async def confirm_buy(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        product = data.get('selected_product')
        selected_district = data.get('selected_district')
        if not all([product, selected_district]):
            await callback.answer("Информация о товаре или районе не найдена", show_alert=True)
            return
        stash_type = product.get('stash_type', 'клад')
        order_number = random.randint(100000, 999999)
        CARD_COMMISSION = 0.05
        CRYPTO_COMMISSION = 0.005
        
        # Применяем скидку к базовой цене
        base_price = product['price']
        promo_percent = data.get('promo_percent')
        promo_code = data.get('active_promo_code')
        discount_text = ""
        
        logger.info(f"[confirm_buy] Initial base_price: {base_price}, promo_percent: {promo_percent}")

        if promo_percent:
            try:
                promo_percent_float = float(promo_percent)
                discount = base_price * promo_percent_float / 100
                base_price = max(0, base_price - discount)
                discount_text = f"\n🎟️ Применён промокод: -{promo_percent}%"
                logger.info(f"[confirm_buy] Discount applied. New base_price: {base_price}")
            except ValueError:
                logger.warning(f"[confirm_buy] Invalid promo_percent value: {promo_percent}")
        
        # Применяем комиссии к цене со скидкой
        card_price = base_price * (1 + CARD_COMMISSION)
        crypto_price = base_price * (1 + CRYPTO_COMMISSION)
        logger.info(f"[confirm_buy] Final card_price: {card_price}, crypto_price: {crypto_price}")
        
        with Session(engine) as session:
            order = Order(
                order_number=str(order_number),
                user_id=callback.from_user.id,
                product_name=product['name'],
                product_weight=product['weight'],
                price=base_price,  # Сохраняем цену со скидкой
                commission=CARD_COMMISSION,
                total_price=card_price,
                district=selected_district,
                stash_type=StashType.MAGNET if stash_type == 'магнит' else StashType.STASH,
                status=OrderStatus.PENDING,
                payment_method=None
            )
            session.add(order)
            # Если был промокод — увеличить activations и, если лимит, пометить как использованный
            if promo_code:
                promo = session.query(PromoCode).filter_by(code=promo_code).first()
                if promo:
                    promo.activations += 1
                    if promo.activations >= promo.max_activations:
                        promo.is_used = True
                    promo.used_at = datetime.now()
            session.commit()
        await state.update_data(
            order_number=order_number,
            product=product,
            district=selected_district,
            card_price=card_price,
            crypto_price=crypto_price,
            stash_type=stash_type
        )
        order_details = (
            f"🛍 <b>Ваш заказ #{order_number}</b>\n\n"
            f"📍 Район: {selected_district}\n"
            f"📦 Товар: {product['name'].split(' ', 1)[-1]} ({product['weight']})\n"
            f"💰 Стоимость: {base_price:.1f} руб.\n"
            f"🗺 Тип тайника: {'Магнит 🧲' if stash_type == 'магнит' else 'Тайник 🗺'}\n\n"
            f"💳 Оплата картой: {card_price:.2f} руб. (комиссия {int(CARD_COMMISSION * 100)}%)\n"
            f"₿ BTC: {crypto_price:.2f} руб. (комиссия {CRYPTO_COMMISSION * 100}%)\n"
            f"💵 USDT: {crypto_price:.2f} руб. (комиссия {CRYPTO_COMMISSION * 100}%)\n"
            f"{discount_text}\n\n"
            f"Выберите способ оплаты:"
        )
        payment_methods_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перевод на карту", callback_data=f"pay_method_card_{order_number}")],
            [InlineKeyboardButton(text="Оплатить USDT", callback_data=f"pay_method_usdt_{order_number}")],
            [InlineKeyboardButton(text="Оплатить BTC", callback_data=f"pay_method_btc_{order_number}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
        ])
        await callback.message.edit_text(
            order_details,
            reply_markup=payment_methods_keyboard,
            parse_mode="HTML"
        )
        await state.update_data(active_promo_code=None, promo_percent=None)
    except Exception as e:
        logger.error(f"Error in confirm_buy: {e}")
        await callback.answer("Ошибка при оформлении заказа", show_alert=True)

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Логируем отмену заказа
        await log_user_action(
            info_bot,
            callback.from_user.id,
            "order_cancelled",
            {
                "button": callback.data
            }
        )
        
        await state.clear()
        await callback.message.edit_text("Заказ отменен")
        await show_main_menu(callback.message)
    except Exception as e:
        logger.error(f"Error in cancel_order: {e}")
        await callback.answer("Произошла ошибка при отмене заказа")
        await state.clear()
        await show_main_menu(callback.message)

@dp.message(F.text == "👽 Оператор")
async def menu_operator(message: types.Message):
    if await check_user_banned(message):
        return
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "Оператор"})
    with Session(engine) as session:
        setting = session.query(BotSettings).filter_by(key="operator").first()
        operator = setting.value if setting else "@matras_operator"
    await message.answer(f"Связь с оператором: {operator}")

@dp.message(F.text == "🛠️ Поддержка")
async def menu_support(message: types.Message):
    if await check_user_banned(message):
        return
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "Поддержка"})
    with Session(engine) as session:
        setting = session.query(BotSettings).filter_by(key="support").first()
        support = setting.value if setting else "@matras_support"
    await message.answer(f"Техподдержка: {support}")

@dp.message(F.text == "💬 MATRAS чат")
async def menu_chat(message: types.Message):
    if await check_user_banned(message):
        return
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "MATRAS чат"})
    with Session(engine) as session:
        setting = session.query(BotSettings).filter_by(key="chat").first()
        chat = setting.value if setting else "@matras_chat"
    await message.answer(f"Чат: {chat}")

@dp.message(F.text.startswith("Баланс"))
async def menu_balance(message: types.Message):
    try:
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if user:
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup_balance")],
                    [InlineKeyboardButton(text="💳 Вывод средств", callback_data="withdraw_balance")]
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                await message.answer(
                    f"💰 Ваш баланс: {user.balance} руб.\n\n"
                    f"Выберите действие:",
                    reply_markup=markup
                )
    except Exception as e:
        logger.error(f"Error in menu_balance: {e}")
        await message.answer("Произошла ошибка при получении баланса")

@dp.callback_query(F.data == "topup_balance")
async def topup_balance(callback: types.CallbackQuery):
    try:
        # Создаем клавиатуру с методами оплаты
        keyboard = [
            [InlineKeyboardButton(text="💳 Карта", callback_data="topup_method_card")],
            [InlineKeyboardButton(text="₿ BTC", callback_data="topup_method_btc")],
            [InlineKeyboardButton(text="💵 USDT", callback_data="topup_method_usdt")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_balance")]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "Выберите способ оплаты:",
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in topup_balance: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("topup_method_"))
async def topup_method(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_type = callback.data.split('_')[2]  # card, btc или usdt
        # Получаем реквизиты для выбранного метода оплаты
        with Session(engine) as session:
            payment_method = session.query(PaymentMethod).filter_by(
                type=payment_type,
                is_active=True
            ).first()
            if not payment_method:
                await callback.answer("Нет доступных реквизитов для этого метода оплаты", show_alert=True)
                return
            # Создаем клавиатуру с кнопкой подтверждения
            keyboard = [
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_topup_{payment_type}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="topup_balance")]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            # Отправляем сообщение с реквизитами
            await callback.message.edit_text(
                f"💳 Реквизиты для пополнения:\n\n"
                f"{payment_method.details}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'",
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Error in topup_method: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_topup_"))
async def confirm_topup(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_type = callback.data.split('_')[2]
        
        # Показываем сообщение о поиске платежа
        await callback.message.edit_text(
            "🔍 Ищем ваш платеж...\n"
            "Пожалуйста, подождите..."
        )
        
        # Ждем 10 секунд
        await asyncio.sleep(10)
        
        # Показываем сообщение об ошибке
        keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="topup_balance")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "❌ Платеж не найден\n\n"
            "Если вы уже оплатили, пожалуйста, обратитесь к администратору",
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_topup: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data == "back_to_balance")
async def back_to_balance(callback: types.CallbackQuery):
    try:
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if user:
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="topup_balance")],
                    [InlineKeyboardButton(text="💳 Вывод средств", callback_data="withdraw_balance")]
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await callback.message.edit_text(
                    f"💰 Ваш баланс: {user.balance} руб.\n\n"
                    f"Выберите действие:",
                    reply_markup=markup
                )
    except Exception as e:
        logger.error(f"Error in back_to_balance: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.message(F.text == "Воркер-панель")
async def menu_worker_panel(message: types.Message):
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "Воркер-панель"})
    await show_worker_panel(message)

@dp.message(F.text == "Админ-панель")
async def menu_admin_panel(message: types.Message, state: FSMContext):
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "Админ-панель"})
    
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            await message.answer("Пользователь не найден в базе")
            return
            
        # Debug logging
        logger.info(f"User admin level: {user.admin_level}")
        
        if user.admin_level not in [AdminLevel.ADMIN, AdminLevel.SUPER_ADMIN]:
            await message.answer(f"У вас нет доступа к админ-панели. Ваш уровень: {user.admin_level}")
            return
            
    await state.set_state(UserStates.in_admin_panel)  # Set state when entering admin panel
    await show_admin_panel(message)

@dp.message(UserStates.in_admin_panel)
async def handle_admin_panel(message: types.Message, state: FSMContext):
    if message.text == "👥 Пользователи":
        await admin_users(message)
    elif message.text == "📊 Статистика":
        await admin_stats(message)
    elif message.text == "📝 Логи":
        await admin_logs(message)
    elif message.text == "⚙️ Настройки":
        await admin_settings(message, state)
    elif message.text == "💰 Пополнить баланс":
        await message.answer("Введите ID пользователя для пополнения баланса:")
        await state.set_state(UserStates.waiting_for_user_id)
        await state.update_data(action="topup")
        return
    elif message.text == "💳 Вывод средств":
        await admin_withdraw(message, state)
    elif message.text == "🚫 Бан":
        await admin_ban(message, state)
    elif message.text == "✅ Разбан":
        await admin_unban(message, state)
    elif message.text == "📦 История заказов":
        await admin_orders(message)
    elif message.text == "📍 Управление адресами":
        await admin_address_management(message)
    elif message.text == "📦 Управление заказами":
        await admin_order_management(message)
    elif message.text == "📢 Рассылка":
        await admin_broadcast_start(message, state)
    elif message.text == "🎁 Промокоды":
        await admin_promo_start(message, state)
    elif message.text == "⬅️ Назад":
        await state.clear()
        await show_main_menu(message)
    else:
        await message.answer("Выберите действие из меню:", reply_markup=get_admin_keyboard())

@dp.message(UserStates.waiting_for_topup_amount)
async def process_topup_amount(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_id = data.get('target_user_id')
        amount = float(message.text)
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await message.answer("❌ Пользователь не найден")
                await state.clear()
                await show_admin_panel(message)
                return
            user.balance += amount
            session.commit()
            await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount} руб.\nТекущий баланс: {user.balance} руб.")
        await state.clear()
        await show_admin_panel(message)
    except Exception as e:
        logger.error(f"Error in process_topup_amount: {e}")
        await message.answer("Произошла ошибка при пополнении баланса")
        await state.clear()
        await show_admin_panel(message)

# --- LOG TO INFO BOT ---
def send_log_to_info_bot(text):
    info_bot_token = config.INFO_BOT_TOKEN
    info_bot_id = config.INFO_BOT_CHAT_ID
    url = f"https://api.telegram.org/bot{info_bot_token}/sendMessage"
    data = {
        "chat_id": info_bot_id,
        "text": text
    }
    try:
        resp = requests.post(url, data=data, timeout=5)
        if resp.status_code != 200:
            logger.error(f"Failed to send log to info bot: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Failed to send log to info bot: {e}")

async def log_user_action(info_bot: Bot, user_id: int, action_type: str, details: dict = None):
    """Логирование действий пользователя"""
    try:
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return
                
            # Создаем запись в базе данных
            log = UserAction(
                user_id=user_id,
                action_type=action_type,
                action_data=json.dumps(details) if details else None
            )
            session.add(log)
            session.commit()
            
            # Формируем сообщение для лога
            log_message = f"📝 User Action Log:\nUser: {user.username or user.first_name} (ID: {user_id})\nAction: {action_type}"
            if details:
                log_message += f"\nDetails: {json.dumps(details, ensure_ascii=False, indent=2)}"
            
            # Отправляем лог в чат через инфобота
            try:
                await info_bot.send_message(
                    chat_id=config.INFO_BOT_CHAT_ID,
                    text=log_message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending log to info bot: {e}")
                
    except Exception as e:
        logger.error(f"Error in log_user_action: {e}")

async def get_user_balance(user_id):
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        return user.balance if user else 0.0

async def change_user_balance(user_id, amount):
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            user.balance += amount
            session.commit()
            return user.balance
        return None

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📝 Логи"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="💰 Пополнить баланс"), KeyboardButton(text="💳 Вывод средств")],
        [KeyboardButton(text="🚫 Бан"), KeyboardButton(text="✅ Разбан")],
        [KeyboardButton(text="📦 История заказов"), KeyboardButton(text="📍 Управление адресами")],
        [KeyboardButton(text="📦 Управление заказами")],
        [KeyboardButton(text="📢 Рассылка")],
        [KeyboardButton(text="🎁 Промокоды")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

async def show_admin_panel(message):
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.is_admin:
            await message.answer("У вас нет доступа к админ-панели.")
            return
            
        text = "🛡️ Админ-панель\n\nВыберите действие:"
        reply_markup = get_admin_keyboard()
        await message.answer(text, reply_markup=reply_markup)

# --- Admin Panel Handlers ---
@dp.message(F.text == "👥 Пользователи")
async def admin_users(message: types.Message, state: FSMContext = None):
    page = 0
    await show_users_page(message, page)

@dp.callback_query(F.data.startswith("users_page_"))
async def users_page_callback(callback: types.CallbackQuery):
    page = int(callback.data.split('_')[2])
    await show_users_page(callback.message, page, edit=True)
    await callback.answer()

async def show_users_page(message, page, edit=False):
    with Session(engine) as session:
        users = session.query(User).order_by(User.id).all()
        total_users = len(users)
        if not users:
            await message.answer("Нет пользователей в базе")
            return
        start = page * USERS_PER_PAGE
        end = start + USERS_PER_PAGE
        users_page = users[start:end]
        text = f"👥 Список пользователей (стр. {page+1}):\n\n"
        for user in users_page:
            text += f"ID: {user.telegram_id}\n"
            text += f"Username: @{user.username}\n"
            text += f"Баланс: {user.balance} руб.\n"
            text += f"Статус: {'🚫 Забанен' if user.is_banned else '✅ Активен'}\n"
            text += f"Админ: {'✅' if user.is_admin else '❌'}\n"
            text += f"Воркер: {'✅' if user.is_worker else '❌'}\n"
            text += "-------------------\n"
        # Кнопки пагинации
        keyboard = []
        if start > 0:
            keyboard.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"users_page_{page-1}"))
        if end < total_users:
            keyboard.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"users_page_{page+1}"))
        markup = InlineKeyboardMarkup(inline_keyboard=[keyboard] if keyboard else [])
        if edit:
            await message.edit_text(text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    with Session(engine) as session:
        total_users = session.query(User).count()
        active_users = session.query(User).filter_by(is_banned=False).count()
        banned_users = session.query(User).filter_by(is_banned=True).count()
        blocked_users = session.query(User).filter_by(is_blocked=True).count() # Добавляем подсчет заблокированных
        total_orders = session.query(Order).count()
        completed_orders = session.query(Order).filter_by(status=OrderStatus.COMPLETED).count()
        total_balance = session.query(func.sum(User.balance)).scalar() or 0
        
        text = "📊 Статистика бота:\n\n"
        text += f"👥 Всего пользователей: {total_users}\n"
        text += f"✅ Активных пользователей: {active_users}\n"
        text += f"🚫 Забаненных пользователей: {banned_users}\n"
        text += f"⛔ Заблокировали бота: {blocked_users}\n" # Отображаем количество заблокированных
        text += f"📦 Всего заказов: {total_orders}\n"
        text += f"✅ Выполненных заказов: {completed_orders}\n"
        text += f"💰 Общий баланс: {total_balance} руб."
        
        await message.answer(text)

@dp.message(F.text == "📝 Логи")
async def admin_logs(message: types.Message):
    with Session(engine) as session:
        logs = session.query(UserAction).order_by(UserAction.timestamp.desc()).limit(50).all()
        if not logs:
            await message.answer("Нет логов")
            return
            
        text = "📝 Последние 50 действий:\n\n"
        for log in logs:
            user = session.query(User).filter_by(telegram_id=log.user_id).first()
            username = user.username if user else "Неизвестный"
            text += f"👤 @{username} (ID: {log.user_id})\n"
            text += f"📝 Действие: {log.action_type}\n"
            text += f"📅 Время: {log.timestamp}\n"
            text += "-------------------\n"
            
        await message.answer(text)

def get_settings_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Поддержка", callback_data="change_support")],
        [InlineKeyboardButton(text="👽 Оператор", callback_data="change_operator")],
        [InlineKeyboardButton(text="💳 Управление картами", callback_data="manage_cards")],
        [InlineKeyboardButton(text="₿ Управление BTC", callback_data="manage_btc")],
        [InlineKeyboardButton(text="💵 Управление USDT", callback_data="manage_usdt")],
        [InlineKeyboardButton(text="💬 Чат", callback_data="change_chat")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")]
    ])
    return keyboard

async def is_admin(user_id: int) -> bool:
    try:
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            return user and user.admin_level in [AdminLevel.ADMIN, AdminLevel.SUPER_ADMIN]
    except Exception as e:
        logger.error(f"Error in is_admin check: {e}")
        return False

@dp.message(F.text == "⚙️ Настройки")
async def admin_settings(message: types.Message, state: FSMContext):
    try:
        if not await is_admin(message.from_user.id):
            await message.answer("У вас нет доступа к этой функции.")
            return
            
        await state.set_state(UserStates.in_settings)
        keyboard = get_settings_keyboard()
        await message.answer("Выберите настройку для изменения:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in admin_settings: {e}")
        await message.answer("Произошла ошибка при открытии настроек")
        await state.clear()
        await show_main_menu(message)

@dp.callback_query(F.data.startswith("change_"))
async def handle_setting_change(callback: types.CallbackQuery, state: FSMContext):
    try:
        setting_type = callback.data.split('_')[1]
        setting_key = {
            'support': 'support',
            'operator': 'operator',
            'card': 'card',
            'chat': 'chat',
            'btc': 'crypto_btc',
            'usdt': 'crypto_usdt'
        }.get(setting_type)
        
        if not setting_key:
            await callback.answer("Неизвестный тип настройки")
            return
            
        await state.set_state(UserStates.waiting_for_setting_value)
        await state.update_data(setting_key=setting_key)
        
        current_value = get_bot_setting(setting_key)
        await callback.message.answer(
            f"Текущее значение: {current_value}\n"
            f"Введите новое значение:"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in handle_setting_change: {e}")
        await callback.answer("Произошла ошибка при выборе настройки")
        await state.clear()
        await show_admin_panel(callback.message)

async def show_settings_panel(message: types.Message):
    """Показать панель настроек"""
    try:
        with Session(engine) as session:
            settings = session.query(BotSettings).first()
            if not settings:
                await message.answer("❌ Ошибка: настройки не найдены")
                return
                
            settings_text = (
                "⚙️ <b>Настройки бота:</b>\n\n"
                f"👥 Поддержка: {settings.support}\n"
                f"👨‍💼 Оператор: {settings.operator}\n"
                f"💳 Реквизиты карты: {settings.card_details}\n"
                f"₿ Реквизиты крипты: {settings.crypto_details}\n"
                f"💬 Чат: {settings.chat}\n\n"
                "Выберите настройку для изменения:"
            )
            
            keyboard = get_settings_keyboard()
            await message.answer(settings_text, reply_markup=keyboard, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error in show_settings_panel: {e}")
        await message.answer("Произошла ошибка при загрузке настроек")

@dp.message(UserStates.waiting_for_setting_value)
async def process_setting_value(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        setting_key = data.get("setting_key")
        
        with Session(engine) as session:
            settings = session.query(BotSettings).first()
            if not settings:
                await message.answer("❌ Ошибка: настройки не найдены")
                await state.clear()
                return
                
            # Обновляем соответствующее поле в зависимости от типа настройки
            if setting_key == 'support':
                settings.support = message.text
            elif setting_key == 'operator':
                settings.operator = message.text
            elif setting_key == 'card':
                settings.card_details = message.text
            elif setting_key == 'crypto_btc':
                settings.crypto_details = message.text
            elif setting_key == 'crypto_usdt':
                settings.crypto_details = message.text
            elif setting_key == 'chat':
                settings.chat = message.text
                
            settings.updated_by = message.from_user.id
            session.commit()
            
            # Логируем изменение настройки
            await log_user_action(
                message.from_user.id,
                "admin_setting_updated",
                {
                    "setting_key": setting_key,
                    "new_value": message.text
                }
            )
            
            await message.answer("✅ Настройка успешно обновлена")
            
        await state.clear()
        await show_settings_panel(message)
        
    except Exception as e:
        logger.error(f"Error in process_setting_value: {e}")
        await message.answer("Произошла ошибка при обновлении настройки")
        await state.clear()
        await show_admin_panel(message)

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Логируем нажатие на кнопку "Назад"
        await log_user_action(
            info_bot,
            callback.from_user.id,
            "admin_settings_button_click",
            {
                "button": "back_to_admin",
                "action": "return_to_admin_panel"
            }
        )
        
        await state.clear()
        await show_admin_panel(callback.message)
    except Exception as e:
        logger.error(f"Error in back_to_admin_panel: {e}")
        await callback.answer("Произошла ошибка при возврате в админ-панель")
        await state.clear()
        await show_main_menu(callback.message)

@dp.message(F.text == "💰 Пополнить баланс")
async def admin_topup(message: types.Message, state: FSMContext):
    try:
        # Создаем клавиатуру с методами оплаты
        keyboard = [
            [InlineKeyboardButton(text="💳 Карта", callback_data="topup_method_card")],
            [InlineKeyboardButton(text="₿ BTC", callback_data="topup_method_btc")],
            [InlineKeyboardButton(text="💵 USDT", callback_data="topup_method_usdt")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer("Выберите способ оплаты:", reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in admin_topup: {e}")
        await message.answer("Произошла ошибка")

@dp.callback_query(F.data.startswith("topup_method_"))
async def topup_method(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_type = callback.data.split('_')[2]  # card, btc или usdt
        # Получаем реквизиты для выбранного метода оплаты
        with Session(engine) as session:
            payment_method = session.query(PaymentMethod).filter_by(
                type=payment_type,
                is_active=True
            ).first()
            if not payment_method:
                await callback.answer("Нет доступных реквизитов для этого метода оплаты", show_alert=True)
                return
            # Создаем клавиатуру с кнопкой подтверждения
            keyboard = [
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_topup_{payment_type}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="topup_balance")]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            # Отправляем сообщение с реквизитами
            await callback.message.edit_text(
                f"💳 Реквизиты для пополнения:\n\n"
                f"{payment_method.details}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'",
                reply_markup=markup
            )
    except Exception as e:
        logger.error(f"Error in topup_method: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_topup_"))
async def confirm_topup(callback: types.CallbackQuery, state: FSMContext):
    try:
        payment_type = callback.data.split('_')[2]
        
        # Показываем сообщение о поиске платежа
        await callback.message.edit_text(
            "🔍 Ищем ваш платеж...\n"
            "Пожалуйста, подождите..."
        )
        
        # Ждем 10 секунд
        await asyncio.sleep(10)
        
        # Показываем сообщение об ошибке
        keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="topup_balance")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "❌ Платеж не найден\n\n"
            "Если вы уже оплатили, пожалуйста, обратитесь к администратору",
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_topup: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@dp.message(F.text == "💳 Вывод средств")
async def admin_withdraw(message: types.Message, state: FSMContext):
    await message.answer("Введите ID пользователя:")
    await state.set_state(UserStates.waiting_for_user_id)
    await state.update_data(action="withdraw")

@dp.message(F.text == "🚫 Бан")
async def admin_ban(message: types.Message, state: FSMContext):
    await message.answer("Введите ID пользователя для бана:")
    await state.set_state(UserStates.waiting_for_user_id)
    await state.update_data(action="ban")

@dp.message(F.text == "✅ Разбан")
async def admin_unban(message: types.Message, state: FSMContext):
    await message.answer("Введите ID пользователя для разбана:")
    await state.set_state(UserStates.waiting_for_user_id)
    await state.update_data(action="unban")

@dp.message(UserStates.waiting_for_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            
            if not user:
                await message.answer("❌ Пользователь не найден")
                await state.clear()
                await show_admin_panel(message)
                return
                
            # Получаем текущее действие из состояния
            data = await state.get_data()
            action = data.get('action')
            
            if action == 'ban':
                user.is_banned = True
                session.commit()
                await message.answer(f"✅ Пользователь {user_id} забанен")
                
                # Отправляем уведомление пользователю
                await send_message_and_handle_block(
                    user_id,
                    "🚫 Вы были заблокированы администратором"
                )
                    
            elif action == 'unban':
                user.is_banned = False
                session.commit()
                await message.answer(f"✅ Пользователь {user_id} разбанен")
                
                # Отправляем уведомление пользователю
                await send_message_and_handle_block(
                    user_id,
                    "✅ Ваша блокировка была снята администратором"
                )
                    
            elif action == 'topup':
                # Сохраняем user_id для следующего шага
                await state.update_data(target_user_id=user_id)
                await message.answer("Введите сумму пополнения:")
                await state.set_state(UserStates.waiting_for_topup_amount)
                return
                
            elif action == 'withdraw':
                # Сохраняем user_id для следующего шага
                await state.update_data(target_user_id=user_id)
                await message.answer("Введите сумму вывода:")
                await state.set_state(UserStates.waiting_for_withdraw_amount)
                return
                
            # Логируем действие
                await log_user_action(
                    info_bot,
                    message.from_user.id,
                action,
                {"target_user_id": user_id}
                )
                
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID пользователя")
    except Exception as e:
        logger.error(f"Error in process_user_id: {e}")
        await message.answer("Произошла ошибка при обработке ID пользователя")
    finally:
        if action not in ['topup', 'withdraw']:
            await state.clear()
            await show_admin_panel(message)

@dp.message(F.text == "📦 История заказов")
async def admin_orders(message: types.Message):
    try:
        with Session(engine) as session:
            orders = session.query(Order).order_by(Order.created_at.desc()).all()
            if not orders:
                await message.answer("📦 История заказов пуста")
                return
            text = "📦 История заказов:\n\n"
            chunks_sent = False
            MAX_LEN = 3500
            for order in orders:
                status_emoji = {
                    OrderStatus.PENDING: "⏳",
                    OrderStatus.PAID: "✅",
                    OrderStatus.CANCELLED: "❌",
                    OrderStatus.COMPLETED: "🎉"
                }.get(order.status, "❓")

                created_at_text = order.created_at.strftime('%d.%m.%Y %H:%M') if getattr(order, 'created_at', None) else 'Неизвестно'
                entry = (
                    f"{status_emoji} ID: {order.id}\n"
                    f"👤 Пользователь: {order.user_id}\n"
                    f"📍 Район: {order.district}\n"
                    f"📦 Товар: {order.product_name}\n"
                    f"💰 Сумма: {order.total_price} руб.\n"
                    f"💳 Способ оплаты: {order.payment_method.upper() if order.payment_method else 'Не указан'}\n"
                    f"📝 Примечание: {order.notes if order.notes else 'Нет'}\n"
                    f"⏰ Дата: {created_at_text}\n"
                    "➖➖➖➖➖➖➖➖➖➖\n"
                )

                if len(text) + len(entry) > MAX_LEN:
                    await message.answer(text)
                    chunks_sent = True
                    text = "📦 История заказов (продолжение):\n\n"

                text += entry

            keyboard = [
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_orders")],
                [InlineKeyboardButton(text="📋 Все заказы", callback_data="all_orders")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            # Attach keyboard to the final chunk
            await message.answer(text, reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in admin_orders: {e}")
        await message.answer("Произошла ошибка при получении истории заказов")

@dp.callback_query(F.data == "refresh_orders")
async def refresh_orders(callback: types.CallbackQuery):
    await admin_orders(callback.message)
    await callback.answer("Список заказов обновлен")

@dp.callback_query(F.data == "all_orders")
async def show_all_orders(callback: types.CallbackQuery):
    with Session(engine) as session:
        orders = session.query(Order).order_by(Order.created_at.desc()).all()
        text = "📦 Все заказы:\n\n"
        for order in orders:
            user = session.query(User).filter_by(telegram_id=order.user_id).first()
            username = user.username if user else "Unknown"
            status_emoji = {
                OrderStatus.PENDING: "⏳",
                OrderStatus.PAID: "✅",
                OrderStatus.CANCELLED: "❌",
                OrderStatus.COMPLETED: "🎉"
            }.get(order.status, "❓")
            
            text += f"{status_emoji} Заказ #{order.order_number}\n"
            text += f"👤 Пользователь: @{username}\n"
            text += f"📦 Товар: {order.product_name} ({order.product_weight})\n"
            text += f"🏙 Район: {order.district}\n"
            text += f"🗺 Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
            text += f"💰 Сумма: {order.total_price} руб.\n"
            text += f"💳 Способ оплаты: {order.payment_method.upper()}\n"
            text += f"📅 Дата: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            if order.notes:
                text += f"📝 Заметки: {order.notes}\n"
            text += "\n"
            
            # Split message if it's too long
            if len(text) > 3000:
                await callback.message.answer(text)
                text = ""
        
        if text:
            await callback.message.answer(text)
        
        # Log admin action
        await log_user_action(
            callback.from_user.id,
            "admin_view_all_orders",
            {"total_orders": len(orders)}
        )

@dp.callback_query(F.data.startswith("order_"))
async def manage_order(callback: types.CallbackQuery, state: FSMContext):
    action, order_number = callback.data.split('_')[1:]
    
    with Session(engine) as session:
        order = session.query(Order).filter_by(order_number=order_number).first()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        if action == "complete":
            order.status = OrderStatus.COMPLETED
            session.commit()
            await callback.answer("Заказ отмечен как выполненный")
        elif action == "cancel":
            order.status = OrderStatus.CANCELLED
            session.commit()
            await callback.answer("Заказ отменен")
        elif action == "note":
            await state.set_state(UserStates.waiting_for_order_note)
            await state.update_data(order_number=order_number)
            await callback.message.answer("Введите заметку для заказа:")
            return
        
        # Log admin action
        await log_user_action(
            info_bot,
            callback.from_user.id,
            f"admin_{action}_order",
            {"order_number": order_number}
        )
        
        # Refresh orders list
        await admin_orders(callback.message)

@dp.message(UserStates.waiting_for_order_note)
async def save_order_note(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_number = data.get("order_number")
    
    with Session(engine) as session:
        order = session.query(Order).filter_by(order_number=order_number).first()
        if order:
            order.notes = message.text
            session.commit()
            await message.answer("Заметка добавлена к заказу")
            
            # Log admin action
            await log_user_action(
                info_bot,
                message.from_user.id,
                "admin_add_order_note",
                {
                    "order_number": order_number,
                    "note_length": len(message.text)
                }
            )
    
    await state.clear()
    await admin_orders(message)

# --- Address Management ---
@dp.message(F.text == "📍 Мои адреса")
async def show_my_addresses(message: types.Message):
    if await check_user_banned(message):
        return
    with Session(engine) as session:
        addresses = session.query(UserAddress).filter_by(user_id=message.from_user.id, is_active=True).all()
        if not addresses:
            await message.answer("У вас пока нет сохранённых адресов.")
            return
        text = "Ваши адреса:\n\n"
        for i, addr in enumerate(addresses, 1):
            text += f"{i}. {addr.address}\n   Описание: {addr.description}\n"
        await message.answer(text)
        await log_user_action(
            info_bot,
            message.from_user.id,
            "view_addresses",
            {"addresses_count": len(addresses)}
        )

@dp.message(F.text == "📍 Управление адресами")
async def admin_address_management(message: types.Message):
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет доступа к этой функции.")
            return
        # Получаем всех пользователей
        users = session.query(User).all()
        if not users:
            await message.answer("Нет пользователей в базе")
            return
        # Клавиатура: добавить и удалить адрес
        keyboard = [
            [InlineKeyboardButton(text=f"➕ Добавить адрес @{u.username}", callback_data=f"admin_add_address_{u.telegram_id}")]
            for u in users
        ]
        keyboard += [
            [InlineKeyboardButton(text=f"❌ Удалить адрес @{u.username}", callback_data=f"admin_delete_address_user_{u.telegram_id}")]
            for u in users
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("Выберите действие для пользователя:", reply_markup=markup)
        await log_user_action(
            info_bot,
            message.from_user.id,
            "admin_address_management",
            {"users_count": len(users)}
        )

@dp.callback_query(F.data.startswith("admin_add_address_"))
async def admin_add_address_start(callback: types.CallbackQuery, state: FSMContext):
    try:
        user_id = int(callback.data.split('_')[3])
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await callback.answer("Пользователь не найден")
                return
            await state.update_data(target_user_id=user_id)
            await callback.message.edit_text(f"Отправьте ссылку на фото для пользователя @{user.username} (ID: {user.telegram_id}):")
            await state.set_state(UserStates.waiting_for_address)
    except Exception as e:
        logger.error(f"Error in admin_add_address_start: {e}")
        await callback.answer("Произошла ошибка")
        await state.clear()

@dp.message(UserStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    try:
        with Session(engine) as session:
            admin = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not admin or not admin.is_admin:
                await message.answer("❌ У вас нет доступа к этой функции.")
                await state.clear()
                return
            data = await state.get_data()
            target_user_id = data.get("target_user_id")
            if not target_user_id:
                await message.answer("Ошибка: пользователь не выбран")
                await state.clear()
                return
            url = message.text.strip()
            if not url:
                await message.answer("Ссылка не может быть пустой")
                return
            if not (url.startswith('http://') or url.startswith('https://')):
                await message.answer("Пожалуйста, отправьте корректную ссылку на фото")
                return
            await state.update_data(address_url=url)
            await message.answer("Теперь отправьте описание для этого адреса:")
            await state.set_state(UserStates.waiting_for_address_description)
    except Exception as e:
        logger.error(f"Error in process_address: {e}")
        await message.answer("Произошла ошибка при добавлении адреса")
        await state.clear()

@dp.message(UserStates.waiting_for_address_description)
async def process_address_description(message: types.Message, state: FSMContext):
    try:
        with Session(engine) as session:
            admin = session.query(User).filter_by(telegram_id=message.from_user.id).first()
            if not admin or not admin.is_admin:
                await message.answer("❌ У вас нет доступа к этой функции.")
                await state.clear()
                return
            data = await state.get_data()
            target_user_id = data.get("target_user_id")
            address_url = data.get("address_url")
            if not target_user_id or not address_url:
                await message.answer("Ошибка: данные адреса не найдены")
                await state.clear()
                return
            description = message.text.strip()
            if not description:
                await message.answer("Описание не может быть пустым")
                return
            new_address = UserAddress(
                user_id=target_user_id,
                address=address_url,
                description=description,
                is_active=True
            )
            session.add(new_address)
            session.commit()
            target_user = session.query(User).filter_by(telegram_id=target_user_id).first()
            await message.answer(f"✅ Адрес успешно добавлен для пользователя @{target_user.username}!")
            await log_user_action(
                info_bot,
                message.from_user.id,
                "admin_add_address",
                {
                    "target_user_id": target_user_id,
                    "target_username": target_user.username,
                    "url": address_url,
                    "description": description
                }
            )
    except Exception as e:
        logger.error(f"Error in process_address_description: {e}")
        await message.answer("Произошла ошибка при добавлении адреса")
        await state.clear()

@dp.message(F.text == "📦 Управление заказами")
async def admin_order_management(message: types.Message):
    with Session(engine) as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет доступа к этой функции.")
            return
            
        # Получаем всех пользователей
        users = session.query(User).all()
        if not users:
            await message.answer("Нет пользователей в базе")
            return
            
        # Создаем клавиатуру с действиями
        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить заказ", callback_data="admin_add_order")],
            [InlineKeyboardButton(text="❌ Удалить заказ", callback_data="admin_delete_order")]
        ]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("Выберите действие:", reply_markup=markup)

@dp.callback_query(F.data == "admin_delete_order")
async def admin_delete_order_start(callback: types.CallbackQuery):
    with Session(engine) as session:
        # Получаем последние 10 заказов
        orders = session.query(Order).order_by(Order.created_at.desc()).limit(10).all()
        if not orders:
            await callback.message.edit_text("Нет доступных заказов для удаления.")
            return
            
        keyboard = []
        for order in orders:
            user = session.query(User).filter_by(telegram_id=order.user_id).first()
            username = user.username if user else "Unknown"
            btn_text = f"❌ #{order.order_number} - @{username} - {order.product_name}"
            keyboard.append([
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"admin_delete_order_{order.order_number}"
                )
            ])
            
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            "Выберите заказ для удаления:",
            reply_markup=markup
        )

@dp.callback_query(F.data.startswith("admin_delete_order_"))
async def admin_delete_order_confirm(callback: types.CallbackQuery):
    try:
        order_number = callback.data.split('_')[3]
        with Session(engine) as session:
            order = session.query(Order).filter_by(order_number=order_number).first()
            if not order:
                await callback.answer("Заказ не найден")
                return
                
            # Удаляем заказ
            session.delete(order)
            session.commit()
            
            await callback.message.answer(f"✅ Заказ #{order_number} успешно удалён!")
            
            # Log action
            await log_user_action(
                callback.from_user.id,
                "admin_delete_order",
                {"order_number": order_number}
            )
            
    except Exception as e:
        logger.error(f"Error in admin_delete_order_confirm: {e}")
        await callback.answer("Произошла ошибка при удалении заказа")

@dp.callback_query(F.data == "admin_add_order")
async def admin_add_order_start(callback: types.CallbackQuery, state: FSMContext):
    try:
        with Session(engine) as session:
            # Проверяем права администратора
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
                return
            # Получаем всех пользователей
            users = session.query(User).all()
            if not users:
                await callback.message.edit_text("Нет пользователей в базе")
                return
                
            # Создаем клавиатуру с пользователями
            keyboard = []
            for user in users:
                button_text = f"@{user.username} (ID: {user.telegram_id})"
                callback_data = f"admin_add_order_{user.telegram_id}"
                keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(
                "Выберите пользователя для добавления заказа:",
                reply_markup=markup
            )
            
    except Exception as e:
        logger.error(f"Error in admin_add_order_start: {e}")
        await callback.answer("Произошла ошибка")
        await state.clear()
        await show_admin_panel(callback.message)

@dp.callback_query(F.data.startswith("admin_add_order_"))
async def admin_add_order_user(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Проверяем права администратора
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
                return
        
        user_id = int(callback.data.split('_')[3])
        
        # Очищаем предыдущее состояние и сохраняем новый user_id
        await state.clear()
        await state.update_data(target_user_id=user_id)
        
        # Создаем клавиатуру с городами
        keyboard = []
        for i, city in enumerate(config.CITIES):
            # Используем индекс города как безопасный идентификатор
            keyboard.append([InlineKeyboardButton(text=city, callback_data=f"admin_city_{i}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            "Выберите город:",
            reply_markup=markup
        )
        
    except Exception as e:
        logger.error(f"Error in admin_add_order_user: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
        await state.clear()
        await show_admin_panel(callback.message)

@dp.callback_query(F.data.startswith("admin_district_"))
async def admin_add_order_district(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Проверяем права администратора
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
                return
        
        # Получаем данные о городе и районах
        data = await state.get_data()
        city = data.get('selected_city')
        target_user_id = data.get('target_user_id')
        districts = get_districts_for_city(city)
        
        # Получаем индекс района из callback_data
        district_index = int(callback.data.split('_')[2])
        district = districts[district_index]
        
        # Получаем продукты для выбранного района
        products = get_products_for_district(city, district)
        
        if not products:
            await callback.answer("Нет доступных товаров для этого города.", show_alert=True)
            await state.clear()
            await show_admin_panel(callback.message)
            return
            
        # Выбираем случайный товар
        product = random.choice(products)
        
        # Генерируем номер заказа без приписки ADM-
        order_number = str(int(time.time()))
        
        # Рассчитываем цены с учетом комиссий
        CARD_COMMISSION = 0.05  # 5%
        CRYPTO_COMMISSION = 0.005  # 0.5%
        
        card_price = product['price'] * (1 + CARD_COMMISSION)
        crypto_price = product['price'] * (1 + CRYPTO_COMMISSION)
        
        # Случайно выбираем тип тайника
        stash_type = random.choice(['magnet', 'stash'])
        
        # Generate random date between 1-5 days ago
        days_ago = random.randint(1, 5)
        random_date = datetime.now() - timedelta(days=days_ago)
        
        # Создаем заказ
        with Session(engine) as session:
            order = Order(
                order_number=order_number,
                user_id=target_user_id,
                product_name=product['name'],
                product_weight=product['weight'],
                district=district,
                total_price=card_price,  # Используем цену с комиссией карты
                payment_method='card',  # По умолчанию карта
                stash_type=StashType.MAGNET if stash_type == 'magnet' else StashType.STASH,
                status=OrderStatus.PAID,  # Сразу помечаем как оплаченный
                created_at=random_date,
                updated_at=random_date
            )
            
            session.add(order)
            session.commit()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=target_user_id).first()
            username = user.username if user else "Unknown"
            
            # Отправляем сообщение админу
            await callback.message.edit_text(
                f"✅ Заказ успешно создан!\n\n"
                f"Номер заказа: {order.order_number}\n"
                f"Пользователь: @{username}\n"
                f"Товар: {order.product_name} ({order.product_weight})\n"
                f"Район: {order.district}\n"
                f"Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
                f"Базовая цена: {product['price']} руб.\n"
                f"Итоговая цена: {order.total_price:.2f} руб.\n"
                f"Статус: Оплачен"
            )
            
            # Отправляем сообщение пользователю
            try:
                await send_message_and_handle_block(
                    target_user_id,
                    f"📦 Новый заказ создан!\n\n"
                    f"Номер заказа: {order.order_number}\n"
                    f"Товар: {order.product_name} ({order.product_weight})\n"
                    f"Район: {order.district}\n"
                    f"Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
                    f"Базовая цена: {product['price']} руб.\n"
                    f"Итоговая цена: {order.total_price:.2f} руб.\n"
                    f"Статус: Оплачен"
                )
            except Exception as e:
                logger.error(f"Error sending order notification to user: {e}")
            
            # Логируем создание заказа
            await log_user_action(
                info_bot,
                callback.from_user.id,
                "admin_create_order",
                {
                    "order_number": order.order_number,
                    "user_id": target_user_id,
                    "product": product,
                    "district": district,
                    "stash_type": stash_type,
                    "base_price": product['price'],
                    "final_price": order.total_price
                }
            )
            
    except Exception as e:
        logger.error(f"Error in admin_add_order_district: {e}")
        await callback.answer("Произошла ошибка при создании заказа", show_alert=True)
        await state.clear()
        await show_admin_panel(callback.message)

@dp.callback_query(F.data.startswith("admin_stash_"))
async def admin_select_stash(callback: types.CallbackQuery, state: FSMContext):
    try:
        stash_type = callback.data.split('_')[2]
        data = await state.get_data()
        
        # Проверяем наличие необходимых данных
        if not all(key in data for key in ['target_user_id', 'product', 'selected_district', 'order_number', 'card_price']):
            logger.error(f"Missing required data in state: {data}")
            await callback.answer("Ошибка: отсутствуют необходимые данные", show_alert=True)
            await state.clear()
            await show_admin_panel(callback.message)
            return
        
        # Generate random date between 1-5 days ago
        days_ago = random.randint(1, 5)
        random_date = datetime.now() - timedelta(days=days_ago)
        
        # Создаем заказ
        with Session(engine) as session:
            order = Order(
                order_number=data['order_number'],
                user_id=data['target_user_id'],
                product_name=data['product']['name'],
                product_weight=data['product']['weight'],
                district=data['selected_district'],
                total_price=data['card_price'],  # Используем цену с комиссией карты
                payment_method='card',  # По умолчанию карта
                stash_type=StashType.MAGNET if stash_type == 'magnet' else StashType.STASH,
                status=OrderStatus.PAID,  # Сразу помечаем как оплаченный
                created_at=random_date,
                updated_at=random_date
            )
            
            session.add(order)
            session.commit()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=data['target_user_id']).first()
            username = user.username if user else "Unknown"
            
            # Отправляем сообщение админу
            await callback.message.edit_text(
                f"✅ Заказ успешно создан!\n\n"
                f"Номер заказа: {order.order_number}\n"
                f"Пользователь: @{username}\n"
                f"Товар: {order.product_name} ({order.product_weight})\n"
                f"Район: {order.district}\n"
                f"Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
                f"Базовая цена: {data['product']['price']} руб.\n"
                f"Итоговая цена: {order.total_price:.2f} руб.\n"
                f"Статус: Оплачен"
            )
            
            # Отправляем сообщение пользователю
            try:
                await send_message_and_handle_block(
                    data['target_user_id'],
                    f"📦 Новый заказ создан!\n\n"
                    f"Номер заказа: {order.order_number}\n"
                    f"Товар: {order.product_name} ({order.product_weight})\n"
                    f"Район: {order.district}\n"
                    f"Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
                    f"Базовая цена: {data['product']['price']} руб.\n"
                    f"Итоговая цена: {order.total_price:.2f} руб.\n"
                    f"Статус: Оплачен"
                )
            except Exception as e:
                logger.error(f"Error sending order notification to user: {e}")
            
            # Логируем создание заказа
            await log_user_action(
                info_bot,
                callback.from_user.id,
                "admin_create_order",
                {
                    "order_number": order.order_number,
                    "user_id": data['target_user_id'],
                    "product": data['product'],
                    "district": data['selected_district'],
                    "stash_type": stash_type,
                    "base_price": data['product']['price'],
                    "final_price": order.total_price
                }
            )
            
    except Exception as e:
        logger.error(f"Error in admin_select_stash: {e}")
        await callback.answer("Произошла ошибка при создании заказа", show_alert=True)
        await state.clear()
        await show_admin_panel(callback.message)

@dp.callback_query(F.data.startswith("pay_method_card_"))
async def pay_method_card(callback: types.CallbackQuery, state: FSMContext):
    try:
        order_number = callback.data.split('_')[3]
        
        with Session(engine) as session:
            order = session.query(Order).filter_by(order_number=order_number).first()
            if not order:
                await callback.answer("Заказ не найден!")
                return

            active_cards = session.query(PaymentMethod).filter(
                PaymentMethod.type == "card",
                PaymentMethod.is_active == True
            ).all()
            
            if not active_cards:
                await callback.answer("Временно нет доступных карт для оплаты. Пожалуйста, попробуйте другой способ оплаты.")
                return

            selected_card = random.choice(active_cards)
            order.selected_payment_details = selected_card.details
            session.commit()
            
            await state.update_data(current_order_number=order_number)

            # Send payment details to user
            payment_message = (
                f"💳 Реквизиты для оплаты:\n"
                f"{selected_card.details}\n\n"
                f"#️⃣ Номер заказа: #{order.order_number}\n"
                f"💰 Сумма к оплате: {order.total_price:.2f} руб.\n"
                f"💯 Товар: {order.product_name} ({order.product_weight})\n"
                f"🏙 Район: {order.district}\n"
                f"🗺 Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Тайник'}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'"
            )
            
            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{order.id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
            ])
            
            await callback.message.edit_text(payment_message, reply_markup=confirm_keyboard)

    except Exception as e:
        logger.error(f"Error in pay_method_card: {e}")
        await callback.answer("Произошла ошибка при получении реквизитов")

@dp.callback_query(F.data.startswith("pay_method_usdt_"))
async def pay_method_usdt(callback: types.CallbackQuery, state: FSMContext):
    try:
        order_number = callback.data.split('_')[3]
        with Session(engine) as session:
            order = session.query(Order).filter_by(order_number=order_number).first()
            if not order:
                await callback.answer("Заказ не найден!")
                return

            active_wallets = session.query(PaymentMethod).filter(
                PaymentMethod.type == "usdt",
                PaymentMethod.is_active == True
            ).all()
            
            if not active_wallets:
                await callback.answer("Временно нет доступных USDT кошельков для оплаты. Пожалуйста, попробуйте другой способ оплаты.")
                return

            selected_wallet = random.choice(active_wallets)
            order.selected_payment_details = selected_wallet.details
            session.commit()
            
            await state.update_data(current_order_number=order_number)

            payment_message = (
                f"💳 Реквизиты для оплаты:\n"
                f"{selected_wallet.details}\n\n"
                f"#️⃣ Номер заказа: #{order.order_number}\n"
                f"💰 Сумма к оплате: {order.total_price:.2f} руб.\n"
                f"💯 Товар: {order.product_name} ({order.product_weight})\n"
                f"🏙 Район: {order.district}\n"
                f"🗺 Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Тайник'}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'"
            )

            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{order.id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
            ])

            await callback.message.edit_text(payment_message, reply_markup=confirm_keyboard)

    except Exception as e:
        logger.error(f"Error in pay_method_usdt: {e}")
        await callback.answer("Произошла ошибка при получении реквизитов")

@dp.callback_query(F.data.startswith("pay_method_btc_"))
async def pay_method_btc(callback: types.CallbackQuery, state: FSMContext):
    try:
        order_number = callback.data.split('_')[3]
        with Session(engine) as session:
            order = session.query(Order).filter_by(order_number=order_number).first()
            if not order:
                await callback.answer("Заказ не найден!")
                return

            active_wallets = session.query(PaymentMethod).filter(
                PaymentMethod.type == "btc",
                PaymentMethod.is_active == True
            ).all()
            
            if not active_wallets:
                await callback.answer("Временно нет доступных BTC кошельков для оплаты. Пожалуйста, попробуйте другой способ оплаты.")
                return

            selected_wallet = random.choice(active_wallets)
            order.selected_payment_details = selected_wallet.details
            session.commit()
            
            await state.update_data(current_order_number=order_number)

            payment_message = (
                f"💳 Реквизиты для оплаты:\n"
                f"{selected_wallet.details}\n\n"
                f"#️⃣ Номер заказа: #{order.order_number}\n"
                f"💰 Сумма к оплате: {order.total_price:.2f} руб.\n"
                f"💯 Товар: {order.product_name} ({order.product_weight})\n"
                f"🏙 Район: {order.district}\n"
                f"🗺 Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Тайник'}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'"
            )

            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment_{order.id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
            ])

            await callback.message.edit_text(payment_message, reply_markup=confirm_keyboard)

    except Exception as e:
        logger.error(f"Error in pay_method_btc: {e}")
        await callback.answer("Произошла ошибка при получении реквизитов")

def get_order_by_id(order_id: str):
    """Получить заказ по его ID"""
    with Session(engine) as session:
        return session.query(Order).filter_by(id=order_id).first()

def migrate_database():
    """Perform database migrations if needed"""
    with Session(engine) as session:
        try:
            # Check if created_at column exists in users table
            result = session.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]
            
            if 'created_at' not in columns:
                session.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                session.commit()
                logger.info("Added created_at column to users table")
            
            # Check if is_blocked column exists in users table
            if 'is_blocked' not in columns:
                session.execute(text("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE"))
                session.commit()
                logger.info("Added is_blocked column to users table")
            
            # Create promo_codes table if it doesn't exist
            try:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS promo_codes (
                        id INTEGER PRIMARY KEY,
                        code VARCHAR UNIQUE,
                        percent FLOAT,
                        max_activations INTEGER,
                        activations INTEGER DEFAULT 0,
                        is_used BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        used_at DATETIME
                    )
                """))
                session.commit()
                logger.info("Created promo_codes table")
                
                # Check and add missing columns
                result = session.execute(text("PRAGMA table_info(promo_codes)"))
                existing_columns = [row[1] for row in result]
                
                # List of required columns and their types
                required_columns = {
                    'percent': 'FLOAT',
                    'max_activations': 'INTEGER',
                    'activations': 'INTEGER DEFAULT 0',
                    'is_used': 'BOOLEAN DEFAULT FALSE',
                    'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'used_at': 'DATETIME'
                }
                
                # Add missing columns
                for column, column_type in required_columns.items():
                    if column not in existing_columns:
                        session.execute(text(f"ALTER TABLE promo_codes ADD COLUMN {column} {column_type}"))
                        logger.info(f"Added {column} column to promo_codes table")
                
                session.commit()
                
            except Exception as e:
                logger.error(f"Error creating/updating promo_codes table: {e}")
                session.rollback()
            
        except Exception as e:
            logger.error(f"Error during database migration: {e}")
            session.rollback()

def init_bot_settings():
    """Initialize default bot settings if they don't exist"""
    with Session(engine) as session:
        settings = session.query(BotSettings).first()
        if not settings:
            settings = BotSettings(
                support="Поддержка",
                operator="Оператор",
                card_details="Реквизиты карты",
                crypto_details="Реквизиты крипты",
                chat="Чат"
            )
            session.add(settings)
            session.commit()
            logger.info("Initialized default bot settings")

async def main():
    logger.info("Starting bot...")
    # Initialize default settings
    init_bot_settings()
    logger.info("Settings initialized")
    
    # Migrate database if needed
    migrate_database()
    logger.info("Database migration completed")
    
    # Start polling
    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        logger.info("Bot stopped")

@dp.message(F.text == "📦 Мои заказы")
async def show_my_orders(message: types.Message):
    try:
        with Session(engine) as session:
            orders = session.query(Order).filter_by(user_id=message.from_user.id).order_by(Order.created_at.desc()).all()
            
            if not orders:
                await message.answer("📦 У вас пока нет заказов")
                return
                
            text = "📦 Ваши заказы:\n\n"
            for order in orders:
                status_emoji = {
                    OrderStatus.PENDING: "⏳",
                    OrderStatus.PAID: "✅",
                    OrderStatus.CANCELLED: "❌",
                    OrderStatus.COMPLETED: "🎉"
                }.get(order.status, "❓")
                
                text += f"{status_emoji} Заказ #{order.order_number}\n"
                text += f"📦 Товар: {order.product_name} ({order.product_weight})\n"
                text += f"🏙 Район: {order.district}\n"
                text += f"🗺 Тип тайника: {'Магнит' if order.stash_type == StashType.MAGNET else 'Клад'}\n"
                text += f"💰 Сумма: {order.total_price} руб.\n"
                text += f"💳 Способ оплаты: {order.payment_method.upper() if order.payment_method else 'Не указан'}\n"
                text += f"📅 Дата: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                if order.notes:
                    text += f"📝 Заметки: {order.notes}\n"
                text += "\n"
                
            # Добавляем кнопку обновления
            keyboard = [[InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_my_orders")]]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Error in show_my_orders: {e}")
        await message.answer("Произошла ошибка при получении списка заказов")

@dp.callback_query(F.data == "manage_cards")
async def manage_cards(callback: types.CallbackQuery):
    try:
        with Session(engine) as session:
            cards = session.query(PaymentMethod).filter_by(type="card").all()
            
            text = "💳 Управление картами:\n\n"
            if cards:
                for card in cards:
                    status = "✅ Активна" if card.is_active else "❌ Неактивна"
                    text += f"{status}\n{card.details}\n\n"
            else:
                text += "Нет добавленных карт\n\n"
                
            keyboard = [
                [InlineKeyboardButton(text="➕ Добавить карту", callback_data="add_card")]
            ]
            
            # Добавляем кнопки удаления для каждой карты
            if cards:
                for card in cards:
                    keyboard.append([
                        InlineKeyboardButton(
                            text=f"❌ Удалить: {card.details[:20]}...",
                            callback_data=f"delete_card_{card.id}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Error in manage_cards: {e}")
        await callback.answer("Произошла ошибка")

@dp.callback_query(F.data == "manage_btc")
async def manage_btc(callback: types.CallbackQuery):
    try:
        with Session(engine) as session:
            wallets = session.query(PaymentMethod).filter_by(type="btc").all()
            
            text = "₿ Управление BTC кошельками:\n\n"
            if wallets:
                for wallet in wallets:
                    status = "✅ Активен" if wallet.is_active else "❌ Неактивен"
                    text += f"{status}\n{wallet.details}\n\n"
            else:
                text += "Нет добавленных кошельков\n\n"
                
            keyboard = [
                [InlineKeyboardButton(text="➕ Добавить кошелек", callback_data="add_btc")]
            ]
            
            # Добавляем кнопки удаления для каждого кошелька
            if wallets:
                for wallet in wallets:
                    keyboard.append([
                        InlineKeyboardButton(
                            text=f"❌ Удалить: {wallet.details[:20]}...",
                            callback_data=f"delete_btc_{wallet.id}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Error in manage_btc: {e}")
        await callback.answer("Произошла ошибка")

@dp.callback_query(F.data == "manage_usdt")
async def manage_usdt(callback: types.CallbackQuery):
    try:
        with Session(engine) as session:
            wallets = session.query(PaymentMethod).filter_by(type="usdt").all()
            
            text = "💵 Управление USDT кошельками:\n\n"
            if wallets:
                for wallet in wallets:
                    status = "✅ Активен" if wallet.is_active else "❌ Неактивен"
                    text += f"{status}\n{wallet.details}\n\n"
            else:
                text += "Нет добавленных кошельков\n\n"
                
            keyboard = [
                [InlineKeyboardButton(text="➕ Добавить кошелек", callback_data="add_usdt")]
            ]
            
            # Добавляем кнопки удаления для каждого кошелька
            if wallets:
                for wallet in wallets:
                    keyboard.append([
                        InlineKeyboardButton(
                            text=f"❌ Удалить: {wallet.details[:20]}...",
                            callback_data=f"delete_usdt_{wallet.id}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.edit_text(text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Error in manage_usdt: {e}")
        await callback.answer("Произошла ошибка")

@dp.callback_query(F.data.startswith("delete_card_"))
async def delete_card(callback: types.CallbackQuery):
    try:
        card_id = int(callback.data.split('_')[2])
        with Session(engine) as session:
            card = session.query(PaymentMethod).filter_by(id=card_id, type="card").first()
            if card:
                session.delete(card)
                session.commit()
                await callback.answer("✅ Карта успешно удалена")
                await manage_cards(callback)
            else:
                await callback.answer("❌ Карта не найдена")
    except Exception as e:
        logger.error(f"Error in delete_card: {e}")
        await callback.answer("Произошла ошибка при удалении карты")

@dp.callback_query(F.data.startswith("delete_btc_"))
async def delete_btc(callback: types.CallbackQuery):
    try:
        wallet_id = int(callback.data.split('_')[2])
        with Session(engine) as session:
            wallet = session.query(PaymentMethod).filter_by(id=wallet_id, type="btc").first()
            if wallet:
                session.delete(wallet)
                session.commit()
                await callback.answer("✅ BTC кошелек успешно удален")
                await manage_btc(callback)
            else:
                await callback.answer("❌ Кошелек не найден")
    except Exception as e:
        logger.error(f"Error in delete_btc: {e}")
        await callback.answer("Произошла ошибка при удалении кошелька")

@dp.callback_query(F.data.startswith("delete_usdt_"))
async def delete_usdt(callback: types.CallbackQuery):
    try:
        wallet_id = int(callback.data.split('_')[2])
        with Session(engine) as session:
            wallet = session.query(PaymentMethod).filter_by(id=wallet_id, type="usdt").first()
            if wallet:
                session.delete(wallet)
                session.commit()
                await callback.answer("✅ USDT кошелек успешно удален")
                await manage_usdt(callback)
            else:
                await callback.answer("❌ Кошелек не найден")
    except Exception as e:
        logger.error(f"Error in delete_usdt: {e}")
        await callback.answer("Произошла ошибка при удалении кошелька")

@dp.callback_query(F.data == "add_card")
async def add_card(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_details)
    await state.update_data(payment_type="card")
    await callback.message.edit_text("Введите реквизиты карты:")

@dp.callback_query(F.data == "add_btc")
async def add_btc(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_details)
    await state.update_data(payment_type="btc")
    await callback.message.edit_text("Введите BTC кошелек:")

@dp.callback_query(F.data == "add_usdt")
async def add_usdt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_details)
    await state.update_data(payment_type="usdt")
    await callback.message.edit_text("Введите USDT кошелек:")

@dp.message(UserStates.waiting_for_payment_details)
async def process_payment_details(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        payment_type = data.get('payment_type')
        
        with Session(engine) as session:
            payment_method = PaymentMethod(
                type=payment_type,
                details=message.text,
                is_active=True,
                updated_by=message.from_user.id
            )
            session.add(payment_method)
            session.commit()
            
            await message.answer(f"✅ {payment_type.upper()} успешно добавлен!")
            
            # Создаем клавиатуру для управления реквизитами
            keyboard = []
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
            
            # Добавляем кнопки в зависимости от типа платежа
            if payment_type == "card":
                keyboard.append([InlineKeyboardButton(text="💳 Управление картами", callback_data="manage_cards")])
            elif payment_type == "btc":
                keyboard.append([InlineKeyboardButton(text="₿ Управление BTC", callback_data="manage_btc")])
            elif payment_type == "usdt":
                keyboard.append([InlineKeyboardButton(text="💵 Управление USDT", callback_data="manage_usdt")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            # Отправляем сообщение с реквизитами и клавиатурой
            await message.answer(
                f"Реквизиты {payment_type.upper()}:\n{message.text}\n\n"
                f"⚠️ ВАЖНО: После оплаты нажмите кнопку 'Подтвердить оплату'",
                reply_markup=markup
            )
                
    except Exception as e:
        logger.error(f"Error in process_payment_details: {e}")
        await message.answer("Произошла ошибка при добавлении реквизитов")
    finally:
        await state.clear()

async def show_districts(message: types.Message, city: str):
    """Показать районы для выбранного города"""
    try:
        districts = get_districts_for_city(city)
        if not districts:
            await message.answer("Нет доступных районов для этого города")
            return
            
        keyboard = []
        for district in districts:
            keyboard.append([InlineKeyboardButton(text=district, callback_data=f"dist_{district}")])
            
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(f"Выберите район в городе {city}:", reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error in show_districts: {e}")
        await message.answer("Произошла ошибка при получении списка районов")

@dp.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text("⏳ Подождите, ищем ваш платеж...")
        await callback.answer()
        await asyncio.sleep(10)
        await callback.message.edit_text(
            "❌ Платеж не найден. Если вы оплатили, обратитесь в поддержку.\n\n" 
            "Пожалуйста, проверьте правильность перевода и попробуйте еще раз или напишите оператору."
        )
    except Exception as e:
        logger.error(f"Error in confirm_payment: {e}")
        await callback.answer("Ошибка при подтверждении оплаты", show_alert=True)

@dp.callback_query(F.data.startswith("admin_city_"))
async def admin_add_order_city(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Проверяем права администратора
        with Session(engine) as session:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет доступа к этой функции.", show_alert=True)
                return
        
        # Получаем индекс города из callback_data
        city_index = int(callback.data.split('_')[2])
        city = config.CITIES[city_index]
        
        # Получаем сохраненный user_id
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        # Обновляем состояние
        await state.update_data(
            selected_city=city,
            target_user_id=target_user_id
        )
        
        # Получаем районы для выбранного города
        districts = get_districts_for_city(city)
        
        # Создаем клавиатуру с районами
        keyboard = []
        for i, district in enumerate(districts):
            keyboard.append([InlineKeyboardButton(text=district, callback_data=f"admin_district_{i}")])
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_add_order")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            f"Выбран город: {city}\nВыберите район:",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Error in admin_add_order_city: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
        await state.clear()
        await show_admin_panel(callback.message)

USERS_PER_PAGE = 20

# Обработчик кнопки "📢 Рассылка"
@dp.message(F.text == "📢 Рассылка")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    await message.answer("Введите текст рассылки (он будет отправлен всем пользователям):")
    await state.set_state(UserStates.waiting_for_broadcast_message)

# Обработчик ввода текста рассылки
@dp.message(UserStates.waiting_for_broadcast_message)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    text = message.text
    await message.answer("Начинаю рассылку... Это может занять некоторое время.")
    count = 0
    blocked_count = 0
    with Session(engine) as session:
        users = session.query(User).filter_by(is_banned=False).all()
        for user in users:
            # Используем новую вспомогательную функцию для отправки сообщения
            sent = await send_message_and_handle_block(user.telegram_id, text)
            if sent:
                count += 1
            else:
                # Если сообщение не было отправлено (например, из-за блокировки),
                # send_message_and_handle_block уже обновил is_blocked
                blocked_count += 1 # Увеличиваем счетчик заблокированных, так как is_blocked уже установлен

        session.commit()
    await message.answer(f"Рассылка завершена! Сообщение отправлено {count} пользователям. Заблокировано: {blocked_count}")
    await state.clear()
    await show_admin_panel(message)

@dp.message(F.text == "🎁 Промокоды")
async def admin_promo_start(message: types.Message, state: FSMContext):
    await message.answer("Введите процент скидки для промокода (например, 10):")
    await state.set_state(UserStates.waiting_for_promo_percent)

@dp.message(UserStates.waiting_for_promo_percent)
async def admin_promo_percent(message: types.Message, state: FSMContext):
    try:
        percent = float(message.text)
        await state.update_data(promo_percent=percent)
        await message.answer("Введите максимальное количество активаций для промокода:")
        await state.set_state(UserStates.waiting_for_promo_limit)
    except Exception:
        await message.answer("Введите корректный процент!")

@dp.message(UserStates.waiting_for_promo_limit)
async def admin_promo_limit(message: types.Message, state: FSMContext):
    try:
        logger.info("Начало создания промокода")
        max_activations = int(message.text)
        data = await state.get_data()
        percent = data.get('promo_percent')
        logger.info(f"Получены данные: max_activations={max_activations}, percent={percent}")
        
        code = f"PROMO{random.randint(10000, 99999)}"
        logger.info(f"Сгенерирован код: {code}")
        
        try:
            with Session(engine) as session:
                promo = PromoCode(
                    code=code,
                    percent=percent,
                    max_activations=max_activations,
                    activations=0,
                    is_used=False
                )
                session.add(promo)
                session.commit()
                logger.info("Промокод успешно сохранен в базу данных")
        except Exception as db_error:
            logger.error(f"Ошибка при работе с базой данных: {db_error}")
            raise
            
        await message.answer(f"Промокод: {code}\nСкидка: {percent}%\nЛимит: {max_activations} активаций\nПередайте промокод пользователям!")
        await state.clear()
        await show_admin_panel(message)
    except ValueError as ve:
        logger.error(f"Ошибка при преобразовании числа: {ve}")
        await message.answer("Введите корректное число для лимита активаций!")
        await state.clear()
        await show_admin_panel(message)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании промокода: {e}")
        await message.answer("Ошибка при создании промокода! Проверьте логи для деталей.")
        await state.clear()
        await show_admin_panel(message)

@dp.message(F.text == "🎟️ Ввести промокод")
async def ask_promo_code(message: types.Message, state: FSMContext):
    await message.answer("Введите промокод:")
    await state.set_state(UserStates.waiting_for_promo_code)

@dp.message(UserStates.waiting_for_promo_code)
async def user_activate_promo(message: types.Message, state: FSMContext):
    try:
        code = message.text.strip()
        with Session(engine) as session:
            promo = session.query(PromoCode).filter_by(code=code, is_used=False).first()
            if not promo:
                await message.answer("❌ Промокод не найден или уже использован!")
                await state.clear()
                return
            if promo.activations >= promo.max_activations:
                promo.is_used = True
                session.commit()
                await message.answer("❌ Лимит активаций промокода исчерпан!")
                await state.clear()
                return
            # Сохраняем скидку в state
            await state.update_data(active_promo_code=promo.code, promo_percent=promo.percent)
        await message.answer(f"✅ Промокод активирован! Скидка {promo.percent}% будет применена к вашей следующей покупке.")
    except Exception:
        await message.answer("Ошибка при активации промокода!")
        await state.clear()

async def send_message_and_handle_block(user_id: int, text: str, reply_markup=None, parse_mode=None):
    """Отправляет сообщение пользователю и обрабатывает блокировку бота, помечая пользователя как заблокированного."""
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except TelegramBadRequest as e:
        if "chat not found" in str(e) or "bot was blocked" in str(e):
            logger.warning(f"Пользователь {user_id} заблокировал бота.")
            with Session(engine) as session:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    user.is_blocked = True
                    session.add(user)
                    session.commit()
                    logger.info(f"Пользователь {user_id} помечен как заблокированный.")
            return False
        logger.warning(f"Не удалось отправить сообщение пользователю {user_id} (TelegramBadRequest): {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False

@dp.message(F.text == "Доставка 🏎")
async def menu_delivery(message: types.Message):
    if await check_user_banned(message):
        return
    await log_user_action(info_bot, message.from_user.id, "button_click", {"button": "Доставка"})
    with Session(engine) as session:
        setting = session.query(BotSettings).filter_by(key="operator").first()
        operator = setting.value if setting else "@matras_operator"
    delivery_text = (
        "~ Если вашего товара нету в вашем районе , вы всегда можете заказать товар с доставкой и с минимальной переплатой ! "
        "Если вы хотите заказать товар доставкой , пишите оператору указанному ниже 👇 ( Форма на заказ доставки ) - Пример { Меф 1г , ваш адрес на который нужна доставка }"
    )
    # Формируем ссылку на оператора
    operator_link = operator if operator.startswith("https://") or operator.startswith("tg://") else f"https://t.me/{operator.lstrip('@')}"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оператор", url=operator_link)]
        ]
    )
    await message.answer(delivery_text, reply_markup=keyboard)

if __name__ == '__main__':
    asyncio.run(main())
