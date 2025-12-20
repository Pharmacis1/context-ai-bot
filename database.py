import sqlite3
from datetime import datetime

DB_NAME = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Добавили поле chat_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, 
            user_id INTEGER,
            username TEXT,
            text TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Теперь принимаем chat_id при сохранении
def add_message(chat_id, user_id, username, text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (chat_id, user_id, username, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, user_id, username, text, datetime.now()))
    conn.commit()
    conn.close()

# И фильтруем по chat_id при чтении!
def get_recent_messages(chat_id, limit=20):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, text FROM messages 
        WHERE chat_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (chat_id, limit)) # <-- Вот здесь магия фильтрации
    
    data = cursor.fetchall()
    conn.close()
    return data[::-1]