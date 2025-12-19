import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI
from aiogram.types import FSInputFile

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
    file_path = f"voice_{file_id}.ogg"
    transcript_path = f"transcript_{file_id}.txt" # Имя для текстового файла

    try:
        # Скачиваем файл
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)

        # Отправляем в Whisper
        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        original_text = transcription.text
        
        # --- ЛОГИКА ПРОВЕРКИ ДЛИНЫ ---
        if len(original_text) > 4000:
            # Если текст огромный, сохраняем в файл и отправляем документом
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(original_text)
            
            # Отправка файла
            doc = FSInputFile(transcript_path)
            await message.answer_document(doc, caption="📝 Текст получился длинным, отправляю файлом.")
        else:
            # Если текст влезает, шлем сообщением
            # Убираем parse_mode="Markdown", чтобы спецсимволы в речи не ломали бота
            await message.answer(f"📝 **Текст голосового:**\n\n{original_text}")

        # Генерируем саммари (оно обычно короткое, его можно слать текстом)
        await message.answer("⚙️ Анализирую...")
        summary = await generate_summary(original_text)
        await message.answer(summary)

    except Exception as e:
        await message.answer(f"Ошибка с голосовым: {e}")
    
    finally:
        # Чистим мусор (удаляем и аудио, и текстовый файл, если он был)
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(transcript_path):
            os.remove(transcript_path)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())