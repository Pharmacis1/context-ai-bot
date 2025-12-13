import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# Загружаем секреты
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройка логов (чтобы видеть в консоли, что происходит)
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Системный промпт - это инструкция для ИИ, как себя вести
SYSTEM_PROMPT = """
Ты — опытный Project Manager Assistant. Твоя задача — структурировать входящую информацию.
Тебе пришлют либо переписку из чата, либо заметки со встречи.
Твоя цель — вернуть четкий список Action Items (Задач) и Ключевых Решений.

Формат ответа:
🎯 **Ключевые решения:**
- ...

✅ **Задачи (Action Items):**
- [Исполнитель] Задача (Дедлайн, если есть)
- [Исполнитель] Задача

Если исполнитель не понятен, ставь [?]. Игнорируй флуд и приветствия.
"""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой AI-ассистент. \n\nКидай мне переписку или заметки со встречи, а я превращу их в список задач.")

@dp.message()
async def analyze_text(message: types.Message):
    # Показываем пользователю, что бот "печатает" (думает)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # Дешевая и умная модель
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ]
        )
        result = response.choices[0].message.content
        await message.answer(result)
        
    except Exception as e:
        await message.answer(f"Ой, что-то пошло не так: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())