import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI

# Загружаем секреты
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Наш мощный системный промпт
SYSTEM_PROMPT = """
Ты — профессиональный Project Manager Assistant. Твоя цель — превратить хаос переписки в структуру.

Проанализируй входящий текст и сформируй отчет в формате Markdown:

### 🎯 Summary
(Кратко в 1-2 предложениях: о чем шло обсуждение и каков главный итог)

### ✅ Action Items (Задачи)
- [ ] **[Имя Ответственного]**: Задача (Дедлайн/Срок).
- [ ] **[?]**: Задача (если ответственный не ясен из текста).

### ⚡ Key Decisions (Принятые решения)
- Тезисно зафиксированные договоренности.

### ⚠️ Risks & Blockers (Риски и проблемы)
- Если кто-то упомянул проблему, задержку или нехватку ресурсов — выпиши сюда.

ВАЖНО: Игнорируй приветствия, флуд и шутки. Пиши на русском языке.
"""

# --- Вспомогательная функция (чтобы не дублировать код) ---
async def generate_summary(text_content):
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text_content}
        ]
    )
    return response.choices[0].message.content

# --- Хендлеры (Обработчики) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! 👋\nЯ умею работать с текстом и голосовыми.\n\n🎤 Перешли мне войс или напиши текст, и я сделаю саммари.")

# 1. Обработка Текста
@dp.message(F.text)
async def handle_text(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        summary = await generate_summary(message.text)
        await message.answer(summary)
    except Exception as e:
        await message.answer(f"Ошибка при анализе текста: {e}")

# 2. Обработка Голосовых (Voice)
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer("🎧 Слушаю и расшифровываю...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    file_id = message.voice.file_id
    file_path = f"voice_{file_id}.ogg" # Временное имя файла

    try:
        # Скачиваем файл с серверов Telegram
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)

        # Отправляем в Whisper для транскрипции
        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        original_text = transcription.text
        
        # Показываем пользователю расшифровку (опционально, но удобно)
        await message.answer(f"📝 **Текст голосового:**\n_{original_text}_", parse_mode="Markdown")

        # Генерируем саммари на основе расшифровки
        await message.answer("⚙️ Анализирую...")
        summary = await generate_summary(original_text)
        await message.answer(summary)

    except Exception as e:
        await message.answer(f"Ошибка с голосовым: {e}")
    
    finally:
        # Удаляем временный файл, чтобы не засорять диск
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())