import sqlite3
from datetime import datetime

DB_NAME = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Таблица сообщений (как была)
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
    
    # 2. НОВАЯ Таблица состояния (закладки)
    # chat_id - уникальный ключ (в одном чате только одна закладка)
    # last_message_id - id последнего сообщения, которое мы уже "отсаммарили"
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summary_state (
            chat_id INTEGER PRIMARY KEY,
            last_message_id INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def add_message(chat_id, user_id, username, text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (chat_id, user_id, username, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, user_id, username, text, datetime.now()))
    conn.commit()
    conn.close()

# НОВАЯ УМНАЯ ФУНКЦИЯ
def get_new_messages(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Узнаем, на чем остановились в прошлый раз
    cursor.execute('SELECT last_message_id FROM summary_state WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    last_read_id = result[0] if result else 0
    
    # 2. Берем только те сообщения, которые НОВЕЕ, чем last_read_id
    cursor.execute('''
        SELECT id, username, text FROM messages 
        WHERE chat_id = ? AND id > ?
        ORDER BY created_at ASC
    ''', (chat_id, last_read_id))
    
    messages = cursor.fetchall()
    conn.close()
    
    return messages

# Функция, чтобы передвинуть закладку вперед
def update_bookmark(chat_id, last_message_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # INSERT OR REPLACE - если записи нет, создаст; если есть - обновит
    cursor.execute('''
        INSERT OR REPLACE INTO summary_state (chat_id, last_message_id)
        VALUES (?, ?)
    ''', (chat_id, last_message_id))
    conn.commit()
    conn.close()