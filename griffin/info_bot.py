import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import config
import json
from datetime import datetime
from aiogram.utils.deep_linking import create_start_link

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot initialization
bot = Bot(token=config.INFO_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.chat.type != "private":
        await message.answer("Инфо-бот работает только в личке.")
        return
    # Профиль пользователя
    user = message.from_user
    text = f"👤 Ваш профиль\nID: {user.id}\nЮзернейм: @{user.username or '-'}"
    # Ссылка на основного бота с параметром worker
    main_bot_username = "matrascity_bot"  # замените на актуальный username основного бота
    link = f"https://t.me/{main_bot_username}?start=worker"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👷‍♂️ Стать воркером", url=link)],
        [InlineKeyboardButton(text="🔄 Профиль", callback_data="profile_refresh")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.message()
async def handle_logs(message: types.Message):
    if message.chat.id != int(config.INFO_BOT_CHAT_ID):
        return
    
    if "оплатил" in message.text:
        await message.answer(f"💸 {message.text}")
    elif "User Action Log:" in message.text:
        await message.answer(f"�� {message.text}")

@dp.callback_query(F.data.startswith("view_user_"))
async def view_user(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[2]
    # Здесь можно добавить логику для просмотра информации о пользователе
    await callback.answer(f"Viewing user {user_id}")

@dp.callback_query(F.data.startswith("delete_log_"))
async def delete_log(callback: types.CallbackQuery):
    message_id = callback.data.split("_")[2]
    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=int(message_id))
        await callback.answer("Log deleted")
    except Exception as e:
        await callback.answer("Failed to delete log")

@dp.callback_query(F.data == "info_stats")
async def show_stats(callback: types.CallbackQuery):
    # Здесь можно добавить логику для отображения статистики
    await callback.answer("Statistics feature coming soon")

@dp.callback_query(F.data == "info_search")
async def search_logs(callback: types.CallbackQuery):
    # Здесь можно добавить логику для поиска по логам
    await callback.answer("Search feature coming soon")

@dp.callback_query(F.data == "profile_refresh")
async def profile_refresh(callback: types.CallbackQuery):
    user = callback.from_user
    text = f"👤 Ваш профиль\nID: {user.id}\nЮзернейм: @{user.username or '-'}"
    main_bot_username = "matrascity_bot"  # замените на актуальный username основного бота
    link = f"https://t.me/{main_bot_username}?start=worker"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👷‍♂️ Стать воркером", url=link)],
        [InlineKeyboardButton(text="🔄 Профиль", callback_data="profile_refresh")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main()) 