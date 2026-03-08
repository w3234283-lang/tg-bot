import asyncio
import logging
import random
import aiohttp
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

# Конфигурация проекта
TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"
ADMIN_USER = "Zaniks_coder" #

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Интерфейс без эмодзи
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Generate Image")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "System ready. Enter image description.",
        reply_markup=main_kb
    )

@dp.message(F.text == "Generate Image")
async def request_prompt(message: types.Message):
    await message.answer("Please provide text prompt:")

@dp.message()
async def process_image_request(message: types.Message):
    if not message.text or message.text == "Generate Image":
        return

    status = await message.answer("Processing...")
    
    # Пул эндпоинтов для отказоустойчивости
    seed = random.randint(1, 1000000)
    encoded_text = quote(message.text)
    url = f"https://image.pollinations.ai/prompt/{encoded_text}?width=1024&height=1024&seed={seed}&nologo=true"

    # Жесткий таймаут, чтобы избежать SIGTERM при зависании
    timeout = aiohttp.ClientTimeout(total=30)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    
                    if len(data) > 5000:
                        image = BufferedInputFile(data, filename="result.jpg")
                        await message.answer_photo(
                            photo=image,
                            caption=f"Result for: {message.text}\nStatus: Delivered"
                        )
                        await status.delete()
                    else:
                        await status.edit_text("Error: Received invalid data.")
                else:
                    await status.edit_text("Error: AI server busy.")
    except asyncio.TimeoutError:
        await status.edit_text("Error: Request timed out. Try again.")
    except Exception as e:
        logging.error(f"Global error: {e}")
        await status.edit_text("System error occurred.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
