import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from openai import AsyncOpenAI

from database import init_db, add_message, get_recent_messages

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- NEW: Загружаем белый список ---
# 1. Берем строку из .env
allowed_str = os.getenv("ALLOWED_USERS", "")
# 2. Превращаем "123,456" в список чисел [123, 456]
# (конструкция try-except нужна, чтобы бот не упал, если список пустой)
ALLOWED_USERS = []
try:
    if allowed_str:
        ALLOWED_USERS = [int(x) for x in allowed_str.split(",") if x.strip()]
except ValueError:
    print("⚠️ Ошибка в ALLOWED_USERS. Проверь .env файл (там должны быть только цифры и запятые).")

print(f"🔒 Allowed User IDs: {ALLOWED_USERS}") # Вывод в консоль для проверки

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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

Игнорируй приветствия и флуд.
"""

# --- Хендлеры ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # --- NEW: Проверка доступа ---
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ Access Denied. Бот доступен только авторизованным пользователям.")
        return
    # -----------------------------

    await message.answer(
        "Привет! 👋\n"
        "Я работаю в закрытом режиме.\n"
        "Я сохраняю переписку и делаю саммари по команде /summary."
    )

@dp.message(Command("summary"))
async def cmd_summary(message: types.Message):
    # --- NEW: Проверка доступа ---
    if message.from_user.id not in ALLOWED_USERS:
        return # Просто игнорируем чужаков
    # -----------------------------

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    history = get_recent_messages(chat_id=message.chat.id, limit=50)
    
    if not history:
        await message.answer("📭 В этом чате пока пусто.")
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
    # УБИРАЕМ проверку "if message.from_user.id not in ALLOWED_USERS"
    # Теперь мы сохраняем сообщения ВСЕХ участников чата.
    # Это безопасно, так как это просто текст в локальной базе.

    if message.text.startswith("/"):
        return

    user = message.from_user.first_name or "Unknown"
    
    add_message(
        chat_id=message.chat.id, 
        user_id=message.from_user.id, 
        username=user, 
        text=message.text
    )

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    # --- NEW: Проверка доступа ---
    if message.from_user.id not in ALLOWED_USERS:
        return
    # -----------------------------
    
    file_id = message.voice.file_id
    file_path = f"voice_{file_id}.ogg"

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)

        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        text = transcription.text
        user = message.from_user.first_name
        
        add_message(
            chat_id=message.chat.id,
            user_id=message.from_user.id, 
            username=user, 
            text=f"[Голосовое]: {text}"
        )
        
        await message.react([types.ReactionTypeEmoji(emoji="✍️")])

    except Exception as e:
        await message.answer(f"Ошибка voice: {e}")
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    init_db()
    print("Database initialized!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())