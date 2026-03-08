import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Твой токен
TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопка для удобства
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🎨 Сгенерировать фото")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Я продвинутый ИИ для создания изображений. 🤖\n"
        "Просто напиши мне, что ты хочешь увидеть, или нажми кнопку ниже.",
        reply_markup=main_kb
    )

@dp.message(F.text == "🎨 Сгенерировать фото")
async def prompt_guide(message: types.Message):
    await message.answer("Введите текстовое описание для генерации (на английском или русском):")

@dp.message()
async def generate_fake_photo(message: types.Message):
    if not message.text:
        return

    # Имитация работы ИИ
    status_msg = await message.answer("🔄 Анализирую запрос...")
    await asyncio.sleep(1.5)
    
    await status_msg.edit_text("🧬 Подбираю нейроны и текстуры...")
    await asyncio.sleep(2)
    
    await status_msg.edit_text("🖌 Отрисовка деталей (75%)...")
    await asyncio.sleep(1.5)

    # Здесь мы используем бесплатный генератор картинок по URL (для примера)
    # Этот сервис берет текст и отдает картинку.
    photo_url = f"https://pollinations.ai/p/{message.text.replace(' ', '%20')}?width=1024&height=1024&seed=42"
    
    try:
        await message.answer_photo(
            photo=photo_url,
            caption=f"✅ Готово! Ваш запрос: *{message.text}*\nМодель: Gemini 3 Flash Image",
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("❌ Произошла ошибка при генерации. Попробуйте другой запрос.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
