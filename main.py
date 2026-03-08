import asyncio
import logging
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8741900639:AAEx7WMzNmdFQ3mxSG5Fx8DDSbhGtql7c-I'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('dating_bot.db')
    cur = conn.cursor()
    # Таблица пользователей
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        age INTEGER,
        city TEXT,
        photo_id TEXT,
        description TEXT
    )''')
    # Таблица лайков
    cur.execute('''CREATE TABLE IF NOT EXISTS likes (
        from_id INTEGER,
        to_id INTEGER,
        PRIMARY KEY (from_id, to_id)
    )''')
    conn.commit()
    conn.close()

# --- СОСТОЯНИЯ ---
class Registration(StatesGroup):
    name = State()
    age = State()
    city = State()
    photo = State()

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Смотреть анкеты")],
        [KeyboardButton(text="Моя анкета")]
    ], resize_keyboard=True)

def get_rating_kb(to_id):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️", callback_data=f"like_{to_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{to_id}")
        ]
    ])
    return builder

# --- ХЕНДЛЕРЫ РЕГИСТРАЦИИ ---
@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('dating_bot.db')
    cur = conn.cursor()
    user = cur.execute("SELECT * FROM users WHERE id = ?", (message.from_user.id,)).fetchone()
    conn.close()

    if user:
        await message.answer("С возвращением!", reply_markup=get_main_kb())
    else:
        await message.answer("Привет! Давай создадим анкету. Как тебя зовут?")
        await state.set_state(Registration.name)

@router.message(Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Введи число!")
    await state.update_data(age=int(message.text))
    await message.answer("Из какого ты города?")
    await state.set_state(Registration.city)

@router.message(Registration.city)
async def reg_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Пришли своё фото")
    await state.set_state(Registration.photo)

@router.message(Registration.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    
    conn = sqlite3.connect('dating_bot.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message.from_user.id, message.from_user.username, data['name'], 
                 data['age'], data['city'], photo_id, "Без описания"))
    conn.commit()
    conn.close()
    
    await message.answer("Анкета сохранена!", reply_markup=get_main_kb())
    await state.clear()

# --- ЛОГИКА ПРОСМОТРА ---
@router.message(F.text == "Смотреть анкеты")
async def show_users(message: types.Message):
    conn = sqlite3.connect('dating_bot.db')
    cur = conn.cursor()
    # Выбираем случайного пользователя, который не является текущим
    users = cur.execute("SELECT * FROM users WHERE id != ?", (message.from_user.id,)).fetchall()
    conn.close()

    if not users:
        return await message.answer("Пока анкет нет.")

    target = random.choice(users)
    caption = f"{target[2]}, {target[3]}\nг. {target[4]}"
    await message.answer_photo(target[5], caption=caption, reply_markup=get_rating_kb(target[0]))

# --- ЛАЙКИ И МЭТЧИ ---
@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    to_id = int(callback.data.split("_")[1])
    from_id = callback.from_user.id
    
    conn = sqlite3.connect('dating_bot.db')
    cur = conn.cursor()
    
    # Сохраняем лайк
    cur.execute("INSERT OR IGNORE INTO likes VALUES (?, ?)", (from_id, to_id))
    
    # Проверяем ответный лайк
    match = cur.execute("SELECT * FROM likes WHERE from_id = ? AND to_id = ?", (to_id, from_id)).fetchone()
    conn.commit()
    conn.close()

    await callback.answer("Лайк отправлен!")
    
    if match:
        await bot.send_message(from_id, f"У тебя мэтч! Пиши скорее: @{callback.from_user.username if callback.from_user.username else 'id' + str(to_id)}")
        # Уведомляем второго пользователя
        await bot.send_message(to_id, f"Взаимная симпатия! Твой мэтч: @{callback.from_user.username}")
    
    # Показываем следующую анкету
    await show_users(callback.message)

@router.callback_query(F.data.startswith("dislike_"))
async def handle_dislike(callback: types.CallbackQuery):
    await callback.answer("Пропускаем...")
    await show_users(callback.message)

# --- ЗАПУСК ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
