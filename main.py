import asyncio
import logging
import random
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Твой токен
TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клава с кнопкой
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🎨 Сгенерировать фото")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🤖 Привет! Я ИИ-генератор изображений.\n\n"
        "Пришли мне описание того, что хочешь увидеть (лучше на английском для точности), "
        "и я создам это за пару секунд!",
        reply_markup=main_kb
    )

@dp.message(F.text == "🎨 Сгенерировать фото")
async def prompt_guide(message: types.Message):
    await message.answer("Опиши словами, что нужно нарисовать:")

@dp.message()
async def handle_generation(message: types.Message):
    if not message.text:
        return

    # 1. Информируем пользователя
    status_msg = await message.answer("🔄 Подключаюсь к нейросети...")
    
    try:
        # 2. Имитация этапов работы
        await asyncio.sleep(1)
        await status_msg.edit_text("🖌 Отрисовка деталей и освещения...")
        
        # 3. Формируем запрос
        # Кодируем текст (чтобы русский язык и пробелы работали в ссылке)
        safe_prompt = quote(message.text)
        seed = random.randint(1, 1000000)
        
        # Используем прямой API эндпоинт для картинок
        photo_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true&enhance=true"

        # 4. Отправляем результат
        await message.answer_photo(
            photo=photo_url,
            caption=(
                f"✅ **Готово!**\n"
                f"📝 Запрос: `{message.text}`\n"
                f"🧠 Модель: Gemini 3 Flash Image"
            ),
            parse_mode="Markdown"
        )
        
        # Удаляем сервисное сообщение
        await status_msg.delete()

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Ошибка генерации. Попробуй другой запрос или подожди немного.")

async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
