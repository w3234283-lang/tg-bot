import asyncio
import logging
import random
import aiohttp # Библиотека для скачивания
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile # Для отправки байтов

TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🎨 Сгенерировать фото")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Бот готов к генерации! Напиши запрос.", reply_markup=main_kb)

@dp.message()
async def handle_generation(message: types.Message):
    if not message.text or message.text == "🎨 Сгенерировать фото":
        if message.text == "🎨 Сгенерировать фото":
            await message.answer("Опиши, что нарисовать:")
        return

    status_msg = await message.answer("🔄 Нейросеть генерирует изображение...")
    
    try:
        safe_prompt = quote(message.text)
        seed = random.randint(1, 1000000)
        # Убрали лишние параметры, оставили главное для стабильности
        photo_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true"

        # Скачиваем картинку во временную память
        async with aiohttp.ClientSession() as session:
            async with session.get(photo_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    # Создаем файл из байтов
                    image_file = BufferedInputFile(image_data, filename="ai_photo.jpg")
                    
                    await message.answer_photo(
                        photo=image_file,
                        caption=f"✅ Готово!\nЗапрос: {message.text}\nМодель: Gemini 3 Flash Image"
                    )
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ Сервис генерации временно недоступен.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Ошибка при загрузке фото. Попробуй еще раз.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
