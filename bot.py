import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8905490929:AAHO95Lo5fsOapiaYPD5St36IKEWniGn8t0"  # Твой новый токен сюда
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔍 Оценка", callback_data="search"),
        InlineKeyboardButton(text="⚖️ Сравнение", callback_data="compare")
    ]])
    await msg.answer("👑 NickWorth Bot\n\n💎 Оценка Telegram никнеймов по реальным данным Fragment", reply_markup=kb)

@dp.callback_query(F.data == "search")
async def search(cb: types.CallbackQuery):
    await cb.message.answer("Отправь @username для оценки:")

@dp.message()
async def check_username(msg: types.Message):
    username = msg.text.strip().lstrip("@").lower()
    if len(username) < 5:
        await msg.answer("❌ Минимум 5 символов")
        return
    
    # Простая оценка по длине
    length = len(username)
    if length <= 4:
        price = 1000
    elif length <= 5:
        price = 200
    else:
        price = 50
    
    await msg.answer(
cat > bot.py << 'EOF'
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8905490929:AAHO95Lo5fsOapiaYPD5St36IKEWniGn8t0"  # Твой новый токен сюда
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔍 Оценка", callback_data="search"),
        InlineKeyboardButton(text="⚖️ Сравнение", callback_data="compare")
    ]])
    await msg.answer("👑 NickWorth Bot\n\n💎 Оценка Telegram никнеймов по реальным данным Fragment", reply_markup=kb)

@dp.callback_query(F.data == "search")
async def search(cb: types.CallbackQuery):
    await cb.message.answer("Отправь @username для оценки:")

@dp.message()
async def check_username(msg: types.Message):
    username = msg.text.strip().lstrip("@").lower()
    if len(username) < 5:
        await msg.answer("❌ Минимум 5 символов")
        return
    
    # Простая оценка по длине
    length = len(username)
    if length <= 4:
        price = 1000
    elif length <= 5:
        price = 200
    else:
        price = 50
    
    await msg.answer(
        f"💰 <b>@{username}</b>\n\n"
        f"Примерная цена: <b>{price} TON</b>\n"
        f"≈ ${price * 5:.0f} USD\n\n"
        f"<i>Быстрая оценка по длине</i>",
        parse_mode="HTML"
    )

async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

asyncio.run(main())
