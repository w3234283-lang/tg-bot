import asyncio
import logging
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

API_TOKEN = '8741900639:AAEx7WMzNmdFQ3mxSG5Fx8DDSbhGtql7c-I'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- БАЗА ДАННЫХ ---
def execute_query(query, params=(), fetchone=False, fetchall=False):
    with sqlite3.connect('dating_bot.db') as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetchone: return cur.fetchone()
        if fetchall: return cur.fetchall()
        conn.commit()

def init_db():
    execute_query('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, name TEXT, age INTEGER, city TEXT, photo_id TEXT)''')
    execute_query('''CREATE TABLE IF NOT EXISTS likes (
        from_id INTEGER, to_id INTEGER, PRIMARY KEY (from_id, to_id))''')

# --- СОСТОЯНИЯ ---
class Registration(StatesGroup):
    name, age, city, photo = State(), State(), State(), State()

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Смотреть анкеты")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="⚙️ Изменить анкету")]
    ], resize_keyboard=True)

def get_rating_kb(to_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️", callback_data=f"like_{to_id}"),
         InlineKeyboardButton(text="👎", callback_data=f"dislike_{to_id}")]
    ])

# --- РЕГИСТРАЦИЯ ---
@router.message(CommandStart())
@router.message(F.text == "⚙️ Изменить анкету")
async def start_reg(message: types.Message, state: FSMContext):
    await message.answer("📝 **Как тебя зовут?**", parse_mode="Markdown")
    await state.set_state(Registration.name)

@router.message(Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"👋 Приятно познакомиться, *{message.text}*!\n\n🔢 **Сколько тебе лет?**", parse_mode="Markdown")
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Введи возраст числом!")
    await state.update_data(age=int(message.text))
    await message.answer("📍 **Из какого ты города?**", parse_mode="Markdown")
    await state.set_state(Registration.city)

@router.message(Registration.city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("📸 **Пришли классное фото!**", parse_mode="Markdown")
    await state.set_state(Registration.photo)

@router.message(Registration.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    execute_query("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)",
                (message.from_user.id, message.from_user.username, data['name'], data['age'], data['city'], photo_id))
    
    await message.answer("✅ **Анкета готова!**", reply_markup=get_main_kb(), parse_mode="Markdown")
    await state.clear()

# --- ПРОСМОТР ---
@router.message(F.text == "👤 Моя анкета")
async def my_profile(message: types.Message):
    user = execute_query("SELECT * FROM users WHERE id = ?", (message.from_user.id,), fetchone=True)
    if user:
        caption = f"✨ **Твоя карточка:**\n\n👤 {user[2]}, {user[3]}\n📍 {user[4]}"
        await message.answer_photo(user[5], caption=caption, parse_mode="Markdown")
    else:
        await message.answer("У тебя еще нет анкеты. Жми /start")

@router.message(F.text == "🚀 Смотреть анкеты")
async def show_users(message: types.Message):
    # Ищем тех, кого еще не лайкали/дизлайкали и кто не я сам
    query = """
        SELECT * FROM users 
        WHERE id != ? 
        AND id NOT IN (SELECT to_id FROM likes WHERE from_id = ?)
        ORDER BY RANDOM() LIMIT 1
    """
    target = execute_query(query, (message.from_user.id, message.from_user.id), fetchone=True)

    if not target:
        return await message.answer("💎 **Анкеты закончились!** Приходи позже или измени свою.")

    caption = f"🔥 **{target[2]}, {target[3]}**\n📍 {target[4]}"
    await message.answer_photo(target[5], caption=caption, reply_markup=get_rating_kb(target[0]), parse_mode="Markdown")

# --- ВЗАИМОДЕЙСТВИЕ ---
@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    to_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id
    
    execute_query("INSERT OR IGNORE INTO likes VALUES (?, ?)", (from_id, to_id))
    match = execute_query("SELECT * FROM likes WHERE from_id = ? AND to_id = ?", (to_id, from_id), fetchone=True)

    if match:
        # Инфо о текущем пользователе
        me = execute_query("SELECT * FROM users WHERE id = ?", (from_id,), fetchone=True)
        # Кнопка для перехода в ЛС
        link_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💌 Написать", url=f"tg://user?id={from_id}")]
        ])
        link_kb_target = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💌 Написать", url=f"tg://user?id={to_id}")]
        ])

        await bot.send_message(to_id, f"❤️ **Взаимная симпатия!**\nС тобой хочет пообщаться {me[2]}", 
                               reply_markup=link_kb, parse_mode="Markdown")
        await callback.message.answer("🎉 **Это мэтч!** Ссылка на профиль внизу", reply_markup=link_kb_target, parse_mode="Markdown")
    
    await callback.message.delete()
    await show_users(callback.message)

@router.callback_query(F.data.startswith("dislike_"))
async def handle_dislike(callback: types.CallbackQuery):
    # Записываем дизлайк в ту же таблицу, чтобы больше не показывать эту анкету
    execute_query("INSERT OR IGNORE INTO likes VALUES (?, ?)", (callback.from_user.id, int(callback.data.split("_")[1])))
    await callback.message.delete()
    await show_users(callback.message)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
