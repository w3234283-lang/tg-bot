import asyncio
import logging
import random
import aiohttp
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

# Твой токен
TOKEN = "8755669309:AAG0i_Ql42SevYNgzdvJvRVCEYPe3ttK2XU"

# Настройка логов
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатура (без эмодзи, как в твоих правилах проекта)
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Generate Photo")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Welcome! I am an AI Image Generator.\n"
        "Send me a description of what you want to see.",
        reply_markup=main_kb
    )

@dp.message(F.text == "Generate Photo")
async def prompt_guide(message: types.Message):
    await message.answer("Describe the image you want to create:")

@dp.message()
async def handle_generation(message: types.Message):
    # Игнорируем пустые сообщения
    if not message.text or message.text == "Generate Photo":
        return

    status_msg = await message.answer("🔄 AI is thinking...")
    
    # Список возможных адресов для надежности
    urls = [
        f"https://image.pollinations.ai/prompt/{quote(message.text)}?width=1024&height=1024&seed={random.randint(1,1000)}&nologo=true",
        f"https://pollinations.ai/p/{quote(message.text)}?width=1024&height=1024&seed={random.randint(1,1000)}"
    ]

    success = False
    
    # Настройка сессии с долгим ожиданием
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for photo_url in urls:
            try:
                await status_msg.edit_text("🖌 Drawing details...")
                async with session.get(photo_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Проверка, что пришла картинка, а не ошибка в HTML
                        if len(image_data) > 5000: 
                            image_file = BufferedInputFile(image_data, filename="ai_result.jpg")
                            
                            await message.answer_photo(
                                photo=image_file,
                                caption=f"✅ Done!\nPrompt: {message.text}\nModel: Gemini 3 Flash Image"
                            )
                            await status_msg.delete()
                            success = True
                            break # Выходим из цикла, если успешно
            except Exception as e:
                logging.error(f"Attempt failed: {e}")
                continue
    
    if not success:
        await status_msg.edit_text("❌ Service is busy. Please try a simpler prompt or wait a minute.")

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
