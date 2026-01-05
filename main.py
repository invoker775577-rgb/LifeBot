import telebot
import sqlite3
import threading
import time
import schedule
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
app = Flask('')

@app.route('/')
def home():
    return "Я живой"

def run_flask():
    # Порт 8080 для Render
    app.run(host='0.0.0.0', port=8080)

# --- НАСТРОЙКИ БОТА ---
TOKEN = "8538630326:AAF9z-OU-So_b4YCw3buiAKyFHK3A10aiP8"
bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            birth_date TEXT,
            lifespan INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# --- ГЕНЕРАЦИЯ КАРТИНКИ ---
def create_life_calendar(birth_date_str, lifespan_years):
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.now()
        
        total_weeks = lifespan_years * 52
        weeks_lived = int((today - birth_date).days / 7)
        
        cols, rows = 52, lifespan_years
        box_size, padding, margin = 10, 2, 20
        width = (box_size + padding) * cols + margin * 2
        height = (box_size + padding) * rows + margin * 2 + 50
        
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        for i in range(total_weeks):
            row, col = i // cols, i % cols
            x1 = margin + col * (box_size + padding)
            y1 = margin + row * (box_size + padding)
            x2, y2 = x1 + box_size, y1 + box_size
            
            if i < weeks_lived:
                color = 'black'
            elif i == weeks_lived:
                color = 'red'
            else:
                color = 'lightgray'
            draw.rectangle([x1, y1, x2, y2], fill=color)

        # Текст на русском
        text = f"Прожито: {weeks_lived} нед. | Осталось: {total_weeks - weeks_lived} нед."
        
        try:
            # Путь к шрифту, который мы устанавливаем через Dockerfile
            font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 14)
                draw.text((margin, height - 40), text, fill="black", font=font)
            else:
                draw.text((margin, height - 40), text, fill="black")
        except:
            draw.text((margin, height - 40), text, fill="black")
        
        filename = "calendar.png"
        img.save(filename)
        return filename
    except Exception as e:
        print(f"Ошибка рисования: {e}")
        return None

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой Календарь Жизни.\nВведи дату рождения и сколько лет планируешь прожить.\nПример: /set 2000-01-01 80")

@bot.message_handler(commands=['set'])
def set_user_data(message):
    try:
        parts = message.text.split()
        date_str, lifespan = parts[1], int(parts[2])
        datetime.strptime(date_str, "%Y-%m-%d")
        
        conn = sqlite3.connect('life.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, birth_date, lifespan) VALUES (?, ?, ?)', 
                       (message.chat.id, date_str, lifespan))
        conn.commit()
        conn.close()
        
        img_path = create_life_calendar(date_str, lifespan)
        if img_path:
            with open(img_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="Твой персональный календарь готов!")
    except:
        bot.reply_to(message, "Ошибка! Используй формат: /set ГГГГ-ММ-ДД ВОЗРАСТ")

# --- ПЛАНИРОВЩИК ---
def send_weekly_notifications():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, lifespan FROM users")
    users = cursor.fetchall()
    conn.close()
    
    for user_id, bdate, life in users:
        img_path = create_life_calendar(bdate, life)
        if img_path:
            with open(img_path, 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Началась новая неделя. Твой календарь обновился!")

def run_scheduler():
    schedule.every().monday.at("09:00").do(send_weekly_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- ЗАПУСК ---
if __name__ == '__main__':
    init_db()
    
    # 1. Запуск рассылки
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # 2. Запуск бота
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10), daemon=True).start()
    
    # 3. Запуск Flask
    run_flask()

