from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import PACKAGING_OPTIONS, REVIEWS_LINK, SUPPORT_USERNAME
from catalog import get_product_names, get_variants_for_product

def get_main_keyboard():
    """Главное меню бота"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Отзывы", url=REVIEWS_LINK)],
            [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
            [InlineKeyboardButton(text="🛒 Заказать доставку", callback_data="order")]
        ]
    )
    
    return keyboard

def get_products_keyboard():
    """Клавиатура выбора товаров (из файла каталога)"""
    buttons = []
    for product_name in get_product_names():
        buttons.append([InlineKeyboardButton(text=product_name, callback_data=f"product:{product_name}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_packaging_keyboard(product_name: str):
    """Клавиатура выбора фасовки/вариантов для товара из каталога"""
    buttons = []
    variants = get_variants_for_product(product_name)
    if variants:
        for i, v in enumerate(variants):
            buttons.append([InlineKeyboardButton(text=f"{v.weight} — {int(v.price) if v.price.is_integer() else v.price} ₽", callback_data=f"packaging:{i}")])
    else:
        for i, option in enumerate(PACKAGING_OPTIONS):
            buttons.append([InlineKeyboardButton(text=option, callback_data=f"packaging:{i}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_order")]
        ]
    )
    
    return keyboard

def get_admin_keyboard():
    """Клавиатура администратора"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_orders")
            ],
            [
                InlineKeyboardButton(text="💬 Ответить пользователю", callback_data="admin_reply"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
            ]
        ]
    )
    
    return keyboard

def get_confirm_keyboard():
    """Клавиатура подтверждения заказа"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")
            ]
        ]
    )
    
    return keyboard 

def get_payment_method_keyboard():
    """Клавиатура выбора способа оплаты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перевод на карту", callback_data="pay_card")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
        ]
    )
    return keyboard

def get_payment_confirm_keyboard():
    """Клавиатура подтверждения оплаты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Скопировать номер карты", callback_data="copy_card")],
            [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data="confirm_payment")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")]
        ]
    )
    return keyboard

def get_payment_retry_keyboard():
    """Клавиатура после неуспешной проверки платежа"""
    username = SUPPORT_USERNAME.lstrip('@') if SUPPORT_USERNAME else ''
    operator_url = f"https://t.me/{username}" if username else None
    rows = [
        [InlineKeyboardButton(text="🔁 Попробовать ещё раз", callback_data="retry_payment")],
    ]
    if operator_url:
        rows.append([InlineKeyboardButton(text="👤 Написать оператору", url=operator_url)])
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")])
    return InlineKeyboardMarkup(inline_keyboard=rows)