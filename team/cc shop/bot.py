import asyncio
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, Defaults
from telegram.constants import ParseMode
from database import Database
from cryptobot import CryptoBot
from config import BOT_TOKEN, OWNER_USERNAME, BOT_NAME, ADMIN_CHANNEL_ID, ADMIN_IDS, TON_USDT_WALLET, TRX_USDT_WALLET
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных и криптобота
db = Database()
crypto_bot = CryptoBot()

class ShopBot:
    def __init__(self):
        self.application = (
            Application
            .builder()
            .token(BOT_TOKEN)
            .defaults(Defaults(parse_mode=ParseMode.MARKDOWN))
            .build()
        )
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("rules", self.rules_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("refresh_bins", self.refresh_bins_command))
        
        # Обработчики меню
        self.application.add_handler(MessageHandler(filters.Regex("^Кабинет/Profile$"), self.profile_command))
        self.application.add_handler(MessageHandler(filters.Regex("^Товары/Products$"), self.products_command))
        self.application.add_handler(MessageHandler(filters.Regex("^Правила/Rules$"), self.rules_command))
        self.application.add_handler(MessageHandler(filters.Regex("^Reviews$"), self.reviews_command))
        self.application.add_handler(MessageHandler(filters.Regex("^Help$"), self.help_command))
        self.application.add_handler(MessageHandler(filters.Regex("^Showcase$"), self.showcase_command))
        
        # Обработчики callback запросов
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчики текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        user_id = user.id
        
        # Добавляем пользователя в базу данных
        db.add_user(user_id, user.username, user.first_name)
        
        # Создаем главное меню
        keyboard = [
            [KeyboardButton("Кабинет/Profile"), KeyboardButton("Товары/Products")],
            [KeyboardButton("Правила/Rules"), KeyboardButton("Reviews")],
            [KeyboardButton("Help"), KeyboardButton("Showcase")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Приветственное сообщение
        welcome_text = f"""
🤝 Приветствую в {BOT_NAME}

👑 OWNER: @luxury_sup
📢 Основной канал: https://t.me/luxury_manuals
✅ Канал отзывов: https://t.me/+qlf6Er2I23JjZTlh
📜 Правила: https://telegra.ph/Pravila-proekta-08-19-2

🔥 Используя {BOT_NAME}, вы соглашаетесь с правилами использования ✅
        """.strip()
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=None)
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды профиля"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем информацию о пользователе
        user_info = db.get_user(user_id)
        if not user_info:
            db.add_user(user_id, user.username, user.first_name)
            user_info = db.get_user(user_id)
        
        balance = user_info.get('balance', 0.0)
        
        # Создаем клавиатуру профиля
        keyboard = [
            [InlineKeyboardButton("💰 Пополнить баланс/Top up", callback_data="top_up_balance")],
            [
                InlineKeyboardButton("⭐ Избранные товары/Favorite", callback_data="favorites"),
                InlineKeyboardButton("📋 Правила/Rules", callback_data="rules")
            ],
            [InlineKeyboardButton("📦 История заказов/Order history", callback_data="order_history")],
            [InlineKeyboardButton("🎫 Активировать купон/Activate coupon", callback_data="activate_coupon")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        profile_text = f"""
💙 **Имя:** {user_info.get('first_name', 'Не указано')}
🔑 **ID:** {user_id}
💰 **Ваш баланс:** {balance} $
        """.strip()
        
        await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode=None)
    
    async def products_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды товаров"""
        await update.message.reply_text("📦 Товары/Products")
        
        # Создаем клавиатуру категорий
        keyboard = [
            [InlineKeyboardButton("📖 CHEAP MANUALS", callback_data="category_CHEAP MANUALS")],
            [InlineKeyboardButton("🛢️ CHEAP MERCHANT", callback_data="category_CHEAP MERCHANT")],
            [InlineKeyboardButton("📚 Обучение", callback_data="category_Обучение")],
            [InlineKeyboardButton("💎 MANUALS", callback_data="category_MANUALS")],
            [InlineKeyboardButton("😛 MERCHANT", callback_data="category_MERCHANT")],
            [InlineKeyboardButton("💳 CC", callback_data="category_CC")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
    
    async def showcase_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все товары"""
        products = db.get_products()
        
        if not products:
            await update.message.reply_text("Товары не найдены")
            return
        
        # Короткое описание, чтобы не превысить лимит Telegram
        showcase_text = (
            "📦 **Каталог**\n\n"
            "Выберите категорию ниже, чтобы посмотреть товары."
        )
        
        # Создаем клавиатуру для покупки
        keyboard = [
            [InlineKeyboardButton("🛒 Купить товар", callback_data="buy_product")],
            [InlineKeyboardButton("⭐ В избранное", callback_data="favorite_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(showcase_text, reply_markup=reply_markup, parse_mode=None)
    
    async def rules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила"""
        rules_text = f"""
📋 **Правила и условия использования {BOT_NAME}**

⚠️ **Запуская и используя данный магазин вы соглашаетесь со всеми правилами !**
⚠️ **Незнание правил не освобождает от ответственности !**

1️⃣ Администрация проекта не отвечает и не будет отвечать на вопросы и утверждения, которые никак не связаны с покупкой товара.

2️⃣ Мы не помогаем с профитом и не даём гарантий вбива/профита. (Эти условия были введены, потому что в прошлом часто предпринимались попытки обмана администрации проекта, из-за чего мы ужесточили правила). В некоторых товарах возможно доведение до профита за дополнительную оплату, минимальная стоимость доплаты начинается от 700$ и может быть поднята в зависимости от товара.
        """.strip()
        
        await update.message.reply_text(rules_text, parse_mode=None)
    
    async def reviews_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать отзывы"""
        reviews_text = (
            "💎 **Отзывы**\n\n"
            "📢 Присоединяйтесь к нашему каналу отзывов:\n"
            "[Канал отзывов](https://t.me/+qlf6Er2I23JjZTlh)\n\n"
            "🔗 [Основной канал](https://t.me/luxury_manuals)"
        )
        
        await update.message.reply_text(reviews_text, parse_mode=None)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать справку"""
        help_text = f"""
👷 **Help**

{OWNER_USERNAME} - По покупке рекламы / Главный администратор (Для оплаты ВТС, ETH, USDT, CRYPTOBOT)

---

Greetings 👋
If you want to buy something in the shop or you want to ask a question email me {OWNER_USERNAME}
        """.strip()
        
        await update.message.reply_text(help_text, parse_mode=None)
    
    async def refresh_bins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для ручного обновления BIN'ов (для тестирования)"""
        user_id = update.effective_user.id
        
        # Проверяем, является ли пользователь владельцем (можно настроить по ID)
        if user_id == 123456789:  # Замените на ваш ID
            await update.message.reply_text("🔄 Обновление BIN'ов...")
            try:
                db.generate_random_bins_for_all_countries()
                await update.message.reply_text("✅ BIN'ы успешно обновлены!")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка обновления: {e}")
        else:
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок"""
        query = update.callback_query
        
        data = query.data
        
        if data.startswith("category_"):
            await query.answer()
            category = data.replace("category_", "")
            await self.show_category_products(query, category)
        elif data == "top_up_balance":
            await query.answer()
            await self.top_up_balance(query)
        elif data.startswith("topup_"):
            await query.answer("Создаю счет...")
            amount_str = data.replace("topup_", "")
            try:
                amount = int(amount_str)
            except ValueError:
                await query.answer("Неверная сумма")
                return
            await self.process_balance_topup(query, amount)
        elif data == "favorites":
            await query.answer()
            await self.show_favorites(query)
        elif data == "order_history":
            await query.answer()
            await self.show_order_history(query)
        elif data == "rules":
            await query.answer()
            await self.show_rules_callback(query)
        elif data == "buy_product":
            await query.answer()
            await self.show_product_selection(query)
        elif data == "buy_all_favorites":
            # Пока массовая покупка не реализована
            await query.answer("Групповая покупка скоро будет доступна")
        elif data == "favorite_all":
            # Общее действие для экрана витрины — подсказываем, как добавить
            await query.answer("Откройте товар и нажмите ⭐ В избранное")
        elif data.startswith("product_"):
            await query.answer()
            product_id = int(data.replace("product_", ""))
            await self.show_product_details(query, product_id)
        elif data.startswith("cc_country_"):
            await query.answer()
            country_code = data.replace("cc_country_", "")
            await self.show_country_bins(query, country_code)
        elif data.startswith("cc_bin_"):
            await query.answer()
            bin_data = data.replace("cc_bin_", "")
            country_code, bin_number = bin_data.split("_", 1)
            await self.show_quantity_selection(query, country_code, bin_number)
        elif data.startswith("cc_quantity_"):
            await query.answer()
            quantity_data = data.replace("cc_quantity_", "")
            country_code, bin_number, quantity_str = quantity_data.split("_", 2)
            try:
                quantity = int(quantity_str)
                await self.show_cc_payment(query, country_code, bin_number, quantity)
            except ValueError:
                await query.answer("Неверное количество")
                return
        elif data.startswith("cc_ton_"):
            await query.answer()
            payload = data.replace("cc_ton_", "")
            try:
                country_code, bin_number, quantity_str = payload.split("_", 2)
                quantity = int(quantity_str)
            except ValueError:
                await query.answer("Ошибка данных")
                return
            # Для единообразия создадим инвойс на сумму и покажем инструкции TON
            # Повторно используем процесс CC, но не уходим с экрана инструкций
            cc_products = db.get_products("CC")
            if not cc_products:
                await query.answer("CC продукты не найдены")
                return
            cc_product = cc_products[0]
            total_price = cc_product['price'] * quantity
            text = (
                "💠 **Оплата USDT (TON)**\n\n"
                f"**Сумма к оплате:** {total_price} USDT\n"
                f"**Кошелек:** `{TON_USDT_WALLET}`\n\n"
                "После перевода нажмите **'Я оплатил'**."
            )
            # Для ссылочной проверки используем фиктивный invoice_id на основе BIN
            invoice_id = f"CC-{country_code}-{bin_number}-{quantity}"
            # Создаем заказ в БД для TON-оплаты, чтобы подтверждение смогло его найти
            try:
                user_id = query.from_user.id
                db.create_order(user_id, cc_product['id'], total_price, invoice_id)
            except Exception as e:
                logger.error("Failed to create CC TON order: %s", e)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")]
            ])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        elif data.startswith("cc_trx_"):
            await query.answer()
            payload = data.replace("cc_trx_", "")
            try:
                country_code, bin_number, quantity_str = payload.split("_", 2)
                quantity = int(quantity_str)
            except ValueError:
                await query.answer("Ошибка данных")
                return
            await self.show_cc_trx_payment(query, country_code, bin_number, quantity)
        elif data.startswith("cc_wallets_"):
            await query.answer()
            payload = data.replace("cc_wallets_", "")
            try:
                country_code, bin_number, quantity_str = payload.split("_", 2)
                quantity = int(quantity_str)
            except ValueError:
                await query.answer("Ошибка данных")
                return
            await self.show_cc_wallets(query, country_code, bin_number, quantity)
        elif data.startswith("buy_cc_"):
            await query.answer("Создаю счет для CC...")
            cc_data = data.replace("buy_cc_", "")
            country_code, bin_number, quantity_str = cc_data.split("_", 2)
            try:
                quantity = int(quantity_str)
            except ValueError:
                await query.answer("Неверное количество товара")
                return
            await self.process_cc_purchase(query, country_code, bin_number, quantity)
        elif data.startswith("buy_"):
            await query.answer("Создаю счет...")
            logger.info("Buy button pressed: %s", data)
            product_id_str = data.replace("buy_", "")
            try:
                product_id = int(product_id_str)
            except ValueError:
                # Не наш ID — игнорируем
                logger.warning("Invalid buy ID: %s", product_id_str)
                return
            await self.process_purchase(query, product_id)
        elif data.startswith("favorite_"):
            product_id = int(data.replace("favorite_", ""))
            await self.add_to_favorites_action(query, product_id)
        elif data.startswith("check_payment_"):
            await query.answer()
            invoice_id = data.replace("check_payment_", "")
            await self.check_payment_status(query, invoice_id)
        elif data.startswith("cancel_payment_"):
            await query.answer()
            invoice_id = data.replace("cancel_payment_", "")
            await self.cancel_payment(query, invoice_id)
        elif data.startswith("pay_ton_"):
            await query.answer()
            invoice_id = data.replace("pay_ton_", "")
            await self.show_ton_wallet_instructions(query, invoice_id)
        elif data.startswith("pay_trx_"):
            await query.answer()
            invoice_id = data.replace("pay_trx_", "")
            await self.show_trx_wallet_instructions(query, invoice_id)
        elif data == "back_to_products":
            await query.answer()
            await self.show_product_selection(query)
        elif data == "back_to_profile":
            await query.answer()
            # Отрисовываем меню профиля через callback
            user = query.from_user
            user_info = db.get_user(user.id) or {"first_name": user.first_name, "balance": 0.0}
            balance = user_info.get('balance', 0.0)
            keyboard = [
                [InlineKeyboardButton("💰 Пополнить баланс/Top up", callback_data="top_up_balance")],
                [
                    InlineKeyboardButton("⭐ Избранные товары/Favorite", callback_data="favorites"),
                    InlineKeyboardButton("📋 Правила/Rules", callback_data="rules")
                ],
                [InlineKeyboardButton("📦 История заказов/Order history", callback_data="order_history")],
                [InlineKeyboardButton("🎫 Активировать купон/Activate coupon", callback_data="activate_coupon")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            profile_text = f"""
💙 **Имя:** {user_info.get('first_name', 'Не указано')}
🔑 **ID:** {user.id}
💰 **Ваш баланс:** {balance} $
""".strip()
            await query.edit_message_text(profile_text, reply_markup=reply_markup)
        elif data.startswith("manual_paid_"):
            await query.answer("Отправлено на проверку")
            order_id_str = data.replace("manual_paid_", "")
            if order_id_str.isdigit():
                db.update_order_status(int(order_id_str), "verifying")
            confirm_text = (
                "✅ Спасибо! Мы проверим оплату в ближайшее время.\n"
                f"ID заказа: `{order_id_str}`"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]]
            await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))
        elif data.startswith("manual_cancel_"):
            await query.answer("Заказ отменен")
            order_id_str = data.replace("manual_cancel_", "")
            if order_id_str.isdigit():
                db.update_order_status(int(order_id_str), "canceled")
            await query.edit_message_text("❌ Заказ отменен")
        elif data.startswith("topup_paid_"):
            await query.answer("Отправлено на проверку")
            amount_str = data.replace("topup_paid_", "")
            try:
                amount = int(amount_str)
            except ValueError:
                await query.answer("Неверная сумма")
                return
            user_id = query.from_user.id
            db.add_balance(user_id, amount)
            confirm_text = (
                "✅ Спасибо! Ваш баланс пополнен на {amount} USDT.\n"
                f"Ваш новый баланс: {db.get_user(user_id)['balance']} USDT"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]]
            await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))
        elif data.startswith("topup_ton_"):
            await query.answer("Показываю инструкции для TON...")
            payload = data.replace("topup_ton_", "")
            parts = payload.split("_", 1)
            if len(parts) >= 2:
                amount = parts[0]
                invoice_id = parts[1]
                await self.show_topup_ton_instructions(query, invoice_id, amount)
            else:
                await query.answer("Ошибка данных")
        elif data.startswith("topup_trx_"):
            await query.answer("Показываю инструкции для TRX...")
            payload = data.replace("topup_trx_", "")
            parts = payload.split("_", 1)
            if len(parts) >= 2:
                amount = parts[0]
                invoice_id = parts[1]
                await self.show_topup_trx_instructions(query, invoice_id, amount)
            else:
                await query.answer("Ошибка данных")
        elif data.startswith("topup_confirmed_"):
            await query.answer("Создаю уведомление...")
            invoice_id = data.replace("topup_confirmed_", "")
            await self.handle_topup_confirmation(query, invoice_id)
        elif data.startswith("admin_confirm_"):
            await self.handle_admin_confirmation(query, data, context)
        elif data.startswith("admin_reject_"):
            await self.handle_admin_rejection(query, data, context)
        elif data.startswith("payment_confirmed_"):
            await query.answer("Отправлено на проверку администратору")
            invoice_id = data.replace("payment_confirmed_", "")
            await self.handle_payment_confirmation(query, invoice_id, context)
        elif data == "cc_countries":
            await query.answer()
            await self.show_countries_for_cc(query)

    async def show_product_selection(self, query):
        """Показать список категорий для выбора товаров"""
        # Собираем уникальные категории из доступных товаров
        products = db.get_products()
        categories = sorted({p["category"] for p in products}) if products else []

        if not categories:
            await query.edit_message_text("Товары не найдены")
            return

        keyboard = [[InlineKeyboardButton(cat, callback_data=f"category_{cat}")] for cat in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите категорию:", reply_markup=reply_markup)

    async def show_country_bins(self, query, country_code: str):
        """Показать BIN'ы для выбранной страны"""
        country = None
        countries = db.get_countries()
        for c in countries:
            if c['code'] == country_code:
                country = c
                break
        
        if not country:
            await query.answer("Страна не найдена")
            return
        
        # Получаем BIN'ы для страны
        bins = db.get_bins_by_country(country_code)
        
        if not bins:
            await query.answer("BIN'ы не найдены")
            return
        
        text = f"💳 **BIN'ы для {country['flag']} {country['name']}:**\n\n"
        
        # Создаем клавиатуру BIN'ов (по 2 в ряд)
        keyboard = []
        for i in range(0, len(bins), 2):
            row = []
            row.append(InlineKeyboardButton(
                f"{bins[i]['bin_number']}",
                callback_data=f"cc_bin_{country_code}_{bins[i]['bin_number']}"
            ))
            
            # Добавляем второй BIN в ряд, если он есть
            if i + 1 < len(bins):
                row.append(InlineKeyboardButton(
                    f"{bins[i+1]['bin_number']}",
                    callback_data=f"cc_bin_{country_code}_{bins[i+1]['bin_number']}"
                ))
            
            keyboard.append(row)
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="cc_countries")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_quantity_selection(self, query, country_code: str, bin_number: str):
        """Показать выбор количества для CC"""
        country = None
        countries = db.get_countries()
        for c in countries:
            if c['code'] == country_code:
                country = c
                break
        
        if not country:
            await query.answer("Страна не найдена")
            return
        
        # Получаем информацию о BIN'е
        bins = db.get_bins_by_country(country_code)
        selected_bin = None
        for bin_data in bins:
            if bin_data['bin_number'] == bin_number:
                selected_bin = bin_data
                break
        
        if not selected_bin:
            await query.answer("BIN не найден")
            return
        
        text = f"""Выберите количество CC

Страна: {country['flag']} {country['name']}
BIN: {bin_number}
Тип карты: {selected_bin['card_type']}

Выберите количество для покупки:"""
        
        # Создаем кнопки для выбора количества (1-10)
        keyboard = []
        row = []
        for i in range(1, 11):
            row.append(InlineKeyboardButton(
                f"{i} шт",
                callback_data=f"cc_quantity_{country_code}_{bin_number}_{i}"
            ))
            if len(row) == 5:  # По 5 кнопок в ряд
                keyboard.append(row)
                row = []
        if row:  # Добавляем оставшиеся кнопки
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_cc_payment(self, query, country_code: str, bin_number: str, quantity: int):
        """Показать оплату для выбранного BIN'а"""
        country = None
        countries = db.get_countries()
        for c in countries:
            if c['code'] == country_code:
                country = c
                break
        
        if not country:
            await query.answer("Страна не найдена")
            return
        
        # Получаем информацию о продукте CC
        cc_products = db.get_products("CC")
        if not cc_products:
            await query.answer("CC продукты не найдены")
            return
        
        # Берем первый CC продукт (или можно сделать выбор)
        cc_product = cc_products[0]
        
        # Получаем информацию о BIN'е
        bins = db.get_bins_by_country(country_code)
        selected_bin = None
        for bin_data in bins:
            if bin_data['bin_number'] == bin_number:
                selected_bin = bin_data
                break
        
        if not selected_bin:
            await query.answer("BIN не найден")
            return
        
        # Генерируем случайное количество от 1 до 10
        # quantity = random.randint(1, 10) # This line is now handled in button_callback
        total_price = cc_product['price'] * quantity
        
        text = f"""Оплата CC

Страна: {country['flag']} {country['name']}
BIN: {bin_number}
Тип карты: {selected_bin['card_type']}
Товар: {cc_product['name'].replace('...', '').replace('…', '').strip()}
Количество: {quantity} шт
Цена за единицу: {cc_product['price']} $
Общая стоимость: {total_price} $

Выберите способ оплаты:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить через CryptoBot", callback_data=f"buy_cc_{country_code}_{bin_number}_{quantity}")],
        ]
        if TON_USDT_WALLET:
            keyboard.append([InlineKeyboardButton("💠 Перевод USDT (TON)", callback_data=f"cc_ton_{country_code}_{bin_number}_{quantity}")])
        if TRX_USDT_WALLET:
            keyboard.append([InlineKeyboardButton("⚡ Перевод TRX", callback_data=f"cc_trx_{country_code}_{bin_number}_{quantity}")])
        keyboard.append([InlineKeyboardButton("💳 Кошельки", callback_data=f"cc_wallets_{country_code}_{bin_number}_{quantity}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception as e:
            # Если ошибка Markdown, очистим все специальные символы
            clean_text = text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "").replace("(", "").replace(")", "")
            await query.edit_message_text(clean_text, reply_markup=reply_markup)

    def _escape_markdown(self, text: str) -> str:
        """Безопасное экранирование Markdown символов"""
        if not text:
            return ""
        return (
            text
            .replace("\\", "\\\\")
            .replace("_", "\\_")
            .replace("*", "\\*")
            .replace("`", "\\`")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("~", "\\~")
            .replace(">", "\\>")
            .replace("#", "\\#")
            .replace("+", "\\+")
            .replace("-", "\\-")
            .replace("=", "\\=")
            .replace("|", "\\|")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace(".", "\\.")
            .replace("!", "\\!")
        )

    async def show_cc_wallets(self, query, country_code: str, bin_number: str, quantity: int):
        """Показать кошельки для оплаты CC"""
        country = None
        countries = db.get_countries()
        for c in countries:
            if c['code'] == country_code:
                country = c
                break
        
        if not country:
            await query.answer("Страна не найдена")
            return
        
        # Получаем информацию о продукте CC
        cc_products = db.get_products("CC")
        if not cc_products:
            await query.answer("CC продукты не найдены")
            return
        
        cc_product = cc_products[0]
        total_price = cc_product['price'] * quantity
        
        # Безопасно экранируем все динамические данные
        safe_country_name = self._escape_markdown(country['name'])
        safe_bin = self._escape_markdown(bin_number)
        safe_product_name = self._escape_markdown(cc_product['name'].replace('...', '').replace('…', '').strip())
        
        text = f"""💳 **Кошельки для оплаты CC**

**Страна:** {country['flag']} {safe_country_name}
**BIN:** {safe_bin}
**Товар:** {safe_product_name}
**Количество:** {quantity} шт
**Общая стоимость:** {total_price} $

Выберите кошелек для оплаты:"""
        
        keyboard = [
            [InlineKeyboardButton("💠 USDT (TON)", callback_data=f"cc_ton_{country_code}_{bin_number}_{quantity}")],
            [InlineKeyboardButton("⚡ TRX", callback_data=f"cc_trx_{country_code}_{bin_number}_{quantity}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def show_cc_trx_payment(self, query, country_code: str, bin_number: str, quantity: int):
        """Показать оплату TRX для CC"""
        country = None
        countries = db.get_countries()
        for c in countries:
            if c['code'] == country_code:
                country = c
                break
        
        if not country:
            await query.answer("Страна не найдена")
            return
        
        # Получаем информацию о продукте CC
        cc_products = db.get_products("CC")
        if not cc_products:
            await query.answer("CC продукты не найдены")
            return
        
        cc_product = cc_products[0]
        total_price = cc_product['price'] * quantity
        
        # Безопасно экранируем все динамические данные
        safe_country_name = self._escape_markdown(country['name'])
        safe_bin = self._escape_markdown(bin_number)
        safe_product_name = self._escape_markdown(cc_product['name'].replace('...', '').replace('…', '').strip())
        
        text = f"""⚡ **Оплата TRX**

**Страна:** {country['flag']} {safe_country_name}
**BIN:** {safe_bin}
**Товар:** {safe_product_name}
**Количество:** {quantity} шт
**Общая стоимость:** {total_price} $

Отправьте **{total_price} TRX** на кошелек:
`{TRX_USDT_WALLET}`

После перевода нажмите **'Я оплатил'**."""
        
        # Создаем заказ в БД для TRX-оплаты, чтобы подтверждение смогло его найти
        try:
            user_id = query.from_user.id
            invoice_id = f"CC-TRX-{country_code}-{bin_number}-{quantity}"
            db.create_order(user_id, cc_product['id'], total_price, invoice_id)
        except Exception as e:
            logger.error("Failed to create CC TRX order: %s", e)
        
        keyboard = [
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def add_to_favorites_action(self, query, product_id: int):
        """Добавить товар в избранное пользователя"""
        user_id = query.from_user.id
        ok = db.add_to_favorites(user_id, product_id)
        await query.answer("Добавлено в избранное" if ok else "Уже в избранном")
    
    async def show_category_products(self, query, category: str):
        """Показать товары категории"""
        if category == "CC":
            # Для CC категории показываем страны
            await self.show_countries_for_cc(query)
            return
        
        products = db.get_products(category)
        
        if not products:
            await query.edit_message_text("В данной категории товары не найдены")
            return
        
        # Короткий заголовок без длинных списков, чтобы избежать Message_too_long
        text = f"📦 **{category}**\n\nВыберите товар:"
        
        # Создаем клавиатуру для каждого товара
        keyboard = []
        for product in products:
            # Очищаем название от лишних символов и обрезаем до 30 символов
            clean_name = product['name'].replace("...", "").replace("…", "").strip()
            display_name = clean_name[:30] if len(clean_name) > 30 else clean_name
            keyboard.append([
                InlineKeyboardButton(
                    f"🛒 {display_name} - {product['price']}$",
                    callback_data=f"product_{product['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_countries_for_cc(self, query):
        """Показать страны для CC категории"""
        countries = db.get_countries()
        
        if not countries:
            await query.edit_message_text("Страны не найдены")
            return
        
        text = "🌍 **Выберите страну:**\n\n"
        
        # Создаем клавиатуру стран (по 2 в ряд)
        keyboard = []
        for i in range(0, len(countries), 2):
            row = []
            # Получаем количество BIN'ов для страны
            bins_count = len(db.get_bins_by_country(countries[i]['code']))
            row.append(InlineKeyboardButton(
                f"{countries[i]['flag']} {countries[i]['name']} ({bins_count})", 
                callback_data=f"cc_country_{countries[i]['code']}"
            ))
            if i + 1 < len(countries):
                bins_count_next = len(db.get_bins_by_country(countries[i + 1]['code']))
                row.append(InlineKeyboardButton(
                    f"{countries[i + 1]['flag']} {countries[i + 1]['name']} ({bins_count_next})", 
                    callback_data=f"cc_country_{countries[i + 1]['code']}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_products")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_product_details(self, query, product_id: int):
        """Показать детали товара"""
        product = db.get_product(product_id)
        
        if not product:
            await query.answer("Товар не найден")
            return
        
        text = f"""
📦 **{product['name'].replace('...', '').replace('…', '').strip()}** {product['emoji']}

📝 **Описание:** {product['description']}
💰 **Цена:** {product['price']} $
📊 **Категория:** {product['category']}
📦 **Количество:** {'∞' if product['quantity'] == -1 else product['quantity']} шт.
        """.strip()
        
        keyboard = [
            [InlineKeyboardButton("🛒 Купить", callback_data=f"buy_{product_id}")],
            [InlineKeyboardButton("⭐ В избранное", callback_data=f"favorite_{product_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_products")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def process_purchase(self, query, product_id: int):
        """Обработка покупки"""
        user_id = query.from_user.id
        logger.info("Start purchase. user_id=%s product_id=%s", user_id, product_id)
        product = db.get_product(product_id)
        
        if not product:
            logger.error("Product not found: %s", product_id)
            await query.answer("Товар не найден")
            return
        
        # Создаем счет на оплату через криптобота
        invoice_data = await crypto_bot.create_invoice(
            amount=product['price'],
            description=f"Покупка: {product['name'].replace('...', '').replace('…', '').strip()}"
        )
        
        if not invoice_data:
            logger.error("Failed to create invoice for product_id=%s", product_id)
            # Ручная оплата: создаем заказ и показываем инструкции
            order_id = db.create_order(user_id, product_id, product['price'], None)
            if order_id == -1:
                await query.answer("Ошибка создания заказа")
                return
            # Экранируем подчёркивания в нике, чтобы не ломать Markdown
            safe_owner = OWNER_USERNAME.replace("_", "\\_")
            manual_text = (
                "💳 Оплата вручную\n\n"
                f"Товар: {product['name'].replace('...', '').replace('…', '').strip()}\n"
                f"Сумма к пополнению: {product['price']} USDT\n\n"
                f"Свяжитесь с администратором {safe_owner} и укажите ID заказа: {order_id}.\n"
                "После оплаты нажмите кнопку ниже."
            )
            manual_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я оплатил", callback_data=f"manual_paid_{order_id}")],
                [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"manual_cancel_{order_id}")]
            ])
            await query.edit_message_text(manual_text, reply_markup=manual_keyboard)
            return
        
        # Создаем заказ в базе данных
        order_id = db.create_order(user_id, product_id, product['price'], invoice_data.get('invoice_id'))
        
        if order_id == -1:
            logger.error("Failed to create order for user_id=%s product_id=%s", user_id, product_id)
            await query.answer("Ошибка создания заказа")
            return
        
        # Отправляем сообщение об оплате
        payment_text = crypto_bot.format_payment_message(invoice_data)
        logger.info("Invoice created: %s", invoice_data.get('invoice_id'))
        invoice_id = invoice_data.get('invoice_id')
        # Предпочитаем bot_invoice_url (формат ?start=invoice-<ID>), затем pay_url
        invoice_url = (
            invoice_data.get('bot_invoice_url')
            or invoice_data.get('pay_url')
            or f"https://t.me/CryptoBot?start=pay-{invoice_id}"
        )
        
        # Корректно формируем клавиатуру Telegram (список списков InlineKeyboardButton)
        # Добавляем альтернативные методы: перевод USDT (TON) и TRX на кошельки из .env
        alt_buttons = []
        if TON_USDT_WALLET:
            alt_buttons.append([InlineKeyboardButton("💠 Перевод USDT (TON)", callback_data=f"pay_ton_{invoice_id}")])
        if TRX_USDT_WALLET:
            alt_buttons.append([InlineKeyboardButton("⚡ Перевод TRX", callback_data=f"pay_trx_{invoice_id}")])

        payment_reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить", url=invoice_url)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
            *alt_buttons,
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_payment_{invoice_id}")]
        ])
        
        await query.edit_message_text(
            payment_text,
            reply_markup=payment_reply_markup
        )
        
        # Добавляем сообщение о выдаче товара через админа
        await query.answer("💡 После оплаты товар будет выдан через администратора")
    
    async def process_cc_purchase(self, query, country_code: str, bin_number: str, quantity: int):
        """Обработка покупки CC через CryptoBot"""
        user_id = query.from_user.id
        logger.info("Start CC purchase. user_id=%s country_code=%s bin_number=%s quantity=%s", user_id, country_code, bin_number, quantity)

        # Получаем информацию о продукте CC
        cc_products = db.get_products("CC")
        if not cc_products:
            await query.answer("CC продукты не найдены")
            return
        
        # Берем первый CC продукт (или можно сделать выбор)
        cc_product = cc_products[0]

        # Рассчитываем общую стоимость
        total_price = cc_product['price'] * quantity

        # Создаем счет на оплату через криптобота
        invoice_data = await crypto_bot.create_invoice(
            amount=total_price,
            description=f"Оплата CC: {cc_product['name'].replace('...', '').replace('…', '').strip()} (BIN: {bin_number}, Количество: {quantity})"
        )

        if not invoice_data:
            logger.error("Failed to create CC invoice for user_id=%s product_id=%s", user_id, cc_product['id'])
            await query.answer("Ошибка создания счета для оплаты CC")
            return
        
        # Создаем заказ в базе данных
        order_id = db.create_order(user_id, cc_product['id'], total_price, invoice_data.get('invoice_id'))

        if order_id == -1:
            logger.error("Failed to create CC order for user_id=%s product_id=%s", user_id, cc_product['id'])
            await query.answer("Ошибка создания заказа для оплаты CC")
            return
        
        # Отправляем сообщение об оплате
        payment_text = crypto_bot.format_payment_message(invoice_data)
        logger.info("CC invoice created: %s", invoice_data.get('invoice_id'))
        invoice_id = invoice_data.get('invoice_id')
        invoice_url = (
            invoice_data.get('bot_invoice_url')
            or invoice_data.get('pay_url')
            or f"https://t.me/CryptoBot?start=pay-{invoice_id}"
        )

        # Добавляем альтернативные методы: перевод USDT (TON) и TRX
        alt_buttons = []
        if TON_USDT_WALLET:
            alt_buttons.append([InlineKeyboardButton("💠 Перевод USDT (TON)", callback_data=f"pay_ton_{invoice_id}")])
        if TRX_USDT_WALLET:
            alt_buttons.append([InlineKeyboardButton("⚡ Перевод TRX", callback_data=f"pay_trx_{invoice_id}")])

        payment_reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оплатить", url=invoice_url)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
            *alt_buttons,
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_payment_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cc_country_{country_code}")]
        ])
        
        await query.edit_message_text(
            payment_text,
            reply_markup=payment_reply_markup
        )
        
        # Добавляем сообщение о выдаче товара через админа
        await query.answer("💡 После оплаты товар будет выдан через администратора")
    
    async def top_up_balance(self, query):
        """Пополнение баланса"""
        text = """
💰 **Пополнение баланса**

Выберите сумму для пополнения:
        """.strip()
        
        keyboard = [
            [InlineKeyboardButton("💵 50 $", callback_data="topup_50")],
            [InlineKeyboardButton("💵 100 $", callback_data="topup_100")],
            [InlineKeyboardButton("💵 200 $", callback_data="topup_200")],
            [InlineKeyboardButton("💵 500 $", callback_data="topup_500")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def process_balance_topup(self, query, amount: int):
        """Обработка пополнения баланса"""
        user_id = query.from_user.id
        logger.info("Balance topup. user_id=%s amount=%s", user_id, amount)
        
        # Создаем счет на оплату через криптобота
        invoice_data = await crypto_bot.create_invoice(
            amount=amount,
            description=f"Пополнение баланса на {amount} USDT"
        )
        
        if not invoice_data:
            logger.error("Failed to create topup invoice for amount=%s", amount)
            # Ручная оплата для пополнения баланса
            manual_text = (
                "💳 Пополнение баланса вручную\n\n"
                f"Сумма к пополнению: {amount} USDT\n\n"
                f"Свяжитесь с администратором @luxury_sup и укажите сумму пополнения.\n"
                "После оплаты нажмите кнопку ниже."
            )
            manual_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Я оплатил", callback_data=f"topup_paid_{amount}")],
                [InlineKeyboardButton("❌ Отменить", callback_data="back_to_profile")]
            ])
            await query.edit_message_text(manual_text, reply_markup=manual_keyboard)
            return
        
        # Отправляем сообщение об оплате
        payment_text = crypto_bot.format_payment_message(invoice_data)
        logger.info("Topup invoice created: %s", invoice_data.get('invoice_id'))
        invoice_id = invoice_data.get('invoice_id')
        invoice_url = (
            invoice_data.get('bot_invoice_url')
            or invoice_data.get('pay_url')
            or f"https://t.me/CryptoBot?start=pay-{invoice_id}"
        )
        
        # Создаем заказ для пополнения баланса (используем специальный product_id = 0)
        order_id = db.create_order(user_id, 0, amount, invoice_id)
        if order_id == -1:
            logger.error("Failed to create topup order")
            await query.answer("Ошибка создания заказа")
            return
        
        # Создаем клавиатуру с альтернативными способами оплаты
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", url=invoice_url)],
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"topup_confirmed_{invoice_id}")]
        ]
        
        if TON_USDT_WALLET:
            keyboard.append([InlineKeyboardButton("💠 Перевод USDT (TON)", callback_data=f"topup_ton_{amount}_{invoice_id}")])
        if TRX_USDT_WALLET:
            keyboard.append([InlineKeyboardButton("⚡ Перевод TRX", callback_data=f"topup_trx_{amount}_{invoice_id}")])
        
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="back_to_profile")])
        
        payment_reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            payment_text,
            reply_markup=payment_reply_markup
        )
    
    async def show_favorites(self, query):
        """Показать избранные товары"""
        user_id = query.from_user.id
        favorites = db.get_favorites(user_id)
        
        if not favorites:
            text = "⭐ У вас пока нет избранных товаров"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]]
        else:
            text = "⭐ **Ваши избранные товары:**\n\n"
            for product in favorites:
                # Очищаем название от лишних символов
                clean_name = product['name'].replace("...", "").replace("…", "").strip()
                text += f"{product['emoji']} {clean_name} - {product['price']} $\n"
            
            keyboard = [
                [InlineKeyboardButton("🛒 Купить все", callback_data="buy_all_favorites")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_order_history(self, query):
        """Показать историю заказов"""
        user_id = query.from_user.id
        orders = db.get_user_orders(user_id)
        
        if not orders:
            text = "📦 У вас пока нет заказов"
        else:
            text = "📦 **История заказов:**\n\n"
            for order in orders:
                status_emoji = "✅" if order['status'] == 'completed' else "⏳"
                # Очищаем название от лишних символов
                order_name = order['name'] or "Пополнение баланса"
                clean_name = order_name.replace("...", "").replace("…", "").strip()
                emoji = order['emoji'] or "💰"
                text += f"{status_emoji} {emoji} {clean_name} - {order['amount']} $ ({order['status']})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def check_payment_status(self, query, invoice_id: str):
        """Проверить статус платежа - ОТКЛЮЧЕНО"""
        # Автоматическая проверка отключена - пользователь сам подтверждает оплату
        await query.answer("✅ Автоматическая проверка отключена. Нажмите 'Я оплатил' после оплаты.")
        
        # Старый код закомментирован:
        # status = await crypto_bot.get_invoice_status(invoice_id)
        # 
        # if status == "paid":
        #     await query.answer("✅ Платеж успешно обработан!")
        # elif status == "pending":
        #     await query.answer("⏳ Платеж в обработке")
        # else:
        #     await query.answer("❌ Платеж не найден или отменен")
    
    async def cancel_payment(self, query, invoice_id: str):
        """Отменить платеж"""
        await query.answer("❌ Платеж отменен")
        await query.edit_message_text("❌ Платеж отменен")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        if not update.message:
            return
            
        text = update.message.text
        
        if text == "Меню":
            await self.show_main_menu(update)
        else:
            await update.message.reply_text("Используйте кнопки меню для навигации")
    
    async def show_main_menu(self, update: Update):
        """Показать главное меню"""
        keyboard = [
            [KeyboardButton("Кабинет/Profile"), KeyboardButton("Товары/Products")],
            [KeyboardButton("Правила/Rules"), KeyboardButton("Reviews")],
            [KeyboardButton("Help"), KeyboardButton("Showcase")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("🏠 Главное меню", reply_markup=reply_markup)

    async def show_ton_wallet_instructions(self, query, invoice_id: str):
        """Показывает инструкции по оплате USDT (TON)"""
        if not TON_USDT_WALLET:
            await query.answer("Кошелек не настроен")
            return
        text = (
            "💠 **Оплата USDT (TON)**\n\n"
            f"Отправьте сумму на кошелек: `{TON_USDT_WALLET}`\n"
            f"В комментарии/мемо укажите: `{invoice_id}`\n\n"
            "После перевода нажмите **'Я оплатил'**."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cancel_payment_{invoice_id}")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    async def show_trx_wallet_instructions(self, query, invoice_id: str):
        """Показывает инструкции по оплате TRX"""
        if not TRX_USDT_WALLET:
            await query.answer("Кошелек не настроен")
            return
        text = (
            "⚡ **Оплата TRX**\n\n"
            f"Отправьте сумму на кошелек: `{TRX_USDT_WALLET}`\n"
            f"В комментарии/мемо укажите: `{invoice_id}`\n\n"
            "После перевода нажмите **'Я оплатил'**."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"payment_confirmed_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cancel_payment_{invoice_id}")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_payment_confirmation(self, query, invoice_id: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения оплаты от пользователя"""
        logger.info("=== handle_payment_confirmation called ===")
        logger.info("query type: %s", type(query))
        logger.info("invoice_id: %s", invoice_id)
        logger.info("context type: %s", type(context))
        logger.info("ADMIN_CHANNEL_ID: %s", ADMIN_CHANNEL_ID)
        
        user_id = query.from_user.id
        logger.info("Payment confirmed by user. user_id=%s invoice_id=%s", user_id, invoice_id)

        # Получаем информацию о заказе
        order = db.get_order_by_payment_id(invoice_id)
        if not order:
            logger.error("Order not found for invoice_id=%s", invoice_id)
            await query.answer("Заказ не найден")
            return

        logger.info("Order found: %s", order)

        # Обновляем статус заказа
        db.update_order_status(order['id'], "pending_verification")
        
        # Отправляем уведомление администратору
        try:
            logger.info("Preparing admin notification for order_id=%s", order['id'])
            
            # Определяем, является ли это заказом CC
            is_cc_order = order.get('category') == 'CC' or order.get('name', '').startswith('CC')
            logger.info("Is CC order: %s", is_cc_order)
            
            # Экранируем спецсимволы Markdown для динамических полей
            def _esc_md(value: object) -> str:
                text = str(value) if value is not None else ""
                return (
                    text
                    .replace("\\", "\\\\")
                    .replace("_", "\\_")
                    .replace("*", "\\*")
                    .replace("`", "\\`")
                    .replace("[", "\\[")
                    .replace("]", "\\]")
                )

            safe_first_name = _esc_md(query.from_user.first_name)
            safe_username = _esc_md(query.from_user.username or 'без username')
            safe_product_name = _esc_md(order['name']).replace('...', '').replace('…', '').strip()
            
            admin_message = f"""
💰 **Новый платеж!**

👤 **Пользователь:** {safe_first_name} (@{safe_username})
🆔 **ID:** `{user_id}`
💰 **Сумма:** {order['amount']} $
🛍️ **Товар:** {safe_product_name} {order['emoji']}
🔗 **Счет:** `{invoice_id}`
📅 **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            # Добавляем информацию о количестве для CC заказов
            if is_cc_order:
                # Вычисляем количество на основе цены товара и общей суммы
                product_price = order.get('product_price', order['amount'])
                if product_price and product_price > 0:
                    quantity = int(order['amount'] / product_price)
                    admin_message += f"\n🔢 **Количество:** {quantity} шт."
                    logger.info("CC order quantity: %s", quantity)

            admin_message += "\n\nВыберите действие:"

            # Создаем клавиатуру для админа
            admin_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{order['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{order['id']}")
                ],
                [InlineKeyboardButton("🔍 Проверить в CryptoBot", url=f"https://t.me/CryptoBot?start=invoice-{invoice_id}")]
            ])

            # Отправляем в админский канал
            admin_chat_id = ADMIN_CHANNEL_ID
            logger.info("Sending admin notification to chat_id=%s", admin_chat_id)
            
            # Проверяем, что ADMIN_CHANNEL_ID не равен значению по умолчанию
            if admin_chat_id == -1001234567890:
                logger.warning("ADMIN_CHANNEL_ID is still default value! Please set it in .env file")
                await query.answer("⚠️ ADMIN_CHANNEL_ID не настроен! Уведомление не отправлено.")
                return
            
            logger.info("Admin message: %s", admin_message)
            
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=admin_message,
                reply_markup=admin_keyboard,
                parse_mode=ParseMode.MARKDOWN
            )

            logger.info("Admin notification sent successfully")
            await query.answer("✅ Запрос отправлен администратору на проверку.")
            
            # Обновляем сообщение пользователя
            success_text = f"""
✅ Заявка на подтверждение отправлена администратору.

💰 Сумма: {order['amount']} $
🛍️ Товар: {order['name'].replace('...', '').replace('…', '').strip()}
📅 Время: {datetime.now().strftime('%H:%M:%S')}"""

            # Добавляем количество для CC заказов
            if is_cc_order:
                product_price = order.get('product_price', order['amount'])
                if product_price and product_price > 0:
                    quantity = int(order['amount'] / product_price)
                    success_text += f"\n🔢 Количество: {quantity} шт."

            success_text += """

⏳ Ожидайте решения администратора.
После подтверждения вы получите инструкцию по выдаче товара."""

            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в профиль", callback_data="back_to_profile")
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error("Failed to send admin notification: %s", e, exc_info=True)
            await query.answer("Ошибка отправки уведомления администратору")

    async def handle_topup_confirmation(self, query, invoice_id: str):
        """Обработка подтверждения оплаты пополнения баланса от пользователя"""
        user_id = query.from_user.id
        logger.info("Topup confirmed by user. user_id=%s invoice_id=%s", user_id, invoice_id)

        # Получаем информацию о заказе пополнения баланса
        order = db.get_order_by_payment_id(invoice_id)
        if not order:
            await query.answer("Заказ не найден")
            return

        # Обновляем статус заказа
        db.update_order_status(order['id'], "completed")

        # Добавляем баланс пользователю
        amount = order['amount']
        db.add_balance(user_id, amount)

        # Отправляем уведомление пользователю
        user_info = db.get_user(user_id)
        if user_info:
            await query.answer("✅ Баланс пополнен!")
            
            # Обновляем сообщение
            success_text = f"""
✅ **Баланс пополнен!**

💰 **Сумма пополнения:** {amount} USDT
💳 **Новый баланс:** {db.get_user(user_id)['balance']} USDT
📅 **Время:** {datetime.now().strftime('%H:%M:%S')}

🎉 Спасибо за пополнение!
            """.strip()
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в профиль", callback_data="back_to_profile")
                ]])
            )
        else:
            await query.answer("Пользователь не найден")
            await query.edit_message_text(
                "Пользователь не найден.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в профиль", callback_data="back_to_profile")
                ]])
            )

    async def show_topup_ton_instructions(self, query, invoice_id: str, amount: str = None):
        """Показывает инструкции по пополнению баланса USDT (TON)"""
        if not TON_USDT_WALLET:
            await query.answer("Кошелек не настроен")
            return
        
        # Получаем информацию о заказе пополнения баланса
        order = db.get_order_by_payment_id(invoice_id)
        if not order:
            # Если заказ не найден, создаем новый для TON пополнения
            user_id = query.from_user.id
            # Используем переданную сумму или извлекаем из invoice_id
            if amount:
                try:
                    amount_float = float(amount)
                except ValueError:
                    amount_float = 0
            else:
                try:
                    amount_str = invoice_id.split('_')[1] if '_' in invoice_id else "0"
                    amount_float = float(amount_str)
                except (ValueError, IndexError):
                    amount_float = 0
            
            # Создаем заказ для TON пополнения
            order_id = db.create_order(user_id, 0, amount_float, f"TON-{invoice_id}")
            if order_id == -1:
                await query.answer("Ошибка создания заказа")
                return
            
            order = {
                'amount': amount_float,
                'id': order_id
            }
        
        text = (
            "💠 **Пополнение баланса USDT (TON)**\n\n"
            f"Отправьте **{order['amount']} USDT** на кошелек: `{TON_USDT_WALLET}`\n"
            f"В комментарии/мемо укажите: `{invoice_id}`\n\n"
            "После перевода нажмите **'Я оплатил'**."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"topup_confirmed_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    async def show_topup_trx_instructions(self, query, invoice_id: str, amount: str = None):
        """Показывает инструкции по пополнению баланса TRX"""
        if not TRX_USDT_WALLET:
            await query.answer("Кошелек не настроен")
            return
        
        # Получаем информацию о заказе пополнения баланса
        order = db.get_order_by_payment_id(invoice_id)
        if not order:
            # Если заказ не найден, создаем новый для TRX пополнения
            user_id = query.from_user.id
            # Используем переданную сумму или извлекаем из invoice_id
            if amount:
                try:
                    amount_float = float(amount)
                except ValueError:
                    amount_float = 0
            else:
                try:
                    amount_str = invoice_id.split('_')[1] if '_' in invoice_id else "0"
                    amount_float = float(amount_str)
                except (ValueError, IndexError):
                    amount_float = 0
            
            # Создаем заказ для TRX пополнения
            order_id = db.create_order(user_id, 0, amount_float, f"TRX-{invoice_id}")
            if order_id == -1:
                await query.answer("Ошибка создания заказа")
                return
            
            order = {
                'amount': amount_float,
                'id': order_id
            }
        
        text = (
            "⚡ **Пополнение баланса TRX**\n\n"
            f"Отправьте **{order['amount']} TRX** на кошелек: `{TRX_USDT_WALLET}`\n"
            f"В комментарии/мемо укажите: `{invoice_id}`\n\n"
            "После перевода нажмите **'Я оплатил'**."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"topup_confirmed_{invoice_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    async def handle_admin_confirmation(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения администратором"""
        # Проверяем права администратора
        if not self.is_admin(query.from_user.id):
            await query.answer("❌ У вас нет прав для выполнения этого действия")
            return
            
        order_id_str = data.replace("admin_confirm_", "")
        if order_id_str.isdigit():
            order_id = int(order_id_str)
            order = db.get_order_by_id(order_id)
            if order:
                db.update_order_status(order_id, "completed")
                await query.answer("✅ Заказ подтвержден!")
                await query.edit_message_text(
                    f"✅ Заказ {order['emoji']} {order['name'].replace('...', '').replace('…', '').strip()} (ID: {order_id}) подтвержден администратором.\n\n"
                    f"💰 Сумма: {order['amount']} $\n"
                    f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n"
                    "🛍️ Товар будет выдан пользователю.",
                    parse_mode=None
                )
                # Отправляем уведомление пользователю
                user_id = order['user_id']
                user_info = db.get_user(user_id)
                if user_info:
                    user_name = user_info.get('first_name', 'пользователь')
                    user_username = user_info.get('username', 'без username')
                    user_emoji = "👤" if user_username else "👤"
                    # Определяем контакт для выдачи
                    is_cc_order = order.get('category') == 'CC' or (order.get('name') or '').upper().startswith('CC')
                    delivery_contact = "@luxury_sup" if not is_cc_order else "@Bellffortt"

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"{user_emoji} Ваш заказ {order['emoji']} {order['name'].replace('...', '').replace('…', '').strip()} (ID: {order_id}) подтвержден администратором!\n\n"
                            f"💰 Сумма: {order['amount']} $\n"
                            f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                            f"📦 Заберите товар у {delivery_contact}"
                        ),
                        parse_mode=None
                    )
            else:
                await query.answer("Заказ не найден")
        else:
            await query.answer("Неверный ID заказа")

    async def handle_admin_rejection(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка отклонения администратором"""
        # Проверяем права администратора
        if not self.is_admin(query.from_user.id):
            await query.answer("❌ У вас нет прав для выполнения этого действия")
            return
            
        order_id_str = data.replace("admin_reject_", "")
        if order_id_str.isdigit():
            order_id = int(order_id_str)
            order = db.get_order_by_id(order_id)
            if order:
                db.update_order_status(order_id, "canceled")
                await query.answer("❌ Заказ отклонен!")
                await query.edit_message_text(
                    f"❌ Заказ {order['emoji']} {order['name'].replace('...', '').replace('…', '').strip()} (ID: {order_id}) отклонен администратором.\n\n"
                    f"💰 Сумма: {order['amount']} $\n"
                    f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n"
                    "❌ Заказ отменен.",
                    parse_mode=None
                )
                # Отправляем уведомление пользователю
                user_id = order['user_id']
                user_info = db.get_user(user_id)
                if user_info:
                    user_name = user_info.get('first_name', 'пользователь')
                    user_username = user_info.get('username', 'без username')
                    user_emoji = "👤" if user_username else "👤"
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"{user_emoji} Ваш заказ {order['emoji']} {order['name'].replace('...', '').replace('…', '').strip()} (ID: {order_id}) отклонен администратором!\n\n"
                             f"💰 Сумма: {order['amount']} $\n"
                             f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n"
                             "❌ Заказ отменен.",
                        parse_mode=None
                    )
            else:
                await query.answer("Заказ не найден")
        else:
            await query.answer("Неверный ID заказа")
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        # Добавьте сюда ID администраторов
        admin_ids = ADMIN_IDS  # Используем ID из config
        return user_id in admin_ids
    
    def run(self):
        """Запуск бота"""
        print(f"🚀 Запуск {BOT_NAME} бота...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = ShopBot()
    bot.run()
