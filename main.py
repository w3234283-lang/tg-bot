import asyncio
import logging
import random
import aiohttp
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

# Токен и настройки
TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"
ADMIN_USERNAME = "Admin1111" # Строгое ограничение прав

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки без эмодзи
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Generate Image")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "AI Image Generator System Initialized.\n"
        "Send a text description to create an image.",
        reply_markup=main_kb
    )

@dp.message(F.text == "Generate Image")
async def prompt_request(message: types.Message):
    await message.answer("Enter your prompt:")

@dp.message()
async def handle_generation(message: types.Message):
    if not message.text or message.text == "Generate Image":
        return

    # Проверка на админ-права для системных уведомлений (опционально)
    is_admin = message.from_user.username == ADMIN_USERNAME

    status_msg = await message.answer("Processing request...")
    
    # Пул адресов для обхода блокировок
    urls = [
        f"https://image.pollinations.ai/prompt/{quote(message.text)}?width=1024&height=1024&seed={random.randint(1,100000)}&nologo=true",
        f"https://pollinations.ai/p/{quote(message.text)}?width=1024&height=1024&seed={random.randint(1,100000)}&model=flux"
    ]

    success = False
    timeout = aiohttp.ClientTimeout(total=45) # Оптимальное время ожидания
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in urls:
            try:
                await status_msg.edit_text("Generating visual data...")
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        
                        # Если это картинка, а не ошибка (минимум 5КБ)
                        if len(data) > 5000:
                            photo = BufferedInputFile(data, filename="result.jpg")
                            await message.answer_photo(
                                photo=photo,
                                caption=f"Status: Success\nPrompt: {message.text}\nAdmin: {ADMIN_USERNAME if is_admin else 'User'}"
                            )
                            await status_msg.delete()
                            success = True
                            break
            except Exception as e:
                logging.error(f"Error on {url}: {e}")
                continue
    
    if not success:
        await status_msg.edit_text("System failure: Service unavailable. Try again later.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
