import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from openai import AsyncOpenAI

# Импортируем наши новые функции базы данных
# (убедись, что файл database.py лежит рядом)
from database import init_db, add_message, get_recent_messages

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

# Наш системный промпт
SYSTEM_PROMPT = """
Ты — профессиональный Project Manager Assistant. 
Тебе будет передан лог переписки из группового чата.
Твоя цель — превратить хаос обсуждения в структурированный отчет.

Формат ответа (Markdown):
### 🎯 Summary
(Кратко: о чем шло обсуждение и каков главный итог)

### ✅ Action Items (Задачи)
- [ ] **[Имя]**: Задача (Дедлайн/Срок).
- [ ] **[?]**: Задача (если ответственный не ясен).

### ⚡ Key Decisions (Решения)
- Тезисно зафиксированные договоренности.

### ⚠️ Risks (Риски)
- Проблемы или блокирующие факторы.

Игнорируй приветствия ("Привет", "Ку") и флуд.
"""

# --- Хендлеры (Обработчики) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! 👋\n"
        "Я теперь работаю в режиме наблюдателя.\n"
        "1. Просто общайтесь в чате.\n"
        "2. Я буду молча сохранять историю.\n"
        "3. Напиши /summary, чтобы получить отчет по последним сообщениям."
    )

# НОВАЯ КОМАНДА: Генерация отчета
# ... (начало файла без изменений)

@dp.message(Command("summary"))
async def cmd_summary(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # ПЕРЕДАЕМ message.chat.id, чтобы получить переписку ТОЛЬКО этого чата
    history = get_recent_messages(chat_id=message.chat.id, limit=50)
    
    if not history:
        await message.answer("📭 В этом чате пока пусто. Напишите что-нибудь.")
        return

    chat_log = "\n".join([f"{name}: {text}" for name, text in history])
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Вот переписка:\n{chat_log}"}
            ]
        )
        report = response.choices[0].message.content
        await message.answer(report)
        
    except Exception as e:
        await message.answer(f"Ошибка AI: {e}")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith("/"):
        return

    user = message.from_user.first_name or "Unknown"
    # ПЕРЕДАЕМ message.chat.id при сохранении
    add_message(
        chat_id=message.chat.id, 
        user_id=message.from_user.id, 
        username=user, 
        text=message.text
    )

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    # ... (код скачивания и whisper без изменений) ...
        
        text = transcription.text
        user = message.from_user.first_name
        
        # ПЕРЕДАЕМ message.chat.id при сохранении голосового
        add_message(
            chat_id=message.chat.id,
            user_id=message.from_user.id, 
            username=user, 
            text=f"[Голосовое]: {text}"
        )
        
        await message.react([types.ReactionTypeEmoji(emoji="✍️")])
        
    # ... (остаток функции без изменений)

async def main():
    # ВАЖНО: Инициализируем базу данных при старте
    init_db()
    print("Database initialized!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())